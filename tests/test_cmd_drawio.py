"""tests/test_cmd_drawio.py — archpilot drawio CLI 커맨드 유닛 테스트."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from archpilot.cli.main import app


runner = CliRunner()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_output(tmp_path: Path) -> Path:
    output = tmp_path / "output"
    output.mkdir()
    return output


@pytest.fixture
def system_json(tmp_output: Path) -> Path:
    """최소 system.json을 tmp_output에 생성한다."""
    data = {
        "name": "Test System",
        "components": [
            {"id": "web_svc", "type": "service", "label": "Web Service"},
            {"id": "db", "type": "database", "label": "Database"},
        ],
        "connections": [{"from_id": "web_svc", "to_id": "db", "protocol": "TCP"}],
    }
    path = tmp_output / "system.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def drawio_file(tmp_output: Path) -> Path:
    """최소 .drawio 파일을 tmp_output/legacy에 생성한다."""
    legacy = tmp_output / "legacy"
    legacy.mkdir()
    xml = (
        '<mxGraphModel><root>'
        '<mxCell id="0"/>'
        '<mxCell id="1" parent="0"/>'
        '<mxCell id="2" value="WebSvc" style="shape=mxgraph.archpilot.service;" vertex="1" parent="1">'
        '<mxGeometry x="100" y="100" width="120" height="60" as="geometry"/>'
        '</mxCell>'
        '</root></mxGraphModel>'
    )
    path = legacy / "diagram.drawio"
    path.write_text(xml, encoding="utf-8")
    return path


# ── drawio export ─────────────────────────────────────────────────────────────

class TestDrawioExport:
    def test_export_creates_drawio_file(self, system_json: Path, tmp_output: Path):
        result = runner.invoke(app, [
            "drawio", "export", str(system_json),
            "--dest", str(tmp_output / "out.drawio"),
        ])
        assert result.exit_code == 0, result.output
        assert (tmp_output / "out.drawio").exists()

    def test_export_file_not_found_exits_1(self, tmp_path: Path):
        result = runner.invoke(app, [
            "drawio", "export", str(tmp_path / "nonexistent.json"),
        ])
        assert result.exit_code == 1

    def test_export_output_contains_xml(self, system_json: Path, tmp_output: Path):
        dest = tmp_output / "diagram.drawio"
        runner.invoke(app, ["drawio", "export", str(system_json), "--dest", str(dest)])
        content = dest.read_text(encoding="utf-8")
        assert "<mxGraphModel" in content or "mxCell" in content

    def test_export_default_dest(self, system_json: Path, tmp_output: Path):
        """dest 미지정 시 system.json 옆 legacy/diagram.drawio에 저장."""
        with patch("archpilot.config.settings") as mock_settings:
            mock_settings.output_dir = tmp_output
            result = runner.invoke(app, ["drawio", "export", str(system_json)])
        assert result.exit_code == 0, result.output


# ── drawio watch ─────────────────────────────────────────────────────────────

class TestDrawioWatch:
    def test_watch_file_not_found_exits_1(self, tmp_path: Path):
        result = runner.invoke(app, [
            "drawio", "watch", str(tmp_path / "missing.drawio"),
        ])
        assert result.exit_code == 1
        assert "파일 없음" in result.output or "없음" in result.output

    def test_watch_missing_watchdog_exits_1(self, drawio_file: Path, tmp_output: Path):
        """watchdog 미설치 시 exit code 1."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "watchdog.observers":
                raise ImportError("No module named 'watchdog'")
            if name == "watchdog.events":
                raise ImportError("No module named 'watchdog'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = runner.invoke(app, [
                "drawio", "watch", str(drawio_file),
                "--output", str(tmp_output),
            ])
        assert result.exit_code == 1


# ── drawio setup ─────────────────────────────────────────────────────────────

class TestDrawioSetup:
    def test_setup_no_drawio_executable_exits_1(self):
        with patch(
            "archpilot.core.drawio_config.find_drawio_executable",
            return_value=None,
        ):
            result = runner.invoke(app, ["drawio", "setup"])
        assert result.exit_code == 1
        assert "draw.io" in result.output.lower() or "drawio" in result.output.lower()

    def test_setup_no_localstorage_exits_1(self, tmp_path: Path):
        fake_exe = tmp_path / "drawio"
        fake_exe.touch()
        with (
            patch("archpilot.core.drawio_config.find_drawio_executable", return_value=fake_exe),
            patch("archpilot.core.drawio_config.find_drawio_localstorage_path", return_value=None),
            patch("archpilot.renderers.drawio_library.write_library_file"),
        ):
            result = runner.invoke(app, ["drawio", "setup"])
        assert result.exit_code == 1

    def test_setup_inject_fails_exits_1(self, tmp_path: Path):
        fake_exe = tmp_path / "drawio"
        fake_exe.touch()
        ldb_path = tmp_path / "localstorage"
        with (
            patch("archpilot.core.drawio_config.find_drawio_executable", return_value=fake_exe),
            patch("archpilot.core.drawio_config.find_drawio_localstorage_path", return_value=ldb_path),
            patch("archpilot.core.drawio_config.inject_custom_library", return_value=False),
            patch("archpilot.renderers.drawio_library.write_library_file"),
        ):
            result = runner.invoke(app, ["drawio", "setup"])
        assert result.exit_code == 1

    def test_setup_success(self, tmp_path: Path):
        fake_exe = tmp_path / "drawio"
        fake_exe.touch()
        ldb_path = tmp_path / "localstorage"
        lib_path = tmp_path / ".archpilot" / "archpilot-library.drawio.xml"
        lib_path.parent.mkdir(parents=True, exist_ok=True)
        lib_path.touch()
        with (
            patch("archpilot.core.drawio_config.find_drawio_executable", return_value=fake_exe),
            patch("archpilot.core.drawio_config.find_drawio_localstorage_path", return_value=ldb_path),
            patch("archpilot.core.drawio_config.inject_custom_library", return_value=True),
            patch("archpilot.renderers.drawio_library.write_library_file"),
            patch("archpilot.cli.cmd_drawio._default_library_path", return_value=lib_path),
        ):
            result = runner.invoke(app, ["drawio", "setup"])
        assert result.exit_code == 0


