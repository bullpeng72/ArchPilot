"""draw.io XML → SystemModel 역방향 파서.

DrawioRenderer가 생성한 XML뿐 아니라
diagrams.net에서 직접 편집한 임의 XML도 최대한 복원한다.
"""

from __future__ import annotations

import logging
import re

import defusedxml.ElementTree as ET  # XXE-safe XML parser
from defusedxml import DefusedXmlException

_log = logging.getLogger(__name__)

from archpilot.core.models import (
    Component,
    ComponentType,
    Connection,
    Criticality,
    HostType,
    LifecycleStatus,
    SystemModel,
)


# ── 스타일 → ComponentType 역매핑 ─────────────────────────────────────────────
#
# 우선순위 순으로 정의된 (키워드, ComponentType) 쌍.
# 앞에 위치할수록 먼저 매칭되며, 상호 배타적이지 않은 패턴은 순서가 중요하다.
_STYLE_PATTERNS: list[tuple[str, ComponentType]] = [
    # DATABASE — Cisco disk_storage, 실린더, flowchart 심볼, AWS Aurora/RDS
    ("disk_storage",          ComponentType.DATABASE),
    ("cylinder",              ComponentType.DATABASE),
    ("flowchart.database",    ComponentType.DATABASE),
    ("aws4.aurora",           ComponentType.DATABASE),
    ("aws4.rds",              ComponentType.DATABASE),
    # STORAGE — flowchart, Cisco 서버 심볼, AWS S3/Glacier
    ("flowchart.stored_data", ComponentType.STORAGE),
    ("cisco.servers",         ComponentType.STORAGE),
    ("aws4.s3",               ComponentType.STORAGE),
    ("aws4.glacier",          ComponentType.STORAGE),
    # CLIENT — flowchart 터미네이터, Cisco PC 심볼
    ("flowchart.terminator",  ComponentType.CLIENT),
    ("cisco.computers",       ComponentType.CLIENT),
    ("peripherals.pc",        ComponentType.CLIENT),
    # QUEUE — flowchart delay, BPMN, AWS SQS/MQ
    ("flowchart.delay",       ComponentType.QUEUE),
    ("bpmn",                  ComponentType.QUEUE),
    ("aws4.sqs",              ComponentType.QUEUE),
    ("aws4.mq",               ComponentType.QUEUE),
    # CACHE — AWS ElastiCache/Redis
    ("aws4.elasticache",      ComponentType.CACHE),
    ("aws4.redis",            ComponentType.CACHE),
    # CDN — AWS CloudFront
    ("aws4.cloudfront",       ComponentType.CDN),
    # GATEWAY — AWS API Gateway
    ("aws4.api_gateway",      ComponentType.GATEWAY),
    # LOADBALANCER — AWS ELB/ALB
    ("aws4.elb",              ComponentType.LOADBALANCER),
    ("aws4.alb",              ComponentType.LOADBALANCER),
    # SECURITY — flowchart.decision 다이아몬드 (rhombus와 상호 배타적)
    ("flowchart.decision",    ComponentType.SECURITY),
    # LOADBALANCER — rhombus (flowchart.decision 이후 체크하여 오분류 방지)
    ("rhombus",               ComponentType.LOADBALANCER),
]

# Ellipse 셀 전용 색상 코드 매핑 (drawio.py STYLE_MAP의 fillColor/strokeColor 기반)
# ⚠ drawio.py의 STYLE_MAP 색상 변경 시 여기도 동기화 필요
_ELLIPSE_COLOR_PATTERNS: list[tuple[str, ComponentType]] = [
    ("fff2cc", ComponentType.CACHE),    # Cache fillColor
    ("d6b656", ComponentType.CACHE),    # Cache strokeColor
    ("d5e8d4", ComponentType.CDN),      # CDN fillColor
    ("82b366", ComponentType.CDN),      # CDN strokeColor
]

# 사각형 계열 색상 코드 매핑 (shape 키워드 미매칭 시 최후 수단)
_COLOR_PATTERNS: list[tuple[str, ComponentType]] = [
    ("arcsize=50", ComponentType.GATEWAY),     # Gateway: 둥근 모서리 50%
    ("e1d5e7",     ComponentType.GATEWAY),     # Gateway fillColor
    ("9673a6",     ComponentType.GATEWAY),     # Gateway strokeColor
    ("arcsize=30", ComponentType.ESB),         # ESB: 둥근 모서리 30%
    ("f0d0ff",     ComponentType.ESB),         # ESB fillColor
    ("9933cc",     ComponentType.ESB),         # ESB strokeColor
    ("ccccff",     ComponentType.MAINFRAME),   # Mainframe fillColor (남보라)
    ("3333cc",     ComponentType.MAINFRAME),   # Mainframe strokeColor
    ("fffacd",     ComponentType.MONITORING),  # Monitoring fillColor (연노랑)
    ("d4ac0d",     ComponentType.MONITORING),  # Monitoring strokeColor
    ("d5e8d4",     ComponentType.SERVICE),     # Service fillColor (초록)
    ("82b366",     ComponentType.SERVICE),     # Service strokeColor
    ("dae8fc",     ComponentType.SERVER),      # Server fillColor (파랑)
    ("6c8ebf",     ComponentType.SERVER),      # Server strokeColor
]


