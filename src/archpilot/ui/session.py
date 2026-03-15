"""서버 인메모리 세션 상태 — 단일 사용자 로컬 도구 전용."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppSession:
    # 파싱된 시스템 모델 (JSON-serializable dict)
    system: dict[str, Any] | None = None
    analysis: dict[str, Any] | None = None
    modern: dict[str, Any] | None = None

    # 다이어그램 DSL 문자열
    legacy_mmd: str = ""
    legacy_drawio: str = ""
    modern_mmd: str = ""
    modern_drawio: str = ""

    # 현대화 입력 & 결과
    requirements: str = ""
    migration_plan: str = ""

    # 현대화 시나리오 (full_replace | partial | additive | None)
    scenario: str | None = None

    # 재귀적 메타 인지 (RMC) 결과
    analysis_rmc: dict[str, Any] | None = None       # AnalysisRMC
    design_rationale: dict[str, Any] | None = None   # DesignRationale
    migration_plan_rmc: dict[str, Any] | None = None # MigrationPlanRMC

    def reset_modernization(self) -> None:
        """새 시스템 주입 시 이전 분석·현대화 결과를 모두 초기화한다."""
        self.analysis = None
        self.modern = None
        self.modern_mmd = ""
        self.modern_drawio = ""
        self.migration_plan = ""
        self.scenario = None
        self.analysis_rmc = None
        self.design_rationale = None
        self.migration_plan_rmc = None

    @property
    def step(self) -> int:
        """현재 완료된 최대 단계."""
        if self.modern:
            return 4
        if self.analysis:
            return 3
        if self.system:
            return 1
        return 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "system": self.system,
            "analysis": self.analysis,
            "modern": self.modern,
            "legacy_mmd": self.legacy_mmd,
            "legacy_drawio": self.legacy_drawio,
            "modern_mmd": self.modern_mmd,
            "modern_drawio": self.modern_drawio,
            "requirements": self.requirements,
            "migration_plan": self.migration_plan,
            "scenario": self.scenario,
            "analysis_rmc": self.analysis_rmc,
            "design_rationale": self.design_rationale,
            "migration_plan_rmc": self.migration_plan_rmc,
        }


# ── 단일 사용자 전용 싱글턴 ────────────────────────────────────────────────────
# ArchPilot 서버는 로컬 단일 사용자 도구입니다.
# 동시 접속 시 세션 상태가 충돌합니다.
# 멀티 사용자 지원이 필요하면 dict[session_id, AppSession] 구조로 전환하세요.
_session = AppSession()


def get() -> AppSession:
    return _session


def reset() -> None:
    global _session
    _session = AppSession()
