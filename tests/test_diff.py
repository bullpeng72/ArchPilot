"""DiffEngine 단위 테스트."""

from archpilot.core.diff import SystemDiff
from archpilot.core.models import (
    Component,
    ComponentType,
    Connection,
    HostType,
    SystemModel,
)


def _make_model(components, connections=None):
    return SystemModel(
        name="Test",
        components=components,
        connections=connections or [],
    )


def test_added_component():
    legacy = _make_model([
        Component(id="web", type=ComponentType.SERVER, label="Web"),
    ])
    modern = _make_model([
        Component(id="web", type=ComponentType.SERVER, label="Web"),
        Component(id="api", type=ComponentType.GATEWAY, label="API GW"),
    ])
    diff = SystemDiff().compare(legacy, modern)
    assert len(diff.added) == 1
    assert diff.added[0].id == "api"


def test_removed_component():
    legacy = _make_model([
        Component(id="web", type=ComponentType.SERVER, label="Web"),
        Component(id="old", type=ComponentType.SERVER, label="Old"),
    ])
    modern = _make_model([
        Component(id="web", type=ComponentType.SERVER, label="Web"),
    ])
    diff = SystemDiff().compare(legacy, modern)
    assert len(diff.removed) == 1
    assert diff.removed[0].id == "old"


def test_modified_component():
    legacy = _make_model([
        Component(id="db", type=ComponentType.DATABASE, label="MySQL",
                  host=HostType.ON_PREMISE, tech=["MySQL 5.7"]),
    ])
    modern = _make_model([
        Component(id="db", type=ComponentType.DATABASE, label="Aurora",
                  host=HostType.AWS, tech=["Aurora MySQL"]),
    ])
    diff = SystemDiff().compare(legacy, modern)
    assert len(diff.modified) == 1
    assert "host" in diff.modified[0].changed_fields


def test_unchanged_component(sample_model):
    diff = SystemDiff().compare(sample_model, sample_model)
    assert len(diff.unchanged) == len(sample_model.components)
    assert len(diff.added) == 0
    assert len(diff.removed) == 0
