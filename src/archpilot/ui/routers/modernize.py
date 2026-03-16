"""현대화(Modernize) SSE 스트리밍 라우터."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, AsyncGenerator

if TYPE_CHECKING:
    from archpilot.core.models import SystemModel
    from archpilot.ui.session import AppSession

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from archpilot.core.models import (
    AnalysisResult,
    DesignRationale,
    MigrationPlanRMC,
    ModernizationScenario,
    MultiPerspectiveAnalysis,
)
from archpilot.core.parser import SystemParser
from archpilot.llm.client import AsyncLLMClient, get_async_client
from archpilot.llm.grounding import build_pattern_grounding
from archpilot.llm.prompts import (
    DESIGN_RATIONALE_PROMPT,
    LLM_JSON_SUFFIX,
    MIGRATION_PLAN_PROMPT,
    MIGRATION_PLAN_RMC_PROMPT,
    MODERNIZE_PATCH_SYSTEM_PROMPT,
    MODERNIZE_PATCH_USER_TEMPLATE,
    MODERNIZE_SKELETON_PROMPT,
    MODERNIZE_SYSTEM_PROMPT,
    MULTI_PERSPECTIVE_DESIGN_PROMPT,
)
from archpilot.llm.utils import (
    LARGE_SYSTEM_THRESHOLD,
    MAX_MODERNIZE_TOKENS,
    MAX_PERSPECTIVE_TOKENS,
    MAX_PLAN_SYSTEM_CHARS,
    MAX_PLAN_TOKENS,
    MAX_RATIONALE_TOKENS,
    MAX_RMC_TOKENS,
    MAX_SKELETON_TOKENS,
    MAX_SYSTEM_CHARS,
    build_component_checklist,
    compress_analysis,
    compress_for_plan,
    compress_system_dict,
)
from archpilot.renderers.drawio import DrawioRenderer
from archpilot.renderers.mermaid import MermaidRenderer
from archpilot.ui import session as sess
from archpilot.ui.helpers import _clean_json, _repair_connections, _sse, _stream_response
from archpilot.ui.schemas import ModernizeRequest
from archpilot.ui.stream_utils import collect_stream

_log = logging.getLogger("archpilot.server")


@dataclass
class _LargeCtx:
    """대형 시스템 2단계 생성(_stream_large_system)에 필요한 컨텍스트 묶음."""

    resolved_scenario: str
    legacy_comps: list[dict]
    legacy_conns: list[dict]
    comp_checklist: str
    min_modern_comps: int
    retire_count: int
    analysis_section: str

router = APIRouter(prefix="/api")

# 마이그레이션 플랜용 분석 결과 추출 키
_PLAN_ANALYSIS_KEYS = (
    "component_decisions", "risk_areas", "compliance_gaps",
    "security_findings", "recommended_patterns", "estimated_effort",
)

# 설계 해설용 분석 결과 추출 키
_RATIONALE_ANALYSIS_KEYS = (
    "component_decisions", "pain_points", "recommended_patterns", "compliance_gaps",
)


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _resolve_scenario(req: ModernizeRequest, s: "AppSession") -> tuple[str, str, str]:
    """시나리오 결정 → (resolved_value, human_label, scenario_section)."""
    resolved = (
        req.scenario
        or s.scenario
        or (s.analysis or {}).get("recommended_scenario")
        or ModernizationScenario.FULL_REPLACE.value
    )
    s.scenario = resolved
    try:
        label = ModernizationScenario(resolved).label
    except ValueError:
        label = resolved
    section = f"\n\nscenario: {resolved}\n시나리오 설명: {label}"
    return resolved, label, section


def _is_patch_mode(req: ModernizeRequest, s: "AppSession") -> bool:
    """피드백이 있고 이미 현대화 결과가 존재하면 부분 수정 모드."""
    return bool(req.feedback and req.feedback.strip() and s.modern is not None)


def _build_analysis_section(s: "AppSession", resolved_scenario: str) -> str:
    """분석 결과가 있으면 LLM user_msg용 분석 섹션 문자열을 반환한다."""
    if not s.analysis:
        return ""
    analysis_obj = AnalysisResult.model_validate(s.analysis)
    decisions_json = json.dumps(
        s.analysis.get("component_decisions", []), ensure_ascii=False, indent=2
    )
    scenario_rationale = s.analysis.get("scenario_rationale", "")
    return (
        f"\n\n분석 결과 (시나리오: {resolved_scenario}):\n"
        f"추천 시나리오 근거: {scenario_rationale}\n"
        f"컴포넌트별 전략 결정 (component_decisions):\n{decisions_json}\n"
        f"전체 분석:\n{compress_analysis(analysis_obj)}"
    )


async def _stream_large_system(
    client: AsyncLLMClient,
    s: "AppSession",
    req: ModernizeRequest,
    lctx: _LargeCtx,
    result: dict,
) -> AsyncGenerator[str, None]:
    """대형 시스템 2단계 생성 (Phase 1: 스켈레톤 → Phase 2: 상세 설계).

    Yields SSE strings. 최종 모델 텍스트는 result["full_text"]에 저장.
    """
    yield _sse({
        "type": "progress", "pct": 8,
        "msg": f"🏗️ 대형 시스템 ({len(lctx.legacy_comps)}개) — Phase 1: 컴포넌트 구조 설계 중...",
    })

    decisions_json_for_skel = json.dumps(
        s.analysis.get("component_decisions", []) if s.analysis else [],
        ensure_ascii=False, indent=2,
    )
    decisions_section = f"\n\ncomponent_decisions:\n{decisions_json_for_skel}" if s.analysis else ""
    skeleton_user_msg = (
        f"시나리오: {lctx.resolved_scenario}\n"
        f"레거시 컴포넌트 수: {len(lctx.legacy_comps)}개 "
        f"(retire {lctx.retire_count}개 제외 → 최소 {lctx.min_modern_comps}개 필요)\n\n"
        f"처리해야 할 레거시 컴포넌트 목록 (빠짐없이 처리할 것):\n{lctx.comp_checklist}"
        f"{decisions_section}"
    )

    skeleton_text = ""
    async for chunk in client.stream_chat(
        MODERNIZE_SKELETON_PROMPT, skeleton_user_msg, max_tokens=MAX_SKELETON_TOKENS
    ):
        skeleton_text += chunk
        yield _sse({"type": "chunk", "text": chunk})

    skeleton_dict = json.loads(_clean_json(skeleton_text))
    skeleton_count = len(skeleton_dict.get("components", []))

    yield _sse({
        "type": "progress", "pct": 30,
        "msg": f"✅ Phase 1 완료 ({skeleton_count}개) — Phase 2: 상세 설계 및 연결 생성 중...",
    })

    enrich_user_msg = (
        f"[2단계: 스켈레톤 확장]\n"
        f"아래 컴포넌트 스켈레톤의 각 항목에 tech·criticality·lifecycle_status·"
        f"data_classification·metadata를 추가하고,\n"
        f"레거시 connections를 현대화하여 connections 배열을 생성하라.\n"
        f"컴포넌트 id 목록은 변경하지 말 것 (추가는 가능, 삭제·id 변경 불가).\n\n"
        f"확정된 컴포넌트 스켈레톤 ({skeleton_count}개):\n"
        f"{json.dumps(skeleton_dict, ensure_ascii=False, indent=2)}\n\n"
        f"레거시 connections (현대화된 연결 설계에 활용):\n"
        f"{json.dumps(lctx.legacy_conns, ensure_ascii=False)}\n\n"
        f"요구사항: {req.requirements}"
        f"{lctx.analysis_section}"
    )

    full_text = ""
    async for chunk in client.stream_chat(
        MODERNIZE_SYSTEM_PROMPT + LLM_JSON_SUFFIX,
        enrich_user_msg,
        max_tokens=MAX_MODERNIZE_TOKENS,
    ):
        full_text += chunk
        yield _sse({"type": "chunk", "text": chunk})

    result["full_text"] = full_text


async def _stream_single_pass(
    client: AsyncLLMClient,
    user_msg: str,
    must_include_ids: list[str],
    min_modern_comps: int,
    ctx: dict,
) -> AsyncGenerator[str, None]:
    """단일 패스 + A2 재시도 생성.

    Yields SSE strings. 최종 모델 텍스트는 ctx["full_text"]에 저장.
    """
    yield _sse({"type": "progress", "pct": 10, "msg": "새로운 아키텍처를 설계하고 있습니다..."})

    full_text = ""
    async for chunk in client.stream_chat(
        MODERNIZE_SYSTEM_PROMPT + LLM_JSON_SUFFIX,
        user_msg,
        max_tokens=MAX_MODERNIZE_TOKENS,
    ):
        full_text += chunk
        yield _sse({"type": "chunk", "text": chunk})

    # A2: 컴포넌트 수 사전 검증 → 부족 시 교정 재생성
    try:
        _pre_dict = json.loads(_clean_json(full_text))
        _actual_count = len(_pre_dict.get("components", []))
        if _actual_count < min_modern_comps * 0.6:
            _actual_ids = {c.get("id") for c in _pre_dict.get("components", [])}
            _missing_ids = [id for id in must_include_ids if id not in _actual_ids]
            yield _sse({
                "type": "progress", "pct": 58,
                "msg": (
                    f"⚠ 컴포넌트 {_actual_count}/{min_modern_comps}개 감지 — "
                    f"누락 {len(_missing_ids)}개 교정 재생성 중..."
                ),
            })
            corrective_msg = (
                f"[재설계 요청] 이전 응답에서 {len(_missing_ids)}개 컴포넌트가 누락됐습니다:\n"
                + "\n".join(f"  - {id}" for id in _missing_ids[:30])
                + "\n\n위 컴포넌트를 반드시 포함하여 전체 아키텍처를 재설계하십시오.\n\n"
                + user_msg
            )
            full_text = ""
            async for chunk in client.stream_chat(
                MODERNIZE_SYSTEM_PROMPT + LLM_JSON_SUFFIX,
                corrective_msg,
                max_tokens=MAX_MODERNIZE_TOKENS,
            ):
                full_text += chunk
                yield _sse({"type": "chunk", "text": chunk})
    except (json.JSONDecodeError, ValueError):
        pass  # 파싱 오류는 아래 메인 파싱 단계에서 처리

    ctx["full_text"] = full_text


def _build_patch_context(s: "AppSession", resolved_scenario: str) -> tuple[str, str]:
    """패치 LLM에 전달할 컨텍스트 빌드.

    Returns:
        keep_constraints: 변경 금지 컴포넌트 섹션 문자열 (없으면 "")
        analysis_context: 분석 컨텍스트 섹션 문자열 (없으면 "")
    """
    keep_constraints = ""
    analysis_context = ""

    if s.analysis:
        decisions: list[dict] = s.analysis.get("component_decisions", [])

        # ── 변경 금지 컴포넌트 (keep / rehost 결정) ───────────────────────────
        keep_items = [d for d in decisions if d.get("action") in ("keep", "rehost")]
        if keep_items:
            lines = [
                "\n[변경 금지 컴포넌트 — 분석 결정 준수]",
                "아래 컴포넌트는 분석에서 keep/rehost로 결정됐습니다. 피드백이 수정을 요청해도 변경하지 마세요:",
            ]
            for d in keep_items:
                rationale = d.get("rationale", "")
                suffix = f" — {rationale}" if rationale else ""
                lines.append(f"  - {d['component_id']} (action: {d['action']}{suffix})")
            keep_constraints = "\n".join(lines) + "\n\n"

        # ── 분석 컨텍스트 ─────────────────────────────────────────────────────
        scenario_rationale = s.analysis.get("scenario_rationale", "")
        health_score = s.analysis.get("health_score")
        pain_points = (s.analysis.get("pain_points") or [])[:3]

        ctx_lines = ["\n[분석 컨텍스트 — 설계 의도 참고]"]
        ctx_lines.append(f"시나리오: {resolved_scenario}")
        if scenario_rationale:
            ctx_lines.append(f"시나리오 근거: {scenario_rationale}")
        if health_score is not None:
            ctx_lines.append(f"헬스 스코어: {health_score}/10")
        if pain_points:
            ctx_lines.append(f"해결 목표 문제점: {'; '.join(str(p) for p in pain_points)}")
        if decisions:
            ctx_lines.append("컴포넌트 전략 결정:")
            for d in decisions:
                action = d.get("action", "?")
                comp_id = d.get("component_id", "?")
                rationale = d.get("rationale", "")
                suffix = f" — {rationale}" if rationale else ""
                ctx_lines.append(f"  {comp_id}: {action}{suffix}")
        analysis_context = "\n".join(ctx_lines) + "\n\n"

    # ── 설계 철학 (design_rationale 있으면 추가) ──────────────────────────────
    if s.design_rationale:
        philosophy = s.design_rationale.get("design_philosophy", "")
        if philosophy:
            analysis_context += f"[설계 철학]\n{philosophy}\n\n"

    return keep_constraints, analysis_context


async def _stream_patch(
    client: AsyncLLMClient,
    s: "AppSession",
    req: ModernizeRequest,
    ctx: dict,
    resolved_scenario: str,
) -> AsyncGenerator[str, None]:
    """부분 수정 모드 — 기존 modern 모델에 피드백만 적용.

    Yields SSE strings. 최종 모델 텍스트는 ctx["full_text"]에 저장.
    """
    yield _sse({"type": "progress", "pct": 10,
                "msg": "기존 설계에 피드백을 반영하고 있습니다..."})

    keep_constraints, analysis_context = _build_patch_context(s, resolved_scenario)
    current_modern_json = compress_system_dict(s.modern, MAX_SYSTEM_CHARS)
    user_msg = MODERNIZE_PATCH_USER_TEMPLATE.format(
        requirements=req.requirements,
        feedback=req.feedback,
        keep_constraints=keep_constraints,
        analysis_context=analysis_context,
        current_modern_json=current_modern_json,
    )

    full_text = ""
    async for chunk in client.stream_chat(
        MODERNIZE_PATCH_SYSTEM_PROMPT,
        user_msg,
        max_tokens=MAX_MODERNIZE_TOKENS,
    ):
        full_text += chunk
        yield _sse({"type": "chunk", "text": chunk})

    ctx["full_text"] = full_text


async def _phase_design_perspective(
    client: AsyncLLMClient,
    s: "AppSession",
    req: ModernizeRequest,
    modern_model: "SystemModel",
    resolved_scenario: str,
    scenario_label: str,
) -> dict | None:
    """Phase ②: 8대 관점 설계 검증. Returns MultiPerspectiveAnalysis dict or None."""
    user_msg = (
        f"시나리오: {resolved_scenario} — {scenario_label}\n"
        f"현대화 요구사항: {req.requirements}\n\n"
        f"레거시 시스템 (참고):\n{compress_system_dict(s.system, MAX_SYSTEM_CHARS)}\n\n"
        f"현대화 설계안:\n"
        f"{compress_for_plan(json.loads(modern_model.model_dump_json()), MAX_PLAN_SYSTEM_CHARS)}"
    )
    if s.analysis:
        user_msg += (
            "\n\n분석 결과 참고 (component_decisions):\n"
            + json.dumps(s.analysis.get("component_decisions", [])[:15], ensure_ascii=False)
        )
    text = await collect_stream(
        client,
        MULTI_PERSPECTIVE_DESIGN_PROMPT + LLM_JSON_SUFFIX,
        user_msg,
        max_tokens=MAX_PERSPECTIVE_TOKENS,
    )
    try:
        dp = MultiPerspectiveAnalysis.model_validate(json.loads(_clean_json(text)))
        return json.loads(dp.model_dump_json())
    except (json.JSONDecodeError, ValueError) as e:
        _log.warning("[modernize] 설계 퍼스펙티브 파싱 실패 (무시): %s", e)
        return None


async def _phase_migration_plan(
    client: AsyncLLMClient,
    s: "AppSession",
    req: ModernizeRequest,
    modern_model: "SystemModel",
) -> str:
    """Phase ③: 마이그레이션 플랜 생성. Returns markdown text."""
    user_msg = (
        f"요구사항: {req.requirements}\n\n"
        f"레거시:\n{compress_for_plan(s.system, MAX_PLAN_SYSTEM_CHARS)}\n\n"
        f"현대화:\n"
        f"{compress_for_plan(json.loads(modern_model.model_dump_json()), MAX_PLAN_SYSTEM_CHARS)}"
    )
    if s.analysis:
        plan_analysis = {k: s.analysis[k] for k in _PLAN_ANALYSIS_KEYS if k in s.analysis}
        user_msg += (
            f"\n\n분석 결과:\n{json.dumps(plan_analysis, ensure_ascii=False, indent=2)}"
        )
    return await collect_stream(
        client, MIGRATION_PLAN_PROMPT, user_msg, max_tokens=MAX_PLAN_TOKENS
    )


async def _phase_rmc_rationale(
    client: AsyncLLMClient,
    s: "AppSession",
    req: ModernizeRequest,
    resolved_scenario: str,
) -> dict | None:
    """Phase ④: RMC 설계 해설 생성. Returns DesignRationale dict or None."""
    user_msg = (
        f"시나리오: {resolved_scenario}\n"
        f"요구사항: {req.requirements}\n\n"
        f"레거시 시스템:\n{compress_system_dict(s.system, MAX_SYSTEM_CHARS)}\n\n"
        f"현대화 설계 결과:\n{compress_for_plan(s.modern, MAX_PLAN_SYSTEM_CHARS)}"
    )
    if s.analysis:
        user_msg += (
            "\n\n분석 참고 (component_decisions, pain_points):\n"
            + json.dumps(
                {k: s.analysis[k] for k in _RATIONALE_ANALYSIS_KEYS if k in s.analysis},
                ensure_ascii=False,
            )
        )
    text = await collect_stream(
        client,
        DESIGN_RATIONALE_PROMPT + LLM_JSON_SUFFIX,
        user_msg,
        max_tokens=MAX_RATIONALE_TOKENS,
    )
    try:
        rationale = DesignRationale.model_validate(json.loads(_clean_json(text)))
        return json.loads(rationale.model_dump_json())
    except (json.JSONDecodeError, ValueError) as e:
        _log.warning("[modernize] 설계 해설 파싱 실패 (무시): %s", e)
        return None


async def _phase_rmc_plan(
    client: AsyncLLMClient,
    s: "AppSession",
    resolved_scenario: str,
    legacy_comps: list[dict],
    plan_text: str,
) -> dict | None:
    """Phase ⑤: RMC 마이그레이션 계획 자기평가. Returns MigrationPlanRMC dict or None."""
    analysis_ctx = ""
    if s.analysis:
        pain_pts = "; ".join((s.analysis.get("pain_points") or [])[:3])
        analysis_ctx = (
            f"\n시스템 분석 컨텍스트:"
            f"\n  헬스 스코어: {s.analysis.get('health_score', '?')}/10"
            f"\n  예상 공수: {s.analysis.get('estimated_effort', '?')}"
            f"\n  주요 문제점: {pain_pts}"
            f"\n  컴포넌트: 레거시 {len(legacy_comps)}개 → "
            f"현대 {len((s.modern or {}).get('components', []))}개"
        )
    user_msg = (
        f"시스템: {s.system.get('name', '(미상)') if s.system else '(미상)'}\n"
        f"시나리오: {resolved_scenario}"
        f"{analysis_ctx}\n\n"
        f"작성한 마이그레이션 계획:\n{plan_text[:8000]}"
    )
    text = await collect_stream(
        client,
        MIGRATION_PLAN_RMC_PROMPT + LLM_JSON_SUFFIX,
        user_msg,
        max_tokens=MAX_RMC_TOKENS,
    )
    try:
        plan_rmc = MigrationPlanRMC.model_validate(json.loads(_clean_json(text)))
        return json.loads(plan_rmc.model_dump_json())
    except (json.JSONDecodeError, ValueError) as e:
        _log.warning("[modernize] 마이그레이션 계획 RMC 파싱 실패 (무시): %s", e)
        return None


# ── 현대화 스트리밍 핵심 로직 (테스트 가능하도록 라우터 외부로 분리) ──────────────

async def _run_modernize(
    req: ModernizeRequest,
    s: "AppSession",
    output_dir: Any,
) -> AsyncGenerator[str, None]:
    """modernize_stream의 실제 생성 로직.

    HTTPException·Request 의존성을 제거하여 독립 테스트가 가능하다.
    output_dir: pathlib.Path — 파일 저장 위치
    """
    try:
        async with s.busy("modernize"):
            is_patch = _is_patch_mode(req, s)
            client = get_async_client()
            ctx: dict = {}

            if is_patch:
                # ── 부분 수정 모드 ─────────────────────────────────────────────
                # 시나리오는 세션에서 유지 (재평가 없음)
                resolved_scenario = s.scenario or ModernizationScenario.FULL_REPLACE.value
                yield _sse({"type": "progress", "pct": 5,
                            "msg": "부분 수정 모드 — 기존 설계에 피드백을 반영합니다..."})
                async for event in _stream_patch(client, s, req, ctx, resolved_scenario):
                    yield event
                scenario_label = resolved_scenario
                try:
                    scenario_label = ModernizationScenario(resolved_scenario).label
                except ValueError:
                    pass
                legacy_comps = s.system.get("components", [])
            else:
                # ── 전체 재생성 모드 ───────────────────────────────────────────
                yield _sse({"type": "progress", "pct": 5, "msg": "현대화 설계를 시작합니다..."})

                resolved_scenario, scenario_label, scenario_section = _resolve_scenario(req, s)
                legacy_comps = s.system.get("components", [])
                legacy_conns = s.system.get("connections", [])

                comp_checklist, must_include_ids, retire_ids, min_modern_comps = (
                    build_component_checklist(s.analysis, legacy_comps)
                )
                retire_count = len(retire_ids)
                analysis_section = _build_analysis_section(s, resolved_scenario)

                pattern_grounding = build_pattern_grounding(s.system)
                user_msg = (
                    f"[레거시 규모: {len(legacy_comps)}개 컴포넌트, {len(legacy_conns)}개 연결]\n"
                    f"[현대화 설계 최소 컴포넌트 수: {min_modern_comps}개 이상 "
                    f"(retire {retire_count}개 제외)]\n"
                    f"[처리 대상 컴포넌트 목록 (빠짐없이 현대화 설계에 반영할 것)]:\n"
                    f"{comp_checklist}\n\n"
                    f"현대화 요구사항:\n{req.requirements}"
                    f"{scenario_section}"
                    f"{analysis_section}"
                    f"\n\nLegacy 시스템:\n{compress_system_dict(s.system, MAX_SYSTEM_CHARS)}"
                    f"{pattern_grounding}"
                )

                # ── Phase ①: SystemModel 생성 ────────────────────────────────────
                if len(legacy_comps) > LARGE_SYSTEM_THRESHOLD:
                    lctx = _LargeCtx(
                        resolved_scenario=resolved_scenario,
                        legacy_comps=legacy_comps,
                        legacy_conns=legacy_conns,
                        comp_checklist=comp_checklist,
                        min_modern_comps=min_modern_comps,
                        retire_count=retire_count,
                        analysis_section=analysis_section,
                    )
                    async for event in _stream_large_system(client, s, req, lctx, ctx):
                        yield event
                else:
                    async for event in _stream_single_pass(
                        client, user_msg, must_include_ids, min_modern_comps, ctx
                    ):
                        yield event

            yield _sse({"type": "progress", "pct": 60, "msg": "시스템 모델을 파싱하고 있습니다..."})
            modern_dict = _repair_connections(
                json.loads(_clean_json(ctx["full_text"])), _log
            )
            modern_model = SystemParser()._dict_to_model(modern_dict)
            modern_mmd = MermaidRenderer().render(modern_model)
            modern_drawio = DrawioRenderer().render(modern_model)

            # dropped connections 경고 SSE 방출
            dropped_conns = modern_model.metadata.get("_dropped_connections")
            if dropped_conns:
                _log.warning("[modernize] LLM 생성 연결 %d개 드롭: %s", len(dropped_conns), dropped_conns)
                yield _sse({
                    "type": "warning",
                    "msg": (
                        f"현대화 설계에서 {len(dropped_conns)}개 연결이 "
                        f"유효하지 않은 컴포넌트를 참조하여 제거됐습니다: "
                        + ", ".join(dropped_conns[:5])
                        + ("..." if len(dropped_conns) > 5 else "")
                    ),
                })

            # missing components 경고 SSE 방출
            missing_comps = modern_model.metadata.get("_missing_components")
            if missing_comps:
                yield _sse({
                    "type": "warning",
                    "msg": (
                        f"재시도 후에도 {len(missing_comps)}개 컴포넌트가 누락됐습니다: "
                        + ", ".join(missing_comps[:5])
                        + ("..." if len(missing_comps) > 5 else "")
                        + " 재분석 또는 수동 보정을 권장합니다."
                    ),
                })

            # ── Phase ②: 멀티 퍼스펙티브 설계 검증 (전체 재생성 시에만) ────────
            if not is_patch:
                yield _sse({
                    "type": "progress", "pct": 65,
                    "msg": "🏛️ 8대 아키텍처 관점에서 설계안을 검증하고 있습니다...",
                })
                s.design_perspective = await _phase_design_perspective(
                    client, s, req, modern_model, resolved_scenario, scenario_label
                )

            # ── Phase ③: 마이그레이션 플랜 (항상 실행 — 수정된 아키텍처 반영) ──
            yield _sse({"type": "progress", "pct": 75, "msg": "마이그레이션 플랜을 작성하고 있습니다..."})
            plan_text = await _phase_migration_plan(client, s, req, modern_model)

            s.modern = json.loads(modern_model.model_dump_json())
            s.modern_mmd = modern_mmd
            s.modern_drawio = modern_drawio
            s.migration_plan = plan_text

            # 부분 수정 이력 기록
            if is_patch and req.feedback:
                s.last_feedback = req.feedback
                s.patch_history.append(req.feedback)

            # ── Phase ④: RMC 설계 해설 (전체 재생성 시에만) ─────────────────
            if not is_patch:
                yield _sse({"type": "progress", "pct": 88,
                            "msg": "🧠 RMC: 설계 해설을 작성하고 있습니다..."})
                s.design_rationale = await _phase_rmc_rationale(
                    client, s, req, resolved_scenario
                )

                # ── Phase ⑤: RMC 마이그레이션 계획 자기평가 ─────────────────
                yield _sse({
                    "type": "progress", "pct": 95,
                    "msg": "🧠 RMC: 마이그레이션 계획을 자기검토하고 있습니다...",
                })
                s.migration_plan_rmc = await _phase_rmc_plan(
                    client, s, resolved_scenario, legacy_comps, plan_text
                )

            # ── 파일 저장 (블로킹 I/O → 스레드 오프로드) ─────────────────────
            modern_dir = output_dir / "modern"
            design_rationale_json = (
                json.dumps(s.design_rationale, ensure_ascii=False, indent=2)
                if s.design_rationale else None
            )

            def _write_modern_files() -> None:
                modern_dir.mkdir(exist_ok=True)
                (modern_dir / "system.json").write_text(
                    modern_model.model_dump_json(indent=2), encoding="utf-8"
                )
                (modern_dir / "diagram.mmd").write_text(modern_mmd, encoding="utf-8")
                (modern_dir / "diagram.drawio").write_text(modern_drawio, encoding="utf-8")
                (modern_dir / "migration_plan.md").write_text(plan_text, encoding="utf-8")
                if design_rationale_json:
                    (modern_dir / "design_rationale.json").write_text(
                        design_rationale_json, encoding="utf-8"
                    )

            await asyncio.to_thread(_write_modern_files)

            yield _sse({
                "type": "done",
                "modern": s.modern,
                "modern_mmd": modern_mmd,
                "modern_drawio": modern_drawio,
                "migration_plan": plan_text,
                "scenario": resolved_scenario,
                "design_rationale": s.design_rationale,
                "migration_plan_rmc": s.migration_plan_rmc,
                "design_perspective": s.design_perspective,
                "patch_mode": is_patch,
                "feedback": req.feedback if is_patch else None,
            })

    except Exception as e:
        _log.exception("[modernize] 오류: %s", e)
        yield _sse({"type": "error", "msg": str(e)})


# ── POST /api/modernize/stream ────────────────────────────────────────────────

@router.post("/modernize/stream")
async def modernize_stream(req: ModernizeRequest, request: Request) -> StreamingResponse:
    s = sess.get()
    if not s.system:
        raise HTTPException(status_code=400, detail="먼저 시스템을 주입하세요")

    s.requirements = req.requirements
    output_dir = request.app.state.output_dir
    return await _stream_response(_run_modernize(req, s, output_dir))
