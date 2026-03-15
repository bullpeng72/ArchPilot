"""llm/utils.py 단위 테스트 — 압축 함수 3단계 검증."""

from __future__ import annotations

import json

import pytest

from archpilot.core.models import (
    AnalysisResult,
    ComponentDecision,
    ModernizationAction,
    ModernizationScenario,
)
from archpilot.llm.utils import (
    MAX_ANALYSIS_CHARS,
    MAX_PAYLOAD_CHARS,
    MAX_PLAN_SYSTEM_CHARS,
    compress_analysis,
    compress_for_plan,
    compress_model,
    compress_system_dict,
)


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _make_system(n_components: int, with_metadata: bool = False) -> dict:
    """n개 컴포넌트를 가진 시스템 dict 생성."""
    components = []
    for i in range(n_components):
        c: dict = {"id": f"c{i}", "type": "server", "label": f"Component {i}"}
        if with_metadata:
            c["metadata"] = {"detail": "x" * 200, "extra": "y" * 200}
            c["specs"] = {"cpu": 4, "ram": "16GB"}
        components.append(c)
    return {"name": "Test System", "components": components, "connections": []}


def _make_analysis(
    n_components: int = 3,
    n_pain_points: int = 3,
    with_large_lists: bool = False,
) -> AnalysisResult:
    """AnalysisResult 객체 생성."""
    decisions = [
        ComponentDecision(
            component_id=f"c{i}",
            action=ModernizationAction.REPLATFORM,
            rationale="성능 개선 필요",
        )
        for i in range(n_components)
    ]
    pain_points = [f"pain_{i}" for i in range(n_pain_points)]
    tech_debt_raw = []
    risk_areas_raw = []

    if with_large_lists:
        pain_points = [f"pain_{i} " + "x" * 100 for i in range(20)]

    return AnalysisResult(
        system_name="Test",
        health_score=60,
        recommended_scenario=ModernizationScenario.PARTIAL,
        scenario_rationale="일부 컴포넌트 재사용 가능",
        component_decisions=decisions,
        pain_points=pain_points,
        estimated_effort="M",
    )


# ── compress_system_dict 테스트 ───────────────────────────────────────────────

class TestCompressSystemDict:
    def test_stage1_small_payload_returned_with_indent(self):
        """작은 시스템은 indent=2 JSON 그대로 반환."""
        d = _make_system(2)
        result = compress_system_dict(d, max_chars=MAX_PAYLOAD_CHARS)
        parsed = json.loads(result)
        assert parsed["name"] == "Test System"
        assert len(parsed["components"]) == 2
        # indent=2 형식 확인
        assert "\n" in result

    def test_stage2_compact_when_indent_exceeds_limit(self):
        """indent 형식이 한도 초과 시 compact JSON 반환."""
        d = _make_system(5)
        # 아주 작은 한도 설정해 indent 형식이 초과하도록
        indented = json.dumps(d, ensure_ascii=False, indent=2)
        compact = json.dumps(d, ensure_ascii=False)
        limit = len(indented) - 1  # indent는 초과, compact는 통과

        result = compress_system_dict(d, max_chars=limit)
        assert len(result) <= limit
        assert "\n" not in result  # compact 형식

    def test_stage3_metadata_dropped_when_compact_exceeds_limit(self):
        """compact도 초과 시 metadata/specs 제거."""
        d = _make_system(5, with_metadata=True)
        compact = json.dumps(d, ensure_ascii=False)
        # compact보다 1자 작은 한도 → metadata 제거 필요
        limit = len(compact) - 1

        result = compress_system_dict(d, max_chars=limit)
        parsed = json.loads(result)
        for comp in parsed["components"]:
            assert "metadata" not in comp
            assert "specs" not in comp

    def test_stage3_preserves_component_ids(self):
        """metadata 제거 후에도 컴포넌트 id 보존."""
        d = _make_system(3, with_metadata=True)
        result = compress_system_dict(d, max_chars=10)  # 극단적으로 작은 한도
        parsed = json.loads(result)
        ids = {c["id"] for c in parsed["components"]}
        assert ids == {"c0", "c1", "c2"}

    def test_exact_limit_boundary(self):
        """한도와 동일한 크기는 통과."""
        d = _make_system(1)
        payload = json.dumps(d, ensure_ascii=False, indent=2)
        result = compress_system_dict(d, max_chars=len(payload))
        assert json.loads(result) == json.loads(payload)

    def test_empty_components(self):
        """빈 컴포넌트 시스템도 정상 처리."""
        d = {"name": "Empty", "components": [], "connections": []}
        result = compress_system_dict(d)
        assert json.loads(result)["name"] == "Empty"


# ── compress_model 테스트 ─────────────────────────────────────────────────────

class TestCompressModel:
    def test_wraps_system_model(self, sample_model):
        """SystemModel을 dict로 변환 후 압축."""
        result = compress_model(sample_model)
        parsed = json.loads(result)
        assert parsed["name"] == "Test System"
        assert len(parsed["components"]) == 3


# ── compress_analysis 테스트 ─────────────────────────────────────────────────

