"""draw.io XML 역방향 파서 테스트."""

import pytest

from archpilot.core.models import (
    Component,
    ComponentType,
    Connection,
    HostType,
    SystemModel,
)
from archpilot.renderers.drawio import DrawioRenderer
from archpilot.renderers.drawio_parser import parse_drawio_xml, _style_to_type, _label_to_host


# ── 라운드트립: DrawioRenderer → parse_drawio_xml ─────────────────────────────

class TestRoundTrip:
    """DrawioRenderer 출력을 파싱해 원본 SystemModel이 복원되는지 검증."""

    def test_components_roundtrip(self, sample_model):
        xml = DrawioRenderer().render(sample_model)
        restored = parse_drawio_xml(xml, system_name=sample_model.name)

        orig_ids  = {c.id for c in sample_model.components}
        rest_ids  = {c.id for c in restored.components}
        assert orig_ids == rest_ids, f"component ID 불일치: {orig_ids} vs {rest_ids}"

    def test_component_labels_roundtrip(self, sample_model):
        xml = DrawioRenderer().render(sample_model)
        restored = parse_drawio_xml(xml)
        label_map = {c.id: c.label for c in restored.components}

        for orig in sample_model.components:
            assert label_map[orig.id] == orig.label

    def test_tech_roundtrip(self, sample_model):
        xml = DrawioRenderer().render(sample_model)
        restored = parse_drawio_xml(xml)
        tech_map = {c.id: c.tech for c in restored.components}

        for orig in sample_model.components:
            assert tech_map[orig.id] == orig.tech, (
                f"{orig.id}: {tech_map[orig.id]} != {orig.tech}"
            )

    def test_host_roundtrip(self, sample_model):
        xml = DrawioRenderer().render(sample_model)
        restored = parse_drawio_xml(xml)
        host_map = {c.id: c.host for c in restored.components}

        for orig in sample_model.components:
            assert host_map[orig.id] == orig.host, (
                f"{orig.id}: {host_map[orig.id]} != {orig.host}"
            )

    def test_type_roundtrip(self, sample_model):
        xml = DrawioRenderer().render(sample_model)
        restored = parse_drawio_xml(xml)
        type_map = {c.id: c.type for c in restored.components}

        for orig in sample_model.components:
            assert type_map[orig.id] == orig.type, (
                f"{orig.id}: {type_map[orig.id]} != {orig.type}"
            )

    def test_connections_roundtrip(self, sample_model):
        xml = DrawioRenderer().render(sample_model)
        restored = parse_drawio_xml(xml)

        orig_edges = {(c.from_id, c.to_id) for c in sample_model.connections}
        rest_edges = {(c.from_id, c.to_id) for c in restored.connections}
        assert orig_edges == rest_edges

    def test_connection_protocol_roundtrip(self, sample_model):
        xml = DrawioRenderer().render(sample_model)
        restored = parse_drawio_xml(xml)
        proto_map = {(c.from_id, c.to_id): c.protocol for c in restored.connections}

        for orig in sample_model.connections:
            key = (orig.from_id, orig.to_id)
            assert proto_map[key] == orig.protocol, (
                f"{key}: {proto_map[key]} != {orig.protocol}"
            )

    def test_name_preserved(self, sample_model):
        xml = DrawioRenderer().render(sample_model)
        restored = parse_drawio_xml(xml, system_name=sample_model.name)
        assert restored.name == sample_model.name

    def test_multi_host_roundtrip(self):
        """복수 HostType 그룹이 모두 올바르게 복원되는지 확인."""
        model = SystemModel(
            name="Multi-host",
            components=[
                Component(id="web",  type=ComponentType.SERVER,   label="Web",   host=HostType.ON_PREMISE),
                Component(id="db",   type=ComponentType.DATABASE,  label="DB",    host=HostType.AWS),
                Component(id="cdn",  type=ComponentType.CDN,       label="CDN",   host=HostType.GCP),
                Component(id="bus",  type=ComponentType.QUEUE,     label="Queue", host=HostType.AZURE),
            ],
            connections=[
                Connection(from_id="web", to_id="db",  protocol="JDBC"),
                Connection(from_id="web", to_id="cdn", protocol="HTTP"),
            ],
        )
        xml = DrawioRenderer().render(model)
        restored = parse_drawio_xml(xml)

        host_map = {c.id: c.host for c in restored.components}
        assert host_map["web"]  == HostType.ON_PREMISE
        assert host_map["db"]   == HostType.AWS
        assert host_map["cdn"]  == HostType.GCP
        assert host_map["bus"]  == HostType.AZURE


# ── 모든 ComponentType 라운드트립 ────────────────────────────────────────────

