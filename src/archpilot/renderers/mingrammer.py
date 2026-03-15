"""diagrams(mingrammer) 렌더러 — Graphviz 기반 PNG/SVG 생성."""

from __future__ import annotations

import os
import re
import textwrap
from pathlib import Path
from typing import ClassVar

from archpilot.core.models import Component, ComponentType, HostType, SystemModel
from archpilot.renderers.base import BaseRenderer

# (type, host, tech_keyword) → diagrams 완전 클래스 경로
# 우선순위: 더 구체적인 항목이 앞에 위치해야 함
ICON_TABLE: list[tuple[tuple[str, str, str], str]] = [
    # AWS compute — serverless/managed → service type; raw compute → server type
    (("service", "aws", "lambda"),     "diagrams.aws.compute.Lambda"),
    (("server",  "aws", "ec2"),        "diagrams.aws.compute.EC2"),
    (("service", "aws", "ecs"),        "diagrams.aws.compute.ECS"),
    (("service", "aws", "eks"),        "diagrams.aws.compute.EKS"),
    (("service", "aws", "fargate"),    "diagrams.aws.compute.Fargate"),
    # AWS database
    (("database","aws", "aurora"),     "diagrams.aws.database.Aurora"),
    (("database","aws", "rds"),        "diagrams.aws.database.RDS"),
    (("database","aws", "dynamodb"),   "diagrams.aws.database.Dynamodb"),
    (("cache",   "aws", "redis"),      "diagrams.aws.database.ElastiCache"),
    (("cache",   "aws", "elasticache"),"diagrams.aws.database.ElastiCache"),
    # AWS network
    (("cdn",     "aws", "cloudfront"), "diagrams.aws.network.CloudFront"),
    (("gateway", "aws", "apigw"),      "diagrams.aws.network.APIGateway"),
    (("gateway", "aws", "api"),        "diagrams.aws.network.APIGateway"),
    (("loadbalancer","aws", "alb"),    "diagrams.aws.network.ALB"),
    (("loadbalancer","aws", "elb"),    "diagrams.aws.network.ELB"),
    # AWS storage / integration
    (("storage", "aws", "s3"),         "diagrams.aws.storage.S3"),
    (("queue",   "aws", "sqs"),        "diagrams.aws.integration.SQS"),
    (("service", "aws", "sns"),        "diagrams.aws.integration.SNS"),
    # GCP compute
    (("service", "gcp", "function"),   "diagrams.gcp.compute.Functions"),
    (("service", "gcp", "cloud run"),  "diagrams.gcp.compute.Run"),
    (("server",  "gcp", "gce"),        "diagrams.gcp.compute.ComputeEngine"),
    (("service", "gcp", "gke"),        "diagrams.gcp.compute.KubernetesEngine"),
    # GCP database
    (("database","gcp", "spanner"),    "diagrams.gcp.database.Spanner"),
    (("database","gcp", "sql"),        "diagrams.gcp.database.SQL"),
    (("cache",   "gcp", "memorystore"),"diagrams.gcp.database.Memorystore"),
    # AWS monitoring / security
    (("monitoring",  "aws", "cloudwatch"),  "diagrams.aws.management.Cloudwatch"),
    (("monitoring",  "aws", ""),            "diagrams.aws.management.Cloudwatch"),
    (("security",    "aws", "waf"),         "diagrams.aws.security.WAF"),
    (("security",    "aws", "cognito"),     "diagrams.aws.security.Cognito"),
    (("security",    "aws", ""),            "diagrams.aws.security.Shield"),
    (("esb",         "aws", ""),            "diagrams.aws.integration.MQ"),
    # On-Premise fallback
    (("server",      "on-premise", ""), "diagrams.onprem.compute.Server"),
    (("database",    "on-premise", ""), "diagrams.onprem.database.Mysql"),
    (("cache",       "on-premise", ""), "diagrams.onprem.inmemory.Memcached"),
    (("queue",       "on-premise", ""), "diagrams.onprem.queue.Rabbitmq"),
    (("loadbalancer","on-premise", ""), "diagrams.onprem.network.Nginx"),
    (("gateway",     "on-premise", ""), "diagrams.onprem.network.Nginx"),
    (("storage",     "on-premise", ""), "diagrams.onprem.storage.CephOsd"),
    (("cdn",         "on-premise", ""), "diagrams.onprem.network.Internet"),
    # 엔터프라이즈 타입 — 기술 키워드 우선, 폴백 순
    (("monitoring",  "on-premise", "grafana"),    "diagrams.onprem.monitoring.Grafana"),
    (("monitoring",  "on-premise", "prometheus"), "diagrams.onprem.monitoring.Prometheus"),
    (("monitoring",  "on-premise", ""),           "diagrams.onprem.monitoring.Grafana"),
    (("security",    "on-premise", "vault"),      "diagrams.onprem.security.Vault"),
    (("security",    "on-premise", ""),           "diagrams.onprem.security.Vault"),
    (("esb",         "on-premise", ""),           "diagrams.onprem.network.Internet"),
    (("mainframe",   "on-premise", ""),           "diagrams.onprem.compute.Server"),
    # Generic fallback
    (("service",     "on-premise", ""), "diagrams.onprem.compute.Server"),
    (("client",      "on-premise", ""), "diagrams.onprem.client.User"),
]


