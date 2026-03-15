"""패턴 그라운딩 — LLM 호출 시 DT/AI 패턴 지식을 컨텍스트로 주입."""

from __future__ import annotations

from archpilot.core.transformation_patterns import TransformationPattern, match_patterns


def build_pattern_grounding(
    system_dict: dict,
    top_k: int = 8,
    max_chars: int = 6_000,
) -> str:
    """시스템 dict에서 컴포넌트 타입·기술 스택을 추출해 관련 DT/AI 패턴 그라운딩 텍스트 반환.

    Args:
        system_dict: SystemModel.model_dump() 결과
        top_k:       주입할 최대 패턴 수
        max_chars:   반환 문자열 최대 길이 (LLM 컨텍스트 보호)

    Returns:
        LLM user_msg에 추가할 그라운딩 텍스트 (빈 시스템이면 빈 문자열)
    """
    if not system_dict:
        return ""
    components = system_dict.get("components", [])
    if not components:
        return ""

    # 컴포넌트 타입 수집
    component_types: list[str] = [c.get("type", "") for c in components if c.get("type")]

    # 기술 키워드 수집 (소문자)
    tech_keywords: list[str] = []
    for c in components:
        for tech in c.get("tech", []):
            tech_keywords.append(str(tech).lower())

    # 도메인·이슈 키워드도 추가 (매칭 정확도 향상)
    for issue in system_dict.get("known_issues", []):
        tech_keywords.extend(str(issue).lower().split())
    compliance = system_dict.get("compliance", [])
    tech_keywords.extend(str(c).lower() for c in compliance)

    patterns = match_patterns(component_types, tech_keywords, top_k=top_k)
    if not patterns:
        return ""

    return _format_grounding(patterns, max_chars)


def _format_grounding(patterns: list[TransformationPattern], max_chars: int) -> str:
    """패턴 목록을 LLM 주입용 텍스트로 포맷."""
    dt_patterns = [p for p in patterns if p.category == "DT"]
    ai_patterns = [p for p in patterns if p.category == "AI"]

    lines: list[str] = [
        "",
        "=== 관련 DT/AI 전환 패턴 (지식 그라운딩) ===",
        "아래 패턴들은 이 시스템의 컴포넌트 구성·기술 스택 기반으로 자동 선별되었습니다.",
        "분석·설계 시 해당 패턴의 적용 가능성과 트레이드오프를 반드시 고려하십시오.",
    ]

    if dt_patterns:
        lines.append("\n[디지털 트랜스포메이션 패턴]")
        for p in dt_patterns:
            lines.append(f"\n■ {p.name}")
            lines.append(f"  요약: {p.summary}")
            lines.append(f"  문제: {p.problem}")
            lines.append(f"  해법: {p.solution}")
            if p.benefits:
                lines.append(f"  이점: {', '.join(p.benefits)}")
            if p.tradeoffs:
                lines.append(f"  트레이드오프: {', '.join(p.tradeoffs)}")
            if p.when_to_apply:
                lines.append(f"  적용 시점: {p.when_to_apply}")

    if ai_patterns:
        lines.append("\n[AI 트랜스포메이션 패턴]")
        for p in ai_patterns:
            lines.append(f"\n■ {p.name}")
            lines.append(f"  요약: {p.summary}")
            lines.append(f"  문제: {p.problem}")
            lines.append(f"  해법: {p.solution}")
            if p.benefits:
                lines.append(f"  이점: {', '.join(p.benefits)}")
            if p.tradeoffs:
                lines.append(f"  트레이드오프: {', '.join(p.tradeoffs)}")
            if p.when_to_apply:
                lines.append(f"  적용 시점: {p.when_to_apply}")

    lines.append("\n=== 패턴 그라운딩 끝 ===")

    text = "\n".join(lines)
    # 길이 제한
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...(패턴 그라운딩 일부 생략)"
    return text
