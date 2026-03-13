"""기술명 → ComponentType·EOL·카테고리·벤더 자동 매핑 온톨로지.

사용 방법:
    from archpilot.core.tech_ontology import enrich_component
    enriched = enrich_component(raw_component_dict)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TechRecord:
    canonical: str           # 정규화된 기술명
    component_type: str      # ComponentType enum 값
    category: str            # 세부 분류 (rdbms, nosql, web-server, …)
    vendor: str
    eol_year: Optional[int]  # EOL 연도 (None = 현재 지원 중)


# ── 온톨로지 테이블 ──────────────────────────────────────────────────────────
TECH_ONTOLOGY: dict[str, TechRecord] = {
    # ── Web / App Servers ─────────────────────────────────────────────────
    "iis":           TechRecord("IIS",            "server",       "web-server",     "Microsoft",  None),
    "iis 6":         TechRecord("IIS 6",          "server",       "web-server",     "Microsoft",  2015),
    "iis 7":         TechRecord("IIS 7",          "server",       "web-server",     "Microsoft",  2023),
    "iis 8.5":       TechRecord("IIS 8.5",        "server",       "web-server",     "Microsoft",  2023),
    "apache":        TechRecord("Apache HTTP",    "server",       "web-server",     "Apache",     None),
    "apache 2.2":    TechRecord("Apache 2.2",     "server",       "web-server",     "Apache",     2017),
    "nginx":         TechRecord("Nginx",          "server",       "web-server",     "F5",         None),
    "tomcat":        TechRecord("Tomcat",         "server",       "app-server",     "Apache",     None),
    "tomcat 6":      TechRecord("Tomcat 6",       "server",       "app-server",     "Apache",     2016),
    "tomcat 7":      TechRecord("Tomcat 7",       "server",       "app-server",     "Apache",     2021),
    "jboss":         TechRecord("JBoss",          "server",       "app-server",     "Red Hat",    None),
    "jboss 4":       TechRecord("JBoss 4",        "server",       "app-server",     "Red Hat",    2012),
    "jboss 5":       TechRecord("JBoss 5",        "server",       "app-server",     "Red Hat",    2013),
    "wildfly":       TechRecord("WildFly",        "server",       "app-server",     "Red Hat",    None),
    "weblogic":      TechRecord("WebLogic",       "server",       "app-server",     "Oracle",     None),
    "websphere":     TechRecord("WebSphere",      "server",       "app-server",     "IBM",        None),
    "glassfish":     TechRecord("GlassFish",      "server",       "app-server",     "Eclipse",    None),
    # ── Databases: RDBMS ──────────────────────────────────────────────────
    "oracle":        TechRecord("Oracle DB",      "database",     "rdbms",          "Oracle",     None),
    "oracle 9i":     TechRecord("Oracle 9i",      "database",     "rdbms",          "Oracle",     2010),
    "oracle 10g":    TechRecord("Oracle 10g",     "database",     "rdbms",          "Oracle",     2013),
    "oracle 11g":    TechRecord("Oracle 11g",     "database",     "rdbms",          "Oracle",     2020),
    "oracle 12c":    TechRecord("Oracle 12c",     "database",     "rdbms",          "Oracle",     2022),
    "mysql":         TechRecord("MySQL",          "database",     "rdbms",          "Oracle",     None),
    "mysql 5.5":     TechRecord("MySQL 5.5",      "database",     "rdbms",          "Oracle",     2018),
    "mysql 5.7":     TechRecord("MySQL 5.7",      "database",     "rdbms",          "Oracle",     2023),
    "postgresql":    TechRecord("PostgreSQL",     "database",     "rdbms",          "Community",  None),
    "mssql":         TechRecord("SQL Server",     "database",     "rdbms",          "Microsoft",  None),
    "sql server":    TechRecord("SQL Server",     "database",     "rdbms",          "Microsoft",  None),
    "db2":           TechRecord("IBM DB2",        "database",     "rdbms",          "IBM",        None),
    "sybase":        TechRecord("Sybase ASE",     "database",     "rdbms",          "SAP",        2025),
    # ── Databases: NoSQL ──────────────────────────────────────────────────
    "mongodb":       TechRecord("MongoDB",        "database",     "nosql-doc",      "MongoDB",    None),
    "cassandra":     TechRecord("Cassandra",      "database",     "nosql-wide",     "Apache",     None),
    "dynamodb":      TechRecord("DynamoDB",       "database",     "nosql-kv",       "AWS",        None),
    "hbase":         TechRecord("HBase",          "database",     "nosql-wide",     "Apache",     None),
    "couchdb":       TechRecord("CouchDB",        "database",     "nosql-doc",      "Apache",     None),
    # ── Cache ─────────────────────────────────────────────────────────────
    "redis":         TechRecord("Redis",          "cache",        "in-memory",      "Redis Ltd",  None),
    "memcached":     TechRecord("Memcached",      "cache",        "in-memory",      "Community",  None),
    "ehcache":       TechRecord("Ehcache",        "cache",        "in-process",     "Terracotta", None),
    "hazelcast":     TechRecord("Hazelcast",      "cache",        "distributed",    "Hazelcast",  None),
    # ── Message Queue / Broker ────────────────────────────────────────────
    "kafka":         TechRecord("Apache Kafka",   "queue",        "message-broker", "Confluent",  None),
    "rabbitmq":      TechRecord("RabbitMQ",       "queue",        "message-broker", "VMware",     None),
    "activemq":      TechRecord("ActiveMQ",       "queue",        "message-broker", "Apache",     None),
    "activemq 5":    TechRecord("ActiveMQ 5",     "queue",        "message-broker", "Apache",     None),
    "ibm mq":        TechRecord("IBM MQ",         "queue",        "message-broker", "IBM",        None),
    "sqs":           TechRecord("Amazon SQS",     "queue",        "managed-queue",  "AWS",        None),
    "azure service bus": TechRecord("Azure SB",   "queue",        "managed-queue",  "Microsoft",  None),
    "google pub/sub":TechRecord("Google Pub/Sub", "queue",        "managed-queue",  "GCP",        None),
    # ── Storage ───────────────────────────────────────────────────────────
    "s3":            TechRecord("Amazon S3",      "storage",      "object-store",   "AWS",        None),
    "gcs":           TechRecord("Google GCS",     "storage",      "object-store",   "GCP",        None),
    "azure blob":    TechRecord("Azure Blob",     "storage",      "object-store",   "Microsoft",  None),
    "hdfs":          TechRecord("HDFS",           "storage",      "distributed-fs", "Apache",     None),
    "nfs":           TechRecord("NFS",            "storage",      "file-server",    "Community",  None),
    # ── CDN ───────────────────────────────────────────────────────────────
    "cloudfront":    TechRecord("CloudFront",     "cdn",          "cdn",            "AWS",        None),
    "akamai":        TechRecord("Akamai",         "cdn",          "cdn",            "Akamai",     None),
    "fastly":        TechRecord("Fastly",         "cdn",          "cdn",            "Fastly",     None),
    "cloudflare":    TechRecord("Cloudflare",     "cdn",          "cdn",            "Cloudflare", None),
    # ── Load Balancer ─────────────────────────────────────────────────────
    "elb":           TechRecord("AWS ELB",        "loadbalancer", "lb",             "AWS",        None),
    "alb":           TechRecord("AWS ALB",        "loadbalancer", "lb",             "AWS",        None),
    "haproxy":       TechRecord("HAProxy",        "loadbalancer", "lb",             "Community",  None),
    "f5":            TechRecord("F5 BIG-IP",      "loadbalancer", "lb",             "F5",         None),
    # ── API Gateway ───────────────────────────────────────────────────────
    "api gateway":   TechRecord("API Gateway",    "gateway",      "api-gw",         "AWS",        None),
    "kong":          TechRecord("Kong",           "gateway",      "api-gw",         "Kong",       None),
    "apigee":        TechRecord("Apigee",         "gateway",      "api-gw",         "Google",     None),
    "zuul":          TechRecord("Netflix Zuul",   "gateway",      "api-gw",         "Netflix",    None),
    "traefik":       TechRecord("Traefik",        "gateway",      "api-gw",         "Traefik",    None),
    # ── Client ────────────────────────────────────────────────────────────
    "react":         TechRecord("React",          "client",       "spa",            "Meta",       None),
    "vue":           TechRecord("Vue.js",         "client",       "spa",            "Community",  None),
    "angular":       TechRecord("Angular",        "client",       "spa",            "Google",     None),
    "flutter":       TechRecord("Flutter",        "client",       "mobile",         "Google",     None),
    "react native":  TechRecord("React Native",   "client",       "mobile",         "Meta",       None),
}


def lookup(tech_name: str) -> Optional[TechRecord]:
    """대소문자·공백 무시 온톨로지 조회."""
    return TECH_ONTOLOGY.get(tech_name.lower().strip())


def enrich_component(comp: dict) -> dict:
    """컴포넌트 dict의 tech 배열을 순회해 type·vintage를 자동 보완.

    원칙: 기존 값이 있으면 절대 덮어쓰지 않음 (보완만).
    """
    records = [r for t in comp.get("tech", []) if (r := lookup(t)) is not None]
    if not records:
        return comp

    # type 미지정 또는 unknown → 온톨로지 첫 매치에서 추론
    if comp.get("type") in (None, "unknown", ""):
        comp["type"] = records[0].component_type

    # vintage 미지정이고 EOL 정보 있음 → 보수적 추정 (최소 EOL - 7년)
    if not comp.get("vintage"):
        eol_years = [r.eol_year for r in records if r.eol_year]
        if eol_years:
            comp["vintage"] = min(eol_years) - 7

    # metadata.vendor, metadata.category 보강 (없을 때만)
    meta = comp.setdefault("metadata", {})
    if not meta.get("vendor") and records[0].vendor:
        meta["vendor"] = records[0].vendor
    if not meta.get("category") and records[0].category:
        meta["category"] = records[0].category

    return comp
