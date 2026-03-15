"""analyze SSE 라우터 테스트 — LLM 호출 모킹."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from archpilot.ui import session as sess

# ── 픽스처 공유 데이터 ────────────────────────────────────────────────────────

MINIMAL_SYSTEM = {
    "name": "Test System",
    "components": [
        {"id": "web", "type": "server", "label": "Web Server", "tech": ["Nginx"]},
        {"id": "db", "type": "database", "label": "MySQL", "tech": ["MySQL 8"]},
    ],
    "connections": [{"from": "web", "to": "db", "protocol": "JDBC"}],
}

# 모의 LLM 응답 — AnalysisResult 최소 유효 JSON
_ANALYSIS_RESPONSE = json.dumps({
    "system_name": "Test System",
    "health_score": 65,
    "pain_points": ["legacy DB", "no cache"],
    "recommended_scenario": "partial",
    "scenario_rationale": "Core components are reusable.",
    "component_decisions": [
        {"component_id": "web", "action": "replatform", "rationale": "containerize"},
        {"component_id": "db", "action": "keep", "rationale": "stable schema"},
    ],
})

# 모의 LLM 응답 — MultiPerspectiveAnalysis 최소 유효 JSON
_PERSPECTIVE_RESPONSE = json.dumps({
    "perspectives": [
        {
            "perspective": "sa",
            "concerns": ["monolithic coupling"],
            "recommendations": ["extract auth service"],
            "risks": ["migration downtime"],
            "score": 58,
            "rationale": "Tightly coupled components limit scalability.",
        }
    ],
    "consensus_summary": "Decomposition required.",
    "conflict_areas": [],
    "priority_actions": ["decouple services", "adopt container orchestration"],
})

# 모의 LLM 응답 — AnalysisRMC 최소 유효 JSON
_RMC_RESPONSE = json.dumps({
    "coverage_score": 78,
    "assumptions": ["single-region deployment"],
    "blind_spots": ["DR plan not assessed"],
    "verification_questions": ["What is the target RPO?"],
    "confidence_level": "medium",
    "confidence_rationale": "Limited observable context.",
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
    """시스템이 주입된 세션을 준비한다."""
    s = sess.get()
    s.system = MINIMAL_SYSTEM
    s.legacy_mmd = "graph LR\n  web --> db"
    s.legacy_drawio = "<mxGraphModel/>"
    return s


# ── 가드 조건 ─────────────────────────────────────────────────────────────────

class TestAnalyzeGuards:
    def test_no_system_returns_400(self, client):
        resp = client.get("/api/analyze/stream")
        assert resp.status_code == 400

    def test_no_system_error_detail_mentions_ingest(self, client):
        resp = client.get("/api/analyze/stream")
        detail = resp.json()["detail"]
        assert "ingest" in detail.lower()


# ── 정상 3-pass 파이프라인 ────────────────────────────────────────────────────

class TestAnalyzeStream:
    def test_returns_event_stream_content_type(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _ANALYSIS_RESPONSE, _PERSPECTIVE_RESPONSE, _RMC_RESPONSE
        )
        mocker.patch("archpilot.llm.client.get_async_client", return_value=mock_client)

        resp = client.get("/api/analyze/stream")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    def test_done_event_present(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _ANALYSIS_RESPONSE, _PERSPECTIVE_RESPONSE, _RMC_RESPONSE
        )
        mocker.patch("archpilot.llm.client.get_async_client", return_value=mock_client)

        resp = client.get("/api/analyze/stream")
        events = parse_sse(resp.text)
        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1

    def test_done_event_contains_analysis_result(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _ANALYSIS_RESPONSE, _PERSPECTIVE_RESPONSE, _RMC_RESPONSE
        )
        mocker.patch("archpilot.llm.client.get_async_client", return_value=mock_client)

        resp = client.get("/api/analyze/stream")
        events = parse_sse(resp.text)
        done = next(e for e in events if e.get("type") == "done")
        assert "result" in done
        assert done["result"]["system_name"] == "Test System"
        assert done["result"]["health_score"] == 65

    def test_done_event_contains_rmc_and_perspective(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _ANALYSIS_RESPONSE, _PERSPECTIVE_RESPONSE, _RMC_RESPONSE
        )
        mocker.patch("archpilot.llm.client.get_async_client", return_value=mock_client)

        resp = client.get("/api/analyze/stream")
        events = parse_sse(resp.text)
        done = next(e for e in events if e.get("type") == "done")
        assert "analysis_rmc" in done
        assert "multi_perspective" in done

    def test_progress_events_emitted(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _ANALYSIS_RESPONSE, _PERSPECTIVE_RESPONSE, _RMC_RESPONSE
        )
        mocker.patch("archpilot.llm.client.get_async_client", return_value=mock_client)

        resp = client.get("/api/analyze/stream")
        events = parse_sse(resp.text)
        progress_events = [e for e in events if e.get("type") == "progress"]
        assert len(progress_events) >= 3

    def test_chunk_events_emitted(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _ANALYSIS_RESPONSE, _PERSPECTIVE_RESPONSE, _RMC_RESPONSE
        )
        mocker.patch("archpilot.llm.client.get_async_client", return_value=mock_client)

        resp = client.get("/api/analyze/stream")
        events = parse_sse(resp.text)
        chunk_events = [e for e in events if e.get("type") == "chunk"]
        assert len(chunk_events) >= 1

    def test_session_analysis_updated(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _ANALYSIS_RESPONSE, _PERSPECTIVE_RESPONSE, _RMC_RESPONSE
        )
        mocker.patch("archpilot.llm.client.get_async_client", return_value=mock_client)

        client.get("/api/analyze/stream")
        s = sess.get()
        assert s.analysis is not None
        assert s.analysis["system_name"] == "Test System"
        assert s.analysis["health_score"] == 65

    def test_session_rmc_saved(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _ANALYSIS_RESPONSE, _PERSPECTIVE_RESPONSE, _RMC_RESPONSE
        )
        mocker.patch("archpilot.llm.client.get_async_client", return_value=mock_client)

        client.get("/api/analyze/stream")
        s = sess.get()
        assert s.analysis_rmc is not None
        assert s.analysis_rmc["coverage_score"] == 78
        assert s.analysis_rmc["confidence_level"] == "medium"

    def test_session_multi_perspective_merged_into_analysis(self, client, session_with_system, mocker):
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _ANALYSIS_RESPONSE, _PERSPECTIVE_RESPONSE, _RMC_RESPONSE
        )
        mocker.patch("archpilot.llm.client.get_async_client", return_value=mock_client)

        client.get("/api/analyze/stream")
        s = sess.get()
        assert s.analysis.get("multi_perspective") is not None
        assert s.analysis["multi_perspective"]["consensus_summary"] == "Decomposition required."

    def test_stream_chat_called_three_times(self, client, session_with_system, mocker):
        """3-pass: main analyze → multi-perspective → RMC."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _ANALYSIS_RESPONSE, _PERSPECTIVE_RESPONSE, _RMC_RESPONSE
        )
        mocker.patch("archpilot.llm.client.get_async_client", return_value=mock_client)

        client.get("/api/analyze/stream")
        assert mock_client.stream_chat.call_count == 3

    def test_analysis_file_written_to_output_dir(self, tmp_path, mocker):
        from archpilot.ui.server import create_app
        fresh_app = create_app(output_dir=tmp_path)
        s = sess.get()
        s.system = MINIMAL_SYSTEM

        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _ANALYSIS_RESPONSE, _PERSPECTIVE_RESPONSE, _RMC_RESPONSE
        )
        mocker.patch("archpilot.llm.client.get_async_client", return_value=mock_client)

        with TestClient(fresh_app) as tc:
            tc.get("/api/analyze/stream")

        assert (tmp_path / "analysis.json").exists()
        saved = json.loads((tmp_path / "analysis.json").read_text())
        assert saved["system_name"] == "Test System"

    def test_requirements_in_user_msg_when_set(self, client, session_with_system, mocker):
        """요구사항이 세션에 저장되면 첫 번째 LLM 호출 user_msg에 반영된다."""
        session_with_system.requirements = "마이크로서비스로 전환"
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _ANALYSIS_RESPONSE, _PERSPECTIVE_RESPONSE, _RMC_RESPONSE
        )
        mocker.patch("archpilot.llm.client.get_async_client", return_value=mock_client)

        client.get("/api/analyze/stream")
        first_call_args = mock_client.stream_chat.call_args_list[0]
        user_msg = first_call_args[0][1]  # 두 번째 positional 인수 = user_msg
        assert "마이크로서비스로 전환" in user_msg

    def test_progress_percentage_increases(self, client, session_with_system, mocker):
        """progress 이벤트의 pct 값이 단조 증가해야 한다."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _ANALYSIS_RESPONSE, _PERSPECTIVE_RESPONSE, _RMC_RESPONSE
        )
        mocker.patch("archpilot.llm.client.get_async_client", return_value=mock_client)

        resp = client.get("/api/analyze/stream")
        events = parse_sse(resp.text)
        pcts = [e["pct"] for e in events if e.get("type") == "progress"]
        assert pcts == sorted(pcts), f"progress pct가 단조 증가하지 않음: {pcts}"


# ── 오류 시나리오 ─────────────────────────────────────────────────────────────

class TestAnalyzeStreamErrors:
    def test_invalid_analysis_json_yields_error_event(self, client, session_with_system, mocker):
        """LLM이 파싱 불가 응답을 반환하면 error SSE 이벤트가 방출된다."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            "not valid json {{{{ at all",
            "{}",
            "{}",
        )
        mocker.patch("archpilot.llm.client.get_async_client", return_value=mock_client)

        resp = client.get("/api/analyze/stream")
        events = parse_sse(resp.text)
        error_events = [e for e in events if e.get("type") == "error"]
        assert len(error_events) >= 1

    def test_perspective_parse_failure_tolerated(self, client, session_with_system, mocker):
        """Multi-perspective 파싱 실패는 무시되고 done 이벤트가 방출된다."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _ANALYSIS_RESPONSE,
            "not valid json",   # perspective 파싱 실패
            _RMC_RESPONSE,
        )
        mocker.patch("archpilot.llm.client.get_async_client", return_value=mock_client)

        resp = client.get("/api/analyze/stream")
        events = parse_sse(resp.text)
        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1

    def test_rmc_parse_failure_tolerated(self, client, session_with_system, mocker):
        """RMC 파싱 실패는 무시되고 done 이벤트가 방출된다."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _ANALYSIS_RESPONSE,
            _PERSPECTIVE_RESPONSE,
            "not valid json",   # RMC 파싱 실패
        )
        mocker.patch("archpilot.llm.client.get_async_client", return_value=mock_client)

        resp = client.get("/api/analyze/stream")
        events = parse_sse(resp.text)
        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1

    def test_rmc_failure_sets_analysis_rmc_to_none(self, client, session_with_system, mocker):
        """RMC 파싱 실패 시 session.analysis_rmc는 None으로 남는다."""
        mock_client = mocker.MagicMock()
        mock_client.stream_chat.side_effect = _make_stream(
            _ANALYSIS_RESPONSE,
            _PERSPECTIVE_RESPONSE,
            "not valid json",
        )
        mocker.patch("archpilot.llm.client.get_async_client", return_value=mock_client)

        client.get("/api/analyze/stream")
        assert sess.get().analysis_rmc is None
