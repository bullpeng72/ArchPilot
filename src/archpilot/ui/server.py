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

    # ── API: 시스템 모델 다운로드 (yaml / json / drawio) ──────────────────────

    @app.get("/api/download/{step}")
    async def download_system(step: str, fmt: str = "yaml"):
        import json as _json

        import yaml as _yaml

        s = sess.get()
        data = s.modern if step == "modern" else s.system if step == "legacy" else None
        if data is None:
            raise HTTPException(status_code=404, detail=f"데이터가 없습니다: {step}")

        import re as _re
        system_name = (data.get("name") or step).lower().replace(" ", "_")
        # HTTP 헤더는 ASCII만 허용 — 비ASCII 문자 제거 후 fallback
        system_name = _re.sub(r"[^\x00-\x7F]+", "", system_name).strip("_") or step

        if fmt == "yaml":
            # connections: from_id/to_id → from/to (YAML 표준 입력 형식)
            import copy
            export = copy.deepcopy(data)
            for conn in export.get("connections", []):
                if "from_id" in conn:
                    conn["from"] = conn.pop("from_id")
                if "to_id" in conn:
                    conn["to"] = conn.pop("to_id")
            content = _yaml.dump(
                export, allow_unicode=True, default_flow_style=False,
                sort_keys=False, width=120,
            )
            media = "text/yaml"
            filename = f"{system_name}.yaml"

        elif fmt == "json":
            content = _json.dumps(data, ensure_ascii=False, indent=2)
            media = "application/json"
            filename = f"{system_name}.json"

        elif fmt == "drawio":
            drawio = s.modern_drawio if step == "modern" else s.legacy_drawio
            if not drawio:
                raise HTTPException(status_code=404, detail="draw.io 파일이 없습니다")
            content = drawio
            media = "application/xml"
            filename = f"{system_name}.drawio"

        else:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 포맷: {fmt} (yaml/json/drawio)")

        from urllib.parse import quote as _quote
        filename_star = _quote(filename, safe="")
        return StreamingResponse(
            iter([content]),
            media_type=media,
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{filename_star}"},
        )

    return app
