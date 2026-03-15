"""modernize SSE 라우터 테스트 — LLM 호출 모킹."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from archpilot.ui import session as sess

# ── 픽스처 공유 데이터 ────────────────────────────────────────────────────────

MINIMAL_SYSTEM = {
    "name": "Legacy Bank System",
    "components": [
        {"id": "web", "type": "server", "label": "Web Server", "tech": ["Apache Tomcat"]},
        {"id": "db", "type": "database", "label": "Oracle DB", "tech": ["Oracle 11g"]},
    ],
    "connections": [{"from": "web", "to": "db", "protocol": "JDBC"}],
}

ANALYSIS_RESULT = {
    "system_name": "Legacy Bank System",
    "health_score": 55,
    "pain_points": ["tight coupling", "no container support"],
    "recommended_scenario": "partial",
    "scenario_rationale": "Core DB schema is stable.",
    "component_decisions": [
        {"component_id": "web", "action": "replatform", "rationale": "containerize"},
        {"component_id": "db", "action": "keep", "rationale": "stable schema"},
    ],
}

# ── 모의 LLM 응답 ─────────────────────────────────────────────────────────────

_MODERN_SYSTEM_RESPONSE = json.dumps({
    "name": "Modern Bank System",
    "components": [
        {"id": "api_gw", "type": "api_gateway", "label": "API Gateway", "tech": ["Kong"]},
        {"id": "web_svc", "type": "server", "label": "Web Service", "tech": ["Spring Boot"]},
        {"id": "db_managed", "type": "database", "label": "Managed DB", "tech": ["PostgreSQL"]},
    ],
    "connections": [
        {"from": "api_gw", "to": "web_svc", "protocol": "HTTP"},
        {"from": "web_svc", "to": "db_managed", "protocol": "TCP"},
    ],
})

_PERSPECTIVE_RESPONSE = json.dumps({
    "perspectives": [
        {
            "perspective": "sa",
            "concerns": ["latency"],
            "recommendations": ["add CDN"],
            "risks": [],
            "score": 75,
            "rationale": "Good decomposition.",
        }
    ],
    "consensus_summary": "Well structured.",
    "conflict_areas": [],
    "priority_actions": ["add observability"],
})

_MIGRATION_PLAN_RESPONSE = "# Migration Plan\n## Phase 1\n- Containerize web tier\n## Phase 2\n- Migrate DB\n"

_RATIONALE_RESPONSE = json.dumps({
    "design_philosophy": "Cloud-native, container-first.",
    "key_decisions": [],
    "arch_quality_eval": {
        "overall_score": 82,
        "strengths": ["scalable"],
        "weaknesses": [],
        "improvement_recommendations": [],
    },
    "rmc_self_eval": {
        "completeness_score": 85,
        "coverage_gaps": [],
        "design_risks": [],
        "improvement_suggestions": [],
        "confidence_level": "high",
    },
})

_RMC_PLAN_RESPONSE = json.dumps({
    "completeness_score": 80,
    "well_covered_phases": ["containerization"],
    "missing_aspects": ["rollback testing"],
    "risk_blind_spots": [],
    "dependency_gaps": [],
    "rollback_adequacy": "adequate",
    "timeline_realism": "optimistic",
    "improvement_suggestions": ["add canary deploy"],
    "confidence_level": "medium",
})


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _make_stream(*responses: str):
    """순서대로 각 응답을 yield하는 stream_chat side_effect를 반환한다."""
    it = iter(responses)

    def side_effect(*args, **kwargs):
        data = next(it)

        async def gen():
            yield data

        return gen()

    return side_effect


def parse_sse(text: str) -> list[dict]:
    """SSE 응답 텍스트를 event dict 목록으로 변환한다."""
    events = []
    for line in text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


def _all_5_streams():
    """5-pass 전체에 대한 mock stream side_effect를 반환한다."""
    return _make_stream(
        _MODERN_SYSTEM_RESPONSE,   # Phase 1: modernize
        _PERSPECTIVE_RESPONSE,     # Phase 2: design perspective
        _MIGRATION_PLAN_RESPONSE,  # Phase 3: migration plan
        _RATIONALE_RESPONSE,       # Phase 4: RMC rationale
        _RMC_PLAN_RESPONSE,        # Phase 5: RMC plan
    )


# ── 픽스처 ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_session():
    sess.reset()
    yield
    sess.reset()


@pytest.fixture
def app(tmp_path: Path):
    from archpilot.ui.server import create_app
    return create_app(output_dir=tmp_path)


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=True) as tc:
        yield tc


@pytest.fixture
def session_with_system():
    s = sess.get()
    s.system = MINIMAL_SYSTEM
    s.legacy_mmd = "graph LR\n  web --> db"
    s.legacy_drawio = "<mxGraphModel/>"
    return s


@pytest.fixture
def session_with_analysis(session_with_system):
    s = sess.get()
    s.analysis = ANALYSIS_RESULT
    return s


# ── 내부 헬퍼 함수 단위 테스트 ────────────────────────────────────────────────

class TestResolveScenario:
    """_resolve_scenario 헬퍼 함수 단위 테스트."""

    def _make_session(self, **kwargs: Any):
        s = sess.get()
        for k, v in kwargs.items():
            setattr(s, k, v)
        return s

    def test_explicit_req_scenario_takes_priority(self):
        from archpilot.ui.routers.modernize import _resolve_scenario
        from archpilot.ui.schemas import ModernizeRequest

        s = self._make_session(scenario="partial", analysis={"recommended_scenario": "full_replace"})
        req = ModernizeRequest(requirements="test", scenario="additive")
        resolved, label, section = _resolve_scenario(req, s)
        assert resolved == "additive"

    def test_session_scenario_used_when_req_is_none(self):
        from archpilot.ui.routers.modernize import _resolve_scenario
        from archpilot.ui.schemas import ModernizeRequest

        s = self._make_session(scenario="partial", analysis=None)
        req = ModernizeRequest(requirements="test", scenario=None)
        resolved, label, section = _resolve_scenario(req, s)
        assert resolved == "partial"

    def test_analysis_recommended_scenario_fallback(self):
        from archpilot.ui.routers.modernize import _resolve_scenario
        from archpilot.ui.schemas import ModernizeRequest

        s = self._make_session(scenario=None, analysis={"recommended_scenario": "additive"})
        req = ModernizeRequest(requirements="test", scenario=None)
        resolved, label, section = _resolve_scenario(req, s)
        assert resolved == "additive"

    def test_default_is_full_replace(self):
        from archpilot.ui.routers.modernize import _resolve_scenario
        from archpilot.ui.schemas import ModernizeRequest

        s = self._make_session(scenario=None, analysis=None)
        req = ModernizeRequest(requirements="test", scenario=None)
        resolved, label, section = _resolve_scenario(req, s)
        assert resolved == "full_replace"

    def test_label_is_human_readable(self):
        from archpilot.ui.routers.modernize import _resolve_scenario
        from archpilot.ui.schemas import ModernizeRequest

        s = self._make_session(scenario=None, analysis=None)
        req = ModernizeRequest(requirements="test", scenario="partial")
        _resolved, label, _section = _resolve_scenario(req, s)
        assert "Partial" in label or "부분" in label

    def test_session_scenario_updated_after_resolve(self):
        from archpilot.ui.routers.modernize import _resolve_scenario
        from archpilot.ui.schemas import ModernizeRequest

        s = self._make_session(scenario=None, analysis=None)
        req = ModernizeRequest(requirements="test", scenario="additive")
        _resolve_scenario(req, s)
        assert s.scenario == "additive"

    def test_section_contains_scenario_value(self):
        from archpilot.ui.routers.modernize import _resolve_scenario
        from archpilot.ui.schemas import ModernizeRequest

        s = self._make_session(scenario=None, analysis=None)
        req = ModernizeRequest(requirements="test", scenario="partial")
        _resolved, _label, section = _resolve_scenario(req, s)
        assert "partial" in section


class TestBuildAnalysisSection:
    """_build_analysis_section 헬퍼 함수 단위 테스트."""

    def test_returns_empty_when_no_analysis(self):
        from archpilot.ui.routers.modernize import _build_analysis_section

        s = sess.get()
        s.analysis = None
        assert _build_analysis_section(s, "full_replace") == ""

    def test_returns_section_with_analysis(self):
        from archpilot.ui.routers.modernize import _build_analysis_section

        s = sess.get()
        s.analysis = ANALYSIS_RESULT
        section = _build_analysis_section(s, "partial")
        assert "component_decisions" in section
        assert "replatform" in section

    def test_scenario_value_in_section(self):
        from archpilot.ui.routers.modernize import _build_analysis_section

        s = sess.get()
        s.analysis = ANALYSIS_RESULT
        section = _build_analysis_section(s, "additive")
        assert "additive" in section

    def test_scenario_rationale_in_section(self):
        from archpilot.ui.routers.modernize import _build_analysis_section

        s = sess.get()
        s.analysis = ANALYSIS_RESULT
        section = _build_analysis_section(s, "partial")
        assert "Core DB schema is stable" in section


# ── 가드 조건 ─────────────────────────────────────────────────────────────────

class TestModernizeGuards:
    def test_no_system_returns_400(self, client):
        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "마이크로서비스 전환"},
        )
        assert resp.status_code == 400

    def test_no_system_error_detail(self, client):
        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "마이크로서비스 전환"},
        )
        detail = resp.json()["detail"]
        assert "ingest" in detail.lower() or "시스템" in detail


# ── 정상 5-pass 파이프라인 ────────────────────────────────────────────────────

class TestModernizeStream:
    def test_returns_event_stream_content_type(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native 전환"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    def test_done_event_present(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native 전환"},
        )
        events = parse_sse(resp.text)
        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1

    def test_done_event_contains_modern_system(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native 전환"},
        )
        events = parse_sse(resp.text)
        done = next(e for e in events if e.get("type") == "done")
        assert "modern" in done
        assert done["modern"]["name"] == "Modern Bank System"
        assert len(done["modern"]["components"]) == 3

    def test_done_event_contains_mermaid_and_drawio(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native 전환"},
        )
        events = parse_sse(resp.text)
        done = next(e for e in events if e.get("type") == "done")
        assert "modern_mmd" in done
        assert "modern_drawio" in done
        assert done["modern_mmd"]  # 비어 있지 않아야 함
        assert done["modern_drawio"]

    def test_done_event_contains_migration_plan(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native 전환"},
        )
        events = parse_sse(resp.text)
        done = next(e for e in events if e.get("type") == "done")
        assert "migration_plan" in done
        assert "Phase 1" in done["migration_plan"]

    def test_done_event_contains_scenario(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native 전환", "scenario": "partial"},
        )
        events = parse_sse(resp.text)
        done = next(e for e in events if e.get("type") == "done")
        assert done["scenario"] == "partial"

    def test_done_event_contains_design_rationale(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native 전환"},
        )
        events = parse_sse(resp.text)
        done = next(e for e in events if e.get("type") == "done")
        assert "design_rationale" in done
        assert done["design_rationale"]["design_philosophy"] == "Cloud-native, container-first."

    def test_done_event_contains_rmc_results(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native 전환"},
        )
        events = parse_sse(resp.text)
        done = next(e for e in events if e.get("type") == "done")
        assert "migration_plan_rmc" in done
        assert done["migration_plan_rmc"]["completeness_score"] == 80

    def test_session_modern_updated(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native 전환"},
        )
        s = sess.get()
        assert s.modern is not None
        assert s.modern["name"] == "Modern Bank System"

    def test_session_migration_plan_saved(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native 전환"},
        )
        assert "Phase 1" in sess.get().migration_plan

    def test_session_requirements_saved(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post(
            "/api/modernize/stream",
            json={"requirements": "마이크로서비스 아키텍처"},
        )
        assert sess.get().requirements == "마이크로서비스 아키텍처"

    def test_stream_chat_called_five_times(self, client, session_with_system, mocker):
        """5-pass: modernize → perspective → migration plan → rationale → RMC plan."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native"},
        )
        assert mock_client.stream_chat.call_count == 5

    def test_progress_events_emitted(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native"},
        )
        events = parse_sse(resp.text)
        progress_events = [e for e in events if e.get("type") == "progress"]
        assert len(progress_events) >= 4

    def test_output_files_written(self, tmp_path, mocker):
        from archpilot.ui.server import create_app
        fresh_app = create_app(output_dir=tmp_path)

        s = sess.get()
        s.system = MINIMAL_SYSTEM

        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        with TestClient(fresh_app) as tc:
            tc.post(
                "/api/modernize/stream",
                json={"requirements": "Cloud-native"},
            )

        modern_dir = tmp_path / "modern"
        assert modern_dir.exists()
        assert (modern_dir / "system.json").exists()
        assert (modern_dir / "diagram.mmd").exists()
        assert (modern_dir / "diagram.drawio").exists()
        assert (modern_dir / "migration_plan.md").exists()

    def test_migration_plan_file_content(self, tmp_path, mocker):
        from archpilot.ui.server import create_app
        fresh_app = create_app(output_dir=tmp_path)

        s = sess.get()
        s.system = MINIMAL_SYSTEM

        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        with TestClient(fresh_app) as tc:
            tc.post(
                "/api/modernize/stream",
                json={"requirements": "Cloud-native"},
            )

        plan = (tmp_path / "modern" / "migration_plan.md").read_text()
        assert "Phase 1" in plan

    def test_with_analysis_in_session(self, client, session_with_analysis, mocker):
        """분석 결과가 있을 때 현대화가 정상 동작한다."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native", "scenario": "partial"},
        )
        events = parse_sse(resp.text)
        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1

    def test_analysis_included_in_first_llm_call(self, client, session_with_analysis, mocker):
        """분석 결과의 component_decisions가 첫 번째 LLM 호출에 반영된다."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native"},
        )
        first_call_args = mock_client.stream_chat.call_args_list[0]
        user_msg = first_call_args[0][1]
        assert "replatform" in user_msg or "component_decisions" in user_msg