def _safe_var(component_id: str) -> str:
    """컴포넌트 ID를 exec() 안전한 Python 변수명으로 변환.

    사용자 YAML/draw.io에서 유입된 ID가 생성 코드에 그대로 삽입되는
    코드 인젝션을 방지한다. 영숫자·밑줄 외 모든 문자를 '_'로 치환.
    """
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", component_id)
    if sanitized and sanitized[0].isdigit():
        sanitized = f"c_{sanitized}"
    return sanitized or "comp"


def _resolve_class(component: Component) -> str:
    tech_lower = " ".join(component.tech).lower()
    ctype = component.type.value
    host = component.host.value

    for (ttype, thost, keyword), class_path in ICON_TABLE:
        host_match = thost == host or (thost == "on-premise" and host not in ("aws", "gcp", "azure"))
        type_match = ttype == ctype
        keyword_match = keyword == "" or keyword in tech_lower

        if type_match and host_match and keyword_match:
            return class_path

    return "diagrams.onprem.compute.Server"


def _build_imports(components: list[Component]) -> str:
    classes = {_resolve_class(c) for c in components}
    by_module: dict[str, list[str]] = {}
    for cls_path in classes:
        module, cls = cls_path.rsplit(".", 1)
        by_module.setdefault(module, []).append(cls)
    return "\n".join(
        f"from {mod} import {', '.join(sorted(clss))}"
        for mod, clss in sorted(by_module.items())
    )


class MingrammerRenderer(BaseRenderer):
    name: ClassVar[str] = "diagrams"
    output_ext: ClassVar[str] = ".png"

    def render(self, model: SystemModel) -> str:
        """diagrams 파이썬 코드 문자열 반환 (참고/디버그용)."""
        return self._build_code(model, output_path="diagram")

    def save(self, model: SystemModel, output_dir: Path, filename: str = "diagram") -> Path:
        self._check_graphviz()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / filename)

        code = self._build_code(model, output_path=output_path)
        exec(compile(code, "<archpilot:mingrammer>", "exec"), {})  # noqa: S102

        result = Path(f"{output_path}.png")
        if not result.exists():
            raise RuntimeError(f"PNG 생성 실패: {result}")
        return result

    def _build_code(self, model: SystemModel, output_path: str) -> str:
        imports = _build_imports(model.components)
        groups = model.components_by_host()

        # 컴포넌트 ID → 안전한 Python 변수명 매핑 (exec 코드 인젝션 방지)
        id_to_var: dict[str, str] = {c.id: _safe_var(c.id) for c in model.components}

        node_lines: list[str] = []
        edge_lines: list[str] = []
        indent = "    "

        for host, components in groups.items():
            is_cloud = host in ("aws", "gcp", "azure")
            cluster_label = {
                "aws": "AWS Cloud", "gcp": "GCP Cloud", "azure": "Azure Cloud",
            }.get(host, host)

            if is_cloud:
                node_lines.append(f'{indent}with Cluster("{cluster_label}"):')
                inner = indent * 2
            else:
                inner = indent

            for c in components:
                cls = _resolve_class(c).rsplit(".", 1)[-1]
                safe_label = c.label.replace('"', "'").replace("\\", "")
                var = id_to_var[c.id]
                node_lines.append(f'{inner}{var} = {cls}("{safe_label}")')

        for conn in model.connections:
            proto = (conn.protocol or "").replace('"', "'").replace("\\", "")
            if proto and proto != "HTTP":
                edge = f'Edge(label="{proto}")'
            else:
                edge = "Edge()"
            src = id_to_var.get(conn.from_id, _safe_var(conn.from_id))
            tgt = id_to_var.get(conn.to_id, _safe_var(conn.to_id))
            edge_lines.append(f"{indent}{src} >> {edge} >> {tgt}")

        safe_name = model.name.replace('"', "'")
        code = textwrap.dedent(f"""\
            from diagrams import Diagram, Cluster, Edge
            {imports}

            with Diagram("{safe_name}", filename="{output_path}", show=False, direction="LR"):
            """)
        code += "\n".join(node_lines)
        if edge_lines:
            code += "\n\n"
            code += "\n".join(edge_lines)

        return code

    def _check_graphviz(self) -> None:
        import shutil

        if shutil.which("dot") is None:
            raise RuntimeError(
                "Graphviz가 설치되지 않았습니다.\n"
                "  macOS: brew install graphviz\n"
                "  Ubuntu: sudo apt install graphviz\n"
                "--format mermaid 또는 drawio 를 사용하면 Graphviz 없이 동작합니다."
            )
