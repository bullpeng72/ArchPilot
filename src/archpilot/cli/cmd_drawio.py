"""archpilot drawio — draw.io Desktop 통합 커맨드 그룹."""

from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="drawio",
    help="draw.io Desktop 통합 도구 (설치·편집·감시·내보내기)",
    no_args_is_help=True,
)
console = Console()

# ArchPilot 라이브러리 기본 설치 경로
_LIBRARY_FILENAME = "archpilot-library.drawio.xml"


def _default_library_path() -> Path:
    return Path.home() / ".archpilot" / _LIBRARY_FILENAME


# ── setup ─────────────────────────────────────────────────────────────────────

@app.command("setup")
def setup(
    reset: Annotated[bool, typer.Option("--reset", help="기존 설정을 초기화하고 재설치")] = False,
    library_dir: Annotated[Optional[Path], typer.Option("--lib-dir", help="라이브러리 파일 저장 위치")] = None,
) -> None:
    """draw.io Desktop에 ArchPilot 컴포넌트 라이브러리를 설치합니다.

    \b
    동작:
      1. ~/.archpilot/archpilot-library.drawio.xml 생성
      2. draw.io Desktop localStorage(LevelDB)에 라이브러리 등록
      3. defaultLibraries를 빈 문자열로 설정해 기본 패널 숨김

    주의: 실행 전 draw.io Desktop을 완전히 종료해야 합니다.
    """
    from archpilot.core.drawio_config import (
        find_drawio_executable,
        find_drawio_localstorage_path,
        inject_custom_library,
    )
    from archpilot.renderers.drawio_library import write_library_file

    console.print("\n[bold cyan]⚙️  draw.io Desktop 통합 설정[/bold cyan]\n")

    # ── 1. draw.io 설치 확인 ───────────────────────────────────────────────
    exe = find_drawio_executable()
    if exe:
        console.print(f"[green]✅ draw.io 발견:[/green] {exe}")
    else:
        console.print(
            "[yellow]⚠️  draw.io Desktop을 찾지 못했습니다.[/yellow]\n"
            "   https://github.com/jgraph/drawio-desktop/releases 에서 무료 설치 후 재실행하세요."
        )
        raise typer.Exit(1)

    # ── 2. 라이브러리 파일 생성 ───────────────────────────────────────────
    lib_path = (library_dir or _default_library_path().parent) / _LIBRARY_FILENAME
    write_library_file(lib_path)
    console.print(f"[green]✅ 라이브러리 생성:[/green] {lib_path}")

    # ── 3. Electron localStorage에 라이브러리 등록 ────────────────────────
    # draw.io Desktop은 설정을 config.json이 아닌 Electron 브라우저 localStorage(LevelDB)에 저장한다.
    # DesktopLibrary.prototype.getHash() = 'S' + encodeURIComponent(path)
    console.print("[dim]draw.io Desktop이 닫혀 있어야 합니다.[/dim]")
    ldb_path = find_drawio_localstorage_path()
    if ldb_path is None:
        console.print(
            "[yellow]⚠️  draw.io Desktop을 아직 한 번도 실행하지 않았습니다.[/yellow]\n"
            "  draw.io Desktop을 한 번 실행 후 종료한 뒤 다시 실행하세요."
        )
        raise typer.Exit(1)

    ok = inject_custom_library(lib_path)
    if ok:
        console.print(f"[green]✅ localStorage 등록:[/green] {ldb_path}")
    else:
        console.print(
            "[red]❌ localStorage 등록 실패.[/red] draw.io Desktop을 완전히 종료 후 재시도하세요."
        )
        raise typer.Exit(1)

    # ── 결과 요약 ──────────────────────────────────────────────────────────
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("라이브러리 파일", str(lib_path))
    table.add_row("localStorage", str(ldb_path))

    console.print()
    console.print(Panel(table, title="[bold]설치 완료[/bold]", border_style="green"))
    console.print(
        "\n[bold]다음 단계:[/bold] draw.io Desktop을 [cyan]시작[/cyan]하면 "
        "ArchPilot 라이브러리가 사이드바에 표시됩니다.\n"
    )


