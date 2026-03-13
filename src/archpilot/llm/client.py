"""OpenAI LLM 클라이언트 — 모든 LLM 호출의 단일 진입점."""

from __future__ import annotations

import json

from tenacity import retry, stop_after_attempt, wait_exponential

from archpilot.config import settings


class LLMError(Exception):
    """LLM 호출 또는 응답 파싱 실패."""


class LLMClient:
    def __init__(self) -> None:
        settings.require_api_key()
        from openai import OpenAI

        self._client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def chat(
        self,
        system_prompt: str,
        user_message: str,
        json_mode: bool = True,
        max_tokens: int | None = None,
    ) -> str:
        kwargs: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens or settings.openai_max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self._client.chat.completions.create(**kwargs)
        except Exception as e:
            raise LLMError(f"OpenAI API 호출 실패: {e}") from e

        content = response.choices[0].message.content or ""
        return content

    def chat_json(self, system_prompt: str, user_message: str) -> dict:
        """chat() + JSON 파싱을 한 번에."""
        raw = self.chat(system_prompt, user_message, json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise LLMError(f"LLM 응답을 JSON으로 파싱할 수 없습니다: {e}\n응답: {raw[:200]}") from e


class AsyncLLMClient:
    """FastAPI SSE 스트리밍 전용 비동기 클라이언트."""

    def __init__(self) -> None:
        settings.require_api_key()
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    async def stream_chat(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int | None = None,
    ):
        """텍스트 청크를 yield하는 async generator."""
        try:
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=max_tokens or settings.openai_max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            raise LLMError(f"OpenAI 스트리밍 실패: {e}") from e

    async def stream_chat_messages(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int | None = None,
    ):
        """멀티턴 대화 스트리밍 — messages는 [{role, content}, ...] 리스트."""
        try:
            full_messages = [{"role": "system", "content": system_prompt}] + messages
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                max_tokens=max_tokens or settings.openai_max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            raise LLMError(f"OpenAI 스트리밍 실패: {e}") from e


# ── 모듈 수준 싱글턴 ──────────────────────────────────────────────────────────

_client: LLMClient | None = None
_async_client: AsyncLLMClient | None = None


def get_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def get_async_client() -> AsyncLLMClient:
    global _async_client
    if _async_client is None:
        _async_client = AsyncLLMClient()
    return _async_client