class TestAllComponentTypes:
    # UNKNOWN 은 DrawioRenderer에서 SERVER와 동일 스타일(무색)을 사용하므로
    # 역변환 시 SERVER로 복원되는 것이 정상 동작.
    _ROUNDTRIP_SKIP = {ComponentType.UNKNOWN}

    @pytest.mark.parametrize(
        "comp_type",
        [ct for ct in ComponentType if ct not in {ComponentType.UNKNOWN}],
    )
    def test_type_roundtrip_all(self, comp_type):
        model = SystemModel(
            name="Type Test",
            components=[
                Component(id="c1", type=comp_type, label="Test", host=HostType.ON_PREMISE)
            ],
        )
        xml = DrawioRenderer().render(model)
        restored = parse_drawio_xml(xml)
        assert restored.components[0].type == comp_type, (
            f"ComponentType.{comp_type.value} 라운드트립 실패"
        )


# ── 유효성 검사 ───────────────────────────────────────────────────────────────

class TestValidation:
    def test_empty_xml_raises(self):
        with pytest.raises(ValueError, match="파싱 실패"):
            parse_drawio_xml("not xml")

    def test_no_components_raises(self):
        empty = '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel>'
        with pytest.raises(ValueError, match="컴포넌트를 찾을 수 없습니다"):
            parse_drawio_xml(empty)

    def test_dangling_edge_ignored(self):
        """source/target이 없는 edge는 무시되고 파싱이 완료되어야 한다."""
        xml = DrawioRenderer().render(SystemModel(
            name="X",
            components=[
                Component(id="a", type=ComponentType.SERVER, label="A", host=HostType.ON_PREMISE),
            ],
        ))
        # 유효하지 않은 edge를 XML에 직접 주입
        xml = xml.replace(
            "</root>",
            '<mxCell id="bad_edge" edge="1" source="a" target="nonexistent" parent="1">'
            '<mxGeometry relative="1" as="geometry"/></mxCell></root>',
        )
        restored = parse_drawio_xml(xml)
        assert len(restored.connections) == 0  # 무효 edge 제거됨

    def test_duplicate_cell_ids_handled(self):
        """동일 id의 mxCell이 중복 존재해도 유니크한 component id 생성."""
        # 중복 ID가 있는 최소 XML 수동 작성
        xml = """<mxGraphModel><root>
          <mxCell id="0"/>
          <mxCell id="1" parent="0"/>
          <mxCell id="group_on_premise" value="On-Premise" style="swimlane;" vertex="1" parent="1">
            <mxGeometry as="geometry"/>
          </mxCell>
          <mxCell id="dup" value="Node A" style="rounded=1;" vertex="1" parent="group_on_premise">
            <mxGeometry as="geometry"/>
          </mxCell>
          <mxCell id="dup" value="Node B" style="rounded=1;" vertex="1" parent="group_on_premise">
            <mxGeometry as="geometry"/>
          </mxCell>
        </root></mxGraphModel>"""
        restored = parse_drawio_xml(xml)
        ids = [c.id for c in restored.components]
        assert len(ids) == len(set(ids)), "중복 component ID 발생"
        assert len(restored.components) == 2


# ── 자유형 diagrams.net XML ───────────────────────────────────────────────────

class TestFreeFormXml:
    def test_html_labels_parsed(self):
        """diagrams.net이 생성하는 HTML 레이블 파싱."""
        xml = """<mxGraphModel><root>
          <mxCell id="0"/>
          <mxCell id="1" parent="0"/>
          <mxCell id="group_aws" value="AWS Cloud" style="swimlane;" vertex="1" parent="1">
            <mxGeometry as="geometry"/>
          </mxCell>
          <mxCell id="svc1" value="&lt;b&gt;API Server&lt;/b&gt;&lt;br&gt;Node.js&lt;br&gt;Express"
                  style="rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="group_aws">
            <mxGeometry as="geometry"/>
          </mxCell>
        </root></mxGraphModel>"""
        restored = parse_drawio_xml(xml)
        assert len(restored.components) == 1
        c = restored.components[0]
        assert c.label == "API Server"
        assert "Node.js" in c.tech
        assert "Express" in c.tech
        assert c.host == HostType.AWS

    def test_unknown_swimlane_label_defaults_to_on_premise(self):
        xml = """<mxGraphModel><root>
          <mxCell id="0"/>
          <mxCell id="1" parent="0"/>
          <mxCell id="custom_group" value="My Custom DC" style="swimlane;" vertex="1" parent="1">
            <mxGeometry as="geometry"/>
          </mxCell>
          <mxCell id="node1" value="Server" style="rounded=1;" vertex="1" parent="custom_group">
            <mxGeometry as="geometry"/>
          </mxCell>
        </root></mxGraphModel>"""
        restored = parse_drawio_xml(xml)
        assert restored.components[0].host == HostType.ON_PREMISE

    def test_no_swimlane_defaults_to_on_premise(self):
        """swimlane이 없는 플랫 다이어그램도 파싱 가능."""
        xml = """<mxGraphModel><root>
          <mxCell id="0"/>
          <mxCell id="1" parent="0"/>
          <mxCell id="nodeA" value="Server A" style="rounded=1;" vertex="1" parent="1">
            <mxGeometry as="geometry"/>
          </mxCell>
          <mxCell id="nodeB" value="DB" style="shape=mxgraph.cisco.storage.disk_storage;" vertex="1" parent="1">
            <mxGeometry as="geometry"/>
          </mxCell>
          <mxCell id="e1" value="JDBC" edge="1" source="nodeA" target="nodeB" parent="1">
            <mxGeometry relative="1" as="geometry"/>
          </mxCell>
        </root></mxGraphModel>"""
        restored = parse_drawio_xml(xml)
        assert len(restored.components) == 2
        assert len(restored.connections) == 1
        ids = {c.id for c in restored.components}
        assert "nodeA" in ids
        assert "nodeB" in ids


