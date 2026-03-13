"""pytest 공통 fixture."""

import pytest

from archpilot.core.models import (
    Component,
    ComponentType,
    Connection,
    HostType,
    SystemModel,
)


@pytest.fixture
def sample_model() -> SystemModel:
    return SystemModel(
        name="Test System",
        description="테스트용 시스템",
        components=[
            Component(id="web", type=ComponentType.SERVER, label="Web Server",
                      tech=["Nginx"], host=HostType.ON_PREMISE),
            Component(id="db", type=ComponentType.DATABASE, label="MySQL",
                      tech=["MySQL 8.0"], host=HostType.ON_PREMISE),
            Component(id="cache", type=ComponentType.CACHE, label="Redis",
                      tech=["Redis 7"], host=HostType.AWS),
        ],
        connections=[
            Connection(from_id="web", to_id="db", protocol="JDBC"),
            Connection(from_id="web", to_id="cache", protocol="TCP"),
        ],
    )


@pytest.fixture
def ecommerce_yaml_path(tmp_path):
    import shutil
    from pathlib import Path
    src = Path(__file__).parent.parent / "examples" / "legacy_ecommerce.yaml"
    dst = tmp_path / "legacy_ecommerce.yaml"
    shutil.copy(src, dst)
    return dst
