"""파서 단위 테스트."""

import pytest
from pathlib import Path

from archpilot.core.models import ComponentType, HostType, SystemModel
from archpilot.core.parser import ParseError, SystemParser


def test_parse_yaml_ecommerce(ecommerce_yaml_path):
    model = SystemParser().from_file(ecommerce_yaml_path)
    assert model.name == "E-Commerce Legacy System"
    assert len(model.components) == 7
    assert len(model.connections) == 6


def test_parse_component_types(ecommerce_yaml_path):
    model = SystemParser().from_file(ecommerce_yaml_path)
    types = {c.type for c in model.components}
    assert ComponentType.SERVER in types
    assert ComponentType.DATABASE in types
    assert ComponentType.CACHE in types


def test_parse_json(tmp_path):
    json_content = """{
        "name": "JSON System",
        "components": [
            {"id": "svc", "type": "service", "label": "My Service"}
        ]
    }"""
    path = tmp_path / "system.json"
    path.write_text(json_content)
    model = SystemParser().from_file(path)
    assert model.name == "JSON System"
    assert len(model.components) == 1


def test_invalid_connection_raises(tmp_path):
    yaml_content = """
name: Bad System
components:
  - id: web
    type: server
    label: Web
connections:
  - from: web
    to: nonexistent
    protocol: HTTP
"""
    path = tmp_path / "bad.yaml"
    path.write_text(yaml_content)
    with pytest.raises(Exception):
        SystemParser().from_file(path)


def test_duplicate_id_raises(tmp_path):
    yaml_content = """
name: Dup System
components:
  - id: web
    type: server
    label: Web1
  - id: web
    type: server
    label: Web2
"""
    path = tmp_path / "dup.yaml"
    path.write_text(yaml_content)
    with pytest.raises(Exception):
        SystemParser().from_file(path)


def test_missing_name_raises(tmp_path):
    yaml_content = "components:\n  - id: a\n    type: server\n    label: A\n"
    path = tmp_path / "no_name.yaml"
    path.write_text(yaml_content)
    with pytest.raises(ParseError, match="name"):
        SystemParser().from_file(path)


def test_unknown_host_falls_back(tmp_path):
    yaml_content = """
name: S
components:
  - id: a
    type: server
    label: A
    host: unknown_cloud
"""
    path = tmp_path / "unk.yaml"
    path.write_text(yaml_content)
    model = SystemParser().from_file(path)
    assert model.components[0].host == HostType.ON_PREMISE