# ── drawio edit ───────────────────────────────────────────────────────────────

class TestDrawioEdit:
    def test_edit_no_drawio_executable_exits_1(self, tmp_output: Path):
        with (
            patch("archpilot.core.drawio_config.find_drawio_executable", return_value=None),
            patch("archpilot.config.settings") as mock_settings,
        ):
            mock_settings.output_dir = tmp_output
            result = runner.invoke(app, [
                "drawio", "edit", "--no-watch", "--output", str(tmp_output),
            ])
        assert result.exit_code == 1

    def test_edit_opens_existing_drawio(self, drawio_file: Path, tmp_output: Path):
        fake_exe = Path("/usr/bin/drawio")
        with (
            patch("archpilot.core.drawio_config.find_drawio_executable", return_value=fake_exe),
            patch("subprocess.Popen") as mock_popen,
            patch("archpilot.config.settings") as mock_settings,
        ):
            mock_settings.output_dir = tmp_output
            result = runner.invoke(app, [
                "drawio", "edit", "--no-watch", "--output", str(tmp_output),
            ])
        assert result.exit_code == 0
        mock_popen.assert_called_once()

    def test_edit_creates_blank_canvas_when_no_files(self, tmp_output: Path):
        fake_exe = Path("/usr/bin/drawio")
        with (
            patch("archpilot.core.drawio_config.find_drawio_executable", return_value=fake_exe),
            patch("subprocess.Popen"),
            patch("archpilot.config.settings") as mock_settings,
        ):
            mock_settings.output_dir = tmp_output
            result = runner.invoke(app, [
                "drawio", "edit", "--no-watch", "--output", str(tmp_output),
            ])
        assert result.exit_code == 0
        drawio_path = tmp_output / "legacy" / "diagram.drawio"
        assert drawio_path.exists()
        content = drawio_path.read_text()
        assert "mxCell" in content

    def test_edit_creates_drawio_from_system_json(
        self, system_json: Path, tmp_output: Path
    ):
        fake_exe = Path("/usr/bin/drawio")
        with (
            patch("archpilot.core.drawio_config.find_drawio_executable", return_value=fake_exe),
            patch("subprocess.Popen"),
            patch("archpilot.config.settings") as mock_settings,
        ):
            mock_settings.output_dir = tmp_output
            result = runner.invoke(app, [
                "drawio", "edit", "--no-watch", "--output", str(tmp_output),
            ])
        assert result.exit_code == 0
        drawio_path = tmp_output / "legacy" / "diagram.drawio"
        assert drawio_path.exists()


# ── _reparse 내부 유틸 ────────────────────────────────────────────────────────

class TestReparse:
    def test_reparse_updates_system_json(self, drawio_file: Path, tmp_output: Path):
        from archpilot.cli.cmd_drawio import _reparse
        _reparse(drawio_file, tmp_output)
        sys_json = tmp_output / "system.json"
        assert sys_json.exists()

    def test_reparse_preserves_existing_metadata(
        self, drawio_file: Path, tmp_output: Path
    ):
        from archpilot.cli.cmd_drawio import _reparse
        # 기존 system.json에 메타데이터 설정
        existing = {
            "name": "Old",
            "metadata": {"domain": "banking"},
            "components": [],
            "connections": [],
        }
        (tmp_output / "system.json").write_text(json.dumps(existing), encoding="utf-8")
        _reparse(drawio_file, tmp_output)
        updated = json.loads((tmp_output / "system.json").read_text())
        assert updated.get("metadata", {}).get("domain") == "banking"

    def test_reparse_invalid_xml_does_not_crash(
        self, tmp_path: Path, tmp_output: Path
    ):
        from archpilot.cli.cmd_drawio import _reparse
        bad_file = tmp_path / "bad.drawio"
        bad_file.write_text("not valid xml at all!!!", encoding="utf-8")
        # should not raise
        _reparse(bad_file, tmp_output)


# ── _merge_metadata ───────────────────────────────────────────────────────────

class TestMergeMetadata:
    def _make_model(self, comps: list[dict]):
        from archpilot.core.models import Component, SystemModel
        return SystemModel(
            name="Test",
            components=[Component(**c) for c in comps],
            connections=[],
        )

    def test_merge_system_metadata(self):
        from archpilot.cli.cmd_drawio import _merge_metadata
        model = self._make_model([{"id": "svc_a", "type": "service", "label": "A"}])
        prev_meta = {"domain": "banking", "vintage": 2010}
        result = _merge_metadata(model, prev_meta, {})
        assert result.metadata.get("domain") == "banking"

    def test_merge_component_metadata(self):
        from archpilot.cli.cmd_drawio import _merge_metadata
        model = self._make_model([{"id": "svc_a", "type": "service", "label": "A"}])
        prev_comp_meta = {"svc_a": {"criticality": "high", "owner": "팀A"}}
        result = _merge_metadata(model, {}, prev_comp_meta)
        svc = next(c for c in result.components if c.id == "svc_a")
        assert svc.metadata.get("criticality") == "high"

    def test_empty_prev_meta_unchanged(self):
        from archpilot.cli.cmd_drawio import _merge_metadata
        model = self._make_model([{"id": "svc_a", "type": "service", "label": "A"}])
        result = _merge_metadata(model, {}, {})
        assert result.metadata == model.metadata
