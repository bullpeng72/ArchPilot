"""LLM 호출 공통 유틸리티 — 페이로드 압축 및 컨텍스트 상수."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from archpilot.core.models import AnalysisResult, SystemModel

_console = Console(stderr=True)

# ── 대형 시스템 임계값 ────────────────────────────────────────────────────────
# 이 값 초과 시 2단계 분할 현대화(Skeleton → Enrich) 자동 적용
LARGE_SYSTEM_THRESHOLD: int = 20

# ── LLM 컨텍스트 길이 제한 (문자 수) ─────────────────────────────────────────
# GPT-4o 컨텍스트 = 128k 토큰 ≈ 51만 자. 아래 한도는 비용 절감보다 품질 보존 우선.
# analyze  : 단일 시스템 페이로드 (~컴포넌트 60개 수준)
MAX_PAYLOAD_CHARS: int = 40_000
# modernize: 시스템 1개 (32개+ 컴포넌트 metadata 보존을 위해 여유 확보)
MAX_SYSTEM_CHARS: int = 40_000
# modernize: analysis 결과 압축 상한 — component_decisions 보존 우선
MAX_ANALYSIS_CHARS: int = 12_000
# migration plan: 레거시 + 현대 두 시스템을 포함, modern의 strategy/reason 보존 필수
MAX_PLAN_SYSTEM_CHARS: int = 30_000

# ── LLM 출력 토큰 상한 ────────────────────────────────────────────────────────
# chat ingest: 대화형 시스템 추출 — 단일 사용자 메시지 응답
MAX_CHAT_TOKENS: int = 4_096
# analyze: 분석 JSON — 컴포넌트 10개 기준 ~3000 토큰
MAX_ANALYZE_TOKENS: int = 6_000
# modernize: 현대화 시스템 JSON — 30개+ 컴포넌트 기준 ~12000 토큰
# 대규모 레거시(20개+)는 동등한 수의 현대화 컴포넌트가 필요하므로 여유 있게 설정
MAX_MODERNIZE_TOKENS: int = 16_000
# skeleton: 컴포넌트 목록만 생성 (id/type/label/host/strategy) — 경량
MAX_SKELETON_TOKENS: int = 4_000
# migration plan: 마크다운 11섹션 — 대규모 시스템에서 4096 토큰 초과
MAX_PLAN_TOKENS: int = 6_000
# RMC 분석 자기평가: JSON 구조 — 대규모 시스템에서 3000 토큰 초과 가능
MAX_RMC_TOKENS: int = 4_000
# RMC 설계 해설: 6개+ 결정 + 12차원 품질 평가 + 자기평가 — 대규모에서 6000 토큰 초과
MAX_RATIONALE_TOKENS: int = 10_000
# 멀티 퍼스펙티브: 8개 관점 × ~300 토큰 + 종합 요약 — 대규모 시스템에서 5000 토큰 초과 가능
MAX_PERSPECTIVE_TOKENS: int = 6_000

# 마이그레이션 플랜 및 시스템 압축 시 보존할 metadata 핵심 키
# strategy/reason/replaces/is_new 는 partial·additive 시나리오 설계 품질에 직결
_PLAN_META_KEEP = {"strategy", "replaces", "reason", "is_new"}


def compress_system_dict(d: dict, max_chars: int = MAX_PAYLOAD_CHARS) -> str:
    """시스템 dict를 LLM 컨텍스트 길이 제한에 맞게 압축·직렬화한다.

    압축 단계 (필요한 경우에만 순차 적용):
    1. indent=2 JSON — 제한 이하면 그대로 반환
    2. indent 제거 — ~30% 절감
    3. specs 제거 + metadata는 핵심 키(strategy/reason/replaces/is_new)만 보존
    4. 핵심 metadata도 제거 (최후 수단) — 경고 출력 후 반환
    """
    payload = json.dumps(d, ensure_ascii=False, indent=2)
    if len(payload) <= max_chars:
        return payload

    compact = json.dumps(d, ensure_ascii=False)
    if len(compact) <= max_chars:
        return compact

    # 3단계: specs 제거 + metadata는 핵심 키만 보존
    d_copy = json.loads(compact)
    for c in d_copy.get("components", []):
        c.pop("specs", None)
        meta = c.get("metadata", {})
        if meta:
            trimmed = {k: v for k, v in meta.items() if k in _PLAN_META_KEEP}
            if trimmed:
                c["metadata"] = trimmed
            else:
                c.pop("metadata", None)

    trimmed_payload = json.dumps(d_copy, ensure_ascii=False)
    if len(trimmed_payload) <= max_chars:
        return trimmed_payload

    # 4단계: 핵심 metadata도 제거 (최후 수단)
    dropped = sum(1 for c in d_copy.get("components", []) if c.get("metadata"))
    for c in d_copy.get("components", []):
        c.pop("metadata", None)
    if dropped:
        _console.print(
            f"[yellow]⚠ 대형 시스템: {dropped}개 컴포넌트의 strategy/reason까지 "
            f"제거했습니다 (LLM 컨텍스트 {max_chars:,}자 제한)[/yellow]"
        )
    return json.dumps(d_copy, ensure_ascii=False)


def compress_model(model: "SystemModel", max_chars: int = MAX_SYSTEM_CHARS) -> str:
    """SystemModel을 LLM 컨텍스트 길이 제한에 맞게 압축·직렬화한다."""
    return compress_system_dict(json.loads(model.model_dump_json()), max_chars)


def compress_analysis(analysis: "AnalysisResult", max_chars: int = MAX_ANALYSIS_CHARS) -> str:
    """AnalysisResult를 modernize 페이로드용으로 압축·직렬화한다.

    압축 단계 (순차 적용, 필요한 경우에만):
    1. compact JSON (indent 제거) — 제한 이하이면 반환
    2. 목록 필드(pain_points·tech_debt·risk_areas·opportunities·patterns) 각 3개로 축약
       + multi_perspective는 perspectives[] 제거, consensus_summary·priority_actions만 보존
    3. 핵심 필드만 보존:
       - component_decisions (필수 — partial/additive 시나리오 핵심)
       - recommended_scenario, scenario_rationale, health_score, estimated_effort
       - legacy_quality, compliance_gaps(3개), security_findings(3개), pain_points(3개)
       - multi_perspective.consensus_summary + priority_actions(3개)
    """
    d = json.loads(analysis.model_dump_json())

    # 1단계: compact
    payload = json.dumps(d, ensure_ascii=False)
    if len(payload) <= max_chars:
        return payload

    # 2단계: 목록 필드 축약 + multi_perspective 경량화
    _truncate_limits: list[tuple[str, int]] = [
        ("pain_points", 3),
        ("modernization_opportunities", 3),
        ("tech_debt", 3),
        ("risk_areas", 3),
        ("recommended_patterns", 3),
        ("compliance_gaps", 5),
        ("security_findings", 5),
    ]
    for key, limit in _truncate_limits:
        if d.get(key) and len(d[key]) > limit:
            d[key] = d[key][:limit]

    # multi_perspective: perspectives[] 상세 제거, 합의 요약만 보존
    mp = d.get("multi_perspective")
    if mp and isinstance(mp, dict):
        d["multi_perspective"] = {
            "consensus_summary": mp.get("consensus_summary", ""),
            "priority_actions": mp.get("priority_actions", [])[:3],
            "conflict_areas": mp.get("conflict_areas", [])[:2],
        }

    payload = json.dumps(d, ensure_ascii=False)
    if len(payload) <= max_chars:
        return payload

    # 3단계: 핵심 필드만 추출 — component_decisions 반드시 보존
    n_decisions = len(d.get("component_decisions", []))
    mp_summary = (d.get("multi_perspective") or {}).get("consensus_summary")
    essential: dict = {
        "system_name": d.get("system_name"),
        "health_score": d.get("health_score"),
        "recommended_scenario": d.get("recommended_scenario"),
        "scenario_rationale": d.get("scenario_rationale"),
        "estimated_effort": d.get("estimated_effort"),
        "legacy_quality": d.get("legacy_quality"),
        "component_decisions": d.get("component_decisions", []),
    }
    if mp_summary:
        essential["multi_perspective"] = {
            "consensus_summary": mp_summary,
            "priority_actions": (d.get("multi_perspective") or {}).get("priority_actions", [])[:3],
        }
    for key in ("pain_points", "compliance_gaps", "security_findings"):
        if d.get(key):
            essential[key] = d[key][:3]

    _console.print(
        f"[yellow]⚠ 분석 결과 압축: 상세 항목 제거, "
        f"component_decisions({n_decisions}개)·시나리오 보존[/yellow]"
    )
    return json.dumps(essential, ensure_ascii=False)


def build_component_checklist(
    analysis_dict: dict | None,
    legacy_comps: list[dict],
) -> tuple[str, list[str], set[str], int]:
    """레거시 컴포넌트 체크리스트를 구성한다.

    UI 라우터와 CLI 현대화 공통 로직 — raw dict 기반.

    Args:
        analysis_dict: AppSession.analysis (JSON dict) 또는 None
        legacy_comps:  system["components"] 목록

    Returns:
        checklist:       포맷된 체크리스트 문자열
        must_include_ids: retire 제외 처리 대상 id 목록
        retire_ids:      retire 대상 id 집합
        min_modern_comps: 현대화 결과 최소 컴포넌트 수
    """
    decisions: list[dict] = (analysis_dict or {}).get("component_decisions", [])
    decisions_by_id: dict[str, str] = {
        d.get("component_id"): d.get("action")
        for d in decisions
        if d.get("component_id")
    }
    retire_ids: set[str] = {
        d.get("component_id")
        for d in decisions
        if d.get("action") == "retire" and d.get("component_id")
    }
    lines = []
    for c in legacy_comps:
        action = decisions_by_id.get(c["id"], "")
        action_str = f" → {action}" if action else ""
        lines.append(f"  - {c['id']} ({c.get('type', '?')}){action_str}")

    must_include_ids = [c["id"] for c in legacy_comps if c["id"] not in retire_ids]
    min_modern_comps = max(len(legacy_comps) - len(retire_ids), 1)
    return "\n".join(lines), must_include_ids, retire_ids, min_modern_comps


def compress_for_plan(d: dict, max_chars: int = MAX_PLAN_SYSTEM_CHARS) -> str:
    """마이그레이션 플랜 생성용 압축 (compress_system_dict 위임).

    기본 상한이 MAX_PLAN_SYSTEM_CHARS(30,000)로 modernize보다 작으며,
    압축 로직은 compress_system_dict와 동일하게 strategy/reason을 최후까지 보존한다.
    """
    return compress_system_dict(d, max_chars)
