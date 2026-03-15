"""서버 공통 유틸리티 — 라우터와 server.py가 공유하는 헬퍼 함수들."""

from __future__ import annotations

import json
import re
from typing import AsyncGenerator

from fastapi.responses import StreamingResponse


def _clean_json(text: str) -> str:
    """LLM 스트리밍 응답에서 마크다운 코드 펜스 제거 + JSON 정규화."""
    text = text.strip()
    # 마크다운 코드 펜스 제거
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    # 첫 { 부터 마지막 } 까지만 추출 (앞뒤 불필요한 텍스트 제거)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    # 후행 쉼표 제거: ,} 또는 ,] (LLM이 JS 스타일로 생성할 때 발생)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _stream_response(generator: AsyncGenerator[str, None]) -> StreamingResponse:
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── connection id 복구 ────────────────────────────────────────────────────────

_COMMON_TOKENS = frozenset({
    "new", "old", "legacy", "modern", "svc", "service", "sys", "system",
    "db", "server", "app", "api", "gw", "gateway", "mgr", "mgmt",
    "ncp", "aws", "gcp", "az", "azure",
})


def _token_match_score(a: str, b: str) -> int:
    """두 snake_case id 간 의미 있는 토큰 겹침 수 반환."""
    ta = set(a.lower().split("_")) - _COMMON_TOKENS
    tb = set(b.lower().split("_")) - _COMMON_TOKENS
    return len(ta & tb) if ta and tb else 0


def _best_id_match(invalid_id: str, valid_ids: set[str]) -> str | None:
    """유효한 id 집합에서 invalid_id와 가장 유사한 id 반환.

    토큰 겹침이 1개 이상인 경우에만 후보로 인정한다.
    동점인 경우 문자열 길이가 가장 짧은 id 선택 (과도한 매핑 방지).
    """
    best_score, best_id = 0, None
    for vid in valid_ids:
        score = _token_match_score(invalid_id, vid)
        if score > best_score or (score == best_score and best_id and len(vid) < len(best_id)):
            best_score, best_id = score, vid
    return best_id if best_score >= 1 else None


def _repair_connections(modern_dict: dict, log=None) -> dict:
    """LLM 생성 현대화 JSON의 connections에서 유효하지 않은 id를 복구한다.

    복구 우선순위:
    1. metadata.replaces 역매핑 (LLM이 명시적으로 설정한 경우)
    2. snake_case 토큰 유사도 매핑 (LLM이 legacy id를 그대로 사용한 경우)
    3. 복구 불가 → 그대로 반환 (parser.py 필터가 최종 drop 처리)
    """
    import logging
    _log = log or logging.getLogger("archpilot.server")

    valid_ids = {c["id"] for c in modern_dict.get("components", []) if c.get("id")}

    # 1순위: metadata.replaces 역매핑
    replaces_map: dict[str, str] = {}
    for c in modern_dict.get("components", []):
        legacy_id = (c.get("metadata") or {}).get("replaces")
        if legacy_id and c.get("id"):
            replaces_map[legacy_id] = c["id"]

    # 2순위: 아직 미매핑 invalid id에 대해 토큰 유사도 탐색
    all_invalid: set[str] = set()
    for conn in modern_dict.get("connections", []):
        for fid in (conn.get("from") or conn.get("from_id", ""),
                    conn.get("to") or conn.get("to_id", "")):
            if fid and fid not in valid_ids and fid not in replaces_map:
                all_invalid.add(fid)

    for invalid_id in all_invalid:
        match = _best_id_match(invalid_id, valid_ids)
        if match:
            replaces_map[invalid_id] = match
            _log.info("connection 토큰매핑: '%s' → '%s'", invalid_id, match)

    if not replaces_map:
        return modern_dict

    repaired: list[dict] = []
    for conn in modern_dict.get("connections", []):
        from_id = conn.get("from") or conn.get("from_id", "")
        to_id = conn.get("to") or conn.get("to_id", "")

        fixed_from = replaces_map.get(from_id, from_id) if from_id not in valid_ids else from_id
        fixed_to = replaces_map.get(to_id, to_id) if to_id not in valid_ids else to_id

        if fixed_from != from_id or fixed_to != to_id:
            _log.info(
                "connection 복구: %s→%s  ⟹  %s→%s", from_id, to_id, fixed_from, fixed_to
            )
            conn = {**conn, "from": fixed_from, "to": fixed_to}
            conn.pop("from_id", None)
            conn.pop("to_id", None)

        repaired.append(conn)

    return {**modern_dict, "connections": repaired}
