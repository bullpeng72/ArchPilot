"""archpilot ingest — 레거시 시스템 파일 주입 및 다이어그램 생성."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from archpilot.config import settings
from archpilot.core.models import Criticality, LifecycleStatus
from archpilot.core.parser import ParseError, SystemParser
from archpilot.renderers.base import VALID_FORMATS, run_renderers_parallel

console = Console()


def ingest(
    file: Annotated[Path, typer.Argument(help="입력 파일 (yaml/json/txt)")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="출력 디렉토리")] = None,
    formats: Annotated[str, typer.Option("--format", "-f", help="출력 포맷 (콤마 구분): mermaid,png,svg,drawio")] = "mermaid",
    no_llm: Annotated[bool, typer.Option("--no-llm", help="LLM 파싱 비활성화")] = False,
    force: Annotated[bool, typer.Option("--force", help="출력 덮어쓰기")] = False,
) -> None:
    """
    레거시 시스템 파일을 읽어 SystemModel을 생성하고 다이어그램을 출력합니다.

    Examples:

      archpilot ingest system.yaml

      archpilot ingest system.yaml --format mermaid,png,drawio -o ./output
    """
    fmt_list = [f.strip().lower() for f in formats.split(",")]
    invalid = set(fmt_list) - VALID_FORMATS
    if invalid:
        console.print(f"[red]지원하지 않는 포맷: {invalid}. 지원: {VALID_FORMATS}[/red]", err=True)
        raise typer.Exit(1)

    output = (output or settings.output_dir).resolve()
    legacy_dir = output / "legacy"
    if legacy_dir.exists() and not force:
        overwrite = typer.confirm(f"{legacy_dir} 가 이미 존재합니다. 덮어쓰시겠습니까?", default=True)
        if not overwrite:
            raise typer.Exit()

    console.print(f"\n[bold]📂 파일 파싱 중:[/bold] {file}")
    try:
        model = SystemParser().from_file(file, use_llm=not no_llm)
    except ParseError as e:
        console.print(f"[red]파싱 오류:[/red] {e}", err=True)
        raise typer.Exit(1) from e

    output.mkdir(parents=True, exist_ok=True)
    system_json_path = output / "system.json"
    system_json_path.write_text(model.model_dump_json(indent=2), encoding="utf-8")

    console.print(f"[bold]🎨 다이어그램 생성 중:[/bold] {', '.join(fmt_list)}")
    legacy_dir.mkdir(parents=True, exist_ok=True)
    results = run_renderers_parallel(model, fmt_list, legacy_dir, filename="diagram")

    table = Table(title="[bold cyan]ArchPilot — Ingest 완료[/bold cyan]", show_header=True)
    table.add_column("항목", style="bold")
    table.add_column("값")
    table.add_row("시스템", model.name)
    table.add_row("설명", model.description or "-")
    table.add_row("컴포넌트 수", str(len(model.components)))
    table.add_row("연결 수", str(len(model.connections)))
    table.add_row("system.json", str(system_json_path))
    table.add_section()
    for fmt, result in results.items():
        if isinstance(result, Exception):
            table.add_row(fmt, f"[red]❌ {result}[/red]")
        else:
            table.add_row(fmt, f"[green]✅ {result}[/green]")

    console.print()
    console.print(table)

    # ── 엔터프라이즈 경고 요약 ──────────────────────────────────────────────
    eol_comps = [c for c in model.components
                 if c.lifecycle_status in (LifecycleStatus.EOL, LifecycleStatus.DEPRECATED)]
    high_comps = [c for c in model.components if c.criticality == Criticality.HIGH]
    restricted_comps = [c for c in model.components
                        if c.data_classification is not None
                        and c.data_classification.value in ("restricted", "confidential")]

    if eol_comps or high_comps or restricted_comps:
        console.print()
        if eol_comps:
            labels = ", ".join(c.label for c in eol_comps[:5])
            suffix = f" 외 {len(eol_comps) - 5}개" if len(eol_comps) > 5 else ""
            console.print(
                f"[yellow]⚠  EOL/Deprecated 컴포넌트 {len(eol_comps)}개:[/yellow] {labels}{suffix}"
            )
        if high_comps:
            labels = ", ".join(c.label for c in high_comps[:5])
            suffix = f" 외 {len(high_comps) - 5}개" if len(high_comps) > 5 else ""
            console.print(
                f"[red]🔴 HIGH 중요도 컴포넌트 {len(high_comps)}개:[/red] {labels}{suffix}"
            )
        if restricted_comps:
            labels = ", ".join(c.label for c in restricted_comps[:5])
            suffix = f" 외 {len(restricted_comps) - 5}개" if len(restricted_comps) > 5 else ""
            console.print(
                f"[magenta]🔒 민감 데이터 컴포넌트 {len(restricted_comps)}개:[/magenta] {labels}{suffix}"
            )

    console.print(f"\n다음 단계: [cyan]archpilot analyze {system_json_path}[/cyan]")
