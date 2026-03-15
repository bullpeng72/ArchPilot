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


def compress_system_dict(d: dict, max_chars: int = MAX_PAYLOAD_CHARS) -> str:
    """시스템 dict를 LLM 컨텍스트 길이 제한에 맞게 압축·직렬화한다.

    압축 단계 (필요한 경우에만 순차 적용):
    1. indent=2 JSON — 제한 이하면 그대로 반환
    2. indent 제거 — ~30% 절감
    3. component metadata/specs 제거 — 경고 출력 후 반환
    """
    payload = json.dumps(d, ensure_ascii=False, indent=2)
    if len(payload) <= max_chars:
        return payload

    compact = json.dumps(d, ensure_ascii=False)
    if len(compact) <= max_chars:
        return compact

    # metadata/specs 제거 후 재직렬화
    d_copy = json.loads(compact)
    dropped = sum(
        1 for c in d_copy.get("components", [])
        if c.get("metadata") or c.get("specs")
    )
    for c in d_copy.get("components", []):
        c.pop("metadata", None)
        c.pop("specs", None)
    if dropped:
        _console.print(
            f"[yellow]⚠ 대형 시스템: {dropped}개 컴포넌트의 metadata/specs를 "
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
    3. 핵심 필드만 보존:
       - component_decisions (필수 — partial/additive 시나리오 핵심)
       - recommended_scenario, scenario_rationale, health_score, estimated_effort
       - legacy_quality, compliance_gaps(3개), security_findings(3개), pain_points(3개)
    """
    d = json.loads(analysis.model_dump_json())

    # 1단계: compact
    payload = json.dumps(d, ensure_ascii=False)
    if len(payload) <= max_chars:
        return payload

    # 2단계: 목록 필드 축약
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

    payload = json.dumps(d, ensure_ascii=False)
    if len(payload) <= max_chars:
        return payload

    # 3단계: 핵심 필드만 추출 — component_decisions 반드시 보존
    n_decisions = len(d.get("component_decisions", []))
    essential: dict = {
        "system_name": d.get("system_name"),
        "health_score": d.get("health_score"),
        "recommended_scenario": d.get("recommended_scenario"),
        "scenario_rationale": d.get("scenario_rationale"),
        "estimated_effort": d.get("estimated_effort"),
        "legacy_quality": d.get("legacy_quality"),
        "component_decisions": d.get("component_decisions", []),
    }
    for key in ("pain_points", "compliance_gaps", "security_findings"):
        if d.get(key):
            essential[key] = d[key][:3]

    _console.print(
        f"[yellow]⚠ 분석 결과 압축: 상세 항목 제거, "
        f"component_decisions({n_decisions}개)·시나리오 보존[/yellow]"
    )
    return json.dumps(essential, ensure_ascii=False)


# 마이그레이션 플랜용 보존 metadata 키 (strategy/reason/replaces 는 플랜 품질에 직결)
_PLAN_META_KEEP = {"strategy", "replaces", "reason", "is_new"}


def compress_for_plan(d: dict, max_chars: int = MAX_PLAN_SYSTEM_CHARS) -> str:
    """마이그레이션 플랜 생성용 압축.

    compress_system_dict와 달리 metadata의 핵심 키(strategy/reason/replaces)를
    마지막까지 보존한다. specs와 verbose 메타 키만 먼저 제거한다.

    압축 단계:
    1. indent=2  → 제한 이하이면 반환
    2. indent 제거
    3. specs + 비핵심 metadata 제거
    4. 핵심 metadata도 제거 (최후 수단) — 경고 출력
    """
    payload = json.dumps(d, ensure_ascii=False, indent=2)
    if len(payload) <= max_chars:
        return payload

    compact = json.dumps(d, ensure_ascii=False)
    if len(compact) <= max_chars:
        return compact

    # specs 제거 + metadata는 핵심 키만 보존
    d_copy = json.loads(compact)
    for c in d_copy.get("components", []):
        c.pop("specs", None)
        meta = c.get("metadata", {})
        if meta:
            trimmed_meta = {k: v for k, v in meta.items() if k in _PLAN_META_KEEP}
            if trimmed_meta:
                c["metadata"] = trimmed_meta
            else:
                c.pop("metadata", None)

    trimmed = json.dumps(d_copy, ensure_ascii=False)
    if len(trimmed) <= max_chars:
        return trimmed

    # 최후 수단: 핵심 metadata도 제거
    dropped = sum(1 for c in d_copy.get("components", []) if c.get("metadata"))
    for c in d_copy.get("components", []):
        c.pop("metadata", None)
    if dropped:
        _console.print(
            f"[yellow]⚠ 플랜 압축: {dropped}개 컴포넌트의 strategy/reason을 제거했습니다 "
            f"(LLM 컨텍스트 {max_chars:,}자 제한)[/yellow]"
        )
    return json.dumps(d_copy, ensure_ascii=False)
