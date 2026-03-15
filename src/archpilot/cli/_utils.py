"""CLI 공통 유틸리티."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console

from archpilot.core.models import SystemModel

_console = Console()


def load_system_model(path: Path) -> SystemModel:
    """system.json을 읽어 SystemModel을 반환한다.

    실패 시 에러 메시지를 출력하고 typer.Exit(1)을 raise한다.
    """
    try:
        return SystemModel.model_validate_json(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        _console.print(
            f"[red]system.json JSON 파싱 오류 (line {e.lineno}): {e.msg}[/red]",
            err=True,
        )
        raise typer.Exit(1)
    except ValidationError as e:
        first = e.errors()[0]
        _console.print(
            f"[red]system.json 스키마 오류 {e.error_count()}건: "
            f"{first['loc']} — {first['msg']}[/red]",
            err=True,
        )
        raise typer.Exit(1)