# ── 오류 시나리오 ─────────────────────────────────────────────────────────────

class TestModernizeStreamErrors:
    def test_invalid_modern_json_yields_error_event(self, client, session_with_system, mocker):
        """LLM이 파싱 불가 현대화 결과를 반환하면 error SSE 이벤트가 방출된다."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            "totally invalid json {{{{",
            _PERSPECTIVE_RESPONSE,
            _MIGRATION_PLAN_RESPONSE,
            _RATIONALE_RESPONSE,
            _RMC_PLAN_RESPONSE,
        )
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native"},
        )
        events = parse_sse(resp.text)
        error_events = [e for e in events if e.get("type") == "error"]
        assert len(error_events) >= 1

    def test_perspective_failure_tolerated(self, client, session_with_system, mocker):
        """설계 퍼스펙티브 파싱 실패는 무시되고 done 이벤트가 방출된다."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _MODERN_SYSTEM_RESPONSE,
            "not valid json",       # perspective 파싱 실패
            _MIGRATION_PLAN_RESPONSE,
            _RATIONALE_RESPONSE,
            _RMC_PLAN_RESPONSE,
        )
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native"},
        )
        events = parse_sse(resp.text)
        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1

    def test_rationale_failure_tolerated(self, client, session_with_system, mocker):
        """RMC 설계 해설 파싱 실패는 무시되고 done 이벤트가 방출된다."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _MODERN_SYSTEM_RESPONSE,
            _PERSPECTIVE_RESPONSE,
            _MIGRATION_PLAN_RESPONSE,
            "not valid json",   # rationale 파싱 실패
            _RMC_PLAN_RESPONSE,
        )
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native"},
        )
        events = parse_sse(resp.text)
        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1

    def test_rmc_plan_failure_tolerated(self, client, session_with_system, mocker):
        """마이그레이션 계획 RMC 파싱 실패는 무시되고 done 이벤트가 방출된다."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _MODERN_SYSTEM_RESPONSE,
            _PERSPECTIVE_RESPONSE,
            _MIGRATION_PLAN_RESPONSE,
            _RATIONALE_RESPONSE,
            "not valid json",   # RMC plan 파싱 실패
        )
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native"},
        )
        events = parse_sse(resp.text)
        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1

    def test_design_rationale_file_written_on_success(self, tmp_path, mocker):
        """design_rationale.json이 출력 디렉토리에 저장된다."""
        from archpilot.ui.server import create_app
        fresh_app = create_app(output_dir=tmp_path)

        s = sess.get()
        s.system = MINIMAL_SYSTEM

        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        with TestClient(fresh_app) as tc:
            tc.post(
                "/api/modernize/stream",
                json={"requirements": "Cloud-native"},
            )

        rationale_file = tmp_path / "modern" / "design_rationale.json"
        assert rationale_file.exists()
        rationale = json.loads(rationale_file.read_text())
        assert rationale["design_philosophy"] == "Cloud-native, container-first."