# ── 헬퍼 함수 단위 테스트 ─────────────────────────────────────────────────────

class TestHelpers:
    def test_style_to_type_database(self):
        assert _style_to_type("shape=mxgraph.cisco.storage.disk_storage;") == ComponentType.DATABASE

    def test_style_to_type_cylinder_is_database(self):
        """실린더 심볼은 국제 표준 DB 표기이므로 DATABASE로 인식해야 한다."""
        assert _style_to_type("shape=cylinder;") == ComponentType.DATABASE
        assert _style_to_type("shape=cylinder3;whiteSpace=wrap;") == ComponentType.DATABASE

    def test_style_to_type_flowchart_database(self):
        """Flowchart DB 심볼도 DATABASE로 인식해야 한다."""
        assert _style_to_type("shape=mxgraph.flowchart.database;") == ComponentType.DATABASE

    def test_style_to_type_aws_aurora_rds(self):
        assert _style_to_type("shape=mxgraph.aws4.aurora;") == ComponentType.DATABASE
        assert _style_to_type("shape=mxgraph.aws4.rds;") == ComponentType.DATABASE

    def test_style_to_type_aws_s3_storage(self):
        assert _style_to_type("shape=mxgraph.aws4.s3;") == ComponentType.STORAGE
        assert _style_to_type("shape=mxgraph.aws4.glacier;") == ComponentType.STORAGE

    def test_style_to_type_aws_sqs_queue(self):
        assert _style_to_type("shape=mxgraph.aws4.sqs;") == ComponentType.QUEUE
        assert _style_to_type("shape=mxgraph.aws4.mq;") == ComponentType.QUEUE

    def test_style_to_type_aws_elasticache(self):
        assert _style_to_type("shape=mxgraph.aws4.elasticache;") == ComponentType.CACHE
        assert _style_to_type("shape=mxgraph.aws4.redis;") == ComponentType.CACHE

    def test_style_to_type_aws_cloudfront(self):
        assert _style_to_type("shape=mxgraph.aws4.cloudfront;") == ComponentType.CDN

    def test_style_to_type_aws_api_gateway(self):
        assert _style_to_type("shape=mxgraph.aws4.api_gateway;") == ComponentType.GATEWAY

    def test_style_to_type_aws_elb_alb(self):
        assert _style_to_type("shape=mxgraph.aws4.elb;") == ComponentType.LOADBALANCER
        assert _style_to_type("shape=mxgraph.aws4.alb;") == ComponentType.LOADBALANCER

    def test_style_to_type_plain_ellipse_defaults_server(self):
        """색상 정보 없는 일반 타원은 CACHE가 아닌 SERVER로 복원되어야 한다."""
        assert _style_to_type("ellipse;whiteSpace=wrap;") == ComponentType.SERVER

    def test_style_to_type_cache(self):
        assert _style_to_type("ellipse;fillColor=#fff2cc;strokeColor=#d6b656;") == ComponentType.CACHE

    def test_style_to_type_cdn(self):
        assert _style_to_type("ellipse;fillColor=#d5e8d4;strokeColor=#82b366;") == ComponentType.CDN

    def test_style_to_type_loadbalancer(self):
        assert _style_to_type("rhombus;whiteSpace=wrap;") == ComponentType.LOADBALANCER

    def test_style_to_type_gateway(self):
        assert _style_to_type("rounded=1;arcSize=50;fillColor=#e1d5e7;strokeColor=#9673a6;") == ComponentType.GATEWAY

    def test_style_to_type_unknown_defaults_server(self):
        assert _style_to_type("someUnknownStyle=1;") == ComponentType.SERVER

    def test_label_to_host_archpilot_ids(self):
        assert _label_to_host("", "group_aws")   == HostType.AWS
        assert _label_to_host("", "group_gcp")   == HostType.GCP
        assert _label_to_host("", "group_azure") == HostType.AZURE

    def test_label_to_host_labels(self):
        assert _label_to_host("AWS Cloud")  == HostType.AWS
        assert _label_to_host("GCP Cloud")  == HostType.GCP
        assert _label_to_host("On-Premise") == HostType.ON_PREMISE
        assert _label_to_host("Hybrid")     == HostType.HYBRID

    def test_label_to_host_unknown_defaults_on_premise(self):
        assert _label_to_host("Unknown DC") == HostType.ON_PREMISE
