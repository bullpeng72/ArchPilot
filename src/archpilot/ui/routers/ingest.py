"""주입(Ingest) 관련 API 라우터."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from archpilot.core.models import (
    Criticality,
    DataClassification,
    LifecycleStatus,
)
from archpilot.core.parser import ParseError, SystemParser
from archpilot.llm.utils import MAX_CHAT_TOKENS
from archpilot.renderers.drawio import DrawioRenderer
from archpilot.renderers.mermaid import MermaidRenderer
from archpilot.ui import session as sess
from archpilot.ui.helpers import _sse, _stream_response
from archpilot.ui.schemas import ChatIngestRequest, DrawioIngestRequest, IngestRequest

_log = logging.getLogger("archpilot.server")

router = APIRouter(prefix="/api")


def _safe_enum(val: str | None, enum_cls: type, default):  # type: ignore[type-arg]
    """val을 enum_cls로 변환하고, 실패하면 default를 반환한다."""
    if val is None:
        return default
    try:
        return enum_cls(val)
    except ValueError:
        return default


def _get_output_dir(request: Request) -> Path:
    return request.app.state.output_dir


# ── POST /api/ingest ──────────────────────────────────────────────────────────

@router.post("/ingest")
async def ingest(req: IngestRequest, request: Request) -> dict:
    s = sess.get()
    if s.is_busy:
        raise HTTPException(
            status_code=409,
            detail=f"'{s._busy_operation}' 작업이 진행 중입니다. 완료 후 다시 시도하세요.",
        )
    output_dir = _get_output_dir(request)
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
            # 동기 LLM 호출 — 이벤트 루프 블로킹 방지를 위해 스레드 풀 사용
            model = await asyncio.to_thread(parser.from_text, content)
        elif mode == "yaml":
            model = parser._from_yaml(content, Path("<web>"))
        else:  # json
            model = parser._from_json(content, Path("<web>"))
    except ParseError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    legacy_mmd = MermaidRenderer().render(model)
    legacy_drawio = DrawioRenderer().render(model)

    s.system = json.loads(model.model_dump_json())
    s.legacy_mmd = legacy_mmd
    s.legacy_drawio = legacy_drawio
    s.reset_modernization()

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


# ── POST /api/ingest/file ────────────────────────────────────────────────────

@router.post("/ingest/file")
async def ingest_file(request: Request, file: UploadFile = File(...)) -> dict:  # noqa: B008
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
    return await ingest(req, request)


# ── POST /api/ingest/drawio ──────────────────────────────────────────────────

@router.post("/ingest/drawio")
async def ingest_drawio(req: DrawioIngestRequest, request: Request) -> dict:
    output_dir = _get_output_dir(request)

    from archpilot.renderers.drawio_parser import parse_drawio_xml

    s = sess.get()
    if s.is_busy:
        raise HTTPException(
            status_code=409,
            detail=f"'{s._busy_operation}' 작업이 진행 중입니다. 완료 후 다시 시도하세요.",
        )

    try:
        model = await asyncio.to_thread(parse_drawio_xml, req.xml, req.system_name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    # draw.io 파서는 tech_ontology 보강을 거치지 않으므로 여기서 적용
    from archpilot.core.models import Component as _Component
    from archpilot.core.tech_ontology import enrich_component
    enriched_comps = [
        _Component.model_validate(enrich_component(c.model_dump(mode="json")))
        for c in model.components
    ]
    model = model.model_copy(update={"components": enriched_comps})

    # ── 기존 세션의 semantic 메타데이터 보존 ────────────────────────────────
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
                patch["metadata"] = {**prev.get("metadata", {}), **comp.metadata}

                if (comp.criticality == Criticality.MEDIUM
                        and prev.get("criticality") not in (None, "medium")):
                    restored = _safe_enum(prev.get("criticality"), Criticality, None)
                    if restored is not None:
                        patch["criticality"] = restored

                if (comp.lifecycle_status == LifecycleStatus.ACTIVE
                        and prev.get("lifecycle_status") not in (None, "active")):
                    restored = _safe_enum(prev.get("lifecycle_status"), LifecycleStatus, None)
                    if restored is not None:
                        patch["lifecycle_status"] = restored

                if comp.data_classification is None and prev.get("data_classification"):
                    restored = _safe_enum(prev.get("data_classification"), DataClassification, None)
                    if restored is not None:
                        patch["data_classification"] = restored

                if not comp.owner and prev.get("owner"):
                    patch["owner"] = prev["owner"]

                updated.append(comp.model_copy(update=patch))
            model = model.model_copy(update={"components": updated})
    # ────────────────────────────────────────────────────────────────────────

    legacy_mmd = MermaidRenderer().render(model)

    s.system = json.loads(model.model_dump_json())
    s.legacy_mmd = legacy_mmd
    s.legacy_drawio = req.xml          # 사용자가 편집한 원본 XML 보존
    s.reset_modernization()

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "system.json").write_text(
        model.model_dump_json(indent=2), encoding="utf-8"
    )
    legacy_dir = output_dir / "legacy"
    legacy_dir.mkdir(exist_ok=True)
    (legacy_dir / "diagram.mmd").write_text(legacy_mmd, encoding="utf-8")
    (legacy_dir / "diagram.drawio").write_text(req.xml, encoding="utf-8")

    return {
        "system": s.system,
        "legacy_mmd": legacy_mmd,
        "legacy_drawio": req.xml,
    }


# ── POST /api/chat/ingest/stream ─────────────────────────────────────────────

@router.post("/chat/ingest/stream")
async def chat_ingest_stream(req: ChatIngestRequest, request: Request) -> StreamingResponse:
    from archpilot.llm.client import get_async_client
    from archpilot.llm.prompts import CHAT_INGEST_SYSTEM_PROMPT

    output_dir = _get_output_dir(request)

    async def generator():
        try:
            client = get_async_client()
            full_text = ""

            async for chunk in client.stream_chat_messages(
                CHAT_INGEST_SYSTEM_PROMPT,
                req.messages,
                max_tokens=MAX_CHAT_TOKENS,
            ):
                full_text += chunk
                yield _sse({"type": "chunk", "text": chunk})

            clean = full_text.strip()
            system_extracted = False
            if clean.startswith("{"):
                try:
                    result = json.loads(clean)
                    if result.get("__system__"):
                        system_dict = {k: v for k, v in result.items() if k != "__system__"}
                        from archpilot.core.parser import SystemParser as _SP
                        model = _SP()._dict_to_model(system_dict)
                        legacy_mmd = MermaidRenderer().render(model)
                        legacy_drawio = DrawioRenderer().render(model)

                        s = sess.get()
                        s.system = json.loads(model.model_dump_json())
                        s.legacy_mmd = legacy_mmd
                        s.legacy_drawio = legacy_drawio
                        s.reset_modernization()

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
                except (json.JSONDecodeError, ValueError) as e:
                    yield _sse({"type": "warning", "msg": f"JSON 파싱 실패: {e}"})

            if not system_extracted:
                yield _sse({"type": "reply", "text": full_text})

        except Exception as e:
            _log.exception("[chat/ingest] 오류: %s", e)
            yield _sse({"type": "error", "msg": str(e)})

    return await _stream_response(generator())
