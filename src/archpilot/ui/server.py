"""FastAPI 기반 인터랙티브 UI 서버."""

from __future__ import annotations

import logging
from pathlib import Path

_log = logging.getLogger("archpilot.server")

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

from archpilot.core.models import AnalysisResult, SystemModel
from archpilot.ui import session as sess
from archpilot.ui.routers.ingest import router as ingest_router
from archpilot.ui.routers.analyze import router as analyze_router
from archpilot.ui.routers.modernize import router as modernize_router


# ── Jinja2 템플릿 ─────────────────────────────────────────────────────────────

_TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


# ── FastAPI 앱 팩토리 ─────────────────────────────────────────────────────────

def create_app(output_dir: Path = Path("./output")) -> FastAPI:
    app = FastAPI(title="ArchPilot", docs_url=None, redoc_url=None)
    output_dir.mkdir(parents=True, exist_ok=True)

    # output_dir을 app.state에 저장 — 라우터가 request.app.state.output_dir로 접근
    app.state.output_dir = output_dir

    # 라우터 등록
    app.include_router(ingest_router)
    app.include_router(analyze_router)
    app.include_router(modernize_router)

    # ── 페이지 라우트 ─────────────────────────────────────────────────────────

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse("app.html.j2", {"request": request})

    @app.get("/slides", response_class=HTMLResponse)
    async def slides(request: Request, theme: str = "black"):
        s = sess.get()
        ctx = {
            "request": request,
            "theme": theme,
            "legacy": SystemModel.model_validate(s.system) if s.system else None,
            "modern": SystemModel.model_validate(s.modern) if s.modern else None,
            "analysis": AnalysisResult.model_validate(s.analysis) if s.analysis else None,
            "legacy_mermaid": s.legacy_mmd,
            "modern_mermaid": s.modern_mmd,
            "migration_plan": s.migration_plan,
        }
        if ctx["legacy"] and ctx["modern"]:
            from archpilot.core.diff import SystemDiff
            ctx["diff"] = SystemDiff().compare(ctx["legacy"], ctx["modern"])
        else:
            ctx["diff"] = None
        return templates.TemplateResponse("slides.html.j2", ctx)

    # ── API: 세션 상태 ────────────────────────────────────────────────────────

    @app.get("/api/state")
    async def get_state():
        return sess.get().to_dict()

    @app.delete("/api/state")
    async def reset_state():
        sess.reset()
        return {"status": "ok"}

    # ── API: 다이어그램 조회 ──────────────────────────────────────────────────

    @app.get("/api/diagram/{step}")
    async def get_diagram(step: str, fmt: str = "mermaid"):
        s = sess.get()
        if step == "legacy":
            content = s.legacy_mmd if fmt == "mermaid" else s.legacy_drawio
            media = "text/plain" if fmt == "mermaid" else "application/xml"
        elif step == "modern":
            content = s.modern_mmd if fmt == "mermaid" else s.modern_drawio
            media = "text/plain" if fmt == "mermaid" else "application/xml"
        else:
            raise HTTPException(status_code=404, detail=f"Unknown step: {step}")

        if not content:
            raise HTTPException(status_code=404, detail="아직 생성된 다이어그램이 없습니다")

        ext = "mmd" if fmt == "mermaid" else "drawio"
        return StreamingResponse(
            iter([content]),
            media_type=media,
            headers={"Content-Disposition": f'attachment; filename="diagram-{step}.{ext}"'},
        )

    return app
