"""FastAPI 기반 인터랙티브 UI 서버."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel

from archpilot.config import settings
from archpilot.core.models import (
    AnalysisResult, Criticality, DataClassification, LifecycleStatus, SystemModel,
)
from archpilot.core.parser import ParseError, SystemParser
from archpilot.renderers.mermaid import MermaidRenderer
from archpilot.renderers.drawio import DrawioRenderer
from archpilot.ui import session as sess


# ── Jinja2 템플릿 ─────────────────────────────────────────────────────────────

_TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def _clean_json(text: str) -> str:
    """LLM 스트리밍 응답에서 마크다운 코드 펜스 제거."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _stream_response(generator: AsyncGenerator) -> StreamingResponse:
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── Request / Response 모델 ───────────────────────────────────────────────────

class IngestRequest(BaseModel):
    content: str
    mode: str = "auto"  # auto | yaml | json | text


class ModernizeRequest(BaseModel):
    requirements: str


class ChatIngestRequest(BaseModel):
    messages: list[dict]  # [{role: "user"|"assistant", content: "..."}]


class DrawioIngestRequest(BaseModel):
    xml: str
    system_name: str = "Imported System"


# ── FastAPI 앱 팩토리 ─────────────────────────────────────────────────────────

def create_app(output_dir: Path = Path("./output")) -> FastAPI:
    app = FastAPI(title="ArchPilot", docs_url=None, redoc_url=None)
    output_dir.mkdir(parents=True, exist_ok=True)

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

    # ── API: 시스템 주입 ──────────────────────────────────────────────────────

    @app.post("/api/ingest")
    async def ingest(req: IngestRequest):
        content = req.content.strip()
        mode = req.mode

        # mode 자동 감지
        if mode == "auto":
            stripped = content.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                mode = "json"
            elif (stripped.startswith("---")
                  or (":" in stripped
                      and ("\n" in stripped or stripped.count(":") > 1)
                      and not stripped.startswith("http"))):
                mode = "yaml"
            else:
                mode = "text"

        try:
            parser = SystemParser()
            if mode == "text":
                model = parser.from_text(content)
            elif mode == "yaml":
                model = parser._from_yaml(content, Path("<web>"))
            else:  # json
                model = parser._from_json(content, Path("<web>"))
        except ParseError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        # 다이어그램 생성
        legacy_mmd = MermaidRenderer().render(model)
        legacy_drawio = DrawioRenderer().render(model)

        # 세션 저장
        s = sess.get()
        s.system = json.loads(model.model_dump_json())
        s.legacy_mmd = legacy_mmd
        s.legacy_drawio = legacy_drawio
        # 현대화 관련 초기화
        s.analysis = None
        s.modern = None
        s.modern_mmd = ""
        s.modern_drawio = ""
        s.migration_plan = ""

        # output/ 파일 저장
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "system.json").write_text(
            model.model_dump_json(indent=2), encoding="utf-8"
        )
        legacy_dir = output_dir / "legacy"
        legacy_dir.mkdir(exist_ok=True)
        (legacy_dir / "diagram.mmd").write_text(legacy_mmd, encoding="utf-8")
        (legacy_dir / "diagram.drawio").write_text(legacy_drawio, encoding="utf-8")

        return {
            "system": s.system,
            "legacy_mmd": legacy_mmd,
            "legacy_drawio": legacy_drawio,
        }

    @app.post("/api/ingest/file")
    async def ingest_file(file: UploadFile = File(...)):
        content = (await file.read()).decode("utf-8")
        filename = file.filename or ""
        if filename.endswith((".yaml", ".yml")):
            mode = "yaml"
        elif filename.endswith(".json"):
            mode = "json"
        elif filename.endswith(".txt"):
            mode = "text"
        else:
            mode = "auto"
        req = IngestRequest(content=content, mode=mode)
        # 동일 로직 재사용
        return await ingest(req)

    # ── API: draw.io XML 주입 ─────────────────────────────────────────────────

    @app.post("/api/ingest/drawio")
    async def ingest_drawio(req: DrawioIngestRequest):
        from archpilot.renderers.drawio_parser import parse_drawio_xml

        s = sess.get()

        try:
            model = parse_drawio_xml(req.xml, system_name=req.system_name)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        # ── 기존 세션의 semantic 메타데이터 보존 ────────────────────────────
        # draw.io XML은 구조(컴포넌트·연결·호스트)만 담으므로
        # 이전 세션에서 얻은 메타데이터와 enterprise typed 필드를 복원한다.
        # 새 값이 있으면 새 값이 우선한다.
        if s.system:
            prev_sys_meta = s.system.get("metadata", {})
            if prev_sys_meta:
                merged_meta = {**prev_sys_meta, **model.metadata}
                model = model.model_copy(update={"metadata": merged_meta})

            prev_comps: dict[str, dict] = {
                c["id"]: c for c in s.system.get("components", [])
            }
            if prev_comps:
                updated = []
                for comp in model.components:
                    prev = prev_comps.get(comp.id)
                    if not prev:
                        updated.append(comp)
                        continue

                    patch: dict = {}

                    # metadata dict 병합 (새 값 우선)
                    patch["metadata"] = {**prev.get("metadata", {}), **comp.metadata}

                    # draw.io로 표현 불가한 enterprise typed 필드 복원
                    # — 재임포트 후 기본값인 경우에만 이전 값으로 덮어씀
                    if (comp.criticality == Criticality.MEDIUM
                            and prev.get("criticality") not in (None, "medium")):
                        try:
                            patch["criticality"] = Criticality(prev["criticality"])
                        except ValueError:
                            pass

                    if (comp.lifecycle_status == LifecycleStatus.ACTIVE
                            and prev.get("lifecycle_status") not in (None, "active")):
                        try:
                            patch["lifecycle_status"] = LifecycleStatus(prev["lifecycle_status"])
                        except ValueError:
                            pass

                    # data_classification·owner 는 draw.io에 인코딩 자체가 불가하므로 항상 복원
                    if comp.data_classification is None and prev.get("data_classification"):
                        try:
                            patch["data_classification"] = DataClassification(
                                prev["data_classification"]
                            )
                        except ValueError:
                            pass

                    if not comp.owner and prev.get("owner"):
                        patch["owner"] = prev["owner"]

                    updated.append(comp.model_copy(update=patch))
                model = model.model_copy(update={"components": updated})
        # ────────────────────────────────────────────────────────────────────

        legacy_mmd    = MermaidRenderer().render(model)
        legacy_drawio = DrawioRenderer().render(model)

        s.system       = json.loads(model.model_dump_json())
        s.legacy_mmd   = legacy_mmd
        s.legacy_drawio = req.xml          # 사용자가 편집한 원본 XML 보존
        s.analysis     = None
        s.modern       = None
        s.modern_mmd   = ""
        s.modern_drawio = ""
        s.migration_plan = ""

        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "system.json").write_text(
            model.model_dump_json(indent=2), encoding="utf-8"
        )
        legacy_dir = output_dir / "legacy"
        legacy_dir.mkdir(exist_ok=True)
        (legacy_dir / "diagram.mmd").write_text(legacy_mmd, encoding="utf-8")
        (legacy_dir / "diagram.drawio").write_text(req.xml, encoding="utf-8")

        return {
            "system":        s.system,
            "legacy_mmd":    legacy_mmd,
            "legacy_drawio": req.xml,
        }

    # ── API: 대화형 시스템 입력 ───────────────────────────────────────────────

    @app.post("/api/chat/ingest/stream")
    async def chat_ingest_stream(req: ChatIngestRequest):
        from archpilot.llm.client import get_async_client, LLMError
        from archpilot.llm.prompts import CHAT_INGEST_SYSTEM_PROMPT

        async def generator():
            try:
                client = get_async_client()
                full_text = ""

                async for chunk in client.stream_chat_messages(
                    CHAT_INGEST_SYSTEM_PROMPT,
                    req.messages,
                ):
                    full_text += chunk
                    yield _sse({"type": "chunk", "text": chunk})

                # 응답이 JSON({...})으로 시작하면 시스템 모델로 파싱 시도
                clean = full_text.strip()
                system_extracted = False
                if clean.startswith("{"):
                    try:
                        result = json.loads(clean)
                        if result.get("__system__"):
                            system_dict = {k: v for k, v in result.items() if k != "__system__"}
                            # normalize_connections는 _dict_to_model 내부에서 자동 처리
                            from archpilot.core.parser import SystemParser
                            model = SystemParser()._dict_to_model(system_dict)
                            legacy_mmd = MermaidRenderer().render(model)
                            legacy_drawio = DrawioRenderer().render(model)

                            s = sess.get()
                            s.system = json.loads(model.model_dump_json())
                            s.legacy_mmd = legacy_mmd
                            s.legacy_drawio = legacy_drawio
                            s.analysis = None
                            s.modern = None
                            s.modern_mmd = ""
                            s.modern_drawio = ""
                            s.migration_plan = ""

                            output_dir.mkdir(parents=True, exist_ok=True)
                            (output_dir / "system.json").write_text(
                                model.model_dump_json(indent=2), encoding="utf-8"
                            )
                            legacy_dir = output_dir / "legacy"
                            legacy_dir.mkdir(exist_ok=True)
                            (legacy_dir / "diagram.mmd").write_text(legacy_mmd, encoding="utf-8")
                            (legacy_dir / "diagram.drawio").write_text(legacy_drawio, encoding="utf-8")

                            yield _sse({
                                "type": "system_ready",
                                "system": s.system,
                                "legacy_mmd": legacy_mmd,
                                "legacy_drawio": legacy_drawio,
                            })
                            system_extracted = True
                    except Exception:
                        pass

                if not system_extracted:
                    yield _sse({"type": "reply", "text": full_text})

            except Exception as e:
                yield _sse({"type": "error", "msg": str(e)})

        return await _stream_response(generator())

    # ── API: 분석 스트리밍 ────────────────────────────────────────────────────

    @app.get("/api/analyze/stream")
    async def analyze_stream():
        s = sess.get()
        if not s.system:
            raise HTTPException(status_code=400, detail="먼저 시스템을 주입하세요 (/api/ingest)")

        from archpilot.llm.client import get_async_client, LLMError
        from archpilot.llm.prompts import ANALYZE_SYSTEM_PROMPT

        async def generator():
            try:
                yield _sse({"type": "progress", "pct": 5, "msg": "분석을 시작합니다..."})

                # 대형 시스템 컨텍스트 초과 방지 (analyzer.py와 동일 로직)
                _MAX_PAYLOAD_CHARS = 24_000
                payload = json.dumps(s.system, ensure_ascii=False, indent=2)
                if len(payload) > _MAX_PAYLOAD_CHARS:
                    compact = json.dumps(s.system, ensure_ascii=False)
                    if len(compact) > _MAX_PAYLOAD_CHARS:
                        d = json.loads(compact)
                        for c in d.get("components", []):
                            c.pop("metadata", None)
                            c.pop("specs", None)
                        compact = json.dumps(d, ensure_ascii=False)
                    payload = compact

                user_msg = f"분석할 시스템:\n{payload}"

                client = get_async_client()
                full_text = ""

                yield _sse({"type": "progress", "pct": 15, "msg": f"{settings.openai_model}이 시스템을 분석하고 있습니다..."})

                async for chunk in client.stream_chat(
                    ANALYZE_SYSTEM_PROMPT + "\nIMPORTANT: Output ONLY raw JSON, no markdown fences.",
                    user_msg,
                ):
                    full_text += chunk
                    yield _sse({"type": "chunk", "text": chunk})

                yield _sse({"type": "progress", "pct": 90, "msg": "결과를 파싱하고 있습니다..."})

                # JSON 파싱
                clean = _clean_json(full_text)
                result_dict = json.loads(clean)
                analysis = AnalysisResult.model_validate(result_dict)

                # 세션 & 파일 저장
                s.analysis = json.loads(analysis.model_dump_json())
                (output_dir / "analysis.json").write_text(
                    analysis.model_dump_json(indent=2), encoding="utf-8"
                )

                yield _sse({"type": "done", "result": s.analysis})

            except Exception as e:
                yield _sse({"type": "error", "msg": str(e)})

        return await _stream_response(generator())

    # ── API: 현대화 스트리밍 ──────────────────────────────────────────────────

    @app.post("/api/modernize/stream")
    async def modernize_stream(req: ModernizeRequest):
        s = sess.get()
        if not s.system:
            raise HTTPException(status_code=400, detail="먼저 시스템을 주입하세요")

        s.requirements = req.requirements

        from archpilot.llm.client import get_async_client, LLMError
        from archpilot.llm.prompts import MODERNIZE_SYSTEM_PROMPT, MIGRATION_PLAN_PROMPT
        from archpilot.core.parser import SystemParser

        async def generator():
            try:
                yield _sse({"type": "progress", "pct": 5, "msg": "현대화 설계를 시작합니다..."})

                # 레거시 시스템 페이로드 압축
                _MAX_SYSTEM_CHARS = 20_000
                _MAX_PLAN_CHARS = 10_000

                def _compress(system_dict: dict, max_chars: int) -> str:
                    payload = json.dumps(system_dict, ensure_ascii=False, indent=2)
                    if len(payload) <= max_chars:
                        return payload
                    compact = json.dumps(system_dict, ensure_ascii=False)
                    if len(compact) <= max_chars:
                        return compact
                    d = json.loads(compact)
                    for c in d.get("components", []):
                        c.pop("metadata", None)
                        c.pop("specs", None)
                    return json.dumps(d, ensure_ascii=False)

                analysis_section = ""
                if s.analysis:
                    analysis_section = f"\n\n분석 결과:\n{json.dumps(s.analysis, ensure_ascii=False)}"

                user_msg = (
                    f"현대화 요구사항:\n{req.requirements}"
                    f"{analysis_section}"
                    f"\n\nLegacy 시스템:\n{_compress(s.system, _MAX_SYSTEM_CHARS)}"
                )

                client = get_async_client()

                # ① 현대화 SystemModel 생성
                yield _sse({"type": "progress", "pct": 10, "msg": "새로운 아키텍처를 설계하고 있습니다..."})
                full_text = ""
                async for chunk in client.stream_chat(
                    MODERNIZE_SYSTEM_PROMPT + "\nIMPORTANT: Output ONLY raw JSON, no markdown fences.",
                    user_msg,
                ):
                    full_text += chunk
                    yield _sse({"type": "chunk", "text": chunk})

                yield _sse({"type": "progress", "pct": 60, "msg": "시스템 모델을 파싱하고 있습니다..."})

                # 파싱 (normalize_connections는 _dict_to_model 내부에서 자동 처리)
                clean = _clean_json(full_text)
                modern_dict = json.loads(clean)
                modern_model = SystemParser()._dict_to_model(modern_dict)

                # 다이어그램 생성
                modern_mmd = MermaidRenderer().render(modern_model)
                modern_drawio = DrawioRenderer().render(modern_model)

                # ② 마이그레이션 플랜 생성 — 분석 결과 + 압축 페이로드 포함
                yield _sse({"type": "progress", "pct": 70, "msg": "마이그레이션 플랜을 작성하고 있습니다..."})
                plan_user_msg = (
                    f"요구사항: {req.requirements}\n\n"
                    f"레거시:\n{_compress(s.system, _MAX_PLAN_CHARS)}\n\n"
                    f"현대화:\n{_compress(json.loads(modern_model.model_dump_json()), _MAX_PLAN_CHARS)}"
                )
                if s.analysis:
                    plan_user_msg += f"\n\n분석 결과:\n{json.dumps(s.analysis, ensure_ascii=False)}"
                plan_text = ""
                async for chunk in client.stream_chat(
                    MIGRATION_PLAN_PROMPT, plan_user_msg
                ):
                    plan_text += chunk

                # 세션 & 파일 저장
                s.modern = json.loads(modern_model.model_dump_json())
                s.modern_mmd = modern_mmd
                s.modern_drawio = modern_drawio
                s.migration_plan = plan_text

                modern_dir = output_dir / "modern"
                modern_dir.mkdir(exist_ok=True)
                (modern_dir / "system.json").write_text(
                    modern_model.model_dump_json(indent=2), encoding="utf-8"
                )
                (modern_dir / "diagram.mmd").write_text(modern_mmd, encoding="utf-8")
                (modern_dir / "diagram.drawio").write_text(modern_drawio, encoding="utf-8")
                (modern_dir / "migration_plan.md").write_text(plan_text, encoding="utf-8")

                yield _sse({
                    "type": "done",
                    "modern": s.modern,
                    "modern_mmd": modern_mmd,
                    "modern_drawio": modern_drawio,
                    "migration_plan": plan_text,
                })

            except Exception as e:
                yield _sse({"type": "error", "msg": str(e)})

        return await _stream_response(generator())

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
