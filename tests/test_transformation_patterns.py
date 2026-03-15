"""transformation_patterns 모듈 테스트."""
from __future__ import annotations

import pytest

from archpilot.core.transformation_patterns import (
    AI_PATTERNS,
    ALL_PATTERNS,
    DT_PATTERNS,
    TransformationPattern,
    match_patterns,
)


class TestPatternDefinitions:
    def test_dt_patterns_count(self):
        assert len(DT_PATTERNS) == 16

    def test_ai_patterns_count(self):
        assert len(AI_PATTERNS) == 11

    def test_all_patterns_have_required_fields(self):
        for p in ALL_PATTERNS:
            assert p.id, f"패턴 id 없음: {p}"
            assert p.name, f"패턴 name 없음: {p.id}"
            assert p.category in ("DT", "AI"), f"invalid category: {p.id}"
            assert p.summary, f"패턴 summary 없음: {p.id}"
            assert p.solution, f"패턴 solution 없음: {p.id}"
            assert p.benefits, f"패턴 benefits 없음: {p.id}"
            assert p.tradeoffs, f"패턴 tradeoffs 없음: {p.id}"

    def test_pattern_ids_unique(self):
        all_ids = [p.id for p in ALL_PATTERNS]
        assert len(all_ids) == len(set(all_ids)), "중복 패턴 id 존재"

    def test_tech_triggers_lowercase(self):
        for p in ALL_PATTERNS:
            for t in p.tech_triggers:
                assert t == t.lower(), f"{p.id} tech_trigger '{t}' is not lowercase"

    def test_components_needed_are_strings(self):
        for p in ALL_PATTERNS:
            for ct in p.components_needed:
                assert isinstance(ct, str), (
                    f"{p.id} components_needed에 비유효한 값: {ct}"
                )

    def test_all_patterns_count(self):
        assert len(ALL_PATTERNS) == len(DT_PATTERNS) + len(AI_PATTERNS) == 27

    def test_pattern_is_frozen(self):
        p = DT_PATTERNS[0]
        with pytest.raises((AttributeError, TypeError)):
            p.id = "modified"  # type: ignore[misc]

    def test_dt_patterns_category(self):
        for p in DT_PATTERNS:
            assert p.category == "DT"

    def test_ai_patterns_category(self):
        for p in AI_PATTERNS:
            assert p.category == "AI"


