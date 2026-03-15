"""archpilot modernize — LLM 기반 현대화 시스템 설계 생성."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from archpilot.cli._utils import load_system_model
from archpilot.core.models import AnalysisResult
from archpilot.renderers.base import VALID_FORMATS

console = Console()


def modernize(
    system_json: Annotated[Path, typer.Argument(help="system.json 경로")],
    requirements: Annotated[str, typer.Option("--requirements", "-r", help="자연어 현대화 요구사항")] = "",
    output: Annotated[Path | None, typer.Option("--output", "-o", help="출력 디렉토리 (기본: system.json 위치)")] = None,
    formats: Annotated[str, typer.Option("--format", "-f", help="다이어그램 포맷 (콤마 구분): mermaid,png,svg,drawio")] = "mermaid",
    no_analysis: Annotated[bool, typer.Option("--no-analysis", help="analysis.json 참조 건너뜀")] = False,
) -> None:
    """레거시 시스템을 자연어 요구사항에 따라 현대화된 아키텍처로 재설계합니다."""
    if not requirements:
        requirements = typer.prompt("현대화 요구사항을 입력하세요")

    if not system_json.exists():
        console.print(f"[red]파일을 찾을 수 없습니다: {system_json}[/red]", err=True)
        raise typer.Exit(1)

    fmt_list = [f.strip().lower() for f in formats.split(",")]
    invalid = set(fmt_list) - VALID_FORMATS
    if invalid:
        console.print(f"[red]지원하지 않는 포맷: {invalid}[/red]", err=True)
        raise typer.Exit(1)

    output_dir = output or system_json.parent
    modern_dir = output_dir / "modern"
    modern_dir.mkdir(parents=True, exist_ok=True)

    legacy = load_system_model(system_json)

    analysis: AnalysisResult | None = None
    if not no_analysis:
        analysis_path = output_dir / "analysis.json"
        if analysis_path.exists():
            try:
                analysis = AnalysisResult.model_validate_json(analysis_path.read_text())
                console.print(f"[dim]분석 결과 참조: {analysis_path}[/dim]")
            except Exception as e:
                console.print(f"[yellow]⚠ analysis.json 로드 실패 (무시됨): {e}[/yellow]")

    console.print(f"\n[bold]⚙️  현대화 설계 생성 중:[/bold] {legacy.name}")
    console.print(f"[dim]요구사항: {requirements}[/dim]")

    from archpilot.llm.modernizer import SystemModernizer
    from archpilot.renderers.base import run_renderers_parallel

    modernizer = SystemModernizer()
    try:
        modern = modernizer.modernize(legacy, requirements, analysis)
    except Exception as e:
        console.print(f"[red]현대화 설계 생성 실패: {e}[/red]", err=True)
        raise typer.Exit(1) from e

    modern_json_path = modern_dir / "system.json"
    modern_json_path.write_text(modern.model_dump_json(indent=2), encoding="utf-8")

    console.print(f"[bold]🎨 다이어그램 생성 중:[/bold] {', '.join(fmt_list)}")
    diagram_results = run_renderers_parallel(modern, fmt_list, modern_dir, filename="diagram")

    console.print("[bold]📋 마이그레이션 플랜 생성 중...[/bold]")
    plan_path = None
    try:
        plan_md = modernizer.generate_migration_plan(legacy, modern, analysis, requirements)
        plan_path = modern_dir / "migration_plan.md"
        plan_path.write_text(plan_md, encoding="utf-8")
    except Exception as e:
        console.print(f"[yellow]마이그레이션 플랜 생성 실패: {e}[/yellow]")

    table = Table(title="[bold cyan]ArchPilot — Modernize 완료[/bold cyan]")
    table.add_column("항목", style="bold")
    table.add_column("값")
    table.add_row("신규 시스템", modern.name)
    table.add_row("컴포넌트 수", str(len(modern.components)))
    table.add_row("연결 수", str(len(modern.connections)))
    table.add_row("system.json", str(modern_json_path))
    table.add_section()
    for fmt, result in diagram_results.items():
        if isinstance(result, Exception):
            table.add_row(fmt, f"[red]❌ {result}[/red]")
        else:
            table.add_row(fmt, f"[green]✅ {result}[/green]")
    if plan_path:
        table.add_row("migration_plan.md", f"[green]✅ {plan_path}[/green]")

    console.print()
    console.print(table)
    console.print(f"\n다음 단계: [cyan]archpilot serve {output_dir}[/cyan]")