# ── edit ──────────────────────────────────────────────────────────────────────

@app.command("edit")
def edit(
    output: Annotated[Path | None, typer.Option("--output", "-o", help="output 디렉토리")] = None,
    watch: Annotated[bool, typer.Option("--watch", "-w", help="저장 시 자동 파싱 (file watch)")] = True,
) -> None:
    """draw.io Desktop으로 다이어그램을 열고 변경을 감시합니다.

    \b
    - diagram.drawio 가 있으면 해당 파일을 엽니다.
    - system.json 만 있으면 drawio 파일을 자동 생성 후 엽니다.
    - 둘 다 없으면 빈 캔버스를 생성 후 엽니다.
    """
    from archpilot.config import settings
    from archpilot.core.drawio_config import find_drawio_executable

    output = (output or settings.output_dir).resolve()
    drawio_file = output / "legacy" / "diagram.drawio"

    if not drawio_file.exists():
        drawio_file.parent.mkdir(parents=True, exist_ok=True)
        system_json = output / "system.json"

        if system_json.exists():
            # system.json 이 있으면 drawio 파일 자동 생성
            import json as _json
            from archpilot.core.parser import SystemParser
            from archpilot.renderers.drawio import DrawioRenderer
            data = _json.loads(system_json.read_text(encoding="utf-8"))
            model = SystemParser()._dict_to_model(data)
            drawio_file.write_text(DrawioRenderer().render(model), encoding="utf-8")
            console.print(f"[green]✅ system.json으로 다이어그램 생성:[/green] {drawio_file}")
        else:
            # 빈 캔버스 생성
            _BLANK_DRAWIO = (
                '<mxGraphModel><root>'
                '<mxCell id="0"/>'
                '<mxCell id="1" parent="0"/>'
                '</root></mxGraphModel>'
            )
            drawio_file.write_text(_BLANK_DRAWIO, encoding="utf-8")
            console.print(f"[yellow]📄 빈 캔버스를 생성했습니다:[/yellow] {drawio_file}")
            console.print(
                "[dim]draw.io에서 다이어그램을 그린 뒤 저장(Ctrl+S)하면 "
                "ArchPilot에 자동으로 반영됩니다.[/dim]"
            )

    exe = find_drawio_executable()
    if not exe:
        console.print(
            "[red]❌ draw.io Desktop을 찾을 수 없습니다.[/red]\n"
            "https://github.com/jgraph/drawio-desktop/releases 에서 설치 후 재시도하세요.",
        )
        raise typer.Exit(1)

    # OS별 실행
    system = platform.system()
    console.print(f"\n[bold cyan]🖊  draw.io Desktop 실행 중:[/bold cyan] {drawio_file}\n")
    try:
        if system == "Darwin":
            subprocess.Popen(["open", "-a", str(exe), str(drawio_file)])
        elif system == "Windows":
            # os.startfile은 .drawio 파일 연결 앱이 다를 수 있으므로 실행 파일을 명시한다
            subprocess.Popen([str(exe), str(drawio_file)], shell=False)
        else:
            subprocess.Popen([str(exe), str(drawio_file)])
    except Exception as e:
        console.print(f"[red]실행 오류:[/red] {e}")
        raise typer.Exit(1)

    if not watch:
        console.print("[dim]편집 후 저장하면 수동으로 archpilot ingest diagram.drawio 를 실행하세요.[/dim]")
        return

    # ── 파일 감시 시작 ─────────────────────────────────────────────────────
    _watch_file(drawio_file, output)


# ── watch ─────────────────────────────────────────────────────────────────────

@app.command("watch")
def watch_cmd(
    file: Annotated[Path, typer.Argument(help=".drawio 파일 경로")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="output 디렉토리")] = None,
) -> None:
    """draw.io 파일의 변경을 감시하고 저장 시 자동으로 ArchPilot에 반영합니다."""
    from archpilot.config import settings

    if not file.exists():
        console.print(f"[red]❌ 파일 없음:[/red] {file}")
        raise typer.Exit(1)
    _watch_file(file, (output or settings.output_dir).resolve())


# ── export ────────────────────────────────────────────────────────────────────

