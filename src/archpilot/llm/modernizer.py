"""현대화 설계 생성기 — LLM 기반 신규 시스템 아키텍처 생성."""

from __future__ import annotations

import json

from archpilot.core.models import AnalysisResult, SystemModel
from archpilot.core.parser import SystemParser
from archpilot.llm.client import LLMError, get_client
from archpilot.llm.prompts import MIGRATION_PLAN_PROMPT, MODERNIZE_SYSTEM_PROMPT


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
            f"\n\nLegacy 시스템:\n{legacy.model_dump_json(indent=2)}"
        )

        data = client.chat_json(MODERNIZE_SYSTEM_PROMPT, user_message)

        # connections의 from/to 키 정규화
        for conn in data.get("connections", []):
            if "from" in conn and "from_id" not in conn:
                conn["from_id"] = conn.pop("from")
            if "to" in conn and "to_id" not in conn:
                conn["to_id"] = conn.pop("to")

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

        user_message = (
            f"요구사항: {requirements}\n\n"
            f"레거시 시스템:\n{legacy.model_dump_json(indent=2)}\n\n"
            f"현대화 시스템:\n{modern.model_dump_json(indent=2)}"
        )
        if analysis:
            user_message += f"\n\n분석 결과:\n{analysis.model_dump_json(indent=2)}"

        return client.chat(
            MIGRATION_PLAN_PROMPT,
            user_message,
            json_mode=False,
            max_tokens=4096,
        )
