"""draw.io (mxGraph) XML 렌더러."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import ClassVar

from archpilot.core.models import ComponentType, SystemModel
from archpilot.renderers.base import BaseRenderer

# 호스트 타입별 swimlane 스타일 — 클라우드 공급자를 색상으로 구분
HOST_SWIMLANE_STYLES: dict[str, str] = {
    "on-premise": (
        "swimlane;startSize=28;fillColor=#E6E6E6;strokeColor=#666666;"
        "fontStyle=1;fontSize=11;fontColor=#333333;"
    ),
    "aws": (
        "swimlane;startSize=28;fillColor=#FFE6CC;strokeColor=#d79b00;"
        "fontStyle=1;fontSize=11;fontColor=#7A4000;"
    ),
    "gcp": (
        "swimlane;startSize=28;fillColor=#E8F0FE;strokeColor=#4285F4;"
        "fontStyle=1;fontSize=11;fontColor=#1A3C8C;"
    ),
    "azure": (
        "swimlane;startSize=28;fillColor=#CCE5F5;strokeColor=#0078D4;"
        "fontStyle=1;fontSize=11;fontColor=#004578;"
    ),
    "hybrid": (
        "swimlane;startSize=28;fillColor=#d5e8d4;strokeColor=#82b366;"
        "fontStyle=1;fontSize=11;fontColor=#1E4D1E;"
    ),
}
# 알 수 없는 호스트 타입 폴백 스타일
_DEFAULT_SWIMLANE_STYLE = (
    "swimlane;startSize=28;fillColor=#f5f5f5;strokeColor=#666666;"
    "fontStyle=1;fontSize=11;"
)

STYLE_MAP: dict[ComponentType, str] = {
    ComponentType.SERVER:       "rounded=1;whiteSpace=wrap;fillColor=#dae8fc;strokeColor=#6c8ebf;",
    ComponentType.DATABASE:     "shape=mxgraph.flowchart.database;whiteSpace=wrap;fillColor=#f5f5f5;strokeColor=#666666;",
    ComponentType.CACHE:        "ellipse;whiteSpace=wrap;fillColor=#fff2cc;strokeColor=#d6b656;",
    ComponentType.QUEUE:        "shape=mxgraph.flowchart.delay;whiteSpace=wrap;fillColor=#ffe6cc;strokeColor=#d79b00;",
    ComponentType.STORAGE:      "shape=mxgraph.flowchart.stored_data;whiteSpace=wrap;fillColor=#f5f5f5;strokeColor=#666666;",
    ComponentType.CDN:          "ellipse;whiteSpace=wrap;fillColor=#d5e8d4;strokeColor=#82b366;",
    ComponentType.LOADBALANCER: "rhombus;whiteSpace=wrap;fillColor=#f8cecc;strokeColor=#b85450;",
    ComponentType.GATEWAY:      "rounded=1;arcSize=50;whiteSpace=wrap;fillColor=#e1d5e7;strokeColor=#9673a6;",
    ComponentType.SERVICE:      "rounded=1;whiteSpace=wrap;fillColor=#d5e8d4;strokeColor=#82b366;",
    ComponentType.CLIENT:       "shape=mxgraph.flowchart.terminator;whiteSpace=wrap;fillColor=#f5f5f5;strokeColor=#666666;",
    # 엔터프라이즈 타입 — 색상으로 성격 구분
    ComponentType.MAINFRAME:    "rounded=0;whiteSpace=wrap;fillColor=#ccccff;strokeColor=#3333cc;fontStyle=1;",
    ComponentType.ESB:          "rounded=1;arcSize=30;whiteSpace=wrap;fillColor=#f0d0ff;strokeColor=#9933cc;",
    ComponentType.SECURITY:     "shape=mxgraph.flowchart.decision;whiteSpace=wrap;fillColor=#ffe6e6;strokeColor=#cc0000;",
    ComponentType.MONITORING:   "rounded=1;whiteSpace=wrap;fillColor=#fffacd;strokeColor=#d4ac0d;",
    ComponentType.UNKNOWN:      "rounded=1;whiteSpace=wrap;",
}

# 컴포넌트 셀 크기 (픽셀)
CELL_W = 140   # 셀 너비
CELL_H = 60    # 셀 높이

# 그리드 레이아웃
COLS = 4       # 한 행에 배치할 최대 컴포넌트 수
COL_GAP = 180  # 열 간격 (CELL_W 140 + 여백 40)
ROW_GAP = 100  # 행 간격 (CELL_H 60 + 여백 40)
MARGIN = 40    # 그룹 박스 내부 패딩


class DrawioRenderer(BaseRenderer):
    name: ClassVar[str] = "drawio"
    output_ext: ClassVar[str] = ".drawio"

    def render(self, model: SystemModel) -> str:
        root_el = ET.Element("mxGraphModel")
        graph_root = ET.SubElement(root_el, "root")
        ET.SubElement(graph_root, "mxCell", id="0")
        ET.SubElement(graph_root, "mxCell", id="1", parent="0")

        groups = model.components_by_host()
        positions: dict[str, tuple[int, int]] = {}

        # 호스트 그룹별 클러스터 박스 + 내부 컴포넌트 배치
        group_y = MARGIN
        for host, components in groups.items():
            n = len(components)
            rows = (n + COLS - 1) // COLS
            group_w = min(n, COLS) * COL_GAP + MARGIN
            group_h = rows * ROW_GAP + MARGIN * 2

            _HOST_DISPLAY = {
                "on-premise": "On-Premise", "aws": "AWS Cloud",
                "gcp": "GCP Cloud", "azure": "Azure Cloud", "hybrid": "Hybrid",
            }
            group_label = _HOST_DISPLAY.get(host, host)
            group_id = f"group_{host.replace('-', '_')}"

            swimlane_style = HOST_SWIMLANE_STYLES.get(host, _DEFAULT_SWIMLANE_STYLE)
            group_cell = ET.SubElement(graph_root, "mxCell",
                id=group_id, value=group_label,
                style=swimlane_style,
                vertex="1", parent="1")
            ET.SubElement(group_cell, "mxGeometry",
                x=str(MARGIN), y=str(group_y),
                width=str(group_w), height=str(group_h),
                attrib={"as": "geometry"})

            for i, c in enumerate(components):
                col = i % COLS
                row = i // COLS
                x = col * COL_GAP + MARGIN
                y = row * ROW_GAP + MARGIN * 2
                positions[c.id] = (MARGIN + col * COL_GAP, group_y + row * ROW_GAP + MARGIN * 2)

                tech_str = "\n".join(c.tech)
                cell_label = f"{c.label}\n{tech_str}".strip()
                style = STYLE_MAP.get(c.type, "rounded=1;whiteSpace=wrap;")

                cell = ET.SubElement(graph_root, "mxCell",
                    id=c.id, value=cell_label, style=style + "whiteSpace=wrap;",
                    vertex="1", parent=group_id)
                ET.SubElement(cell, "mxGeometry",
                    x=str(x), y=str(y),
                    width=str(CELL_W), height=str(CELL_H),
                    attrib={"as": "geometry"})

            group_y += group_h + MARGIN

        # 연결선
        for i, conn in enumerate(model.connections):
            # 엣지 레이블: label > protocol, data_format은 괄호로 병기
            edge_label = conn.label or (conn.protocol if conn.protocol != "HTTP" else "")
            if conn.data_format:
                edge_label = f"{edge_label} [{conn.data_format}]".strip()
            edge = ET.SubElement(graph_root, "mxCell",
                id=f"edge_{i}",
                value=edge_label,
                style="edgeStyle=orthogonalEdgeStyle;rounded=0;",
                edge="1", source=conn.from_id, target=conn.to_id, parent="1")
            ET.SubElement(edge, "mxGeometry", relative="1", attrib={"as": "geometry"})

        return ET.tostring(root_el, encoding="unicode", xml_declaration=False)