# ── 부분 수정(Patch) 모드 ─────────────────────────────────────────────────────

# 부분 수정 LLM 응답: 기존 modern 시스템에서 DB만 교체
_PATCH_SYSTEM_RESPONSE = json.dumps({
    "name": "Modern Bank System",
    "components": [
        {"id": "api_gw",    "type": "api_gateway", "label": "API Gateway",  "tech": ["Kong"]},
        {"id": "web_svc",   "type": "server",      "label": "Web Service",  "tech": ["Spring Boot"]},
        {"id": "db_aurora", "type": "database",    "label": "Aurora PostgreSQL",
         "tech": ["Aurora PostgreSQL"], "metadata": {"patched_by_feedback": True}},
    ],
    "connections": [
        {"from": "api_gw",  "to": "web_svc",   "protocol": "HTTP"},
        {"from": "web_svc", "to": "db_aurora",  "protocol": "TCP"},
    ],
})

_PATCH_MIGRATION_PLAN = "# Migration Plan (Patched)\n## DB Migration\n- Migrate to Aurora PostgreSQL\n"

EXISTING_MODERN = json.loads(_MODERN_SYSTEM_RESPONSE)


@pytest.fixture
def session_with_modern(session_with_system):
    """modern 결과가 이미 존재하는 세션 픽스처."""
    s = sess.get()
    s.modern = EXISTING_MODERN
    s.modern_mmd = "graph LR\n  api_gw --> web_svc --> db_managed"
    s.modern_drawio = "<mxGraphModel/>"
    s.migration_plan = "# Original Migration Plan"
    s.scenario = "partial"
    s.design_perspective = {"consensus_summary": "Well structured."}
    s.design_rationale = {"design_philosophy": "Cloud-native, container-first."}
    s.migration_plan_rmc = {"completeness_score": 80}
    return s