def _style_to_type(style: str) -> ComponentType:
    """mxCell style 문자열에서 ComponentType 추론.

    매칭 우선순위:
    1. shape/symbol 키워드 (_STYLE_PATTERNS)
    2. ellipse 셀 — 색상 코드로 CACHE/CDN 구분 (_ELLIPSE_COLOR_PATTERNS)
    3. 색상 코드 — 사각형 계열 (_COLOR_PATTERNS)
    4. 기본값 SERVER (알 수 없는 스타일은 DEBUG 로그)
    """
    s = style.lower()

    # 1순위: 명시적 shape/symbol 키워드
    for keyword, ctype in _STYLE_PATTERNS:
        if keyword in s:
            return ctype

    # 2순위: ellipse — 색상으로 CACHE/CDN 구분, 나머지는 SERVER
    if "ellipse" in s:
        for color, ctype in _ELLIPSE_COLOR_PATTERNS:
            if color in s:
                return ctype
        return ComponentType.SERVER  # 색상 정보 없는 일반 타원

    # 3순위: 색상 코드 매칭 (사각형 계열)
    for color, ctype in _COLOR_PATTERNS:
        if color in s:
            return ctype

    # 매칭 없음 — 기본값 SERVER
    _log.debug("알 수 없는 draw.io 스타일, SERVER로 기본 설정: %.120s", style)
    return ComponentType.SERVER


# ── 호스트 레이블 → HostType ──────────────────────────────────────────────────

_HOST_LABEL_MAP: dict[str, HostType] = {
    "on-premise":    HostType.ON_PREMISE,
    "on premise":    HostType.ON_PREMISE,
    "onpremise":     HostType.ON_PREMISE,
    "aws":           HostType.AWS,
    "aws cloud":     HostType.AWS,
    "amazon":        HostType.AWS,
    "amazon web services": HostType.AWS,
    "gcp":           HostType.GCP,
    "gcp cloud":     HostType.GCP,
    "google cloud":  HostType.GCP,
    "azure":         HostType.AZURE,
    "azure cloud":   HostType.AZURE,
    "microsoft azure": HostType.AZURE,
    "hybrid":        HostType.HYBRID,
}

# DrawioRenderer가 생성하는 그룹 ID 패턴
_GROUP_ID_MAP: dict[str, HostType] = {
    "group_on_premise": HostType.ON_PREMISE,
    "group_aws":        HostType.AWS,
    "group_gcp":        HostType.GCP,
    "group_azure":      HostType.AZURE,
    "group_hybrid":     HostType.HYBRID,
}


def _label_to_host(label: str, cell_id: str = "") -> HostType:
    """swimlane 레이블 또는 셀 ID에서 HostType 추론."""
    host = _GROUP_ID_MAP.get(cell_id.lower())
    if host:
        return host
    return _HOST_LABEL_MAP.get(label.lower().strip(), HostType.ON_PREMISE)


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def _parse_edge_label(label: str) -> tuple[str, str]:
    """엣지 레이블 'PROTOCOL [DATA_FORMAT]' → (protocol, data_format) 분리.

    DrawioRenderer가 생성한 'CICS [Fixed-Width]' 형식과
    레이블만 있는 'REST' 형식 모두 처리한다.
    """
    m = re.match(r"^(.*?)\s*\[([^\]]+)\]\s*$", label.strip())
    if m:
        return (m.group(1).strip() or "HTTP"), m.group(2).strip()
    return (label.strip() or "HTTP"), ""


def _safe_id(raw: str) -> str:
    """mxCell id를 유효한 snake_case 식별자로 변환."""
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", raw).strip("_")
    return sanitized or "comp"


def _strip_html(text: str) -> str:
    """간단한 HTML 태그 제거 + 줄바꿈 정규화."""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = (
        text.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&nbsp;", " ")
            .replace("&#xa;", "\n")
    )
    return text


