"""Mermaid DSL 렌더러."""

from __future__ import annotations

import re
from typing import ClassVar

from archpilot.core.models import ComponentType, SystemModel
from archpilot.renderers.base import BaseRenderer


def _safe_mmd_id(raw: str) -> str:
    """Mermaid 노드 ID에서 허용되지 않는 문자를 언더스코어로 치환."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", raw) or "node"

# ComponentType → Mermaid 노드 모양 (open, close)
# 주의: [/ /] 와 [\ \] 는 레이블에 HTML(<br>, </tag> 등)이 포함될 때
#       / 와 \ 구분자를 파서가 잘못 인식해 "Syntax error" 발생.
#       HTML 레이블과 충돌하지 않는 모양만 사용.
SHAPE_MAP: dict[ComponentType, tuple[str, str]] = {
    ComponentType.SERVER:       ("[", "]"),
    ComponentType.DATABASE:     ("[(", ")]"),
    ComponentType.CACHE:        ("((", "))"),
    ComponentType.QUEUE:        ("([", "])"),   # stadium — / \ 없음
    ComponentType.STORAGE:      ("[(", ")]"),   # cylinder — / \ 없음
    ComponentType.LOADBALANCER: ("{", "}"),
    ComponentType.GATEWAY:      ("([", "])"),
    ComponentType.SERVICE:      ("[", "]"),
    ComponentType.CDN:          ("((", "))"),
    ComponentType.CLIENT:       ("(", ")"),
    ComponentType.UNKNOWN:      ("[", "]"),
}

HOST_LABELS: dict[str, str] = {
    "on-premise": "On-Premise",
    "aws":        "AWS Cloud",
    "gcp":        "GCP Cloud",
    "azure":      "Azure Cloud",
    "hybrid":     "Hybrid",
}


class MermaidRenderer(BaseRenderer):
    name: ClassVar[str] = "mermaid"
    output_ext: ClassVar[str] = ".mmd"

    def render(self, model: SystemModel) -> str:
        lines: list[str] = ["flowchart LR", ""]

        # 원본 ID → Mermaid 안전 ID 매핑 (공백·특수문자 제거)
        id_map = {c.id: _safe_mmd_id(c.id) for c in model.components}

        groups = model.components_by_host()

        for host, components in groups.items():
            group_label = HOST_LABELS.get(host, host)
            safe_host = re.sub(r"[^a-zA-Z0-9_]", "_", host)
            lines.append(f'  subgraph {safe_host}["{group_label}"]')

            for c in components:
                open_b, close_b = SHAPE_MAP.get(c.type, ("[", "]"))
                # <br> 사용 (자기닫힘 <br/> 의 / 가 [/ /] 구분자와 충돌)
                # <small> 미사용 (Mermaid 11 securityLevel:loose 에서 비허용)
                tech_str = "<br>".join(c.tech)
                if tech_str:
                    label = f"{c.label}<br>{tech_str}"
                else:
                    label = c.label
                label = label.replace('"', "'")
                lines.append(f'    {id_map[c.id]}{open_b}"{label}"{close_b}')

            lines.append("  end")
            lines.append("")

        # 연결선
        for conn in model.connections:
            from_id = id_map.get(conn.from_id, _safe_mmd_id(conn.from_id))
            to_id   = id_map.get(conn.to_id,   _safe_mmd_id(conn.to_id))

            if conn.label:
                arrow = f'-- "{conn.label}" -->'
            elif conn.protocol and conn.protocol != "HTTP":
                arrow = f'-- "{conn.protocol}" -->'
            else:
                arrow = "-->"

            lines.append(f"  {from_id} {arrow} {to_id}")

            if conn.bidirectional:
                lines.append(f"  {to_id} --> {from_id}")

        return "\n".join(lines)