def _patch_2_streams():
    """부분 수정 2-pass: patch → migration plan."""
    return _make_stream(
        _PATCH_SYSTEM_RESPONSE,  # Phase ①: patch
        _PATCH_MIGRATION_PLAN,   # Phase ③: migration plan
    )


class TestIsPatchMode:
    """_is_patch_mode 헬퍼 단위 테스트."""

    def test_true_when_feedback_and_modern_exist(self):
        from archpilot.ui.routers.modernize import _is_patch_mode
        from archpilot.ui.schemas import ModernizeRequest

        s = sess.get()
        s.modern = EXISTING_MODERN
        req = ModernizeRequest(requirements="req", feedback="DB를 PostgreSQL로 변경")
        assert _is_patch_mode(req, s) is True

    def test_false_when_no_feedback(self):
        from archpilot.ui.routers.modernize import _is_patch_mode
        from archpilot.ui.schemas import ModernizeRequest

        s = sess.get()
        s.modern = EXISTING_MODERN
        req = ModernizeRequest(requirements="req", feedback=None)
        assert _is_patch_mode(req, s) is False

    def test_false_when_feedback_empty_string(self):
        from archpilot.ui.routers.modernize import _is_patch_mode
        from archpilot.ui.schemas import ModernizeRequest

        s = sess.get()
        s.modern = EXISTING_MODERN
        req = ModernizeRequest(requirements="req", feedback="   ")
        assert _is_patch_mode(req, s) is False

    def test_false_when_no_existing_modern(self):
        from archpilot.ui.routers.modernize import _is_patch_mode
        from archpilot.ui.schemas import ModernizeRequest

        s = sess.get()
        s.modern = None
        req = ModernizeRequest(requirements="req", feedback="DB를 PostgreSQL로 변경")
        assert _is_patch_mode(req, s) is False

    def test_false_when_both_missing(self):
        from archpilot.ui.routers.modernize import _is_patch_mode
        from archpilot.ui.schemas import ModernizeRequest

        s = sess.get()
        s.modern = None
        req = ModernizeRequest(requirements="req", feedback=None)
        assert _is_patch_mode(req, s) is False


