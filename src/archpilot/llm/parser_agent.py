"""자연어 텍스트 → SystemModel LLM 파서."""

from __future__ import annotations

from archpilot.core.models import SystemModel
from archpilot.core.parser import ParseError, SystemParser
from archpilot.llm.client import LLMError, get_client
from archpilot.llm.prompts import PARSE_SYSTEM_PROMPT

_MAX_RETRIES = 3


class LLMParser:
    def from_text(self, description: str) -> SystemModel:
        """자연어 설명을 SystemModel로 변환한다.

        파싱·검증 실패 시 오류 내용을 LLM에 피드백하여 최대 3회 재시도한다.
        """
        client = get_client()
        last_error: str = ""

        for attempt in range(_MAX_RETRIES):
            user_message = description
            if last_error:
                user_message = (
                    f"{description}\n\n"
                    f"[PREVIOUS ATTEMPT {attempt} ERROR]: {last_error}\n"
                    "Please fix the JSON to resolve the error above and try again."
                )

            try:
                data = client.chat_json(PARSE_SYSTEM_PROMPT, user_message)
            except LLMError as e:
                last_error = str(e)
                continue
            # _dict_to_model 내부에서 normalize_connections 자동 호출됨

            try:
                return SystemParser()._dict_to_model(data)
            except Exception as e:
                last_error = str(e)

        raise ParseError(
            f"LLM 파싱 실패 ({_MAX_RETRIES}회 시도): {last_error}"
        )
