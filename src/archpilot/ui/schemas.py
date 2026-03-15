"""UI 레이어 Request / Response Pydantic 모델."""

from __future__ import annotations

from pydantic import BaseModel


class IngestRequest(BaseModel):
    content: str
    mode: str = "auto"  # auto | yaml | json | text


class ModernizeRequest(BaseModel):
    requirements: str
    scenario: str | None = None  # full_replace | partial | additive | None(분석 결과 자동 적용)


class ChatIngestRequest(BaseModel):
    messages: list[dict]  # [{role: "user"|"assistant", content: "..."}]


class DrawioIngestRequest(BaseModel):
    xml: str
    system_name: str = "Imported System"
