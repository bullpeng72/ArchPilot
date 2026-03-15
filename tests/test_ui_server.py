"""FastAPI UI 서버 엔드포인트 테스트."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from archpilot.ui import session as sess


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_session():
    """각 테스트 전후 세션 상태 초기화."""
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


# ── 최소 시스템 JSON ──────────────────────────────────────────────────────────

MINIMAL_SYSTEM_JSON = json.dumps({
    "name": "Test System",
    "components": [
        {"id": "web", "type": "server", "label": "Web Server", "tech": ["Nginx"]},
        {"id": "db", "type": "database", "label": "MySQL", "tech": ["MySQL 8"]},
    ],
    "connections": [
        {"from": "web", "to": "db", "protocol": "JDBC"},
    ],
})

MINIMAL_SYSTEM_YAML = """
name: Test System
components:
  - id: web
    type: server
    label: Web Server
    tech: [Nginx]
  - id: db
    type: database
    label: MySQL
    tech: [MySQL 8]
connections:
  - from: web
    to: db
    protocol: JDBC
""".strip()

# 최소한의 유효한 draw.io XML
MINIMAL_DRAWIO_XML = """<?xml version="1.0" encoding="UTF-8"?>
<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>
    <mxCell id="web" value="Web Server" style="rounded=1;fillColor=#dae8fc;" vertex="1" parent="1">
      <mxGeometry x="100" y="100" width="120" height="60" as="geometry"/>
    </mxCell>
    <mxCell id="db" value="MySQL" style="shape=cylinder;fillColor=#f5f5f5;" vertex="1" parent="1">
      <mxGeometry x="300" y="100" width="80" height="80" as="geometry"/>
    </mxCell>
    <mxCell id="e1" style="" edge="1" source="web" target="db" parent="1">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>"""


# ── 페이지 라우트 ─────────────────────────────────────────────────────────────

class TestPageRoutes:
    def test_index_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_slides_without_data(self, client):
        resp = client.get("/slides")
        assert resp.status_code == 200


# ── 세션 상태 API ─────────────────────────────────────────────────────────────

class TestStateApi:
    def test_get_state_initial(self, client):
        resp = client.get("/api/state")
        assert resp.status_code == 200
        data = resp.json()
        assert data["step"] == 0
        assert data["system"] is None

    def test_reset_state(self, client):
        # 먼저 ingest
        client.post("/api/ingest", json={"content": MINIMAL_SYSTEM_JSON, "mode": "json"})
        assert sess.get().system is not None
        # 리셋
        resp = client.delete("/api/state")
        assert resp.status_code == 200
        assert sess.get().system is None


# ── 시스템 주입 API ───────────────────────────────────────────────────────────

class TestIngestApi:
    def test_ingest_json_mode(self, client, tmp_path):
        resp = client.post("/api/ingest", json={"content": MINIMAL_SYSTEM_JSON, "mode": "json"})
        assert resp.status_code == 200
        data = resp.json()
        assert "system" in data
        assert data["system"]["name"] == "Test System"
        assert "legacy_mmd" in data
        assert "legacy_drawio" in data

    def test_ingest_yaml_mode(self, client):
        resp = client.post("/api/ingest", json={"content": MINIMAL_SYSTEM_YAML, "mode": "yaml"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["system"]["name"] == "Test System"

    def test_ingest_auto_mode_json(self, client):
        resp = client.post("/api/ingest", json={"content": MINIMAL_SYSTEM_JSON, "mode": "auto"})
        assert resp.status_code == 200

    def test_ingest_auto_mode_yaml(self, client):
        resp = client.post("/api/ingest", json={"content": MINIMAL_SYSTEM_YAML, "mode": "auto"})
        assert resp.status_code == 200

    def test_ingest_saves_session(self, client):
        client.post("/api/ingest", json={"content": MINIMAL_SYSTEM_JSON, "mode": "json"})
        s = sess.get()
        assert s.system is not None
        assert s.legacy_mmd != ""
        assert s.legacy_drawio != ""

    def test_ingest_saves_files(self, client, tmp_path):
        client.post("/api/ingest", json={"content": MINIMAL_SYSTEM_JSON, "mode": "json"})
        assert (tmp_path / "system.json").exists()
        assert (tmp_path / "legacy" / "diagram.mmd").exists()
        assert (tmp_path / "legacy" / "diagram.drawio").exists()

    def test_ingest_invalid_json_returns_422(self, client):
        resp = client.post("/api/ingest", json={"content": "not valid json or yaml {{{{", "mode": "json"})
        assert resp.status_code in (422, 500)

    def test_ingest_resets_modernization(self, client):
        # 첫 ingest
        client.post("/api/ingest", json={"content": MINIMAL_SYSTEM_JSON, "mode": "json"})
        s = sess.get()
        s.analysis = {"mock": True}  # 임시 분석 결과 주입
        # 재 ingest → 분석 결과 초기화
        client.post("/api/ingest", json={"content": MINIMAL_SYSTEM_JSON, "mode": "json"})
        assert sess.get().analysis is None

    def test_ingest_state_step_updated(self, client):
        client.post("/api/ingest", json={"content": MINIMAL_SYSTEM_JSON, "mode": "json"})
        resp = client.get("/api/state")
        assert resp.json()["step"] >= 1


class TestIngestFileApi:
    def test_ingest_yaml_file(self, client):
        resp = client.post(
            "/api/ingest/file",
            files={"file": ("system.yaml", MINIMAL_SYSTEM_YAML.encode(), "text/yaml")},
        )
        assert resp.status_code == 200
        assert resp.json()["system"]["name"] == "Test System"

    def test_ingest_json_file(self, client):
        resp = client.post(
            "/api/ingest/file",
            files={"file": ("system.json", MINIMAL_SYSTEM_JSON.encode(), "application/json")},
        )
        assert resp.status_code == 200


class TestIngestDrawioApi:
    def test_ingest_drawio_valid(self, client):
        resp = client.post(
            "/api/ingest/drawio",
            json={"xml": MINIMAL_DRAWIO_XML, "system_name": "Drawio System"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "system" in data
        assert data["system"]["name"] == "Drawio System"

    def test_ingest_drawio_invalid_xml(self, client):
        resp = client.post(
            "/api/ingest/drawio",
            json={"xml": "<<not valid xml>>", "system_name": "Bad"},
        )
        assert resp.status_code == 422

    def test_ingest_drawio_empty_diagram(self, client):
        empty_xml = """<?xml version="1.0"?>
