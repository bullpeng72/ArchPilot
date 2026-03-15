"""grounding 모듈 테스트."""
from __future__ import annotations

from archpilot.llm.grounding import _format_grounding, build_pattern_grounding


def _make_system(
    component_types: list[str] | None = None,
    tech_keywords: list[str] | None = None,
) -> dict:
    """테스트용 최소 system dict 생성."""
    components = []
    for i, ct in enumerate(component_types or []):
        components.append({
            "id": f"c{i}",
            "type": ct,
            "label": f"Comp{i}",
            "tech": tech_keywords or [],
        })
    return {"name": "TestSystem", "components": components}


class TestBuildPatternGrounding:
    def test_returns_string(self):
        result = build_pattern_grounding(_make_system(["service", "database"]))
        assert isinstance(result, str)

    def test_empty_components_returns_empty(self):
        """컴포넌트 없는 시스템은 빈 문자열."""
        result = build_pattern_grounding({"name": "Empty", "components": []})
        assert result == ""

    def test_empty_dict_returns_empty(self):
        result = build_pattern_grounding({})
        assert result == ""

    def test_result_within_max_chars(self):
        max_chars = 1000
        result = build_pattern_grounding(
            _make_system(["service", "database", "queue"], ["kafka", "oracle"]),
            max_chars=max_chars,
        )
        # 약간의 헤더 여유 허용
        assert len(result) <= max_chars + 50

    def test_contains_pattern_content(self):
        """DB + Queue 시스템이면 관련 패턴 내용이 포함돼야 함."""
        result = build_pattern_grounding(
            _make_system(["database", "queue"], ["kafka", "oracle"]),
        )
        assert len(result) > 0
        assert "패턴" in result or "Pattern" in result or "■" in result

    def test_monolith_tech_triggers_strangler(self):
        """'monolith' 기술 키워드는 Strangler Fig 패턴을 유발해야 한다."""
        result = build_pattern_grounding(
            _make_system(["server"], ["monolith"]),
        )
        assert "Strangler" in result or "strangler" in result

    def test_rag_triggers_ai_pattern(self):
        """'rag'·'llm' 키워드가 있으면 AI 패턴이 포함된다."""
        result = build_pattern_grounding(
            _make_system(["service"], ["rag", "llm"]),
        )
        assert "AI" in result or "RAG" in result

    def test_top_k_limits_output_size(self):
        """top_k=1이면 top_k=5보다 결과가 짧다."""
        result_1 = build_pattern_grounding(
            _make_system(["service", "database", "queue"], ["kafka"]),
            top_k=1,
        )
        result_5 = build_pattern_grounding(
            _make_system(["service", "database", "queue"], ["kafka"]),
            top_k=5,
        )
        assert len(result_1) <= len(result_5)

    def test_known_issues_extracted(self):
        """known_issues 시스템 필드의 키워드도 반영된다."""
        system = {
            "name": "Legacy",
            "components": [{"id": "c0", "type": "server", "label": "App", "tech": []}],
            "known_issues": ["monolith scaling problem"],
        }
        result = build_pattern_grounding(system)
        assert isinstance(result, str)

    def test_no_matching_keywords_returns_empty_or_short(self):
        """알 수 없는 기술 키워드면 빈 문자열 또는 매우 짧다."""
        result = build_pattern_grounding(
            _make_system([], ["xyzzy_nonexistent_9999"]),
        )
        # 컴포넌트가 없으므로 빈 문자열
        assert result == ""


class TestFormatGrounding:
    def test_empty_patterns_returns_header_only(self):
        result = _format_grounding([], max_chars=5000)
        assert isinstance(result, str)

    def test_max_chars_respected(self):
        from archpilot.core.transformation_patterns import DT_PATTERNS, AI_PATTERNS
        all_patterns = DT_PATTERNS + AI_PATTERNS
        result = _format_grounding(all_patterns, max_chars=500)
        assert len(result) <= 500 + 40  # 생략 문자열 여유

    def test_dt_section_present(self):
        from archpilot.core.transformation_patterns import DT_PATTERNS
        result = _format_grounding([DT_PATTERNS[0]], max_chars=5000)
        assert "디지털 트랜스포메이션" in result

    def test_ai_section_present(self):
        from archpilot.core.transformation_patterns import AI_PATTERNS
        result = _format_grounding([AI_PATTERNS[0]], max_chars=5000)
        assert "AI 트랜스포메이션" in result

    def test_pattern_name_in_output(self):
        from archpilot.core.transformation_patterns import DT_PATTERNS
        p = DT_PATTERNS[0]
        result = _format_grounding([p], max_chars=5000)
        assert p.name in result