class TestCompressAnalysis:
    def test_stage1_small_analysis_compact(self):
        """작은 분석 결과는 compact JSON 반환."""
        analysis = _make_analysis(n_components=2, n_pain_points=2)
        result = compress_analysis(analysis, max_chars=MAX_ANALYSIS_CHARS)
        parsed = json.loads(result)
        assert parsed["system_name"] == "Test"
        assert len(parsed["component_decisions"]) == 2

    def test_stage2_list_fields_truncated(self):
        """목록 필드가 한도 초과 시 각 3개로 축약."""
        analysis = _make_analysis(n_components=2, with_large_lists=True)
        # 충분히 작은 한도 설정
        compact = json.dumps(json.loads(analysis.model_dump_json()), ensure_ascii=False)
        limit = len(compact) - 1  # compact는 초과, 2단계 필요

        result = compress_analysis(analysis, max_chars=limit)
        parsed = json.loads(result)
        # pain_points가 3개 이하로 축약됐는지 확인
        assert len(parsed.get("pain_points", [])) <= 3

    def test_stage3_essential_only_with_decisions_preserved(self):
        """극단적으로 작은 한도: component_decisions 반드시 보존."""
        analysis = _make_analysis(n_components=5, with_large_lists=True)
        result = compress_analysis(analysis, max_chars=10)  # 극소 한도
        parsed = json.loads(result)
        # component_decisions는 무조건 보존
        assert "component_decisions" in parsed
        assert len(parsed["component_decisions"]) == 5

    def test_stage3_essential_fields_present(self):
        """3단계 압축 후 핵심 필드 존재 확인."""
        analysis = _make_analysis(n_components=3, with_large_lists=True)
        result = compress_analysis(analysis, max_chars=10)
        parsed = json.loads(result)
        assert "health_score" in parsed
        assert "recommended_scenario" in parsed
        assert "scenario_rationale" in parsed

    def test_component_decisions_action_preserved(self):
        """component_decisions의 action 값 보존."""
        analysis = _make_analysis(n_components=2)
        result = compress_analysis(analysis)
        parsed = json.loads(result)
        actions = {d["component_id"]: d["action"] for d in parsed["component_decisions"]}
        assert actions["c0"] == "replatform"
        assert actions["c1"] == "replatform"


# ── compress_for_plan 테스트 ─────────────────────────────────────────────────

class TestCompressForPlan:
    def _make_plan_system(self, with_strategy: bool = True, with_specs: bool = True) -> dict:
        components = []
        for i in range(3):
            c: dict = {"id": f"c{i}", "type": "service", "label": f"Svc {i}"}
            if with_strategy:
                c["metadata"] = {
                    "strategy": "replatform",
                    "reason": "컨테이너 전환",
                    "replaces": f"legacy_c{i}",
                    "verbose_field": "x" * 300,
                }
            if with_specs:
                c["specs"] = {"cpu": 4, "ram": "16GB", "disk": "500GB"}
            components.append(c)
        return {"name": "Plan System", "components": components, "connections": []}

    def test_stage1_small_indent_returned(self):
        """작은 시스템은 indent=2로 반환."""
        d = self._make_plan_system(with_strategy=False, with_specs=False)
        result = compress_for_plan(d, max_chars=MAX_PLAN_SYSTEM_CHARS)
        assert "\n" in result
        assert json.loads(result)["name"] == "Plan System"

    def test_stage3_specs_removed_but_strategy_kept(self):
        """specs 제거, strategy/reason/replaces는 보존."""
        d = self._make_plan_system(with_strategy=True, with_specs=True)
        indented = json.dumps(d, ensure_ascii=False, indent=2)
        compact = json.dumps(d, ensure_ascii=False)
        # compact 직후 단계를 강제하기 위해 compact+1보다 작은 한도
        limit = len(compact) - 1

        result = compress_for_plan(d, max_chars=limit)
        parsed = json.loads(result)
        for comp in parsed["components"]:
            assert "specs" not in comp
            meta = comp.get("metadata", {})
            assert meta.get("strategy") == "replatform"
            assert meta.get("reason") == "컨테이너 전환"
            assert meta.get("replaces") is not None
            assert "verbose_field" not in meta  # 비핵심 메타 제거 확인

    def test_stage4_all_metadata_removed_as_last_resort(self):
        """최후 수단: 핵심 메타데이터도 제거."""
        d = self._make_plan_system(with_strategy=True, with_specs=True)
        result = compress_for_plan(d, max_chars=50)
        parsed = json.loads(result)
        for comp in parsed["components"]:
            assert "metadata" not in comp
            assert "specs" not in comp

    def test_stage4_component_ids_preserved(self):
        """최후 수단 압축 후에도 컴포넌트 id 보존."""
        d = self._make_plan_system()
        result = compress_for_plan(d, max_chars=50)
        parsed = json.loads(result)
        ids = {c["id"] for c in parsed["components"]}
        assert ids == {"c0", "c1", "c2"}

    def test_empty_metadata_removed(self):
        """metadata가 비어있으면 제거."""
        d = {
            "name": "S",
            "components": [{"id": "a", "type": "server", "label": "A", "metadata": {}}],
        }
        compact = json.dumps(d, ensure_ascii=False)
        result = compress_for_plan(d, max_chars=len(compact) - 1)
        parsed = json.loads(result)
        assert "metadata" not in parsed["components"][0]
