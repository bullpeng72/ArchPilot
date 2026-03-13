"""archpilot init — .env 초기화 마법사."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()
ENV_PATH = Path(".env")
EXAMPLE_PATH = Path(__file__).parent.parent.parent.parent / ".env.example"


def init_cmd() -> None:
    """[bold].env[/bold] 파일을 생성하고 API 키를 설정합니다."""
    console.print(Panel("[bold cyan]ArchPilot 초기화[/bold cyan]", expand=False))

    if ENV_PATH.exists():
        overwrite = typer.confirm(".env 파일이 이미 존재합니다. 덮어쓰시겠습니까?", default=False)
        if not overwrite:
            console.print("[yellow]초기화를 취소했습니다.[/yellow]")
            raise typer.Exit()

    api_key = typer.prompt("OpenAI API Key (sk-...)", hide_input=True)
    model = typer.prompt("사용할 모델", default="gpt-4o")
    output_dir = typer.prompt("출력 디렉토리", default="./output")

    env_content = f"""\
# ===== OpenAI =====
OPENAI_API_KEY={api_key}
OPENAI_MODEL={model}
OPENAI_MAX_TOKENS=4096

# ===== ArchPilot =====
ARCHPILOT_OUTPUT_DIR={output_dir}
ARCHPILOT_DIAGRAM_FORMAT=png
ARCHPILOT_SERVER_HOST=127.0.0.1
ARCHPILOT_SERVER_PORT=8080
"""
    ENV_PATH.write_text(env_content, encoding="utf-8")
    console.print(f"\n[green]✅ .env 파일이 생성되었습니다:[/green] {ENV_PATH.absolute()}")
    console.print("\n다음 명령어로 시작하세요:")
    console.print("  [cyan]archpilot ingest examples/legacy_ecommerce.yaml[/cyan]")
