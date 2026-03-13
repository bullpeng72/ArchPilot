"""레거시 시스템 분석기 — LLM 기반 분석 보고서 생성."""

from __future__ import annotations

import json

from archpilot.core.models import AnalysisResult, SystemModel
from archpilot.llm.client import LLMError, get_client
from archpilot.llm.prompts import ANALYZE_SYSTEM_PROMPT


# 분석 프롬프트에 포함할 시스템 JSON 최대 길이 (대략 컴포넌트 ~60개 수준)
_MAX_PAYLOAD_CHARS = 24_000


class SystemAnalyzer:
    def analyze(self, model: SystemModel) -> AnalysisResult:
        client = get_client()
        payload = model.model_dump_json(indent=2)

        # 대형 시스템에서 컨텍스트 초과 방지: metadata 등 비핵심 필드 압축
        if len(payload) > _MAX_PAYLOAD_CHARS:
            compact = model.model_dump_json()        # indent 제거만으로도 ~30% 절감
            if len(compact) > _MAX_PAYLOAD_CHARS:
                # 컴포넌트 metadata 제거 후 재직렬화
                import json as _json
                d = _json.loads(compact)
                for c in d.get("components", []):
                    c.pop("metadata", None)
                    c.pop("specs", None)
                compact = _json.dumps(d, ensure_ascii=False)
            payload = compact

        data = client.chat_json(ANALYZE_SYSTEM_PROMPT, f"분석할 시스템:\n{payload}")

        try:
            return AnalysisResult.model_validate(data)
        except Exception as e:
            raise LLMError(f"분석 결과 파싱 실패: {e}\n응답: {json.dumps(data)[:300]}") from e
