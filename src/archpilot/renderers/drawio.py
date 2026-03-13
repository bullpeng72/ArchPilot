"""draw.io (mxGraph) XML 렌더러."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import ClassVar

from archpilot.core.models import ComponentType, SystemModel
from archpilot.renderers.base import BaseRenderer

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
    ComponentType.UNKNOWN:      "rounded=1;whiteSpace=wrap;",
}

CELL_W = 140
CELL_H = 60
COLS = 4
COL_GAP = 180
ROW_GAP = 100
MARGIN = 40


class DrawioRenderer(BaseRenderer):
    name: ClassVar[str] = "drawio"
    output_ext: ClassVar[str] = ".drawio"

    def render(self, model: SystemModel) -> str:
        root_el = ET.Element("mxGraphModel")
        graph_root = ET.SubElement(root_el, "root")
        ET.SubElement(graph_root, "mxCell", id="0")
        ET.SubElement(graph_root, "mxCell", id="1", parent="0")

        groups = model.components_by_host()
        all_components = model.components
        positions: dict[str, tuple[int, int]] = {}

        # 호스트 그룹별 클러스터 박스 + 내부 컴포넌트 배치
        group_y = MARGIN
        for host, components in groups.items():
            n = len(components)
            rows = (n + COLS - 1) // COLS
            group_w = min(n, COLS) * COL_GAP + MARGIN
            group_h = rows * ROW_GAP + MARGIN * 2

            host_labels = {
                "on-premise": "On-Premise", "aws": "AWS Cloud",
                "gcp": "GCP Cloud", "azure": "Azure Cloud", "hybrid": "Hybrid",
            }
            group_label = host_labels.get(host, host)
            group_id = f"group_{host.replace('-', '_')}"

            group_cell = ET.SubElement(graph_root, "mxCell",
                id=group_id, value=group_label,
                style="swimlane;startSize=20;fillColor=#f5f5f5;strokeColor=#666666;",
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
            edge = ET.SubElement(graph_root, "mxCell",
                id=f"edge_{i}",
                value=conn.label or conn.protocol,
                style="edgeStyle=orthogonalEdgeStyle;rounded=0;",
                edge="1", source=conn.from_id, target=conn.to_id, parent="1")
            ET.SubElement(edge, "mxGeometry", relative="1", attrib={"as": "geometry"})

        return ET.tostring(root_el, encoding="unicode", xml_declaration=False)
