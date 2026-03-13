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
        }


# 모듈 수준 싱글턴
_session = AppSession()


def get() -> AppSession:
    return _session


def reset() -> None:
    global _session
    _session = AppSession()
