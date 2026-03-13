"""렌더러 추상 기반 클래스 및 레지스트리."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from archpilot.core.models import SystemModel


class BaseRenderer(ABC):
    name: ClassVar[str] = ""
    output_ext: ClassVar[str] = ".txt"

    @abstractmethod
    def render(self, model: SystemModel) -> str:
        """SystemModel을 문자열(DSL/XML/코드)로 변환."""

    def save(self, model: SystemModel, output_dir: Path, filename: str = "diagram") -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        content = self.render(model)
        path = output_dir / f"{filename}{self.output_ext}"
        path.write_text(content, encoding="utf-8")
        return path


# ── 렌더러 레지스트리 ─────────────────────────────────────────────────────────

def _build_registry() -> dict[str, type[BaseRenderer]]:
    from archpilot.renderers.drawio import DrawioRenderer
    from archpilot.renderers.mermaid import MermaidRenderer
    from archpilot.renderers.mingrammer import MingrammerRenderer

    return {
        "mermaid": MermaidRenderer,
        "png": MingrammerRenderer,
        "svg": MingrammerRenderer,
        "drawio": DrawioRenderer,
    }


def get_renderer(fmt: str) -> BaseRenderer:
    registry = _build_registry()
    cls = registry.get(fmt.lower())
    if cls is None:
        supported = ", ".join(registry.keys())
        raise ValueError(f"알 수 없는 포맷: '{fmt}'. 지원: {supported}")
    return cls()


def run_renderers_parallel(
    model: SystemModel,
    formats: list[str],
    output_dir: Path,
    filename: str = "diagram",
) -> dict[str, Path | Exception]:
    import concurrent.futures

    renderers = [(fmt, get_renderer(fmt)) for fmt in formats]
    results: dict[str, Path | Exception] = {}

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(r.save, model, output_dir, filename): fmt
            for fmt, r in renderers
        }
        for future in concurrent.futures.as_completed(futures):
            fmt = futures[future]
            try:
                results[fmt] = future.result()
            except Exception as e:
                results[fmt] = e

    return results
