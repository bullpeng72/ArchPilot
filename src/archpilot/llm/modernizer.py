"""현대화 설계 생성기 — LLM 기반 신규 시스템 아키텍처 생성."""

from __future__ import annotations

import json

from archpilot.core.models import AnalysisResult, SystemModel
from archpilot.core.parser import SystemParser
from archpilot.llm.client import LLMError, get_client
from archpilot.llm.prompts import MIGRATION_PLAN_PROMPT, MODERNIZE_SYSTEM_PROMPT

# 각 시스템 페이로드 최대 길이
_MAX_SYSTEM_CHARS = 20_000
# 마이그레이션 플랜은 레거시+현대 두 시스템을 포함하므로 각 절반
_MAX_PLAN_SYSTEM_CHARS = 10_000


def _compress_model(model: SystemModel, max_chars: int = _MAX_SYSTEM_CHARS) -> str:
    """SystemModel을 컨텍스트 길이 제한에 맞게 압축·직렬화한다."""
    payload = model.model_dump_json(indent=2)
    if len(payload) <= max_chars:
        return payload
    compact = model.model_dump_json()
    if len(compact) <= max_chars:
        return compact
    # metadata/specs 제거 후 재직렬화
    d = json.loads(compact)
    for c in d.get("components", []):
        c.pop("metadata", None)
        c.pop("specs", None)
    return json.dumps(d, ensure_ascii=False)


class SystemModernizer:
    def modernize(
        self,
        legacy: SystemModel,
        requirements: str,
        analysis: AnalysisResult | None = None,
    ) -> SystemModel:
        client = get_client()

        analysis_section = ""
        if analysis:
            analysis_section = f"\n\n분석 결과:\n{analysis.model_dump_json(indent=2)}"

        user_message = (
            f"현대화 요구사항:\n{requirements}"
            f"{analysis_section}"
            f"\n\nLegacy 시스템:\n{_compress_model(legacy)}"
        )

        data = client.chat_json(MODERNIZE_SYSTEM_PROMPT, user_message)
        # normalize_connections는 _dict_to_model 내부에서 자동 처리
        try:
            return SystemParser()._dict_to_model(data)
        except Exception as e:
            raise LLMError(f"현대화 시스템 모델 파싱 실패: {e}") from e

    def generate_migration_plan(
        self,
        legacy: SystemModel,
        modern: SystemModel,
        analysis: AnalysisResult | None = None,
        requirements: str = "",
    ) -> str:
        client = get_client()

        # 두 시스템 동시 전달 — 각 절반 크기로 압축
        legacy_payload = _compress_model(legacy, max_chars=_MAX_PLAN_SYSTEM_CHARS)
        modern_payload = _compress_model(modern, max_chars=_MAX_PLAN_SYSTEM_CHARS)

        user_message = (
            f"요구사항: {requirements}\n\n"
            f"레거시 시스템:\n{legacy_payload}\n\n"
            f"현대화 시스템:\n{modern_payload}"
        )
        if analysis:
            user_message += f"\n\n분석 결과:\n{analysis.model_dump_json(indent=2)}"

        return client.chat(
            MIGRATION_PLAN_PROMPT,
            user_message,
            json_mode=False,
            max_tokens=6000,
        )
