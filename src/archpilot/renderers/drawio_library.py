"""ArchPilot 컴포넌트 라이브러리 파일 생성.

draw.io Desktop의 File > Open Library에서 불러오거나
config.json에 등록해 자동 로드할 수 있는 .drawio.xml 파일을 생성한다.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from archpilot.core.models import ComponentType
from archpilot.renderers.drawio import STYLE_MAP

# ArchPilot 컴포넌트 정의 (이름 · 치수 · 스타일)
ARCHPILOT_SHAPES: list[dict] = [
    {"name": "Server",        "type": ComponentType.SERVER,       "w": 140, "h": 60},
    {"name": "Database",      "type": ComponentType.DATABASE,     "w": 80,  "h": 80},
    {"name": "Cache",         "type": ComponentType.CACHE,        "w": 100, "h": 60},
    {"name": "Queue",         "type": ComponentType.QUEUE,        "w": 120, "h": 60},
    {"name": "Storage",       "type": ComponentType.STORAGE,      "w": 60,  "h": 80},
    {"name": "CDN",           "type": ComponentType.CDN,          "w": 100, "h": 60},
    {"name": "Load Balancer", "type": ComponentType.LOADBALANCER, "w": 80,  "h": 80},
    {"name": "Gateway",       "type": ComponentType.GATEWAY,      "w": 140, "h": 60},
    {"name": "Service",       "type": ComponentType.SERVICE,      "w": 140, "h": 60},
    {"name": "Client",        "type": ComponentType.CLIENT,       "w": 60,  "h": 80},
]


def _cell_xml(name: str, style: str, w: int, h: int) -> str:
    # extractGraphModel()이 nodeName == 'mxGraphModel'인 노드만 수용하므로
    # <mxGraphModel> 래퍼가 반드시 필요하다.
    return (
        "<mxGraphModel>"
        "<root>"
        '<mxCell id="0"/>'
        '<mxCell id="1" parent="0"/>'
        f'<mxCell value="{name}" style="{style}" vertex="1" parent="1" id="2">'
        f'<mxGeometry width="{w}" height="{h}" as="geometry"/>'
        f"</mxCell>"
        "</root>"
        "</mxGraphModel>"
    )


def generate_mxlibrary_xml() -> str:
    """draw.io mxlibrary 형식의 XML 문자열을 반환한다."""
    entries = [
        {
            "xml":   _cell_xml(s["name"], STYLE_MAP[s["type"]], s["w"], s["h"]),
            "w":     s["w"],
            "h":     s["h"],
            "title": s["name"],
        }
        for s in ARCHPILOT_SHAPES
    ]
    # JSON을 XML text content로 넣을 때 <, >, & 를 이스케이프해야 한다.
    # 그렇지 않으면 XML 파서가 <mxCell...> 을 자식 엘리먼트로 잘못 해석한다.
    escaped = html.escape(json.dumps(entries), quote=False)
    return f'<mxlibrary title="ArchPilot">{escaped}</mxlibrary>'


def write_library_file(dest: Path) -> None:
    """ArchPilot 라이브러리를 dest 경로에 저장한다."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(generate_mxlibrary_xml(), encoding="utf-8")


def config_library_entry(library_path: Path) -> dict:
    """draw.io config.json의 libraries 항목에 추가할 dict를 반환한다."""
    return {
        "title": "ArchPilot",
        "url":   library_path.as_posix(),
    }
