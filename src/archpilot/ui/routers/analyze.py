"""분석(Analyze) SSE 스트리밍 라우터."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from archpilot.llm.grounding import build_pattern_grounding
from archpilot.llm.utils import (
    MAX_ANALYZE_TOKENS,
    MAX_PAYLOAD_CHARS,
    MAX_PERSPECTIVE_TOKENS,
    MAX_RMC_TOKENS,
    MAX_SYSTEM_CHARS,
    compress_system_dict,
)
from archpilot.ui import session as sess
from archpilot.ui.helpers import _clean_json, _sse, _stream_response

_log = logging.getLogger("archpilot.server")

router = APIRouter(prefix="/api")


@router.get("/analyze/stream")
async def analyze_stream(request: Request) -> StreamingResponse:
    s = sess.get()
    if not s.system:
        raise HTTPException(status_code=400, detail="먼저 시스템을 주입하세요 (/api/ingest)")

    from archpilot.config import settings
    from archpilot.llm.client import get_async_client
    from archpilot.llm.prompts import (
        ANALYZE_RMC_PROMPT,
        ANALYZE_SYSTEM_PROMPT,
        LLM_JSON_SUFFIX,
        MULTI_PERSPECTIVE_PROMPT,
    )

    async def generator():
        try:
            with s.busy("analyze"):
                yield _sse({"type": "progress", "pct": 5, "msg": "분석을 시작합니다..."})

                payload = compress_system_dict(s.system, MAX_PAYLOAD_CHARS)
                req_section = (
                    f"\n\n현대화 목표 (component_decisions 수립 시 반드시 반영):\n{s.requirements}"
                    if s.requirements else ""
                )
                grounding = build_pattern_grounding(s.system)
                user_msg = f"분석할 시스템:\n{payload}{req_section}{grounding}"

                client = get_async_client()
                full_text = ""

                yield _sse({
                    "type": "progress",
                    "pct": 15,
                    "msg": f"{settings.openai_model}이 시스템을 분석하고 있습니다...",
                })

                from archpilot.core.models import AnalysisResult
                async for chunk in client.stream_chat(
                    ANALYZE_SYSTEM_PROMPT + LLM_JSON_SUFFIX,
                    user_msg,
                    max_tokens=MAX_ANALYZE_TOKENS,
                ):
                    full_text += chunk
                    yield _sse({"type": "chunk", "text": chunk})

                yield _sse({"type": "progress", "pct": 78, "msg": "결과를 파싱하고 있습니다..."})

                clean = _clean_json(full_text)
                result_dict = json.loads(clean)
                analysis = AnalysisResult.model_validate(result_dict)
                s.analysis = json.loads(analysis.model_dump_json())

                # ── Multi-Perspective 2nd-pass: 8대 아키텍처 관점 분석 ─────────────
                yield _sse({"type": "progress", "pct": 83, "msg": "🏛️ 8대 아키텍처 관점 분석 중..."})

                from archpilot.core.models import AnalysisRMC, MultiPerspectiveAnalysis
                persp_user_msg = (
                    f"분석 대상 시스템:\n{compress_system_dict(s.system, MAX_SYSTEM_CHARS)}\n\n"
                    f"1차 분석 결과 요약:\n"
                    f"health_score={s.analysis.get('health_score')}, "
                    f"recommended_scenario={s.analysis.get('recommended_scenario')}\n"
                    f"pain_points={json.dumps(s.analysis.get('pain_points', [])[:5], ensure_ascii=False)}\n"
                    f"tech_debt={json.dumps(s.analysis.get('tech_debt', [])[:5], ensure_ascii=False)}"
                )
                persp_text = ""
                async for chunk in client.stream_chat(
                    MULTI_PERSPECTIVE_PROMPT + LLM_JSON_SUFFIX,
                    persp_user_msg,
                    max_tokens=MAX_PERSPECTIVE_TOKENS,
                ):
                    persp_text += chunk

                multi_perspective_dict = None
                try:
                    persp_dict = json.loads(_clean_json(persp_text))
                    mp = MultiPerspectiveAnalysis.model_validate(persp_dict)
                    multi_perspective_dict = json.loads(mp.model_dump_json())
                    s.analysis["multi_perspective"] = multi_perspective_dict
                except (json.JSONDecodeError, ValueError) as e:
                    _log.warning("[analyze] 멀티 퍼스펙티브 파싱 실패 (무시): %s", e)

                # ── RMC 3rd-pass: 분석 자기평가 ──────────────────────────────────
                yield _sse({"type": "progress", "pct": 90, "msg": "🧠 RMC: 분석 결과를 자기검토하고 있습니다..."})

                rmc_user_msg = (
                    f"분석 대상 시스템:\n{compress_system_dict(s.system, MAX_SYSTEM_CHARS)}\n\n"
                    f"방금 생성한 분석 결과:\n{json.dumps(s.analysis, ensure_ascii=False, indent=2)}"
                )
                rmc_text = ""
                async for chunk in client.stream_chat(
                    ANALYZE_RMC_PROMPT + LLM_JSON_SUFFIX,
                    rmc_user_msg,
                    max_tokens=MAX_RMC_TOKENS,
                ):
                    rmc_text += chunk

                try:
                    rmc_dict = json.loads(_clean_json(rmc_text))
                    rmc = AnalysisRMC.model_validate(rmc_dict)
                    s.analysis_rmc = json.loads(rmc.model_dump_json())
                except (json.JSONDecodeError, ValueError) as e:
                    _log.warning("[analyze] RMC 파싱 실패 (무시): %s", e)
                    s.analysis_rmc = None

                output_dir = request.app.state.output_dir
                analysis_json = analysis.model_dump_json(indent=2)
                await asyncio.to_thread(
                    lambda: (
                        output_dir.mkdir(parents=True, exist_ok=True),
                        (output_dir / "analysis.json").write_text(analysis_json, encoding="utf-8"),
                    )
                )

                yield _sse({
                    "type": "done",
                    "result": s.analysis,
                    "analysis_rmc": s.analysis_rmc,
                    "multi_perspective": multi_perspective_dict,
                })

        except Exception as e:
            _log.exception("[analyze] 오류: %s", e)
            yield _sse({"type": "error", "msg": str(e)})

    return await _stream_response(generator())
