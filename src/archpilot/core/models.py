"""핵심 데이터 모델 — 모든 레이어가 공유하는 단일 진실 공급원."""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


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
        valid: list[Connection] = []
        for conn in self.connections:
            if conn.from_id not in ids:
                logger.warning(
                    "Connection 출발지 '%s'가 components에 없어 무시됩니다.", conn.from_id
                )
            elif conn.to_id not in ids:
                logger.warning(
                    "Connection 도착지 '%s'가 components에 없어 무시됩니다.", conn.to_id
                )
            else:
                valid.append(conn)
        self.connections = valid
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


# ── 재귀적 메타 인지 (RMC) 모델 ──────────────────────────────────────────────

class AnalysisRMC(BaseModel):
    """분석 결과에 대한 재귀적 메타 인지 자기평가."""
    coverage_score: int = 75          # 0-100: 분석 커버리지
    assumptions: list[str] = Field(default_factory=list)          # 명시적 근거 없이 가정한 사항
    blind_spots: list[str] = Field(default_factory=list)           # 놓쳤을 가능성이 있는 항목
    verification_questions: list[str] = Field(default_factory=list)# 현장 확인이 필요한 질문
    confidence_level: str = "medium"  # high | medium | low
    confidence_rationale: str = ""


class DesignDecision(BaseModel):
    """개별 아키텍처 설계 결정 항목."""
    area: str                                                       # 결정 영역 (예: 인증, 데이터 레이어)
    decision: str                                                   # 구체적 설계 선택
    rationale: str                                                  # 선택 이유 (기술적 + 비즈니스 근거)
    alternatives_rejected: list[str] = Field(default_factory=list) # 고려했지만 기각한 대안
    tradeoffs: list[str] = Field(default_factory=list)             # 수용한 트레이드오프


class RMCSelfEval(BaseModel):
    """현대화 설계에 대한 재귀적 메타 인지 자기평가."""
    completeness_score: int = 75  # 0-100: 레거시 기능 커버리지
    coverage_gaps: list[str] = Field(default_factory=list)         # 충분히 다루지 못한 영역
    design_risks: list[str] = Field(default_factory=list)          # 잠재적 설계 위험
    improvement_suggestions: list[str] = Field(default_factory=list)# 개선 제안
    confidence_level: str = "medium"  # high | medium | low


class ArchQualityScore(BaseModel):
    """SW 아키텍처 품질 평가 — 현대화 설계 결과 기준 (0-100점)."""
    # 핵심 품질 속성
    maintainability: int = 75   # 유지보수성
    performance: int = 75       # 성능
    scalability: int = 75       # 확장성
    reliability: int = 75       # 신뢰성
    security: int = 75          # 보안성
    # 아키텍처 구조적 요소
    simplicity: int = 75        # 단순성
    modularity: int = 75        # 모듈화 (낮은 결합도·높은 응집도)
    understandability: int = 75 # 이해 가능성
    flexibility: int = 75       # 유연성·재사용성
    # 평가·검증 요소
    testability: int = 75       # 테스트 가능성
    risk_management: int = 75   # 위험 요소 조기 발견 능력
    nfr_compliance: int = 75    # 비기능적 요구사항(성능·가용성·용량) 준수
    # 종합
    overall_score: int = 75
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improvement_recommendations: list[str] = Field(default_factory=list)
    business_tradeoff_summary: str = ""  # 비즈니스 목표·제약(비용·일정)과의 타협점 요약


class MigrationPlanRMC(BaseModel):
    """마이그레이션 계획에 대한 재귀적 메타 인지 자기평가."""
    completeness_score: int = 75
    well_covered_phases: list[str] = Field(default_factory=list)
    missing_aspects: list[str] = Field(default_factory=list)
    risk_blind_spots: list[str] = Field(default_factory=list)
    dependency_gaps: list[str] = Field(default_factory=list)
    rollback_adequacy: str = ""
    timeline_realism: str = ""
    improvement_suggestions: list[str] = Field(default_factory=list)
    confidence_level: str = "medium"  # high | medium | low


class DesignRationale(BaseModel):
    """현대화 설계 해설 — 왜 이런 설계를 했는가."""
    design_philosophy: str = ""
    key_decisions: list[DesignDecision] = Field(default_factory=list)
    arch_quality_eval: ArchQualityScore = Field(default_factory=ArchQualityScore)
    rmc_self_eval: RMCSelfEval = Field(default_factory=RMCSelfEval)


# ── 분석 결과 모델 ────────────────────────────────────────────────────────────

class ModernizationAction(str, Enum):
    """컴포넌트별 현대화 전략 (6R)."""
    KEEP        = "keep"        # 변경 없이 유지
    REHOST      = "rehost"      # Lift & Shift — 코드 변경 없이 클라우드 이전
    REPLATFORM  = "replatform"  # 최소 수정으로 플랫폼 전환 (앱서버 → 컨테이너 등)
    REFACTOR    = "refactor"    # 서비스 분리·재설계 (Refactor / Re-architect)
    REPLACE     = "replace"     # SaaS / 매니지드 서비스로 대체
    RETIRE      = "retire"      # 폐기


class ModernizationScenario(str, Enum):
    """현대화 시나리오 유형."""
    FULL_REPLACE = "full_replace"  # (1) 전체 교체 — 대부분의 컴포넌트를 새로 설계
    PARTIAL      = "partial"       # (2) 일부 보존 + 수정 + 신규 — 핵심은 유지, 주변부 현대화
    ADDITIVE     = "additive"      # (3) 대부분 보존 + 신규 추가 — 기존 유지, 기능 확장


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


class ComponentDecision(BaseModel):
    """컴포넌트별 현대화 전략 결정."""
    component_id: str
    action: ModernizationAction
    rationale: str = ""
    target_component_id: str | None = None  # Replace/Refactor 시 대상 컴포넌트 id
    risks: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)  # 먼저 처리해야 할 component_id


class QualityDimension(BaseModel):
    """아키텍처 품질 단일 차원."""
    score: int = 50     # 0(최악) ~ 100(최상)
    rationale: str = ""

    @model_validator(mode="before")
    @classmethod
    def _accept_int(cls, data: object) -> object:
        """LLM이 정수(예: 55)를 직접 반환할 때 자동으로 {"score": 55}로 변환."""
        if isinstance(data, (int, float)):
            return {"score": int(data)}
        return data


class ArchitectureQuality(BaseModel):
    """5차원 아키텍처 품질 모델."""
    performance:  QualityDimension = Field(default_factory=QualityDimension)
    scalability:  QualityDimension = Field(default_factory=QualityDimension)
    cost:         QualityDimension = Field(default_factory=QualityDimension)
    security:     QualityDimension = Field(default_factory=QualityDimension)
    operability:  QualityDimension = Field(default_factory=QualityDimension)


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

    # ── 시나리오 & 컴포넌트 결정 ──────────────────────────────────────────────
    recommended_scenario: ModernizationScenario = ModernizationScenario.FULL_REPLACE
    scenario_rationale: str = ""
    component_decisions: list[ComponentDecision] = Field(default_factory=list)
    legacy_quality: ArchitectureQuality = Field(default_factory=ArchitectureQuality)

    # ── 재귀적 메타 인지 자기평가 ────────────────────────────────────────────
    rmc_evaluation: AnalysisRMC | None = None


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

    # ── 시나리오 & 품질 델타 (Phase 1 신규) ──────────────────────────────────
    inferred_scenario: ModernizationScenario | None = None
    modern_quality: ArchitectureQuality | None = None
