"""archpilot init — .env 초기화 마법사."""

from __future__ import annotations

import getpass
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from archpilot.config import GLOBAL_CONFIG_DIR, GLOBAL_ENV_FILE

console = Console()


def _prompt_api_key(prompt: str) -> str:
    """API 키 입력 (입력 내용 비표시, 크로스 플랫폼)."""
    return getpass.getpass(f"{prompt}: ")


def init_cmd() -> None:
    """[bold]~/.archpilot/config.env[/bold] 파일을 생성하고 API 키를 설정합니다."""
    console.print(Panel("[bold cyan]ArchPilot 초기화[/bold cyan]", expand=False))

    if GLOBAL_ENV_FILE.exists():
        overwrite = typer.confirm(
            f"설정 파일이 이미 존재합니다 ({GLOBAL_ENV_FILE}). 덮어쓰시겠습니까?",
            default=False,
        )
        if not overwrite:
            console.print("[yellow]초기화를 취소했습니다.[/yellow]")
            raise typer.Exit()

    api_key = _prompt_api_key("OpenAI API Key (sk-...)")
    model = typer.prompt("사용할 모델", default="gpt-4o-mini")
    default_output = str(Path.cwd() / "output")
    output_dir_input = typer.prompt("출력 디렉토리", default=default_output)

    # 절대 경로로 저장 — 어디서 실행해도 동일한 경로 참조
    output_dir_abs = Path(output_dir_input).expanduser().resolve()

    env_content = f"""\
# ===== OpenAI =====
OPENAI_API_KEY={api_key}
OPENAI_MODEL={model}
OPENAI_MAX_TOKENS=4096

# ===== ArchPilot =====
ARCHPILOT_OUTPUT_DIR={output_dir_abs}
ARCHPILOT_DIAGRAM_FORMAT=png
ARCHPILOT_SERVER_HOST=127.0.0.1
ARCHPILOT_SERVER_PORT=8080
"""
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    GLOBAL_ENV_FILE.write_text(env_content, encoding="utf-8")
    console.print(f"\n[green]✅ 설정 파일이 생성되었습니다:[/green] {GLOBAL_ENV_FILE}")
    console.print(f"   출력 디렉토리: [cyan]{output_dir_abs}[/cyan]")
    console.print("\n[dim]로컬 .env 파일이 있으면 전역 설정을 오버라이드합니다.[/dim]")

    console.print("\n[bold]── 시작 방법 선택 ──────────────────────────────[/bold]")

    console.print("\n[bold cyan]① YAML / JSON 파일로 시작[/bold cyan]")
    console.print("   [cyan]archpilot ingest <시스템.yaml>[/cyan]")
    console.print("   [cyan]archpilot analyze output/system.json[/cyan]")
    console.print("   [cyan]archpilot modernize output/system.json -r \"요구사항\"[/cyan]")

    console.print("\n[bold cyan]② 인터랙티브 웹 앱으로 시작[/bold cyan]")
    console.print("   [cyan]archpilot serve[/cyan]   [dim]→ 브라우저에서 시스템 입력·분석·발표 슬라이드[/dim]")

    console.print("\n[bold cyan]③ draw.io Desktop 연동[/bold cyan]")
    console.print("   [dim]1) draw.io Desktop 설치:[/dim]")
    console.print("      [link=https://github.com/jgraph/drawio-desktop/releases]https://github.com/jgraph/drawio-desktop/releases[/link]")
    console.print("   [dim]2) ArchPilot 라이브러리 등록 (draw.io 종료 상태에서):[/dim]")
    console.print("      [cyan]archpilot drawio setup[/cyan]")
    console.print("   [dim]3) draw.io Desktop 실행 후 다이어그램 작성, 저장 시 자동 반영:[/dim]")
    console.print("      [cyan]archpilot drawio edit[/cyan]")
