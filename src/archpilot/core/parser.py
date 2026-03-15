"""Legacy 시스템 파일 파서 — YAML/JSON/텍스트 → SystemModel."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

import yaml

_ET = TypeVar("_ET")


def _parse_enum(raw: str, cls: type[_ET], default: _ET) -> _ET:
    """문자열 값을 Enum으로 변환. 실패 시 default 반환."""
    try:
        return cls(raw.lower())  # type: ignore[call-arg]
    except (ValueError, KeyError):
        return default

from archpilot.core.models import (
    Component,
    ComponentType,
    Connection,
    Criticality,
    DataClassification,
    HostType,
    LifecycleStatus,
    SystemModel,
)


class ParseError(Exception):
    """파싱 실패 시 발생."""


def normalize_connections(data: dict) -> None:
    """LLM/외부 입력의 connections 키를 parser 규격으로 정규화 (in-place).

    'from'/'to' → 'from_id'/'to_id' 로 통일.
    _parse_connection이 양쪽을 모두 수용하지만, 미리 정규화하면
    YAML 덤프·직렬화 결과도 일관성 있는 스키마를 유지한다.
    """
    for conn in data.get("connections", []):
        if "from" in conn and "from_id" not in conn:
            conn["from_id"] = conn.pop("from")
        if "to" in conn and "to_id" not in conn:
            conn["to_id"] = conn.pop("to")


class SystemParser:
    """파일 경로를 받아 SystemModel을 반환하는 파서."""

    def from_file(self, path: Path, use_llm: bool = True) -> SystemModel:
        if not path.exists():
            raise ParseError(f"파일을 찾을 수 없습니다: {path}")

        suffix = path.suffix.lower()
        raw = path.read_text(encoding="utf-8")

        if suffix in (".yaml", ".yml"):
            return self._from_yaml(raw, path)
        elif suffix == ".json":
            return self._from_json(raw, path)
        elif suffix == ".txt":
            if use_llm:
                return self.from_text(raw)
            raise ParseError(".txt 파일은 --no-llm 옵션과 함께 사용할 수 없습니다.")
        else:
            raise ParseError(f"지원하지 않는 파일 형식: {suffix} (yaml/json/txt만 지원)")

    def _from_yaml(self, raw: str, path: Path) -> SystemModel:
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as e:
            raise ParseError(f"YAML 파싱 오류 [{path}]: {e}") from e
        return self._dict_to_model(data)

    def _from_json(self, raw: str, path: Path) -> SystemModel:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ParseError(f"JSON 파싱 오류 [{path}:{e.lineno}]: {e.msg}") from e
        return self._dict_to_model(data)

    def from_text(self, description: str) -> SystemModel:
        """자연어 텍스트 → LLM 파싱 → SystemModel."""
        from archpilot.llm.parser_agent import LLMParser

        return LLMParser().from_text(description)

    # SystemModel 이 직접 처리하는 최상위 필드
    _SYSTEM_KNOWN = {"name", "description", "version", "components", "connections", "metadata"}

    def _dict_to_model(self, data: Any) -> SystemModel:
        if not isinstance(data, dict):
            raise ParseError("최상위 데이터는 dict(매핑) 형식이어야 합니다.")
        if "name" not in data:
            raise ParseError("'name' 필드가 필요합니다.")
        if not data.get("components"):
            raise ParseError("'components' 목록이 비어있거나 없습니다.")
        normalize_connections(data)

        from archpilot.core.tech_ontology import enrich_component  # noqa: PLC0415
        raw_comps = [enrich_component(dict(c)) for c in data["components"]]
        components = [self._parse_component(c) for c in raw_comps]
        connections = [self._parse_connection(c) for c in data.get("connections", [])]

        # LLM 생성 모델에서 존재하지 않는 컴포넌트를 참조하는 connection을 제거
        valid_ids = {c.id for c in components}
        filtered: list[Connection] = []
        dropped_conn_refs: list[str] = []
        for conn in connections:
            if conn.from_id not in valid_ids or conn.to_id not in valid_ids:
                ref = f"{conn.from_id}→{conn.to_id}"
                logger.warning("connection 무시 (존재하지 않는 컴포넌트 참조): %s → %s", conn.from_id, conn.to_id)
                dropped_conn_refs.append(ref)
            else:
                filtered.append(conn)
        connections = filtered

        # domain / vintage / scale / compliance / known_issues 등
        # 표준 스키마에 없는 최상위 키를 metadata에 병합
        extra = {k: v for k, v in data.items() if k not in self._SYSTEM_KNOWN}
        metadata = {**data.get("metadata", {}), **extra}
        if dropped_conn_refs:
            metadata["_dropped_connections"] = dropped_conn_refs

        return SystemModel(
            name=data["name"],
            description=data.get("description", ""),
            version=str(data.get("version", "1.0")),
            components=components,
            connections=connections,
            metadata=metadata,
        )

    # Component 가 직접 처리하는 필드
    _COMP_KNOWN = {
        "id", "type", "label", "tech", "host",
        "criticality", "lifecycle_status", "data_classification", "owner",
        "specs", "metadata",
    }

    def _parse_component(self, raw: dict) -> Component:
        required = ("id", "type", "label")
        for field in required:
            if field not in raw:
                raise ParseError(f"component에 '{field}' 필드가 필요합니다: {raw}")

        ctype = _parse_enum(raw["type"], ComponentType, ComponentType.UNKNOWN)
        host = _parse_enum(raw.get("host", "on-premise"), HostType, HostType.ON_PREMISE)
        criticality = (
            _parse_enum(str(raw["criticality"]), Criticality, Criticality.MEDIUM)
            if raw.get("criticality") else Criticality.MEDIUM
        )
        lifecycle_status = (
            _parse_enum(str(raw["lifecycle_status"]), LifecycleStatus, LifecycleStatus.ACTIVE)
            if raw.get("lifecycle_status") else LifecycleStatus.ACTIVE
        )
        data_classification: DataClassification | None = None
        if raw.get("data_classification"):
            try:
                data_classification = DataClassification(str(raw["data_classification"]).lower())
            except ValueError:
                pass

        owner: str = raw.get("owner", "") or ""

        # 나머지 비표준 필드(vintage, notes 등)를 metadata에 병합
        extra = {k: v for k, v in raw.items() if k not in self._COMP_KNOWN}
        metadata = {**raw.get("metadata", {}), **extra}

        return Component(
            id=raw["id"],
            type=ctype,
            label=raw["label"],
            tech=raw.get("tech", []),
            host=host,
            criticality=criticality,
            lifecycle_status=lifecycle_status,
            data_classification=data_classification,
            owner=owner,
            specs=raw.get("specs", {}),
            metadata=metadata,
        )

    # Connection 이 직접 처리하는 필드
    _CONN_KNOWN = {
        "from", "from_id", "to", "to_id",
        "protocol", "label", "bidirectional",
        "data_format", "api_version", "metadata",
    }

    def _parse_connection(self, raw: dict) -> Connection:
        from_id = raw.get("from") or raw.get("from_id")
        to_id = raw.get("to") or raw.get("to_id")
        if not from_id or not to_id:
            raise ParseError(f"connection에 'from'과 'to' 필드가 필요합니다: {raw}")
        return Connection(
            from_id=from_id,
            to_id=to_id,
            protocol=raw.get("protocol", "HTTP"),
            label=raw.get("label", ""),
            bidirectional=raw.get("bidirectional", False),
            data_format=raw.get("data_format", "") or "",
            api_version=raw.get("api_version", "") or "",
            metadata=raw.get("metadata", {}),
        )
