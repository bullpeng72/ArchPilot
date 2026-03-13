"""archpilot serve / export — FastAPI + reveal.js UI 서버."""

from __future__ import annotations

import threading
import webbrowser
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()


def serve(
    output_dir: Annotated[Path, typer.Argument(help="output 디렉토리")] = Path("./output"),
    port: Annotated[int, typer.Option("--port", "-p", help="서버 포트")] = 8080,
    host: Annotated[str, typer.Option("--host", help="서버 호스트 주소")] = "127.0.0.1",
    open_browser: Annotated[bool, typer.Option("--open/--no-open", help="시작 시 브라우저 자동 열기")] = True,
    reload: Annotated[bool, typer.Option("--reload", help="개발 모드 (코드 변경 시 자동 재시작)")] = False,
) -> None:
    """
    FastAPI 기반 인터랙티브 UI 서버를 실행합니다.

    브라우저에서 시스템 주입 → AI 분석 → 현대화 설계 → 발표 모드까지
    전체 워크플로우를 실행할 수 있습니다.
    """
    import uvicorn
    from archpilot.ui.server import create_app

    url = f"http://{host}:{port}"

    console.print(Panel(
        f"[bold cyan]🚀 ArchPilot UI 서버 시작[/bold cyan]\n\n"
        f"  인터랙티브 UI : [link={url}]{url}[/link]\n"
        f"  발표 모드     : [link={url}/slides]{url}/slides[/link]\n\n"
        f"  [dim]종료: Ctrl+C[/dim]",
        expand=False,
    ))

    output_dir.mkdir(parents=True, exist_ok=True)
    app = create_app(output_dir)

    if open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="warning",
        reload=reload,
    )


def export(
    output_dir: Annotated[Path, typer.Argument(help="output 디렉토리")] = Path("./output"),
    dest: Annotated[Path, typer.Option("--dest", "-d", help="저장 디렉토리")] = Path("./dist"),
    theme: Annotated[str, typer.Option("--theme", help="reveal.js 테마: black,white,league,beige,sky,night,moon,serif,solarized")] = "black",
) -> None:
    """발표 슬라이드를 정적 HTML로 내보냅니다."""
    from jinja2 import Environment, PackageLoader, select_autoescape
    from archpilot.core.models import AnalysisResult, SystemModel
    from archpilot.core.diff import SystemDiff
    from archpilot.ui import session as sess

    if not output_dir.exists():
        console.print(f"[red]디렉토리를 찾을 수 없습니다: {output_dir}[/red]", err=True)
        raise typer.Exit(1)

    # output/ 디렉토리에서 직접 파일 읽기
    ctx: dict = {"theme": theme, "diff": None}

    legacy_json = output_dir / "system.json"
    ctx["legacy"] = SystemModel.model_validate_json(legacy_json.read_text()) if legacy_json.exists() else None

    modern_json = output_dir / "modern" / "system.json"
    ctx["modern"] = SystemModel.model_validate_json(modern_json.read_text()) if modern_json.exists() else None

    analysis_json = output_dir / "analysis.json"
    ctx["analysis"] = AnalysisResult.model_validate_json(analysis_json.read_text()) if analysis_json.exists() else None

    ctx["legacy_mermaid"] = (output_dir / "legacy" / "diagram.mmd").read_text() \
        if (output_dir / "legacy" / "diagram.mmd").exists() else ""
    ctx["modern_mermaid"] = (output_dir / "modern" / "diagram.mmd").read_text() \
        if (output_dir / "modern" / "diagram.mmd").exists() else ""
    ctx["migration_plan"] = (output_dir / "modern" / "migration_plan.md").read_text() \
        if (output_dir / "modern" / "migration_plan.md").exists() else ""

    if ctx["legacy"] and ctx["modern"]:
        ctx["diff"] = SystemDiff().compare(ctx["legacy"], ctx["modern"])

    env = Environment(
        loader=PackageLoader("archpilot", "ui/templates"),
        autoescape=select_autoescape(["html"]),
    )
    html = env.get_template("slides.html.j2").render(**ctx)

    dest.mkdir(parents=True, exist_ok=True)
    index_path = dest / "index.html"
    index_path.write_text(html, encoding="utf-8")

    console.print(f"[green]✅ HTML 내보내기 완료:[/green] {index_path.absolute()}")
