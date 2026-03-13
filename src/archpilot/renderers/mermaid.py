"""Mermaid DSL 렌더러."""

from __future__ import annotations

import re
from typing import ClassVar

from archpilot.core.models import (
    ComponentType, Criticality, LifecycleStatus, SystemModel,
)
from archpilot.renderers.base import BaseRenderer


def _safe_mmd_id(raw: str) -> str:
    """Mermaid 노드 ID에서 허용되지 않는 문자를 언더스코어로 치환."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", raw) or "node"


# ComponentType → Mermaid 노드 모양 (open, close)
# 주의: [/ /] 와 [\ \] 는 레이블에 HTML(<br>, </tag> 등)이 포함될 때
#       / 와 \ 구분자를 파서가 잘못 인식해 "Syntax error" 발생.
#       HTML 레이블과 충돌하지 않는 모양만 사용.
SHAPE_MAP: dict[ComponentType, tuple[str, str]] = {
    ComponentType.SERVER:       ("[", "]"),
    ComponentType.DATABASE:     ("[(", ")]"),
    ComponentType.CACHE:        ("((", "))"),
    ComponentType.QUEUE:        ("([", "])"),
    ComponentType.STORAGE:      ("[(", ")]"),
    ComponentType.LOADBALANCER: ("{", "}"),
    ComponentType.GATEWAY:      ("([", "])"),
    ComponentType.SERVICE:      ("[", "]"),
    ComponentType.CDN:          ("((", "))"),
    ComponentType.CLIENT:       ("(", ")"),
    ComponentType.MAINFRAME:    ("[", "]"),
    ComponentType.ESB:          ("([", "])"),
    ComponentType.SECURITY:     ("{", "}"),
    ComponentType.MONITORING:   ("(", ")"),
    ComponentType.UNKNOWN:      ("[", "]"),
}

HOST_LABELS: dict[str, str] = {
    "on-premise": "On-Premise",
    "aws":        "AWS Cloud",
    "gcp":        "GCP Cloud",
    "azure":      "Azure Cloud",
    "hybrid":     "Hybrid",
}

# 프로토콜 키워드 → 화살표 스타일 구분
_LEGACY_PROTO_KEYWORDS  = ("SOAP", "FTP", "CICS", "SNA", "MQ", "CTG", "SFTP")
_ASYNC_PROTO_KEYWORDS   = ("AMQP", "KAFKA", "SQS", "PUBSUB", "EVENTBRIDGE")


def _build_label(c: "SystemModel.components[0]") -> str:  # type: ignore[name-defined]
    """노드 레이블 조합: 이름 + 기술스택 + 상태 배지."""
    parts: list[str] = [c.label]

    if c.tech:
        parts.append("<br>".join(c.tech))

    if c.lifecycle_status == LifecycleStatus.EOL:
        parts.append("⚠ EOL")
    elif c.lifecycle_status == LifecycleStatus.DEPRECATED:
        parts.append("⚠ Deprecated")
    elif c.lifecycle_status == LifecycleStatus.SUNSET:
        parts.append("↓ Sunset")

    if c.criticality == Criticality.HIGH:
        parts.append("🔴 HIGH")

    if c.data_classification is not None:
        dc = c.data_classification.value.upper()
        if dc in ("RESTRICTED", "CONFIDENTIAL"):
            parts.append(f"🔒 {dc}")

    return "<br>".join(parts).replace('"', "'")


class MermaidRenderer(BaseRenderer):
    name: ClassVar[str] = "mermaid"
    output_ext: ClassVar[str] = ".mmd"

    def render(self, model: SystemModel) -> str:
        lines: list[str] = ["flowchart LR", ""]

        id_map = {c.id: _safe_mmd_id(c.id) for c in model.components}
        groups = model.components_by_host()

        for host, components in groups.items():
            group_label = HOST_LABELS.get(host, host)
            safe_host = re.sub(r"[^a-zA-Z0-9_]", "_", host)
            lines.append(f'  subgraph {safe_host}["{group_label}"]')

            for c in components:
                open_b, close_b = SHAPE_MAP.get(c.type, ("[", "]"))
                label = _build_label(c)
                lines.append(f'    {id_map[c.id]}{open_b}"{label}"{close_b}')

            lines.append("  end")
            lines.append("")

        # 연결선 — 프로토콜 유형에 따라 스타일 분기
        for conn in model.connections:
            from_id = id_map.get(conn.from_id, _safe_mmd_id(conn.from_id))
            to_id   = id_map.get(conn.to_id,   _safe_mmd_id(conn.to_id))

            edge_label = conn.label or (conn.protocol if conn.protocol != "HTTP" else "")
            if conn.data_format:
                edge_label = f"{edge_label} [{conn.data_format}]".strip()

            proto_upper = conn.protocol.upper()
            is_legacy = any(k in proto_upper for k in _LEGACY_PROTO_KEYWORDS)
            is_async  = any(k in proto_upper for k in _ASYNC_PROTO_KEYWORDS)

            if edge_label:
                if is_legacy:
                    arrow = f'-. "{edge_label}" .->'   # 점선 — 레거시/동기 프로토콜
                elif is_async:
                    arrow = f'== "{edge_label}" ==>'   # 굵은선 — 비동기 메시징
                else:
                    arrow = f'-- "{edge_label}" -->'
            else:
                if is_legacy:
                    arrow = "-..->"
                elif is_async:
                    arrow = "==>"
                else:
                    arrow = "-->"

            lines.append(f"  {from_id} {arrow} {to_id}")

            if conn.bidirectional:
                lines.append(f"  {to_id} --> {from_id}")

        # EOL / Deprecated / HIGH criticality 노드 색상 강조
        eol_ids  = [id_map[c.id] for c in model.components
                    if c.lifecycle_status == LifecycleStatus.EOL]
        dep_ids  = [id_map[c.id] for c in model.components
                    if c.lifecycle_status == LifecycleStatus.DEPRECATED]
        high_ids = [id_map[c.id] for c in model.components
                    if c.criticality == Criticality.HIGH]

        if eol_ids or dep_ids or high_ids:
            lines.append("")
            lines.append("  %% 상태·중요도 스타일")
            for nid in eol_ids:
                lines.append(f"  style {nid} fill:#ff9999,stroke:#cc0000,color:#000")
            for nid in dep_ids:
                lines.append(f"  style {nid} fill:#ffcc99,stroke:#e68a00,color:#000")
            for nid in high_ids:
                if nid not in eol_ids:  # EOL 스타일과 중복 방지
                    lines.append(f"  style {nid} stroke:#cc0000,stroke-width:3px")

        return "\n".join(lines)
