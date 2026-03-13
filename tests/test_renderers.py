"""렌더러 단위 테스트."""

import pytest

from archpilot.renderers.drawio import DrawioRenderer
from archpilot.renderers.mermaid import MermaidRenderer


def test_mermaid_contains_component_ids(sample_model):
    output = MermaidRenderer().render(sample_model)
    assert "web" in output
    assert "db" in output
    assert "cache" in output


def test_mermaid_contains_protocols(sample_model):
    output = MermaidRenderer().render(sample_model)
    assert "JDBC" in output
    assert "TCP" in output


def test_mermaid_has_subgraphs(sample_model):
    output = MermaidRenderer().render(sample_model)
    assert "subgraph" in output
    assert "on_premise" in output
    assert "aws" in output


def test_mermaid_flowchart_header(sample_model):
    output = MermaidRenderer().render(sample_model)
    assert output.startswith("flowchart LR")


def test_drawio_is_xml(sample_model):
    output = DrawioRenderer().render(sample_model)
    assert "<mxGraphModel>" in output
    assert "<mxCell" in output


def test_drawio_contains_components(sample_model):
    output = DrawioRenderer().render(sample_model)
    assert 'id="web"' in output
    assert 'id="db"' in output


def test_mermaid_save(sample_model, tmp_path):
    path = MermaidRenderer().save(sample_model, tmp_path)
    assert path.exists()
    assert path.suffix == ".mmd"
    content = path.read_text()
    assert "flowchart LR" in content


def test_drawio_save(sample_model, tmp_path):
    path = DrawioRenderer().save(sample_model, tmp_path)
    assert path.exists()
    assert path.suffix == ".drawio"
