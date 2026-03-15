"""레거시 시스템 분석기 — LLM 기반 분석 보고서 생성."""

from __future__ import annotations

import json

from archpilot.core.models import AnalysisResult, SystemModel
from archpilot.llm.client import LLMError, get_client
from archpilot.llm.prompts import ANALYZE_SYSTEM_PROMPT
from archpilot.llm.utils import MAX_ANALYZE_TOKENS, MAX_PAYLOAD_CHARS, compress_model


class SystemAnalyzer:
    def analyze(self, model: SystemModel, requirements: str = "") -> AnalysisResult:
        client = get_client()
        payload = compress_model(model, MAX_PAYLOAD_CHARS)
        req_section = (
            f"\n\n현대화 목표 (component_decisions 수립 시 반드시 반영):\n{requirements}"
            if requirements else ""
        )
        data = client.chat_json(
            ANALYZE_SYSTEM_PROMPT,
            f"분석할 시스템:\n{payload}{req_section}",
            max_tokens=MAX_ANALYZE_TOKENS,
        )

        try:
            return AnalysisResult.model_validate(data)
        except Exception as e:
            raise LLMError(f"분석 결과 파싱 실패: {e}\n응답: {json.dumps(data)[:300]}") from e
