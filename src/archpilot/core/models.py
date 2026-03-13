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
    MAINFRAME = "mainframe"   # 메인프레임 / COBOL 배치 시스템
    ESB = "esb"               # Enterprise Service Bus / 통합 미들웨어
    SECURITY = "security"     # HSM, WAF, IAM, Firewall 등 보안 장비
    MONITORING = "monitoring" # APM, 로그 수집, 알람 시스템
    UNKNOWN = "unknown"


class HostType(str, Enum):
    ON_PREMISE = "on-premise"
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    HYBRID = "hybrid"


class LifecycleStatus(str, Enum):
    """컴포넌트의 운영 생명주기 상태."""
    ACTIVE = "active"                   # 정상 운영 중
    DEPRECATED = "deprecated"           # 지원 중단 예고 (벤더 공지)
    EOL = "eol"                         # End of Life — 벤더 지원 완전 만료
    SUNSET = "sunset"                   # 내부 서비스 종료 예정 (이전 진행 중)
    DECOMMISSIONED = "decommissioned"   # 폐기 완료 (레퍼런스용)


class Criticality(str, Enum):
    """비즈니스 연속성 관점의 컴포넌트 중요도."""
    HIGH = "high"       # 장애 시 매출·규제 직접 영향 (결제, 인증, 핵심 DB)
    MEDIUM = "medium"   # 장애 시 일부 기능 저하
    LOW = "low"         # 장애 시 비즈니스 영향 미미 (모니터링, 로깅)


class DataClassification(str, Enum):
    """컴포넌트가 처리하는 데이터의 민감도 분류."""
    PUBLIC = "public"               # 공개 데이터
    INTERNAL = "internal"           # 내부용 (임직원 접근)
    CONFIDENTIAL = "confidential"   # 기밀 (인가된 직원만)
    RESTRICTED = "restricted"       # 제한 (PII·금융정보·의료정보)


class Component(BaseModel):
    id: str
    type: ComponentType
    label: str
    tech: list[str] = Field(default_factory=list)
    host: HostType = HostType.ON_PREMISE

    # ── 엔터프라이즈 필드 ─────────────────────────────────────────────────────
    criticality: Criticality = Criticality.MEDIUM
    lifecycle_status: LifecycleStatus = LifecycleStatus.ACTIVE
    data_classification: DataClassification | None = None
    owner: str = ""             # 담당팀 또는 담당자 (예: "결제플랫폼팀")

    specs: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_eol(self) -> bool:
        return self.lifecycle_status in (LifecycleStatus.EOL, LifecycleStatus.DEPRECATED)

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
    data_format: str = ""   # JSON, XML, Protobuf, Fixed-Width, EDIFACT, CSV 등
    api_version: str = ""   # REST v2, SOAP 1.1, gRPC proto3 등
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

    def eol_components(self) -> list[Component]:
        """EOL/Deprecated 컴포넌트 목록."""
        return [c for c in self.components if c.is_eol]

    def high_criticality_components(self) -> list[Component]:
        """HIGH 중요도 컴포넌트 목록."""
        return [c for c in self.components if c.criticality == Criticality.HIGH]


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
    health_score: int = 75          # 0(위험) ~ 100(건강): EOL·HIGH criticality·보안·컴플라이언스 종합
    pain_points: list[str] = Field(default_factory=list)
    tech_debt: list[TechDebtItem] = Field(default_factory=list)
    risk_areas: list[RiskArea] = Field(default_factory=list)
    modernization_opportunities: list[Opportunity] = Field(default_factory=list)
    compliance_gaps: list[str] = Field(default_factory=list)    # 규제·컴플라이언스 준수 갭
    security_findings: list[str] = Field(default_factory=list)  # 보안 취약점·위험 목록
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