<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel>"""
        resp = client.post(
            "/api/ingest/drawio",
            json={"xml": empty_xml, "system_name": "Empty"},
        )
        assert resp.status_code == 422

    def test_ingest_drawio_preserves_original_xml(self, client):
        client.post(
            "/api/ingest/drawio",
            json={"xml": MINIMAL_DRAWIO_XML, "system_name": "Test"},
        )
        # 원본 XML이 세션에 보존
        assert sess.get().legacy_drawio == MINIMAL_DRAWIO_XML


# ── 다이어그램 API ────────────────────────────────────────────────────────────

class TestDiagramApi:
    def test_diagram_before_ingest_returns_404(self, client):
        resp = client.get("/api/diagram/legacy")
        assert resp.status_code == 404

    def test_diagram_legacy_mermaid(self, client):
        client.post("/api/ingest", json={"content": MINIMAL_SYSTEM_JSON, "mode": "json"})
        resp = client.get("/api/diagram/legacy?fmt=mermaid")
        assert resp.status_code == 200
        assert "diagram" in resp.text.lower() or "graph" in resp.text.lower()

    def test_diagram_legacy_drawio(self, client):
        client.post("/api/ingest", json={"content": MINIMAL_SYSTEM_JSON, "mode": "json"})
        resp = client.get("/api/diagram/legacy?fmt=drawio")
        assert resp.status_code == 200
        assert "<mxGraphModel" in resp.text

    def test_diagram_unknown_step(self, client):
        resp = client.get("/api/diagram/unknown")
        assert resp.status_code == 404
