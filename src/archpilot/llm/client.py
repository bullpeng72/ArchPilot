"""OpenAI LLM 클라이언트 — 모든 LLM 호출의 단일 진입점."""

from __future__ import annotations

import json

from tenacity import (
    AsyncRetrying,
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from archpilot.config import settings


class LLMError(Exception):
    """LLM 호출 또는 응답 파싱 실패."""


class PermanentLLMError(LLMError):
    """재시도해도 해결할 수 없는 LLM 오류 (인증 실패, 모델 없음, 권한 없음 등).

    tenacity retry 대상에서 제외된다.
    """


class BaseLLMClient:
    """OpenAI LLM 클라이언트 공통 기반 클래스.

    설정 초기화 및 모델 속성을 공통화한다.
    서브클래스는 sync(LLMClient) 또는 async(AsyncLLMClient) 구현을 선택한다.
    테스트에서 이 클래스를 mock하면 두 구현을 모두 대체할 수 있다.
    """

    def __init__(self) -> None:
        settings.require_api_key()
        self._api_key: str = settings.openai_api_key.get_secret_value()
        self.model: str = settings.openai_model


class LLMClient(BaseLLMClient):
    def __init__(self) -> None:
        super().__init__()
        from openai import OpenAI

        self._client = OpenAI(api_key=self._api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_not_exception_type(PermanentLLMError),
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
            # HTTP 4xx 영구 오류는 재시도 없이 즉시 실패
            status_code = getattr(e, "status_code", None)
            if status_code in (401, 403, 404):
                raise PermanentLLMError(
                    f"OpenAI API 영구 오류 (HTTP {status_code}): {e}"
                ) from e
            raise LLMError(f"OpenAI API 호출 실패: {e}") from e

        content = response.choices[0].message.content or ""
        return content

    def chat_json(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int | None = None,
    ) -> dict:
        """chat() + JSON 파싱을 한 번에."""
        raw = self.chat(system_prompt, user_message, json_mode=True, max_tokens=max_tokens)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise LLMError(f"LLM 응답을 JSON으로 파싱할 수 없습니다: {e}\n응답: {raw[:200]}") from e


class AsyncLLMClient(BaseLLMClient):
    """FastAPI SSE 스트리밍 전용 비동기 클라이언트."""

    def __init__(self) -> None:
        super().__init__()
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=self._api_key)

    async def _create_stream(self, messages: list[dict], max_tokens: int):
        """스트림 생성 — 일시적 오류에 대해 최대 3회 재시도."""
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_not_exception_type(PermanentLLMError),
            reraise=True,
        ):
            with attempt:
                try:
                    return await self._client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_tokens=max_tokens,
                        stream=True,
                    )
                except Exception as e:
                    status_code = getattr(e, "status_code", None)
                    if status_code in (401, 403, 404):
                        raise PermanentLLMError(
                            f"OpenAI API 영구 오류 (HTTP {status_code}): {e}"
                        ) from e
                    raise LLMError(f"OpenAI API 호출 실패: {e}") from e

    async def stream_chat(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int | None = None,
    ):
        """텍스트 청크를 yield하는 async generator."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        stream = await self._create_stream(messages, max_tokens or settings.openai_max_tokens)
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def stream_chat_messages(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int | None = None,
    ):
        """멀티턴 대화 스트리밍 — messages는 [{role, content}, ...] 리스트."""
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        stream = await self._create_stream(full_messages, max_tokens or settings.openai_max_tokens)
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


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