@app.command("export")
def export_cmd(
    system_json: Annotated[Optional[Path], typer.Argument(help="system.json 경로")] = None,
    dest: Annotated[Optional[Path], typer.Option("--dest", "-d", help="저장 경로 (기본: output/legacy/diagram.drawio)")] = None,
) -> None:
    """system.json → .drawio 파일로 내보냅니다."""
    import json as _json

    from archpilot.config import settings
    from archpilot.core.parser import SystemParser
    from archpilot.renderers.drawio import DrawioRenderer

    system_json = (system_json or settings.output_dir / "system.json").resolve()

    if not system_json.exists():
        console.print(f"[red]❌ 파일 없음:[/red] {system_json}")
        raise typer.Exit(1)

    data = _json.loads(system_json.read_text(encoding="utf-8"))
    model = SystemParser()._dict_to_model(data)
    xml = DrawioRenderer().render(model)

    out = dest or system_json.parent / "legacy" / "diagram.drawio"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(xml, encoding="utf-8")
    console.print(f"[green]✅ 내보내기 완료:[/green] {out}")


# ── 내부 유틸 ─────────────────────────────────────────────────────────────────

def _watch_file(drawio_file: Path, output: Path) -> None:
    """watchdog으로 drawio_file을 감시하고 변경 시 자동 파싱한다."""
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        console.print(
            "[red]❌ watchdog 패키지가 필요합니다.[/red]\n"
            "  [cyan]pip install watchdog[/cyan]",
        )
        raise typer.Exit(1)

    from archpilot.renderers.drawio_parser import parse_drawio_xml
    from archpilot.renderers.mermaid import MermaidRenderer

    console.print(
        f"[bold]👁  파일 감시 중:[/bold] {drawio_file}\n"
        "[dim]draw.io에서 저장(Ctrl+S)하면 자동으로 ArchPilot에 반영됩니다.[/dim]\n"
        "[dim]종료: Ctrl+C[/dim]\n"
    )

    class _Handler(FileSystemEventHandler):
        def on_modified(self, event):  # type: ignore[override]
            if Path(event.src_path).resolve() != drawio_file.resolve():
                return
            _reparse(drawio_file, output)

    def _reparse(path: Path, out_dir: Path) -> None:
        try:
            xml = path.read_text(encoding="utf-8")
            model = parse_drawio_xml(xml)
        except Exception as e:
            console.print(f"[red]파싱 오류:[/red] {e}")
            return

        # system.json 갱신 (기존 메타데이터 보존)
        sys_json = out_dir / "system.json"
        prev_meta: dict = {}
        prev_comp_meta: dict[str, dict] = {}
        if sys_json.exists():
            try:
                prev = _json_load(sys_json)
                prev_meta = prev.get("metadata", {})
                prev_comp_meta = {c["id"]: c.get("metadata", {}) for c in prev.get("components", [])}
            except Exception:
                pass

        if prev_meta:
            model = model.model_copy(update={"metadata": {**prev_meta, **model.metadata}})
        if prev_comp_meta:
            updated = []
            for comp in model.components:
                prev = prev_comp_meta.get(comp.id, {})
                if prev:
                    comp = comp.model_copy(update={"metadata": {**prev, **comp.metadata}})
                updated.append(comp)
            model = model.model_copy(update={"components": updated})

        out_dir.mkdir(parents=True, exist_ok=True)
        sys_json.write_text(model.model_dump_json(indent=2), encoding="utf-8")

        legacy_dir = out_dir / "legacy"
        legacy_dir.mkdir(exist_ok=True)
        (legacy_dir / "diagram.mmd").write_text(MermaidRenderer().render(model), encoding="utf-8")

        console.print(
            f"[green]✅ 반영 완료:[/green] "
            f"컴포넌트 {len(model.components)}개 · 연결 {len(model.connections)}개"
        )

    import time

    observer = Observer()
    observer.schedule(_Handler(), str(drawio_file.parent), recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        console.print("\n[dim]감시 종료[/dim]")
    observer.join()


def _json_load(path: Path) -> dict:
    import json as _json
    return _json.loads(path.read_text(encoding="utf-8"))
