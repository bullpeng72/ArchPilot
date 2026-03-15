"""archpilot analyze — LLM 기반 레거시 시스템 분석."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from archpilot.cli._utils import load_system_model

console = Console()


def analyze(
    system_json: Annotated[Path, typer.Argument(help="system.json 경로")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="분석 결과 저장 디렉토리 (기본: system.json 위치)")] = None,
    requirements: Annotated[str, typer.Option("--requirements", "-r", help="현대화 목표 (분석 시 component_decisions에 반영)")] = "",
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="문제점·기술부채·현대화 기회 전체 목록 출력")] = False,
) -> None:
    """system.json을 읽어 LLM 분석 보고서를 생성합니다."""
    if not system_json.exists():
        console.print(f"[red]파일을 찾을 수 없습니다: {system_json}[/red]", err=True)
        raise typer.Exit(1)

    output_dir = output or system_json.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    model = load_system_model(system_json)

    console.print(f"\n[bold]🔍 분석 중:[/bold] {model.name}")

    from archpilot.llm.analyzer import SystemAnalyzer
    try:
        result = SystemAnalyzer().analyze(model, requirements=requirements)
    except Exception as e:
        console.print(f"[red]분석 실패: {e}[/red]", err=True)
        raise typer.Exit(1)

    analysis_path = output_dir / "analysis.json"
    analysis_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    console.print(Panel(f"[bold]{result.summary}[/bold]", title="요약", expand=False))

    if verbose:
        if result.pain_points:
            console.print("\n[bold red]⚠ 문제점[/bold red]")
            for p in result.pain_points:
                console.print(f"  • {p}")
        if result.tech_debt:
            console.print("\n[bold yellow]🔧 기술 부채[/bold yellow]")
            for td in result.tech_debt:
                console.print(f"  [{td.severity}] {td.component_id}: {td.description}")
        if result.modernization_opportunities:
            console.print("\n[bold green]💡 현대화 기회[/bold green]")
            for opp in result.modernization_opportunities:
                console.print(f"  P{opp.priority}. {opp.area}: {opp.description}")
    else:
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("항목", style="bold yellow")
        table.add_column("내용")
        table.add_row("예상 공수", result.estimated_effort.value)
        table.add_row("주요 문제", f"{len(result.pain_points)}건")
        table.add_row("기술 부채", f"{len(result.tech_debt)}건")
        table.add_row("위험 영역", f"{len(result.risk_areas)}건")
        table.add_row("권장 패턴", ", ".join(result.recommended_patterns[:3]))
        console.print(table)

    console.print(f"\n[green]✅ 분석 완료:[/green] {analysis_path}")
    console.print(f"\n다음 단계: [cyan]archpilot modernize {system_json} --requirements \"요구사항\"[/cyan]")
