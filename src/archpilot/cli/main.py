"""ArchPilot CLI 진입점."""

import typer
from rich.console import Console

from archpilot import __version__

app = typer.Typer(
    name="archpilot",
    help="Legacy 시스템을 다이어그램으로 코드화하고 AI 기반으로 현대화 설계를 생성합니다.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold cyan]ArchPilot[/bold cyan] v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-V",
        callback=version_callback,
        is_eager=True,
        help="버전 출력",
    ),
) -> None:
    pass


# 서브커맨드 등록
from archpilot.cli.cmd_init import init_cmd
from archpilot.cli.cmd_ingest import ingest
from archpilot.cli.cmd_analyze import analyze
from archpilot.cli.cmd_modernize import modernize
from archpilot.cli.cmd_serve import serve, export
from archpilot.cli.cmd_drawio import app as drawio_app

app.command("init")(init_cmd)
app.command("ingest")(ingest)
app.command("analyze")(analyze)
app.command("modernize")(modernize)
app.command("serve")(serve)
app.command("export")(export)
app.add_typer(drawio_app, name="drawio")
