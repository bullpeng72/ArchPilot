"""현대화(Modernize) SSE 스트리밍 라우터."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Request

from archpilot.core.models import ModernizationScenario
from archpilot.llm.utils import (
    LARGE_SYSTEM_THRESHOLD,
    MAX_MODERNIZE_TOKENS,
    MAX_PLAN_SYSTEM_CHARS,
    MAX_PLAN_TOKENS,
    MAX_RATIONALE_TOKENS,
    MAX_RMC_TOKENS,
    MAX_SKELETON_TOKENS,
    MAX_SYSTEM_CHARS,
    compress_analysis,
    compress_for_plan,
    compress_system_dict,
)
from archpilot.renderers.drawio import DrawioRenderer
from archpilot.renderers.mermaid import MermaidRenderer
from archpilot.ui import session as sess
from archpilot.ui.helpers import _clean_json, _repair_connections, _sse, _stream_response
from archpilot.ui.schemas import ModernizeRequest

_log = logging.getLogger("archpilot.server")

router = APIRouter(prefix="/api")

# 시나리오 레이블 — modernizer.py _SCENARIO_LABELS와 동기화 유지
_SCENARIO_LABELS: dict[str, str] = {
    "full_replace": "전체 교체 — 아키텍처를 완전히 새로 설계",
    "partial":      "일부 보존 — 핵심 컴포넌트 유지, 주변부·통합 레이어 현대화",
    "additive":     "신규 추가 — 기존 시스템 유지, 신규 기능·채널만 추가",
}

# 마이그레이션 플랜용 분석 결과 추출 키
_PLAN_ANALYSIS_KEYS = (
    "component_decisions", "risk_areas", "compliance_gaps",
    "security_findings", "recommended_patterns", "estimated_effort",
)

# 설계 해설용 분석 결과 추출 키
_RATIONALE_ANALYSIS_KEYS = (
    "component_decisions", "pain_points", "recommended_patterns", "compliance_gaps",
)


@router.post("/modernize/stream")
async def modernize_stream(req: ModernizeRequest, request: Request):
    s = sess.get()
    if not s.system:
        raise HTTPException(status_code=400, detail="먼저 시스템을 주입하세요")

    s.requirements = req.requirements

    from archpilot.core.parser import SystemParser
    from archpilot.llm.client import get_async_client
    from archpilot.llm.prompts import (
        MIGRATION_PLAN_PROMPT,
        MODERNIZE_SKELETON_PROMPT,
        MODERNIZE_SYSTEM_PROMPT,
    )

    async def generator():
        try:
            yield _sse({"type": "progress", "pct": 5, "msg": "현대화 설계를 시작합니다..."})

            # 시나리오 결정
            resolved_scenario: str = (
                req.scenario
                or s.scenario
                or (s.analysis or {}).get("recommended_scenario")
                or ModernizationScenario.FULL_REPLACE.value
            )
            s.scenario = resolved_scenario

            scenario_label = _SCENARIO_LABELS.get(resolved_scenario, resolved_scenario)

            scenario_section = f"\n\nscenario: {resolved_scenario}\n시나리오 설명: {scenario_label}"

            legacy_comps = s.system.get("components", [])
            legacy_conns = s.system.get("connections", [])

            retire_count = sum(
                1 for d in (s.analysis or {}).get("component_decisions", [])
                if d.get("action") == "retire"
            )
            min_modern_comps = max(len(legacy_comps) - retire_count, 1)

            # ── A1: 컴포넌트 체크리스트 구성 ────────────────────────────────
            decisions_by_id: dict[str, str] = {
                d.get("component_id"): d.get("action")
                for d in (s.analysis or {}).get("component_decisions", [])
                if d.get("component_id")
            }
            retire_ids: set[str] = {
                d.get("component_id")
                for d in (s.analysis or {}).get("component_decisions", [])
                if d.get("action") == "retire" and d.get("component_id")
            }
            comp_checklist = "\n".join(
                f"  - {c['id']} ({c.get('type', '?')})"
                + (f" → {decisions_by_id[c['id']]}" if c["id"] in decisions_by_id else "")
                for c in legacy_comps
            )
            must_include_ids = [c["id"] for c in legacy_comps if c["id"] not in retire_ids]

            # ── 분석 섹션 구성 ───────────────────────────────────────────────
            analysis_section = ""
            if s.analysis:
                from archpilot.core.models import AnalysisResult as _AR
                analysis_obj = _AR.model_validate(s.analysis)
                decisions_json = json.dumps(
                    s.analysis.get("component_decisions", []), ensure_ascii=False, indent=2
                )
                scenario_rationale = s.analysis.get("scenario_rationale", "")
                analysis_section = (
                    f"\n\n분석 결과 (시나리오: {resolved_scenario}):\n"
                    f"추천 시나리오 근거: {scenario_rationale}\n"
                    f"컴포넌트별 전략 결정 (component_decisions):\n{decisions_json}\n"
                    f"전체 분석:\n{compress_analysis(analysis_obj)}"
                )

            # ── Single-pass용 user_msg (A1 체크리스트 포함) ──────────────────
            user_msg = (
                f"[레거시 규모: {len(legacy_comps)}개 컴포넌트, {len(legacy_conns)}개 연결]\n"
                f"[현대화 설계 최소 컴포넌트 수: {min_modern_comps}개 이상 (retire {retire_count}개 제외)]\n"
                f"[처리 대상 컴포넌트 목록 (빠짐없이 현대화 설계에 반영할 것)]:\n{comp_checklist}\n\n"
                f"현대화 요구사항:\n{req.requirements}"
                f"{scenario_section}"
                f"{analysis_section}"
                f"\n\nLegacy 시스템:\n{compress_system_dict(s.system, MAX_SYSTEM_CHARS)}"
            )

            client = get_async_client()
            is_large = len(legacy_comps) > LARGE_SYSTEM_THRESHOLD

            # ── ① 현대화 SystemModel 생성 ────────────────────────────────────
            if is_large:
                # ── A3: 2단계 분할 생성 ──────────────────────────────────────
                yield _sse({
                    "type": "progress", "pct": 8,
                    "msg": f"🏗️ 대형 시스템 ({len(legacy_comps)}개) — Phase 1: 컴포넌트 구조 설계 중...",
                })

                # Phase 1: 스켈레톤
                decisions_json_for_skel = json.dumps(
                    s.analysis.get("component_decisions", []) if s.analysis else [],
                    ensure_ascii=False, indent=2,
                )
                decisions_section_for_skel = (
                    f"\n\ncomponent_decisions:\n{decisions_json_for_skel}" if s.analysis else ""
                )
                skeleton_user_msg = (
                    f"시나리오: {resolved_scenario}\n"
                    f"레거시 컴포넌트 수: {len(legacy_comps)}개 "
                    f"(retire {retire_count}개 제외 → 최소 {min_modern_comps}개 필요)\n\n"
                    f"처리해야 할 레거시 컴포넌트 목록 (빠짐없이 처리할 것):\n{comp_checklist}"
                    f"{decisions_section_for_skel}"
                )

                skeleton_text = ""
                async for chunk in client.stream_chat(
                    MODERNIZE_SKELETON_PROMPT, skeleton_user_msg, max_tokens=MAX_SKELETON_TOKENS
                ):
                    skeleton_text += chunk
                    yield _sse({"type": "chunk", "text": chunk})

                skeleton_dict = json.loads(_clean_json(skeleton_text))
                skeleton_count = len(skeleton_dict.get("components", []))

                # Phase 2: 상세 설계 + connections 생성
                yield _sse({
                    "type": "progress", "pct": 30,
                    "msg": f"✅ Phase 1 완료 ({skeleton_count}개) — Phase 2: 상세 설계 및 연결 생성 중...",
                })

                skeleton_json = json.dumps(skeleton_dict, ensure_ascii=False, indent=2)
                legacy_conns_for_enrich = json.dumps(legacy_conns, ensure_ascii=False)

                enrich_user_msg = (
                    f"[2단계: 스켈레톤 확장]\n"
                    f"아래 컴포넌트 스켈레톤의 각 항목에 tech·criticality·lifecycle_status·"
                    f"data_classification·metadata를 추가하고,\n"
                    f"레거시 connections를 현대화하여 connections 배열을 생성하라.\n"
                    f"컴포넌트 id 목록은 변경하지 말 것 (추가는 가능, 삭제·id 변경 불가).\n\n"
                    f"확정된 컴포넌트 스켈레톤 ({skeleton_count}개):\n{skeleton_json}\n\n"
                    f"레거시 connections (현대화된 연결 설계에 활용):\n{legacy_conns_for_enrich}\n\n"
                    f"요구사항: {req.requirements}"
                    f"{analysis_section}"
                )

                full_text = ""
                async for chunk in client.stream_chat(
                    MODERNIZE_SYSTEM_PROMPT + "\nIMPORTANT: Output ONLY raw JSON, no markdown fences.",
                    enrich_user_msg,
                    max_tokens=MAX_MODERNIZE_TOKENS,
                ):
                    full_text += chunk
                    yield _sse({"type": "chunk", "text": chunk})

            else:
                # ── Single-pass + A2 재시도 ───────────────────────────────────
                yield _sse({"type": "progress", "pct": 10, "msg": "새로운 아키텍처를 설계하고 있습니다..."})

                full_text = ""
                async for chunk in client.stream_chat(
                    MODERNIZE_SYSTEM_PROMPT + "\nIMPORTANT: Output ONLY raw JSON, no markdown fences.",
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
                        _missing_ids = [
                            id for id in must_include_ids if id not in _actual_ids
                        ]
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
                            + f"\n\n위 컴포넌트를 반드시 포함하여 전체 아키텍처를 재설계하십시오.\n\n"
                            + user_msg
                        )
                        full_text = ""
                        async for chunk in client.stream_chat(
                            MODERNIZE_SYSTEM_PROMPT
                            + "\nIMPORTANT: Output ONLY raw JSON, no markdown fences.",
                            corrective_msg,
                            max_tokens=MAX_MODERNIZE_TOKENS,
                        ):
                            full_text += chunk
                            yield _sse({"type": "chunk", "text": chunk})
                except (json.JSONDecodeError, ValueError):
                    pass  # 파싱 오류는 아래 메인 파싱 단계에서 처리

            yield _sse({"type": "progress", "pct": 60, "msg": "시스템 모델을 파싱하고 있습니다..."})

            clean = _clean_json(full_text)
            modern_dict = json.loads(clean)
            modern_dict = _repair_connections(modern_dict, _log)
            modern_model = SystemParser()._dict_to_model(modern_dict)

            modern_mmd = MermaidRenderer().render(modern_model)
            modern_drawio = DrawioRenderer().render(modern_model)

            # ── ② 마이그레이션 플랜 생성 ─────────────────────────────────────
            yield _sse({"type": "progress", "pct": 70, "msg": "마이그레이션 플랜을 작성하고 있습니다..."})
            plan_user_msg = (
                f"요구사항: {req.requirements}\n\n"
                f"레거시:\n{compress_for_plan(s.system, MAX_PLAN_SYSTEM_CHARS)}\n\n"
                f"현대화:\n{compress_for_plan(json.loads(modern_model.model_dump_json()), MAX_PLAN_SYSTEM_CHARS)}"
            )
            if s.analysis:
                plan_analysis = {k: s.analysis[k] for k in _PLAN_ANALYSIS_KEYS if k in s.analysis}
                plan_user_msg += f"\n\n분석 결과:\n{json.dumps(plan_analysis, ensure_ascii=False, indent=2)}"
            plan_text = ""
            async for chunk in client.stream_chat(
                MIGRATION_PLAN_PROMPT, plan_user_msg, max_tokens=MAX_PLAN_TOKENS
            ):
                plan_text += chunk

            s.modern = json.loads(modern_model.model_dump_json())
            s.modern_mmd = modern_mmd
            s.modern_drawio = modern_drawio
            s.migration_plan = plan_text

            # ── ③ RMC 2nd-pass: 설계 해설 생성 ──────────────────────────────
            yield _sse({"type": "progress", "pct": 88, "msg": "🧠 RMC: 설계 해설을 작성하고 있습니다..."})
            from archpilot.core.models import DesignRationale
            from archpilot.llm.prompts import DESIGN_RATIONALE_PROMPT

            rationale_user_msg = (
                f"시나리오: {resolved_scenario}\n"
                f"요구사항: {req.requirements}\n\n"
                f"레거시 시스템:\n{compress_system_dict(s.system, MAX_SYSTEM_CHARS)}\n\n"
                f"현대화 설계 결과:\n{compress_for_plan(s.modern, MAX_PLAN_SYSTEM_CHARS)}"
            )
            if s.analysis:
                rationale_user_msg += (
                    f"\n\n분석 참고 (component_decisions, pain_points):\n"
                    + json.dumps(
                        {k: s.analysis[k] for k in _RATIONALE_ANALYSIS_KEYS if k in s.analysis},
                        ensure_ascii=False,
                    )
                )
            rationale_text = ""
            async for chunk in client.stream_chat(
                DESIGN_RATIONALE_PROMPT + "\nIMPORTANT: Output ONLY raw JSON, no markdown fences.",
                rationale_user_msg,
                max_tokens=MAX_RATIONALE_TOKENS,
            ):
                rationale_text += chunk

            try:
                rationale_dict = json.loads(_clean_json(rationale_text))
                rationale = DesignRationale.model_validate(rationale_dict)
                s.design_rationale = json.loads(rationale.model_dump_json())
            except (json.JSONDecodeError, ValueError) as e:
                _log.warning("[modernize] 설계 해설 파싱 실패 (무시): %s", e)
                s.design_rationale = None

            # ── ④ RMC 3rd-pass: 마이그레이션 계획 자기평가 ───────────────────
            yield _sse({"type": "progress", "pct": 95, "msg": "🧠 RMC: 마이그레이션 계획을 자기검토하고 있습니다..."})
            from archpilot.core.models import MigrationPlanRMC
            from archpilot.llm.prompts import MIGRATION_PLAN_RMC_PROMPT

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
            plan_rmc_user_msg = (
                f"시스템: {s.system.get('name', '(미상)') if s.system else '(미상)'}\n"
                f"시나리오: {resolved_scenario}"
                f"{analysis_ctx}\n\n"
                f"작성한 마이그레이션 계획:\n{s.migration_plan[:8000]}"
            )
            plan_rmc_text = ""
            async for chunk in client.stream_chat(
                MIGRATION_PLAN_RMC_PROMPT + "\nIMPORTANT: Output ONLY raw JSON, no markdown fences.",
                plan_rmc_user_msg,
                max_tokens=MAX_RMC_TOKENS,
            ):
                plan_rmc_text += chunk

            try:
                plan_rmc_dict = json.loads(_clean_json(plan_rmc_text))
                plan_rmc = MigrationPlanRMC.model_validate(plan_rmc_dict)
                s.migration_plan_rmc = json.loads(plan_rmc.model_dump_json())
            except (json.JSONDecodeError, ValueError) as e:
                _log.warning("[modernize] 마이그레이션 계획 RMC 파싱 실패 (무시): %s", e)
                s.migration_plan_rmc = None

            # ── 파일 저장 (블로킹 I/O → 스레드 오프로드) ────────────────────
            output_dir = request.app.state.output_dir
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
            })

        except Exception as e:
            _log.exception("[modernize] 오류: %s", e)
            yield _sse({"type": "error", "msg": str(e)})

    return await _stream_response(generator())
