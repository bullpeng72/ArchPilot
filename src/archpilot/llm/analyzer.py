"""레거시 시스템 분석기 — LLM 기반 분석 보고서 생성."""

from __future__ import annotations

import json

from archpilot.core.models import AnalysisResult, SystemModel
from archpilot.llm.client import LLMError, get_client
from archpilot.llm.prompts import ANALYZE_SYSTEM_PROMPT


class SystemAnalyzer:
    def analyze(self, model: SystemModel) -> AnalysisResult:
        client = get_client()
        payload = model.model_dump_json(indent=2)
        data = client.chat_json(ANALYZE_SYSTEM_PROMPT, f"분석할 시스템:\n{payload}")

        try:
            return AnalysisResult.model_validate(data)
        except Exception as e:
            raise LLMError(f"분석 결과 파싱 실패: {e}\n응답: {json.dumps(data)[:300]}") from e
