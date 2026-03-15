"""llm/modernizer.py 단위 테스트 — A1/A2/A3 분기 로직 검증."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from archpilot.core.models import (
    AnalysisResult,
    Component,
    ComponentDecision,
    ComponentType,
    HostType,
    ModernizationAction,
    ModernizationScenario,
    SystemModel,
)
from archpilot.llm.modernizer import SystemModernizer, _MAX_RETRY
from archpilot.llm.utils import LARGE_SYSTEM_THRESHOLD


# ── 픽스처 ───────────────────────────────────────────────────────────────────

def _make_system(n: int, prefix: str = "c") -> SystemModel:
    """n개 컴포넌트를 가진 SystemModel 생성."""
    return SystemModel(
        name="Legacy",
        components=[
            Component(id=f"{prefix}{i}", type=ComponentType.SERVER, label=f"Svc {i}",
                      host=HostType.ON_PREMISE)
            for i in range(n)
        ],
    )


def _make_modern_dict(n: int, prefix: str = "m") -> dict:
    """n개 컴포넌트를 가진 현대화 시스템 dict 반환."""
    return {
        "name": "Modern",
        "components": [
            {"id": f"{prefix}{i}", "type": "service", "label": f"Modern {i}"}
            for i in range(n)
        ],
        "connections": [],
    }


def _make_analysis(retire_ids: list[str] | None = None) -> AnalysisResult:
    """간단한 AnalysisResult 생성. retire_ids에 해당하는 컴포넌트는 retire 처리."""
    retire_ids = retire_ids or []
    decisions = [
        ComponentDecision(
            component_id=rid,
            action=ModernizationAction.RETIRE,
            rationale="폐기 예정",
        )
        for rid in retire_ids
    ]
    return AnalysisResult(
        system_name="Legacy",
        component_decisions=decisions,
        recommended_scenario=ModernizationScenario.FULL_REPLACE,
    )


# ── _resolve_scenario 테스트 ─────────────────────────────────────────────────

class TestResolveScenario:
    def setup_method(self):
        self.m = SystemModernizer()

    def test_explicit_scenario_wins(self):
        """명시적 scenario 파라미터가 최우선."""
        analysis = _make_analysis()
        analysis.recommended_scenario = ModernizationScenario.ADDITIVE
        result = self.m._resolve_scenario(ModernizationScenario.PARTIAL, analysis)
        assert result == ModernizationScenario.PARTIAL

    def test_analysis_recommendation_used_when_no_explicit(self):
        """명시 없을 때 분석 추천 시나리오 사용."""
        analysis = _make_analysis()
        analysis.recommended_scenario = ModernizationScenario.ADDITIVE
        result = self.m._resolve_scenario(None, analysis)
        assert result == ModernizationScenario.ADDITIVE

    def test_full_replace_default_when_no_input(self):
        """시나리오와 분석 모두 없으면 FULL_REPLACE 기본값."""
        result = self.m._resolve_scenario(None, None)
        assert result == ModernizationScenario.FULL_REPLACE


# ── _build_component_checklist 테스트 ────────────────────────────────────────

class TestBuildComponentChecklist:
    def setup_method(self):
        self.m = SystemModernizer()

    def test_all_components_in_checklist(self):
        """모든 컴포넌트 ID가 체크리스트에 포함."""
        legacy = _make_system(3)
        checklist, must_include, retire = self.m._build_component_checklist(legacy, None)
        for i in range(3):
            assert f"c{i}" in checklist

    def test_retire_ids_excluded_from_must_include(self):
        """retire 컴포넌트는 must_include에서 제외."""
        legacy = _make_system(3)
        analysis = _make_analysis(retire_ids=["c0", "c2"])
        _, must_include, retire_ids = self.m._build_component_checklist(legacy, analysis)
        assert "c0" not in must_include
        assert "c2" not in must_include
        assert "c1" in must_include
        assert retire_ids == {"c0", "c2"}

    def test_action_labels_in_checklist(self):
        """컴포넌트 action이 체크리스트 라인에 표시."""
        legacy = _make_system(2)
        analysis = AnalysisResult(
            system_name="L",
            component_decisions=[
                ComponentDecision(component_id="c0", action=ModernizationAction.REHOST),
                ComponentDecision(component_id="c1", action=ModernizationAction.RETIRE),
            ],
        )
        checklist, _, _ = self.m._build_component_checklist(legacy, analysis)
        assert "→ rehost" in checklist
        assert "→ retire" in checklist

    def test_no_analysis_all_must_include(self):
        """분석 없으면 전체가 must_include."""
        legacy = _make_system(4)
        _, must_include, retire_ids = self.m._build_component_checklist(legacy, None)
        assert len(must_include) == 4
        assert len(retire_ids) == 0


# ── _check_missing 테스트 ─────────────────────────────────────────────────────

class TestCheckMissing:
    def setup_method(self):
        self.m = SystemModernizer()

    def test_no_missing_when_all_present(self):
        """모든 must_include ID가 modern에 있으면 빈 리스트."""
        modern = _make_system(3, prefix="c")
        missing = self.m._check_missing(modern, ["c0", "c1", "c2"])
        assert missing == []

    def test_detects_missing_ids(self):
        """누락된 ID를 정확히 탐지."""
        modern = _make_system(2, prefix="c")  # c0, c1만 있음
        missing = self.m._check_missing(modern, ["c0", "c1", "c2", "c3"])
        assert "c2" in missing
        assert "c3" in missing
        assert "c0" not in missing

    def test_empty_modern_all_missing(self):
        """현대화 시스템이 비어있으면 전부 누락."""
        modern = SystemModel(name="M", components=[])
        missing = self.m._check_missing(modern, ["c0", "c1"])
        assert missing == ["c0", "c1"]


# ── A3 임계값 분기 테스트 ─────────────────────────────────────────────────────

class TestA3ThresholdRouting:
    """LARGE_SYSTEM_THRESHOLD 기준 single-pass / two-phase 분기 확인."""

    @patch("archpilot.llm.modernizer.SystemModernizer._modernize_single_pass")
    @patch("archpilot.llm.modernizer.SystemModernizer._modernize_two_phase")
    def test_exactly_threshold_uses_single_pass(self, mock_two, mock_single):
        """컴포넌트 수 == LARGE_SYSTEM_THRESHOLD → single-pass."""
        legacy = _make_system(LARGE_SYSTEM_THRESHOLD)
        mock_single.return_value = MagicMock(spec=SystemModel)
        m = SystemModernizer()
        m.modernize(legacy, "req")
        mock_single.assert_called_once()
        mock_two.assert_not_called()

    @patch("archpilot.llm.modernizer.SystemModernizer._modernize_single_pass")
    @patch("archpilot.llm.modernizer.SystemModernizer._modernize_two_phase")
    def test_one_over_threshold_uses_two_phase(self, mock_two, mock_single):
        """컴포넌트 수 == LARGE_SYSTEM_THRESHOLD + 1 → two-phase."""
        legacy = _make_system(LARGE_SYSTEM_THRESHOLD + 1)
        mock_two.return_value = MagicMock(spec=SystemModel)
        m = SystemModernizer()
        m.modernize(legacy, "req")
        mock_two.assert_called_once()
        mock_single.assert_not_called()

    @patch("archpilot.llm.modernizer.SystemModernizer._modernize_single_pass")
    @patch("archpilot.llm.modernizer.SystemModernizer._modernize_two_phase")
    def test_small_system_uses_single_pass(self, mock_two, mock_single):
        """소규모 시스템(5개) → single-pass."""
        legacy = _make_system(5)
        mock_single.return_value = MagicMock(spec=SystemModel)
        m = SystemModernizer()
        m.modernize(legacy, "req")
        mock_single.assert_called_once()

    @patch("archpilot.llm.modernizer.SystemModernizer._modernize_single_pass")
    @patch("archpilot.llm.modernizer.SystemModernizer._modernize_two_phase")
    def test_large_system_uses_two_phase(self, mock_two, mock_single):
        """대형 시스템(34개) → two-phase."""
        legacy = _make_system(34)
        mock_two.return_value = MagicMock(spec=SystemModel)
        m = SystemModernizer()
        m.modernize(legacy, "req")
        mock_two.assert_called_once()


# ── A2 재시도 로직 테스트 ─────────────────────────────────────────────────────

class TestA2RetryLogic:
    """single-pass에서 컴포넌트 누락 시 재시도 동작 검증."""

    def _mock_client_returning(self, dicts: list[dict]) -> MagicMock:
        """chat_json 호출 시 dicts를 순서대로 반환하는 mock client."""
        client = MagicMock()
        client.chat_json.side_effect = dicts
        return client

    @patch("archpilot.llm.modernizer.get_client")
    def test_no_retry_when_all_present(self, mock_get_client):
        """누락 없으면 재시도 없음 (chat_json 1회 호출)."""
        legacy = _make_system(3)
        # 현대화 시스템에 모든 레거시 ID 포함
        modern_dict = _make_modern_dict(3, prefix="c")
        mock_client = self._mock_client_returning([modern_dict])
        mock_get_client.return_value = mock_client

        m = SystemModernizer()
        result = m._modernize_single_pass(legacy, "req", None, None)

        assert mock_client.chat_json.call_count == 1

    @patch("archpilot.llm.modernizer.get_client")
    def test_retry_triggered_when_components_missing(self, mock_get_client):
        """누락 컴포넌트가 있으면 재시도 (chat_json 2회 호출)."""
        legacy = _make_system(3)
        # 1차 응답: c2 누락
        first_dict = {
            "name": "Modern",
            "components": [
                {"id": "c0", "type": "service", "label": "S0"},
                {"id": "c1", "type": "service", "label": "S1"},
            ],
            "connections": [],
        }
        # 2차 응답: 모두 포함
        second_dict = {
            "name": "Modern",
            "components": [
                {"id": "c0", "type": "service", "label": "S0"},
                {"id": "c1", "type": "service", "label": "S1"},
                {"id": "c2", "type": "service", "label": "S2"},
            ],
            "connections": [],
        }
        mock_client = self._mock_client_returning([first_dict, second_dict])
        mock_get_client.return_value = mock_client

        m = SystemModernizer()
        result = m._modernize_single_pass(legacy, "req", None, None)

        assert mock_client.chat_json.call_count == 2

    @patch("archpilot.llm.modernizer.get_client")
    def test_max_retry_respected(self, mock_get_client):
        """MAX_RETRY 한도를 초과해서 재시도하지 않음."""
        legacy = _make_system(5)
        # 항상 누락 있는 응답 반환
        incomplete_dict = {
            "name": "Modern",
            "components": [{"id": "c0", "type": "service", "label": "S0"}],
            "connections": [],
        }
        # _MAX_RETRY + 2개 이상 준비해도 그 이상 호출하지 않아야 함
        mock_client = self._mock_client_returning([incomplete_dict] * (_MAX_RETRY + 5))
        mock_get_client.return_value = mock_client

        m = SystemModernizer()
        m._modernize_single_pass(legacy, "req", None, None)

        # 최초 1회 + 재시도 _MAX_RETRY회 = _MAX_RETRY + 1
        assert mock_client.chat_json.call_count == _MAX_RETRY + 1

    @patch("archpilot.llm.modernizer.get_client")
    def test_retry_message_contains_missing_ids(self, mock_get_client):
        """재시도 메시지에 누락된 ID 목록이 포함."""
        legacy = _make_system(2)
        first_dict = {
            "name": "Modern",
            "components": [{"id": "c0", "type": "service", "label": "S0"}],
            "connections": [],
        }
        second_dict = {
            "name": "Modern",
            "components": [
                {"id": "c0", "type": "service", "label": "S0"},
                {"id": "c1", "type": "service", "label": "S1"},
            ],
            "connections": [],
        }
        mock_client = self._mock_client_returning([first_dict, second_dict])
        mock_get_client.return_value = mock_client

        m = SystemModernizer()
        m._modernize_single_pass(legacy, "req", None, None)

        # 2차 호출 시 user_message에 누락 ID "c1"이 포함되어야 함
        second_call_args = mock_client.chat_json.call_args_list[1]
        retry_msg = second_call_args[0][1]  # positional arg[1] = user_message
        assert "c1" in retry_msg

    @patch("archpilot.llm.modernizer.get_client")
    def test_retire_ids_excluded_from_must_include(self, mock_get_client):
        """retire 처리된 컴포넌트는 누락 체크에서 제외."""
        legacy = _make_system(3)
        analysis = _make_analysis(retire_ids=["c2"])  # c2는 retire

        # c0, c1만 포함 (c2는 retire 처리 → 누락 아님)
        modern_dict = {
            "name": "Modern",
            "components": [
                {"id": "c0", "type": "service", "label": "S0"},
                {"id": "c1", "type": "service", "label": "S1"},
            ],
            "connections": [],
        }
        mock_client = self._mock_client_returning([modern_dict])
        mock_get_client.return_value = mock_client

        m = SystemModernizer()
        result = m._modernize_single_pass(legacy, "req", analysis, None)

        # 재시도 없이 1회만 호출
        assert mock_client.chat_json.call_count == 1


# ── A3 two-phase 테스트 ───────────────────────────────────────────────────────

class TestA3TwoPhase:
    @patch("archpilot.llm.modernizer.get_client")
    def test_two_phase_calls_two_llm_prompts(self, mock_get_client):
        """two-phase는 chat_json을 정확히 2회 호출 (skeleton + enrich)."""
        legacy = _make_system(LARGE_SYSTEM_THRESHOLD + 5)

        skeleton_dict = {
            "name": "Modern",
            "components": [
                {"id": f"c{i}", "type": "service", "label": f"S{i}"}
                for i in range(LARGE_SYSTEM_THRESHOLD + 5)
            ],
        }
        modern_dict = {
            "name": "Modern",
            "components": skeleton_dict["components"],
            "connections": [],
        }

        mock_client = MagicMock()
        mock_client.chat_json.side_effect = [skeleton_dict, modern_dict]
        mock_get_client.return_value = mock_client

        m = SystemModernizer()
        m._modernize_two_phase(legacy, "req", None, None)

        assert mock_client.chat_json.call_count == 2

    @patch("archpilot.llm.modernizer.get_client")
    def test_skeleton_prompt_used_first(self, mock_get_client):
        """Phase 1에서 MODERNIZE_SKELETON_PROMPT 사용 확인."""
        from archpilot.llm.prompts import MODERNIZE_SKELETON_PROMPT

        legacy = _make_system(LARGE_SYSTEM_THRESHOLD + 1)
        skeleton_dict = {
            "name": "Modern",
            "components": [
                {"id": f"c{i}", "type": "service", "label": f"S{i}"}
                for i in range(LARGE_SYSTEM_THRESHOLD + 1)
            ],
        }
        modern_dict = {**skeleton_dict, "connections": []}

        mock_client = MagicMock()
        mock_client.chat_json.side_effect = [skeleton_dict, modern_dict]
        mock_get_client.return_value = mock_client

        m = SystemModernizer()
        m._modernize_two_phase(legacy, "req", None, None)

        first_call_system_prompt = mock_client.chat_json.call_args_list[0][0][0]
        assert first_call_system_prompt == MODERNIZE_SKELETON_PROMPT
