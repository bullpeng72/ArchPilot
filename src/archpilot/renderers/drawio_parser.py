"""draw.io XML → SystemModel 역방향 파서.

DrawioRenderer가 생성한 XML뿐 아니라
diagrams.net에서 직접 편집한 임의 XML도 최대한 복원한다.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from archpilot.core.models import (
    Component,
    ComponentType,
    Connection,
    Criticality,
    DataClassification,
    HostType,
    LifecycleStatus,
    SystemModel,
)


# ── 스타일 → ComponentType 역매핑 ─────────────────────────────────────────────

def _style_to_type(style: str) -> ComponentType:
    """mxCell style 문자열에서 ComponentType 추론."""
    s = style.lower()

    # ── DATABASE ──────────────────────────────────────────────────────────────
    # ArchPilot 기본 스타일 (Cisco disk_storage)
    if "disk_storage" in s:
        return ComponentType.DATABASE
    # 국제 표준 실린더(Cylinder) 심볼
    if "cylinder" in s:
        return ComponentType.DATABASE
    # Flowchart database 심볼
    if "flowchart.database" in s:
        return ComponentType.DATABASE
    # AWS Aurora / RDS
    if "aws4.aurora" in s or "aws4.rds" in s:
        return ComponentType.DATABASE

    # ── STORAGE ───────────────────────────────────────────────────────────────
    if "flowchart.stored_data" in s:
        return ComponentType.STORAGE
    if "cisco.servers" in s:
        return ComponentType.STORAGE
    # AWS S3 / Glacier
    if "aws4.s3" in s or "aws4.glacier" in s:
        return ComponentType.STORAGE

    # ── CLIENT ────────────────────────────────────────────────────────────────
    if "flowchart.terminator" in s:
        return ComponentType.CLIENT
    if "cisco.computers" in s or "peripherals.pc" in s:
        return ComponentType.CLIENT

    # ── QUEUE ─────────────────────────────────────────────────────────────────
    if "flowchart.delay" in s:
        return ComponentType.QUEUE
    if "bpmn" in s:
        return ComponentType.QUEUE
    # AWS SQS / Amazon MQ
    if "aws4.sqs" in s or "aws4.mq" in s:
        return ComponentType.QUEUE

    # ── CACHE ─────────────────────────────────────────────────────────────────
    # AWS ElastiCache / Redis
    if "aws4.elasticache" in s or "aws4.redis" in s:
        return ComponentType.CACHE

    # ── CDN ───────────────────────────────────────────────────────────────────
    # AWS CloudFront
    if "aws4.cloudfront" in s:
        return ComponentType.CDN

    # ── GATEWAY ───────────────────────────────────────────────────────────────
    # AWS API Gateway
    if "aws4.api_gateway" in s:
        return ComponentType.GATEWAY

    # ── LOADBALANCER ──────────────────────────────────────────────────────────
    if "rhombus" in s:
        return ComponentType.LOADBALANCER
    # AWS ELB / ALB
    if "aws4.elb" in s or "aws4.alb" in s:
        return ComponentType.LOADBALANCER

    # ── Ellipse: ArchPilot 색상 코드로 판별, 미매칭은 SERVER(안전 기본값) ─────
    if "ellipse" in s:
        # Cache: fillColor=#fff2cc
        if "fff2cc" in s or "d6b656" in s:
            return ComponentType.CACHE
        # CDN: fillColor=#d5e8d4
        if "d5e8d4" in s or "82b366" in s:
            return ComponentType.CDN
        # 색상 정보 없는 일반 타원 → SERVER (CACHE보다 안전한 기본값)
        return ComponentType.SERVER

    # ── SECURITY: flowchart.decision 다이아몬드 (LOADBALANCER rhombus와 구분) ────
    if "flowchart.decision" in s:
        return ComponentType.SECURITY

    # ── LOADBALANCER: rhombus ────────────────────────────────────────────────
    # (위에서 flowchart.decision 먼저 처리했으므로 여기서 rhombus는 LB만 해당)
    if "rhombus" in s:
        return ComponentType.LOADBALANCER

    # ── Gateway: arcSize=50 + 보라색 ──────────────────────────────────────────
    if "arcsize=50" in s or ("e1d5e7" in s and "9673a6" in s):
        return ComponentType.GATEWAY

    # ── ESB: arcSize=30 + 연보라 (#f0d0ff / #9933cc) ─────────────────────────
    if "arcsize=30" in s or "f0d0ff" in s or "9933cc" in s:
        return ComponentType.ESB

    # ── MAINFRAME: 남보라 (#ccccff / #3333cc) + 직각(rounded=0) ──────────────
    if "ccccff" in s or "3333cc" in s:
        return ComponentType.MAINFRAME

    # ── MONITORING: 연노랑 (#fffacd / #d4ac0d) ───────────────────────────────
    if "fffacd" in s or "d4ac0d" in s:
        return ComponentType.MONITORING

    # ── Service: 초록색 사각형 ─────────────────────────────────────────────────
    if "d5e8d4" in s or "82b366" in s:
        return ComponentType.SERVICE
    # ── Server: 파란색 사각형 (ArchPilot 기본) ────────────────────────────────
    if "dae8fc" in s or "6c8ebf" in s:
        return ComponentType.SERVER
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