class TestPatchModeStream:
    """부분 수정 모드 통합 테스트."""

    def test_patch_mode_returns_done_event(self, client, session_with_modern, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _patch_2_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native", "feedback": "DB를 Aurora PostgreSQL로 변경"},
        )
        events = parse_sse(resp.text)
        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1

    def test_patch_mode_calls_llm_twice_only(self, client, session_with_modern, mocker):
        """부분 수정: Phase ①(patch) + Phase ③(migration plan) — 5-pass 아님."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _patch_2_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native", "feedback": "DB를 Aurora PostgreSQL로 변경"},
        )
        assert mock_client.stream_chat.call_count == 2

    def test_patch_prompt_contains_feedback(self, client, session_with_modern, mocker):
        """패치 LLM 호출의 user_msg에 feedback 내용이 포함된다."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _patch_2_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native", "feedback": "DB를 Aurora PostgreSQL로 변경"},
        )
        first_call = mock_client.stream_chat.call_args_list[0]
        user_msg = first_call[0][1]
        assert "Aurora PostgreSQL" in user_msg

    def test_patch_prompt_contains_current_modern_json(self, client, session_with_modern, mocker):
        """패치 LLM 호출의 user_msg에 기존 modern 시스템 JSON이 포함된다."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _patch_2_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native", "feedback": "DB를 Aurora PostgreSQL로 변경"},
        )
        first_call = mock_client.stream_chat.call_args_list[0]
        user_msg = first_call[0][1]
        # 기존 modern 시스템의 컴포넌트 id가 user_msg에 포함되어야 한다
        assert "api_gw" in user_msg or "Modern Bank System" in user_msg

    def test_done_event_has_patch_mode_true(self, client, session_with_modern, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _patch_2_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native", "feedback": "DB를 Aurora PostgreSQL로 변경"},
        )
        events = parse_sse(resp.text)
        done = next(e for e in events if e.get("type") == "done")
        assert done["patch_mode"] is True

    def test_done_event_has_feedback_field(self, client, session_with_modern, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _patch_2_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native", "feedback": "DB를 Aurora PostgreSQL로 변경"},
        )
        events = parse_sse(resp.text)
        done = next(e for e in events if e.get("type") == "done")
        assert done["feedback"] == "DB를 Aurora PostgreSQL로 변경"

    def test_patch_updates_modern_in_session(self, client, session_with_modern, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _patch_2_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native", "feedback": "DB를 Aurora PostgreSQL로 변경"},
        )
        s = sess.get()
        assert s.modern is not None
        comp_ids = [c["id"] for c in s.modern["components"]]
        assert "db_aurora" in comp_ids

    def test_patch_updates_migration_plan(self, client, session_with_modern, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _patch_2_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native", "feedback": "DB를 Aurora PostgreSQL로 변경"},
        )
        assert "DB Migration" in sess.get().migration_plan

    def test_patch_preserves_design_perspective(self, client, session_with_modern, mocker):
        """부분 수정 후 기존 design_perspective가 유지된다 (Phase ② 스킵)."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _patch_2_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native", "feedback": "DB를 Aurora PostgreSQL로 변경"},
        )
        s = sess.get()
        assert s.design_perspective == {"consensus_summary": "Well structured."}

    def test_patch_preserves_design_rationale(self, client, session_with_modern, mocker):
        """부분 수정 후 기존 design_rationale이 유지된다 (Phase ④ 스킵)."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _patch_2_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native", "feedback": "DB를 Aurora PostgreSQL로 변경"},
        )
        s = sess.get()
        assert s.design_rationale == {"design_philosophy": "Cloud-native, container-first."}

    def test_patch_preserves_migration_plan_rmc(self, client, session_with_modern, mocker):
        """부분 수정 후 기존 migration_plan_rmc가 유지된다 (Phase ⑤ 스킵)."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _patch_2_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native", "feedback": "DB를 Aurora PostgreSQL로 변경"},
        )
        s = sess.get()
        assert s.migration_plan_rmc == {"completeness_score": 80}

    def test_patch_records_feedback_history(self, client, session_with_modern, mocker):
        """부분 수정 성공 후 last_feedback와 patch_history가 기록된다."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _patch_2_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native", "feedback": "DB를 Aurora PostgreSQL로 변경"},
        )
        s = sess.get()
        assert s.last_feedback == "DB를 Aurora PostgreSQL로 변경"
        assert "DB를 Aurora PostgreSQL로 변경" in s.patch_history

    def test_patch_history_accumulates(self, client, session_with_modern, mocker):
        """연속 부분 수정 시 patch_history에 누적된다."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _PATCH_SYSTEM_RESPONSE, _PATCH_MIGRATION_PLAN,
            _PATCH_SYSTEM_RESPONSE, _PATCH_MIGRATION_PLAN,
        )
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post("/api/modernize/stream",
                    json={"requirements": "req", "feedback": "DB를 Aurora PostgreSQL로 변경"})
        # 두 번째 패치를 위해 modern 상태 갱신
        sess.get().modern = json.loads(_PATCH_SYSTEM_RESPONSE)
        client.post("/api/modernize/stream",
                    json={"requirements": "req", "feedback": "Redis 캐시 추가"})

        s = sess.get()
        assert len(s.patch_history) == 2
        assert s.patch_history[0] == "DB를 Aurora PostgreSQL로 변경"
        assert s.patch_history[1] == "Redis 캐시 추가"

    def test_feedback_without_modern_triggers_full_generation(
        self, client, session_with_system, mocker
    ):
        """modern이 없는 상태에서 feedback을 보내면 전체 재생성이 실행된다."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native", "feedback": "DB를 PostgreSQL로"},
        )
        events = parse_sse(resp.text)
        done = next(e for e in events if e.get("type") == "done")
        # 전체 재생성이므로 patch_mode는 False
        assert done["patch_mode"] is False
        # 5-pass 전체 실행
        assert mock_client.stream_chat.call_count == 5

    def test_no_feedback_with_modern_triggers_full_generation(
        self, client, session_with_modern, mocker
    ):
        """feedback 없이 modern이 있어도 전체 재생성이 실행된다."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _all_5_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native"},
        )
        events = parse_sse(resp.text)
        done = next(e for e in events if e.get("type") == "done")
        assert done["patch_mode"] is False
        assert mock_client.stream_chat.call_count == 5

    def test_patch_invalid_llm_response_yields_error(
        self, client, session_with_modern, mocker
    ):
        """부분 수정 시 LLM이 유효하지 않은 JSON을 반환하면 error 이벤트가 방출된다."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            "totally invalid json {{{{",
        )
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        resp = client.post(
            "/api/modernize/stream",
            json={"requirements": "Cloud-native", "feedback": "DB를 Aurora PostgreSQL로 변경"},
        )
        events = parse_sse(resp.text)
        error_events = [e for e in events if e.get("type") == "error"]
        assert len(error_events) >= 1


# ── _build_patch_context 단위 테스트 ─────────────────────────────────────────

class TestBuildPatchContext:
    """_build_patch_context 헬퍼 단위 테스트."""

    def test_empty_when_no_analysis(self):
        from archpilot.ui.routers.modernize import _build_patch_context

        s = sess.get()
        s.analysis = None
        s.design_rationale = None
        keep, ctx = _build_patch_context(s, "full_replace")
        assert keep == ""
        assert ctx == ""

    def test_keep_constraints_built_from_keep_decisions(self):
        from archpilot.ui.routers.modernize import _build_patch_context

        s = sess.get()
        s.analysis = {
            "component_decisions": [
                {"component_id": "legacy_oracle", "action": "keep",
                 "rationale": "stable schema"},
                {"component_id": "app_server",    "action": "replatform"},
                {"component_id": "old_esb",        "action": "replace"},
            ],
            "scenario_rationale": "",
        }
        keep, _ = _build_patch_context(s, "partial")
        assert "legacy_oracle" in keep
        assert "keep" in keep

    def test_rehost_also_appears_in_keep_constraints(self):
        from archpilot.ui.routers.modernize import _build_patch_context

        s = sess.get()
        s.analysis = {
            "component_decisions": [
                {"component_id": "core_db", "action": "rehost", "rationale": "lift-and-shift"},
            ],
            "scenario_rationale": "",
        }
        keep, _ = _build_patch_context(s, "partial")
        assert "core_db" in keep
        assert "rehost" in keep

    def test_replace_action_not_in_keep_constraints(self):
        from archpilot.ui.routers.modernize import _build_patch_context

        s = sess.get()
        s.analysis = {
            "component_decisions": [
                {"component_id": "old_esb", "action": "replace", "rationale": "EOL"},
            ],
            "scenario_rationale": "",
        }
        keep, _ = _build_patch_context(s, "full_replace")
        assert keep == ""

    def test_analysis_context_contains_scenario_and_rationale(self):
        from archpilot.ui.routers.modernize import _build_patch_context

        s = sess.get()
        s.analysis = {
            "component_decisions": [],
            "scenario_rationale": "Core DB schema is stable.",
            "health_score": 55,
            "pain_points": ["tight coupling"],
        }
        _, ctx = _build_patch_context(s, "partial")
        assert "partial" in ctx
        assert "Core DB schema is stable." in ctx

    def test_analysis_context_contains_health_score(self):
        from archpilot.ui.routers.modernize import _build_patch_context

        s = sess.get()
        s.analysis = {"component_decisions": [], "health_score": 42, "scenario_rationale": ""}
        _, ctx = _build_patch_context(s, "full_replace")
        assert "42" in ctx

    def test_pain_points_capped_at_three(self):
        from archpilot.ui.routers.modernize import _build_patch_context

        s = sess.get()
        s.analysis = {
            "component_decisions": [],
            "pain_points": ["a", "b", "c", "d", "e"],
            "scenario_rationale": "",
        }
        _, ctx = _build_patch_context(s, "partial")
        assert "a" in ctx
        assert "d" not in ctx
        assert "e" not in ctx

    def test_analysis_context_contains_all_component_decisions(self):
        from archpilot.ui.routers.modernize import _build_patch_context

        s = sess.get()
        s.analysis = {
            "component_decisions": [
                {"component_id": "web", "action": "replatform", "rationale": "containerize"},
                {"component_id": "db",  "action": "keep",        "rationale": "stable"},
            ],
            "scenario_rationale": "",
        }
        _, ctx = _build_patch_context(s, "partial")
        assert "web" in ctx and "replatform" in ctx
        assert "db" in ctx and "keep" in ctx

    def test_design_philosophy_included_when_rationale_present(self):
        from archpilot.ui.routers.modernize import _build_patch_context

        s = sess.get()
        s.analysis = {"component_decisions": [], "scenario_rationale": ""}
        s.design_rationale = {"design_philosophy": "Cloud-native, container-first."}
        _, ctx = _build_patch_context(s, "full_replace")
        assert "Cloud-native, container-first." in ctx

    def test_design_philosophy_not_included_when_rationale_none(self):
        from archpilot.ui.routers.modernize import _build_patch_context

        s = sess.get()
        s.analysis = {"component_decisions": [], "scenario_rationale": ""}
        s.design_rationale = None
        _, ctx = _build_patch_context(s, "full_replace")
        assert "설계 철학" not in ctx


class TestPatchContextPassedToLLM:
    """패치 LLM 호출에 분석 컨텍스트가 실제로 전달되는지 통합 테스트."""

    def test_keep_constraints_in_user_msg_when_analysis_present(
        self, client, mocker
    ):
        s = sess.get()
        s.system = MINIMAL_SYSTEM
        s.modern = EXISTING_MODERN
        s.modern_mmd = "graph LR"
        s.modern_drawio = "<mxGraphModel/>"
        s.scenario = "partial"
        s.analysis = {
            **ANALYSIS_RESULT,
            "component_decisions": [
                {"component_id": "db", "action": "keep", "rationale": "stable schema"},
                {"component_id": "web", "action": "replatform"},
            ],
        }

        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _patch_2_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post("/api/modernize/stream",
                    json={"requirements": "req", "feedback": "DB를 Aurora로 변경"})

        user_msg = mock_client.stream_chat.call_args_list[0][0][1]
        assert "db" in user_msg
        assert "keep" in user_msg

    def test_analysis_context_scenario_in_user_msg(self, client, mocker):
        s = sess.get()
        s.system = MINIMAL_SYSTEM
        s.modern = EXISTING_MODERN
        s.modern_mmd = "graph LR"
        s.modern_drawio = "<mxGraphModel/>"
        s.scenario = "partial"
        s.analysis = {
            **ANALYSIS_RESULT,
            "scenario_rationale": "Core DB schema is stable.",
            "pain_points": ["tight coupling"],
        }

        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _patch_2_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post("/api/modernize/stream",
                    json={"requirements": "req", "feedback": "API Gateway 추가"})

        user_msg = mock_client.stream_chat.call_args_list[0][0][1]
        assert "Core DB schema is stable." in user_msg
        assert "tight coupling" in user_msg

    def test_design_philosophy_in_user_msg(self, client, mocker):
        s = sess.get()
        s.system = MINIMAL_SYSTEM
        s.modern = EXISTING_MODERN
        s.modern_mmd = "graph LR"
        s.modern_drawio = "<mxGraphModel/>"
        s.scenario = "partial"
        s.analysis = ANALYSIS_RESULT
        s.design_rationale = {"design_philosophy": "Strangler Fig for gradual migration."}

        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _patch_2_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post("/api/modernize/stream",
                    json={"requirements": "req", "feedback": "캐시 추가"})

        user_msg = mock_client.stream_chat.call_args_list[0][0][1]
        assert "Strangler Fig" in user_msg

    def test_no_extra_context_when_no_analysis(self, client, mocker):
        s = sess.get()
        s.system = MINIMAL_SYSTEM
        s.modern = EXISTING_MODERN
        s.modern_mmd = "graph LR"
        s.modern_drawio = "<mxGraphModel/>"
        s.scenario = "full_replace"
        s.analysis = None
        s.design_rationale = None

        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _patch_2_streams()
        mocker.patch("archpilot.ui.routers.modernize.get_async_client", return_value=mock_client)

        client.post("/api/modernize/stream",
                    json={"requirements": "req", "feedback": "캐시 추가"})

        user_msg = mock_client.stream_chat.call_args_list[0][0][1]
        assert "변경 금지" not in user_msg
        assert "분석 컨텍스트" not in user_msg
        assert "설계 철학" not in user_msg
