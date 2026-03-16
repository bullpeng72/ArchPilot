"""SSE 스트리밍 공통 유틸리티 — LLM 응답 수집 헬퍼."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archpilot.llm.client import AsyncLLMClient


async def collect_stream(
    client: "AsyncLLMClient",
    system_prompt: str,
    user_msg: str,
    **kwargs,
) -> str:
    """LLM 스트리밍 응답을 모두 수집해 단일 문자열로 반환한다.

    SSE 청크를 클라이언트에 노출하지 않는 내부 LLM 패스(멀티 퍼스펙티브,
    RMC 자기평가, 마이그레이션 플랜 등)에 사용한다.

    Args:
        client: AsyncLLMClient 인스턴스
        system_prompt: 시스템 프롬프트 문자열
        user_msg: 사용자 메시지 문자열
        **kwargs: stream_chat에 전달할 추가 인자 (max_tokens 등)

    Returns:
        누적된 LLM 응답 전체 텍스트
    """
    text = ""
    async for chunk in client.stream_chat(system_prompt, user_msg, **kwargs):
        text += chunk
    return text
