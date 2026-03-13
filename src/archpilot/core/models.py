"""핵심 데이터 모델 — 모든 레이어가 공유하는 단일 진실 공급원."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ComponentType(str, Enum):
    SERVER = "server"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    STORAGE = "storage"
    CDN = "cdn"
    LOADBALANCER = "loadbalancer"
    GATEWAY = "gateway"
    SERVICE = "service"
    CLIENT = "client"
    UNKNOWN = "unknown"


class HostType(str, Enum):
    ON_PREMISE = "on-premise"
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    HYBRID = "hybrid"


class Component(BaseModel):
    id: str
    type: ComponentType
    label: str
    tech: list[str] = Field(default_factory=list)
    host: HostType = HostType.ON_PREMISE
    specs: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_new(self) -> bool:
        return bool(self.metadata.get("is_new"))

    @property
    def is_removed(self) -> bool:
        return bool(self.metadata.get("removed"))

    @property
    def change_reason(self) -> str:
        return self.metadata.get("reason", "")


class Connection(BaseModel):
    from_id: str
    to_id: str
    protocol: str = "HTTP"
    label: str = ""
    bidirectional: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class SystemModel(BaseModel):
    name: str
    description: str = ""
    version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    components: list[Component]
    connections: list[Connection] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_connections(self) -> SystemModel:
        ids = {c.id for c in self.components}
        for conn in self.connections:
            if conn.from_id not in ids:
                raise ValueError(
                    f"Connection 출발지 '{conn.from_id}'가 components에 존재하지 않습니다."
                )
            if conn.to_id not in ids:
                raise ValueError(
                    f"Connection 도착지 '{conn.to_id}'가 components에 존재하지 않습니다."
                )
        return self

    @model_validator(mode="after")
    def _validate_unique_ids(self) -> SystemModel:
        ids = [c.id for c in self.components]
        seen: set[str] = set()
        for cid in ids:
            if cid in seen:
                raise ValueError(f"Component id '{cid}'가 중복됩니다.")
            seen.add(cid)
        return self

    def get_component(self, component_id: str) -> Component | None:
        return next((c for c in self.components if c.id == component_id), None)

    def components_by_host(self) -> dict[str, list[Component]]:
        groups: dict[str, list[Component]] = {}
        for c in self.components:
            groups.setdefault(c.host.value, []).append(c)
        return groups


# ── 분석 결과 모델 ────────────────────────────────────────────────────────────

class EffortLevel(str, Enum):
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"


class TechDebtItem(BaseModel):
    component_id: str
    description: str
    severity: str = "medium"  # low | medium | high


class RiskArea(BaseModel):
    component_id: str
    risk: str
    mitigation: str = ""


class Opportunity(BaseModel):
    area: str
    description: str
    priority: int = 1  # 1(높음) ~ 3(낮음)


class AnalysisResult(BaseModel):
    system_name: str
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    pain_points: list[str] = Field(default_factory=list)
    tech_debt: list[TechDebtItem] = Field(default_factory=list)
    risk_areas: list[RiskArea] = Field(default_factory=list)
    modernization_opportunities: list[Opportunity] = Field(default_factory=list)
    recommended_patterns: list[str] = Field(default_factory=list)
    estimated_effort: EffortLevel = EffortLevel.M
    summary: str = ""


# ── Diff 모델 ─────────────────────────────────────────────────────────────────

class ComponentChange(BaseModel):
    before: Component
    after: Component
    changed_fields: list[str] = Field(default_factory=list)


class ConnectionChange(BaseModel):
    change_type: str  # added | removed | modified
    connection: Connection


class DiffResult(BaseModel):
    added: list[Component] = Field(default_factory=list)
    removed: list[Component] = Field(default_factory=list)
    modified: list[ComponentChange] = Field(default_factory=list)
    unchanged: list[Component] = Field(default_factory=list)
    connection_changes: list[ConnectionChange] = Field(default_factory=list)