def _parse_value(value: str) -> tuple[str, list[str]]:
    """mxCell value에서 (label, tech[]) 추출.

    DrawioRenderer 형식: "label\\ntech1\\ntech2"
    diagrams.net HTML: "<b>label</b><br>tech1"
    """
    text = _strip_html(value)
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if not lines:
        return "Unknown", []
    return lines[0], lines[1:]


# ── 핵심 파서 ─────────────────────────────────────────────────────────────────

def parse_drawio_xml(xml_str: str, system_name: str = "Imported System") -> SystemModel:
    """draw.io XML 문자열 → SystemModel.

    Args:
        xml_str:     draw.io 형식의 XML 문자열
        system_name: 생성할 SystemModel 의 이름

    Returns:
        파싱된 SystemModel

    Raises:
        ValueError: XML 파싱 실패 또는 컴포넌트 없음
    """
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError as exc:
        raise ValueError(f"draw.io XML 파싱 실패: {exc}") from exc
    except DefusedXmlException as exc:
        raise ValueError(f"draw.io XML 보안 위협 차단 (XXE/DTD): {exc}") from exc

    all_cells = root.findall(".//mxCell")

    # ── 1단계: swimlane 셀 → HostType 매핑 ───────────────────────────────────
    swimlane_host: dict[str, HostType] = {}
    for cell in all_cells:
        style = cell.get("style", "")
        if "swimlane" in style and cell.get("vertex") == "1":
            cid   = cell.get("id", "")
            label = _strip_html(cell.get("value", ""))
            swimlane_host[cid] = _label_to_host(label, cid)

    # ── 2단계: vertex 셀 → Component ────────────────────────────────────────
    _SKIP = {"0", "1"}
    id_map: dict[str, str] = {}   # original cell id → 최종 component id
    comp_ids: set[str] = set()
    components: list[Component] = []

    for cell in all_cells:
        orig_id = cell.get("id", "")
        if orig_id in _SKIP:
            continue
        if cell.get("edge") == "1":
            continue
        if cell.get("vertex") != "1":
            continue
        style = cell.get("style", "")
        if "swimlane" in style:
            continue

        # ID 충돌 방지
        base_id = _safe_id(orig_id)
        final_id = base_id
        n = 2
        while final_id in comp_ids:
            final_id = f"{base_id}_{n}"
            n += 1
        comp_ids.add(final_id)
        id_map[orig_id] = final_id

        label, tech = _parse_value(cell.get("value", ""))
        parent = cell.get("parent", "")
        host   = swimlane_host.get(parent, HostType.ON_PREMISE)

        from archpilot.core.tech_ontology import enrich_component  # noqa: PLC0415
        raw = enrich_component({
            "id":    final_id,
            "type":  _style_to_type(style).value,
            "label": label or final_id,
            "tech":  tech,
            "host":  host.value,
        })
        try:
            ctype = ComponentType(raw["type"])
        except ValueError:
            ctype = ComponentType.SERVER

        # lifecycle_status — enrich_component가 설정했을 수 있음
        lifecycle_status = LifecycleStatus.ACTIVE
        if raw.get("lifecycle_status"):
            try:
                lifecycle_status = LifecycleStatus(str(raw["lifecycle_status"]).lower())
            except ValueError:
                pass

        # criticality — enrich_component가 설정했을 수 있음
        criticality = Criticality.MEDIUM
        if raw.get("criticality"):
            try:
                criticality = Criticality(str(raw["criticality"]).lower())
            except ValueError:
                pass

        components.append(Component(
            id=final_id,
            type=ctype,
            label=raw["label"],
            tech=raw["tech"],
            host=host,
            lifecycle_status=lifecycle_status,
            criticality=criticality,
            metadata=raw.get("metadata", {}),
        ))

    if not components:
        raise ValueError(
            "draw.io XML에서 컴포넌트를 찾을 수 없습니다. "
            "편집기에서 컴포넌트를 추가한 뒤 다시 시도하세요."
        )

    # ── 3단계: edge 셀 → Connection ──────────────────────────────────────────
    connections: list[Connection] = []
    for cell in all_cells:
        if cell.get("edge") != "1":
            continue
        src_orig = cell.get("source", "")
        tgt_orig = cell.get("target", "")
        src = id_map.get(src_orig)
        tgt = id_map.get(tgt_orig)
        if not src or not tgt:
            continue  # dangling edge 무시

        raw_label = _strip_html(cell.get("value", "")).strip()
        proto, data_fmt = _parse_edge_label(raw_label)
        connections.append(Connection(
            from_id=src,
            to_id=tgt,
            protocol=proto,
            data_format=data_fmt,
        ))

    return SystemModel(
        name=system_name,
        components=components,
        connections=connections,
    )
