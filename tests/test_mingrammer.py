"""MingrammerRenderer 및 _safe_var() 유닛 테스트."""

import pytest

from archpilot.renderers.mingrammer import _safe_var, _resolve_class, _build_imports
from archpilot.core.models import Component, ComponentType, HostType


# ── _safe_var 경계 조건 ────────────────────────────────────────────────────────

class TestSafeVar:
    def test_normal_id(self):
        assert _safe_var("my_comp") == "my_comp"

    def test_leading_digit(self):
        result = _safe_var("1comp")
        assert result == "c_1comp"
        assert result[0].isalpha()

    def test_hyphen_and_dot(self):
        assert _safe_var("my-comp.v2") == "my_comp_v2"

    def test_empty_string(self):
        assert _safe_var("") == "comp"

    def test_all_special_chars(self):
        # '---' → '___' (underscores are valid identifiers, not stripped)
        assert _safe_var("---") == "___"

    def test_spaces(self):
        assert _safe_var("my comp") == "my_comp"

    def test_trailing_space(self):
        result = _safe_var("comp ")
        assert result == "comp_"

    def test_only_underscores(self):
        # Valid Python identifier
        assert _safe_var("___") == "___"

    def test_unicode_replaced(self):
        result = _safe_var("компонент")
        # All non-ASCII replaced with '_'
        assert all(c == "_" for c in result)

    def test_sql_injection_pattern(self):
        # Dangerous string should be fully sanitized
        result = _safe_var("'; DROP TABLE users--")
        assert "'" not in result
        assert ";" not in result
        assert "-" not in result
        assert " " not in result

    def test_newline_in_id(self):
        result = _safe_var("comp\nid")
        assert "\n" not in result
        assert "comp_id" == result

    def test_purely_numeric(self):
        result = _safe_var("42")
        assert result.startswith("c_")
        assert not result[0].isdigit()

    def test_single_letter(self):
        assert _safe_var("x") == "x"

    def test_already_valid(self):
        assert _safe_var("validName_123") == "validName_123"


# ── _resolve_class 연기 테스트 ────────────────────────────────────────────────

class TestResolveClass:
    def _make_comp(self, ctype, host, tech=None):
        return Component(
            id="test",
            type=ctype,
            label="Test",
            tech=tech or [],
            host=host,
        )

    def test_aws_server_ec2(self):
        c = self._make_comp(ComponentType.SERVER, HostType.AWS, ["EC2"])
        cls = _resolve_class(c)
        assert "EC2" in cls

    def test_aws_database_rds(self):
        c = self._make_comp(ComponentType.DATABASE, HostType.AWS, ["RDS"])
        cls = _resolve_class(c)
        assert "RDS" in cls

    def test_onprem_server_fallback(self):
        c = self._make_comp(ComponentType.SERVER, HostType.ON_PREMISE)
        cls = _resolve_class(c)
        assert cls == "diagrams.onprem.compute.Server"

    def test_onprem_database_fallback(self):
        c = self._make_comp(ComponentType.DATABASE, HostType.ON_PREMISE)
        cls = _resolve_class(c)
        assert "onprem" in cls or "Mysql" in cls

    def test_unknown_returns_default(self):
        # 알 수 없는 조합 → 기본값
        c = self._make_comp(ComponentType.UNKNOWN, HostType.ON_PREMISE)
        cls = _resolve_class(c)
        assert cls == "diagrams.onprem.compute.Server"


# ── _build_imports 검증 ───────────────────────────────────────────────────────

class TestBuildImports:
    def test_single_component(self):
        comps = [Component(
            id="web", type=ComponentType.SERVER, label="Web",
            tech=[], host=HostType.ON_PREMISE,
        )]
        imports = _build_imports(comps)
        assert "from diagrams" in imports
        assert "import" in imports

    def test_deduplicates_same_class(self):
        comps = [
            Component(id="a", type=ComponentType.SERVER, label="A", tech=[], host=HostType.ON_PREMISE),
            Component(id="b", type=ComponentType.SERVER, label="B", tech=[], host=HostType.ON_PREMISE),
        ]
        imports = _build_imports(comps)
        # Should appear only once
        lines = imports.splitlines()
        class_lines = [l for l in lines if "Server" in l]
        assert len(class_lines) == 1

    def test_multiple_modules(self):
        comps = [
            Component(id="web", type=ComponentType.SERVER, label="Web", tech=[], host=HostType.ON_PREMISE),
            Component(id="db", type=ComponentType.DATABASE, label="DB", tech=[], host=HostType.AWS),
        ]
        imports = _build_imports(comps)
        assert imports.count("from diagrams") >= 1