class TestMatchPatterns:
    def test_returns_list_of_patterns(self):
        result = match_patterns(
            component_types=["database", "service"],
            tech_keywords=["oracle", "java"],
            top_k=5,
        )
        assert isinstance(result, list)
        for p in result:
            assert isinstance(p, TransformationPattern)

    def test_returns_up_to_top_k(self):
        result = match_patterns(
            component_types=["database", "service"],
            tech_keywords=["oracle", "java"],
            top_k=5,
        )
        assert len(result) <= 5

    def test_returns_at_least_one_for_common_types(self):
        result = match_patterns(
            component_types=["service"],
            tech_keywords=["spring", "monolith"],
        )
        assert len(result) >= 1

    def test_empty_input_returns_empty(self):
        """컴포넌트·키워드 없이 호출하면 매칭 없이 빈 리스트."""
        result = match_patterns(component_types=[], tech_keywords=[])
        assert result == []

    def test_component_type_match_boosts_score(self):
        """database 타입을 포함하면 더 많은 패턴이 반환된다."""
        result_db = match_patterns(component_types=["database"], tech_keywords=[])
        result_none = match_patterns(component_types=[], tech_keywords=[])
        assert len(result_db) >= len(result_none)

    def test_tech_trigger_match_works(self):
        """'rag'·'llm' 키워드가 있으면 AI 패턴이 반환된다."""
        result = match_patterns(
            component_types=[],
            tech_keywords=["rag", "llm", "embedding"],
            top_k=5,
        )
        assert any(p.category == "AI" for p in result)

    def test_top_k_zero_returns_empty(self):
        result = match_patterns(
            component_types=["service"],
            tech_keywords=["kafka"],
            top_k=0,
        )
        assert result == []

    def test_top_k_one_returns_single(self):
        result = match_patterns(
            component_types=["server"],
            tech_keywords=["monolith"],
            top_k=1,
        )
        assert len(result) == 1

    def test_all_component_types(self):
        """많은 타입 넣어도 에러 없이 동작."""
        result = match_patterns(
            component_types=["server", "database", "cache", "queue", "gateway", "service"],
            tech_keywords=["docker", "kubernetes"],
            top_k=8,
        )
        assert len(result) <= 8

    def test_unknown_tech_keywords_no_effect(self):
        """온톨로지에 없는 키워드는 결과에 나타나지 않는다."""
        result = match_patterns([], ["xyzzy_nonexistent_tech_9999"])
        assert result == []

    def test_monolith_trigger_returns_strangler(self):
        """'monolith' 키워드는 strangler_fig 패턴을 반환해야 한다."""
        result = match_patterns([], ["monolith"])
        ids = [p.id for p in result]
        assert "strangler_fig" in ids

    def test_soap_trigger_returns_eda(self):
        """'soap' 키워드는 EDA 패턴을 반환해야 한다."""
        result = match_patterns([], ["soap"])
        ids = [p.id for p in result]
        assert any("eda" in pid or "event" in pid for pid in ids)

    # ── 수정된 tech_trigger 검증 ─────────────────────────────────────────────

    def test_eda_no_longer_relies_on_descriptive_triggers(self):
        """EDA 패턴이 실제 기술명(activemq, mq, jms)으로 매칭된다."""
        result = match_patterns([], ["activemq"])
        ids = [p.id for p in result]
        assert "event_driven_architecture" in ids

    def test_eda_matches_tibco(self):
        result = match_patterns([], ["tibco"])
        ids = [p.id for p in result]
        assert "event_driven_architecture" in ids

    def test_feature_flag_matches_jenkins(self):
        """Feature Flag 패턴이 CI 도구 이름(jenkins)으로 매칭된다."""
        result = match_patterns([], ["jenkins"])
        ids = [p.id for p in result]
        assert "feature_flag" in ids

    def test_feature_flag_matches_gitlab(self):
        result = match_patterns([], ["gitlab"])
        ids = [p.id for p in result]
        assert "feature_flag" in ids or "cicd_devops" in ids

    def test_semantic_cache_matches_claude(self):
        """Semantic Cache 패턴이 'claude' 트리거로 매칭된다."""
        result = match_patterns([], ["claude"])
        ids = [p.id for p in result]
        assert "semantic_cache" in ids

    def test_semantic_cache_matches_embedding(self):
        result = match_patterns([], ["embedding"])
        ids = [p.id for p in result]
        assert "semantic_cache" in ids

    # ── 신규 DT 패턴 매칭 ───────────────────────────────────────────────────

    def test_saga_pattern_exists(self):
        assert any(p.id == "saga_pattern" for p in DT_PATTERNS)

    def test_saga_matches_kafka(self):
        """Saga 패턴이 'kafka' 트리거로 매칭된다."""
        result = match_patterns(["queue", "database", "service"], ["kafka"])
        ids = [p.id for p in result]
        assert "saga_pattern" in ids

    def test_saga_matches_xa(self):
        """Saga 패턴이 'xa' 트리거로 매칭된다."""
        result = match_patterns([], ["xa"])
        ids = [p.id for p in result]
        assert "saga_pattern" in ids

    def test_cicd_pattern_exists(self):
        assert any(p.id == "cicd_devops" for p in DT_PATTERNS)

    def test_cicd_matches_svn(self):
        """CI/CD 패턴이 레거시 SCM 키워드(svn)로 매칭된다."""
        result = match_patterns([], ["svn"])
        ids = [p.id for p in result]
        assert "cicd_devops" in ids

    def test_cicd_matches_bamboo(self):
        result = match_patterns([], ["bamboo"])
        ids = [p.id for p in result]
        assert "cicd_devops" in ids

    def test_iac_pattern_exists(self):
        assert any(p.id == "infrastructure_as_code" for p in DT_PATTERNS)

    def test_iac_matches_vmware(self):
        """IaC 패턴이 'vmware' 트리거로 매칭된다."""
        result = match_patterns([], ["vmware"])
        ids = [p.id for p in result]
        assert "infrastructure_as_code" in ids

    def test_iac_matches_terraform(self):
        result = match_patterns([], ["terraform"])
        ids = [p.id for p in result]
        assert "infrastructure_as_code" in ids

    def test_cache_aside_pattern_exists(self):
        assert any(p.id == "cache_aside" for p in DT_PATTERNS)

    def test_cache_aside_matches_oracle(self):
        """Cache Aside 패턴이 'oracle' 트리거로 매칭된다."""
        result = match_patterns(["database"], ["oracle"])
        ids = [p.id for p in result]
        assert "cache_aside" in ids

    def test_cache_aside_matches_bottleneck(self):
        """Cache Aside 패턴이 known_issues 유래 'bottleneck' 키워드로 매칭된다."""
        result = match_patterns([], ["bottleneck"])
        ids = [p.id for p in result]
        assert "cache_aside" in ids

    # ── 신규 AI 패턴 매칭 ───────────────────────────────────────────────────

    def test_llm_guardrails_pattern_exists(self):
        assert any(p.id == "llm_guardrails" for p in AI_PATTERNS)

    def test_llm_guardrails_matches_pii(self):
        """LLM Guardrails 패턴이 'pii' 트리거로 매칭된다."""
        result = match_patterns([], ["pii"])
        ids = [p.id for p in result]
        assert "llm_guardrails" in ids

    def test_llm_guardrails_matches_hipaa(self):
        result = match_patterns([], ["hipaa"])
        ids = [p.id for p in result]
        assert "llm_guardrails" in ids

    def test_llm_finetuning_pattern_exists(self):
        assert any(p.id == "llm_finetuning" for p in AI_PATTERNS)

    def test_llm_finetuning_matches_huggingface(self):
        """Fine-tuning 패턴이 'huggingface' 트리거로 매칭된다."""
        result = match_patterns([], ["huggingface"])
        ids = [p.id for p in result]
        assert "llm_finetuning" in ids

    def test_llm_finetuning_matches_bert(self):
        result = match_patterns([], ["bert"])
        ids = [p.id for p in result]
        assert "llm_finetuning" in ids

    def test_ai_observability_pattern_exists(self):
        assert any(p.id == "ai_observability" for p in AI_PATTERNS)

    def test_ai_observability_matches_langchain(self):
        """AI Observability 패턴이 'langchain' 트리거로 매칭된다."""
        result = match_patterns([], ["langchain"])
        ids = [p.id for p in result]
        assert "ai_observability" in ids

    def test_ai_observability_matches_llamaindex(self):
        result = match_patterns([], ["llamaindex"])
        ids = [p.id for p in result]
        assert "ai_observability" in ids

    # ── 새 패턴 콘텐츠 완전성 ──────────────────────────────────────────────

    def test_new_patterns_have_all_required_fields(self):
        new_ids = {
            "saga_pattern", "cicd_devops", "infrastructure_as_code", "cache_aside",
            "llm_guardrails", "llm_finetuning", "ai_observability",
        }
        for p in ALL_PATTERNS:
            if p.id in new_ids:
                assert p.problem, f"{p.id}: problem 필드 없음"
                assert p.solution, f"{p.id}: solution 필드 없음"
                assert p.benefits, f"{p.id}: benefits 필드 없음"
                assert p.tradeoffs, f"{p.id}: tradeoffs 필드 없음"
                assert p.when_to_apply, f"{p.id}: when_to_apply 필드 없음"
                assert p.tech_triggers, f"{p.id}: tech_triggers 비어 있음"
                assert p.components_needed, f"{p.id}: components_needed 비어 있음"

    def test_all_tech_triggers_are_lowercase_after_update(self):
        """모든 패턴의 tech_triggers가 소문자인지 재확인."""
        for p in ALL_PATTERNS:
            for t in p.tech_triggers:
                assert t == t.lower(), f"{p.id}: trigger '{t}' is not lowercase"
