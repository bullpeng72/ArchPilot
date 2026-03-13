"""자연어 텍스트 → SystemModel LLM 파서."""

from __future__ import annotations

from archpilot.core.models import SystemModel
from archpilot.core.parser import SystemParser
from archpilot.llm.client import get_client
from archpilot.llm.prompts import PARSE_SYSTEM_PROMPT


class LLMParser:
    def from_text(self, description: str) -> SystemModel:
        client = get_client()
        data = client.chat_json(PARSE_SYSTEM_PROMPT, description)
        # connections의 from/to 키를 parser가 인식할 수 있도록 정규화
        for conn in data.get("connections", []):
            if "from" in conn and "from_id" not in conn:
                conn["from_id"] = conn.pop("from")
            if "to" in conn and "to_id" not in conn:
                conn["to_id"] = conn.pop("to")
        return SystemParser()._dict_to_model(data)
