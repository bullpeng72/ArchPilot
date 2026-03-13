"""기술명 → ComponentType·EOL·카테고리·벤더 자동 매핑 온톨로지.

사용 방법:
    from archpilot.core.tech_ontology import enrich_component
    enriched = enrich_component(raw_component_dict)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class TechRecord:
    canonical: str           # 정규화된 기술명
    component_type: str      # ComponentType enum 값
    category: str            # 세부 분류 (rdbms, nosql, web-server, …)
    vendor: str
    eol_year: Optional[int]  # EOL 연도 (None = 현재 지원 중)
    license_type: str = "open-source"  # commercial | open-source | managed | proprietary


# ── 온톨로지 테이블 ──────────────────────────────────────────────────────────
TECH_ONTOLOGY: dict[str, TechRecord] = {
    # ── Web / App Servers ─────────────────────────────────────────────────
    "iis":            TechRecord("IIS",             "server", "web-server",   "Microsoft",  None, "commercial"),
    "iis 6":          TechRecord("IIS 6",           "server", "web-server",   "Microsoft",  2015, "commercial"),
    "iis 7":          TechRecord("IIS 7",           "server", "web-server",   "Microsoft",  2023, "commercial"),
    "iis 8.5":        TechRecord("IIS 8.5",         "server", "web-server",   "Microsoft",  2023, "commercial"),
    "apache":         TechRecord("Apache HTTP",     "server", "web-server",   "Apache",     None),
    "apache 2.2":     TechRecord("Apache 2.2",      "server", "web-server",   "Apache",     2017),
    "nginx":          TechRecord("Nginx",           "server", "web-server",   "F5",         None),
    "tomcat":         TechRecord("Tomcat",          "server", "app-server",   "Apache",     None),
    "tomcat 6":       TechRecord("Tomcat 6",        "server", "app-server",   "Apache",     2016),
    "tomcat 7":       TechRecord("Tomcat 7",        "server", "app-server",   "Apache",     2021),
    "jboss":          TechRecord("JBoss",           "server", "app-server",   "Red Hat",    None, "commercial"),
    "jboss 4":        TechRecord("JBoss 4",         "server", "app-server",   "Red Hat",    2012, "commercial"),
    "jboss 5":        TechRecord("JBoss 5",         "server", "app-server",   "Red Hat",    2013, "commercial"),
    "jboss eap":      TechRecord("JBoss EAP",       "server", "app-server",   "Red Hat",    None, "commercial"),
    "wildfly":        TechRecord("WildFly",         "server", "app-server",   "Red Hat",    None),
    "weblogic":       TechRecord("WebLogic",        "server", "app-server",   "Oracle",     None, "commercial"),
    "weblogic 12c":   TechRecord("WebLogic 12c",    "server", "app-server",   "Oracle",     2027, "commercial"),
    "websphere":      TechRecord("WebSphere",       "server", "app-server",   "IBM",        None, "commercial"),
    "websphere liberty": TechRecord("IBM Liberty",  "server", "app-server",   "IBM",        None, "commercial"),
    "glassfish":      TechRecord("GlassFish",       "server", "app-server",   "Eclipse",    None),
    "spring boot":    TechRecord("Spring Boot",     "server", "app-framework","VMware",     None),

    # ── Databases: RDBMS ──────────────────────────────────────────────────
    "oracle":         TechRecord("Oracle DB",       "database", "rdbms",      "Oracle",     None, "commercial"),
    "oracle 9i":      TechRecord("Oracle 9i",       "database", "rdbms",      "Oracle",     2010, "commercial"),
    "oracle 10g":     TechRecord("Oracle 10g",      "database", "rdbms",      "Oracle",     2013, "commercial"),
    "oracle 11g":     TechRecord("Oracle 11g",      "database", "rdbms",      "Oracle",     2020, "commercial"),
    "oracle 12c":     TechRecord("Oracle 12c",      "database", "rdbms",      "Oracle",     2022, "commercial"),
    "oracle 19c":     TechRecord("Oracle 19c",      "database", "rdbms",      "Oracle",     2027, "commercial"),
    "mysql":          TechRecord("MySQL",           "database", "rdbms",      "Oracle",     None, "commercial"),
    "mysql 5.5":      TechRecord("MySQL 5.5",       "database", "rdbms",      "Oracle",     2018, "commercial"),
    "mysql 5.7":      TechRecord("MySQL 5.7",       "database", "rdbms",      "Oracle",     2023, "commercial"),
    "postgresql":     TechRecord("PostgreSQL",      "database", "rdbms",      "Community",  None),
    "mssql":          TechRecord("SQL Server",      "database", "rdbms",      "Microsoft",  None, "commercial"),
    "sql server":     TechRecord("SQL Server",      "database", "rdbms",      "Microsoft",  None, "commercial"),
    "sql server 2008":TechRecord("SQL Server 2008", "database", "rdbms",      "Microsoft",  2019, "commercial"),
    "sql server 2012":TechRecord("SQL Server 2012", "database", "rdbms",      "Microsoft",  2022, "commercial"),
    "db2":            TechRecord("IBM DB2",         "database", "rdbms",      "IBM",        None, "commercial"),
    "db2 luw":        TechRecord("IBM DB2 LUW",     "database", "rdbms",      "IBM",        None, "commercial"),
    "sybase":         TechRecord("Sybase ASE",      "database", "rdbms",      "SAP",        2025, "commercial"),
    "informix":       TechRecord("IBM Informix",    "database", "rdbms",      "IBM",        None, "commercial"),

    # ── Databases: Mainframe ──────────────────────────────────────────────
    "db2/z":          TechRecord("IBM DB2 for z/OS","database", "rdbms-mainframe","IBM",    None, "commercial"),
    "ims":            TechRecord("IBM IMS DB",      "database", "hierarchical","IBM",       None, "commercial"),
    "ims db":         TechRecord("IBM IMS DB",      "database", "hierarchical","IBM",       None, "commercial"),
    "vsam":           TechRecord("IBM VSAM",        "database", "flat-file",  "IBM",        None, "commercial"),
    "adabas":         TechRecord("Adabas",          "database", "nosql-mainframe","Software AG",None,"commercial"),

    # ── Databases: NoSQL ──────────────────────────────────────────────────
    "mongodb":        TechRecord("MongoDB",         "database", "nosql-doc",  "MongoDB",    None, "commercial"),
    "cassandra":      TechRecord("Cassandra",       "database", "nosql-wide", "Apache",     None),
    "dynamodb":       TechRecord("DynamoDB",        "database", "nosql-kv",   "AWS",        None, "managed"),
    "hbase":          TechRecord("HBase",           "database", "nosql-wide", "Apache",     None),
    "couchdb":        TechRecord("CouchDB",         "database", "nosql-doc",  "Apache",     None),
    "elasticsearch":  TechRecord("Elasticsearch",  "database", "nosql-search","Elastic",   None, "commercial"),

    # ── Cache ─────────────────────────────────────────────────────────────
    "redis":          TechRecord("Redis",           "cache", "in-memory",     "Redis Ltd",  None, "commercial"),
    "memcached":      TechRecord("Memcached",       "cache", "in-memory",     "Community",  None),
    "ehcache":        TechRecord("Ehcache",         "cache", "in-process",    "Terracotta", None, "commercial"),
    "hazelcast":      TechRecord("Hazelcast",       "cache", "distributed",   "Hazelcast",  None, "commercial"),

    # ── Message Queue / Broker ────────────────────────────────────────────
    "kafka":          TechRecord("Apache Kafka",    "queue", "message-broker","Confluent",  None),
    "rabbitmq":       TechRecord("RabbitMQ",        "queue", "message-broker","VMware",     None),
    "activemq":       TechRecord("ActiveMQ",        "queue", "message-broker","Apache",     None),
    "activemq 5":     TechRecord("ActiveMQ 5",      "queue", "message-broker","Apache",     None),
    "ibm mq":         TechRecord("IBM MQ",          "queue", "message-broker","IBM",        None, "commercial"),
    "mq series":      TechRecord("IBM MQ",          "queue", "message-broker","IBM",        None, "commercial"),
    "tibco ems":      TechRecord("TIBCO EMS",       "queue", "message-broker","TIBCO",      None, "commercial"),
    "sqs":            TechRecord("Amazon SQS",      "queue", "managed-queue", "AWS",        None, "managed"),
    "azure service bus": TechRecord("Azure SB",     "queue", "managed-queue", "Microsoft",  None, "managed"),
    "google pub/sub": TechRecord("Google Pub/Sub",  "queue", "managed-queue", "GCP",        None, "managed"),

    # ── ESB / Integration Middleware ──────────────────────────────────────
    "mulesoft":       TechRecord("MuleSoft ESB",    "esb",  "esb",           "Salesforce", None, "commercial"),
    "mule esb":       TechRecord("MuleSoft ESB",    "esb",  "esb",           "Salesforce", None, "commercial"),
    "tibco bw":       TechRecord("TIBCO BusinessWorks","esb","esb",          "TIBCO",      None, "commercial"),
    "tibco":          TechRecord("TIBCO",           "esb",  "esb",           "TIBCO",      None, "commercial"),
    "biztalk":        TechRecord("MS BizTalk",      "esb",  "esb",           "Microsoft",  None, "commercial"),
    "oracle soa":     TechRecord("Oracle SOA Suite","esb",  "esb",           "Oracle",     None, "commercial"),
    "oracle osb":     TechRecord("Oracle OSB",      "esb",  "esb",           "Oracle",     None, "commercial"),
    "ibm esb":        TechRecord("IBM ESB",         "esb",  "esb",           "IBM",        None, "commercial"),
    "ibm iib":        TechRecord("IBM IIB",         "esb",  "esb",           "IBM",        None, "commercial"),
    "ibm ace":        TechRecord("IBM App Connect", "esb",  "esb",           "IBM",        None, "commercial"),
    "webmethods":     TechRecord("webMethods",      "esb",  "esb",           "Software AG",None, "commercial"),
    "axway":          TechRecord("Axway Gateway",   "esb",  "api-gw",        "Axway",      None, "commercial"),
    "sterling b2b":   TechRecord("IBM Sterling B2B","esb",  "b2b-gateway",   "IBM",        None, "commercial"),

    # ── Mainframe ─────────────────────────────────────────────────────────
    "z/os":           TechRecord("IBM z/OS",        "mainframe","os-mainframe","IBM",       None, "commercial"),
    "zos":            TechRecord("IBM z/OS",        "mainframe","os-mainframe","IBM",       None, "commercial"),
    "cobol":          TechRecord("COBOL",           "mainframe","batch",      "Community",  None, "proprietary"),
    "cics":           TechRecord("IBM CICS",        "mainframe","tp-monitor", "IBM",        None, "commercial"),
    "ims tm":         TechRecord("IBM IMS TM",      "mainframe","tp-monitor", "IBM",        None, "commercial"),
    "natural":        TechRecord("Natural",         "mainframe","4gl",        "Software AG",None, "commercial"),
    "jcl":            TechRecord("JCL",             "mainframe","batch-lang", "IBM",        None, "commercial"),
    "rpg":            TechRecord("IBM RPG",         "mainframe","4gl",        "IBM",        None, "commercial"),
    "as400":          TechRecord("IBM AS/400 (IBMi)","mainframe","os-midrange","IBM",       None, "commercial"),
    "ibmi":           TechRecord("IBM i (AS/400)",  "mainframe","os-midrange","IBM",        None, "commercial"),
    "tandem":         TechRecord("HP NonStop (Tandem)","mainframe","fault-tolerant","HPE",  None, "commercial"),

    # ── Security ──────────────────────────────────────────────────────────
    "hsm":            TechRecord("HSM",             "security","hsm",         "Various",    None, "commercial"),
    "active directory":TechRecord("Active Directory","security","iam-ldap",   "Microsoft",  None, "commercial"),
    "ldap":           TechRecord("LDAP",            "security","directory",   "Community",  None),
    "kerberos":       TechRecord("Kerberos",        "security","auth-protocol","MIT",       None),
    "racf":           TechRecord("IBM RACF",        "security","access-control","IBM",      None, "commercial"),
    "acf2":           TechRecord("CA ACF2",         "security","access-control","Broadcom", None, "commercial"),
    "top secret":     TechRecord("CA Top Secret",   "security","access-control","Broadcom", None, "commercial"),
    "waf":            TechRecord("WAF",             "security","waf",         "Various",    None, "commercial"),
    "checkpoint":     TechRecord("Check Point FW",  "security","firewall",    "Check Point",None, "commercial"),
    "pam":            TechRecord("PAM",             "security","privileged-access","Various",None,"commercial"),
    "siem":           TechRecord("SIEM",            "security","siem",        "Various",    None, "commercial"),
    "splunk":         TechRecord("Splunk",          "monitoring","log-analytics","Splunk",  None, "commercial"),

    # ── Monitoring / Observability ─────────────────────────────────────────
    "dynatrace":      TechRecord("Dynatrace",       "monitoring","apm",       "Dynatrace",  None, "commercial"),
    "appdynamics":    TechRecord("AppDynamics",     "monitoring","apm",       "Cisco",      None, "commercial"),
    "new relic":      TechRecord("New Relic",       "monitoring","apm",       "New Relic",  None, "commercial"),
    "datadog":        TechRecord("Datadog",         "monitoring","observability","Datadog",  None, "commercial"),
    "nagios":         TechRecord("Nagios",          "monitoring","infra-monitor","Nagios",   None),
    "zabbix":         TechRecord("Zabbix",          "monitoring","infra-monitor","Zabbix",   None),
    "prometheus":     TechRecord("Prometheus",      "monitoring","metrics",   "CNCF",       None),
    "grafana":        TechRecord("Grafana",         "monitoring","visualization","Grafana",  None),
    "elk":            TechRecord("ELK Stack",       "monitoring","log-analytics","Elastic",  None, "commercial"),

    # ── Storage ───────────────────────────────────────────────────────────
    "s3":             TechRecord("Amazon S3",       "storage","object-store",  "AWS",       None, "managed"),
    "gcs":            TechRecord("Google GCS",      "storage","object-store",  "GCP",       None, "managed"),
    "azure blob":     TechRecord("Azure Blob",      "storage","object-store",  "Microsoft", None, "managed"),
    "hdfs":           TechRecord("HDFS",            "storage","distributed-fs","Apache",    None),
    "nfs":            TechRecord("NFS",             "storage","file-server",   "Community", None),
    "san":            TechRecord("SAN",             "storage","block-storage", "Various",   None, "commercial"),
    "nas":            TechRecord("NAS",             "storage","file-storage",  "Various",   None, "commercial"),
    "netapp":         TechRecord("NetApp",          "storage","enterprise-nas","NetApp",    None, "commercial"),

    # ── CDN ───────────────────────────────────────────────────────────────
    "cloudfront":     TechRecord("CloudFront",      "cdn","cdn",              "AWS",        None, "managed"),
    "akamai":         TechRecord("Akamai",          "cdn","cdn",              "Akamai",     None, "commercial"),
    "fastly":         TechRecord("Fastly",          "cdn","cdn",              "Fastly",     None, "commercial"),
    "cloudflare":     TechRecord("Cloudflare",      "cdn","cdn",              "Cloudflare", None, "commercial"),

    # ── Load Balancer ─────────────────────────────────────────────────────
    "elb":            TechRecord("AWS ELB",         "loadbalancer","lb",      "AWS",        None, "managed"),
    "alb":            TechRecord("AWS ALB",         "loadbalancer","lb",      "AWS",        None, "managed"),
    "haproxy":        TechRecord("HAProxy",         "loadbalancer","lb",      "Community",  None),
    "f5":             TechRecord("F5 BIG-IP",       "loadbalancer","lb",      "F5",         None, "commercial"),
    "f5 big-ip":      TechRecord("F5 BIG-IP",       "loadbalancer","lb",      "F5",         None, "commercial"),
    "citrix adc":     TechRecord("Citrix ADC",      "loadbalancer","lb",      "Citrix",     None, "commercial"),

    # ── API Gateway ───────────────────────────────────────────────────────
    "api gateway":    TechRecord("API Gateway",     "gateway","api-gw",       "AWS",        None, "managed"),
    "kong":           TechRecord("Kong",            "gateway","api-gw",       "Kong",       None, "commercial"),
    "apigee":         TechRecord("Apigee",          "gateway","api-gw",       "Google",     None, "managed"),
    "zuul":           TechRecord("Netflix Zuul",    "gateway","api-gw",       "Netflix",    None),
    "traefik":        TechRecord("Traefik",         "gateway","api-gw",       "Traefik",    None),
    "3scale":         TechRecord("3scale",          "gateway","api-gw",       "Red Hat",    None, "commercial"),

    # ── Service / Cloud-Native Compute ────────────────────────────────────
    # 마이크로서비스·컨테이너 런타임·서버리스 → SERVICE 타입
    "lambda":           TechRecord("AWS Lambda",       "service","serverless",            "AWS",        None, "managed"),
    "aws lambda":       TechRecord("AWS Lambda",       "service","serverless",            "AWS",        None, "managed"),
    "fargate":          TechRecord("AWS Fargate",      "service","serverless-container",  "AWS",        None, "managed"),
    "ecs":              TechRecord("Amazon ECS",       "service","container-svc",         "AWS",        None, "managed"),
    "cloud run":        TechRecord("Google Cloud Run", "service","serverless-container",  "GCP",        None, "managed"),
    "azure functions":  TechRecord("Azure Functions",  "service","serverless",            "Microsoft",  None, "managed"),
    "azure app service":TechRecord("Azure App Svc",    "service","paas",                  "Microsoft",  None, "managed"),
    "istio":            TechRecord("Istio",            "service","service-mesh",          "CNCF",       None),
    "linkerd":          TechRecord("Linkerd",          "service","service-mesh",          "CNCF",       None),
    "envoy":            TechRecord("Envoy",            "service","proxy-sidecar",         "CNCF",       None),
    "consul":           TechRecord("HashiCorp Consul", "service","service-discovery",     "HashiCorp",  None),
    "dapr":             TechRecord("Dapr",             "service","runtime",               "CNCF",       None),
    "microservice":     TechRecord("Microservice",     "service","microservice",          "Community",  None),

    # ── Containerization / Orchestration ──────────────────────────────────
    # 플랫폼 인프라 자체 → SERVER; 매니지드 K8s 서비스 → SERVICE
    "kubernetes":     TechRecord("Kubernetes",      "server","container-orchestration","CNCF",None),
    "docker":         TechRecord("Docker",          "server","containerization","Docker",   None),
    "openshift":      TechRecord("OpenShift",       "server","container-platform","Red Hat",None,"commercial"),
    "eks":            TechRecord("Amazon EKS",      "service","managed-k8s",  "AWS",        None, "managed"),
    "gke":            TechRecord("Google GKE",      "service","managed-k8s",  "GCP",        None, "managed"),
    "aks":            TechRecord("Azure AKS",       "service","managed-k8s",  "Microsoft",  None, "managed"),

    # ── Virtualization ────────────────────────────────────────────────────
    "vmware":         TechRecord("VMware ESXi",     "server","hypervisor",    "Broadcom",   None, "commercial"),
    "vmware esxi":    TechRecord("VMware ESXi",     "server","hypervisor",    "Broadcom",   None, "commercial"),
    "hyper-v":        TechRecord("Hyper-V",         "server","hypervisor",    "Microsoft",  None, "commercial"),

    # ── Client ────────────────────────────────────────────────────────────
    "react":          TechRecord("React",           "client","spa",           "Meta",       None),
    "vue":            TechRecord("Vue.js",          "client","spa",           "Community",  None),
    "angular":        TechRecord("Angular",         "client","spa",           "Google",     None),
    "flutter":        TechRecord("Flutter",         "client","mobile",        "Google",     None),
    "react native":   TechRecord("React Native",    "client","mobile",        "Meta",       None),
    "powerbuilder":   TechRecord("PowerBuilder",    "client","legacy-gui",    "SAP",        2030, "commercial"),
    "vb6":            TechRecord("Visual Basic 6",  "client","legacy-gui",    "Microsoft",  2008, "commercial"),
    "delphi":         TechRecord("Delphi",          "client","legacy-gui",    "Embarcadero",None,"commercial"),
    "swing":          TechRecord("Java Swing",      "client","desktop-gui",   "Oracle",     None),
    "flex":           TechRecord("Adobe Flex",      "client","ria",           "Adobe",      2020, "commercial"),
}


def lookup(tech_name: str) -> Optional[TechRecord]:
    """대소문자·공백 무시 온톨로지 조회."""
    return TECH_ONTOLOGY.get(tech_name.lower().strip())


# 카테고리·타입 → criticality 자동 추론 맵
# 원칙: 기존 값이 있으면 절대 덮어쓰지 않음
_HIGH_CRITICALITY_CATEGORIES = {
    # 핵심 데이터 저장소
    "rdbms", "rdbms-mainframe", "hierarchical", "flat-file",
    # 메인프레임 트랜잭션 모니터 / 배치
    "tp-monitor", "batch", "os-mainframe", "os-midrange", "fault-tolerant",
    # 보안 장비
    "hsm", "iam-ldap", "access-control", "privileged-access", "firewall", "waf", "siem",
}
_HIGH_CRITICALITY_TYPES = {"mainframe", "security"}  # 타입 자체가 HIGH 를 암시

_LOW_CRITICALITY_CATEGORIES = {
    "apm", "metrics", "log-analytics", "observability",
    "infra-monitor", "visualization",
}
_LOW_CRITICALITY_TYPES = {"monitoring"}


# 상용 라이선스 벤더 집합 (license_type 추론 보조)
_COMMERCIAL_VENDORS = {
    "Microsoft", "Oracle", "IBM", "SAP", "TIBCO", "Salesforce",
    "Broadcom", "Red Hat", "Software AG", "HPE", "Dynatrace",
    "Cisco", "New Relic", "Datadog", "F5", "Citrix", "Axway",
    "Check Point", "Nagios", "Splunk", "Kong", "Hazelcast",
    "Terracotta", "MongoDB", "Elastic", "Akamai", "Fastly",
    "Cloudflare", "Redis Ltd", "VMware", "NetApp", "Embarcadero",
    "Adobe", "Docker",
}
_MANAGED_VENDORS = {"AWS", "GCP", "Google", "Azure", "Microsoft"}


def enrich_component(comp: dict) -> dict:
    """컴포넌트 dict의 tech 배열을 순회해 type·vintage·license 등을 자동 보완.

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

    # lifecycle_status: EOL 연도가 과거면 자동으로 eol 설정
    if not comp.get("lifecycle_status"):
        from datetime import date
        current_year = date.today().year
        eol_years = [r.eol_year for r in records if r.eol_year]
        if eol_years and min(eol_years) <= current_year:
            comp["lifecycle_status"] = "eol"

    # criticality: 카테고리·타입 기반 자동 추론 (명시 값 없을 때만)
    if not comp.get("criticality"):
        ctype = comp.get("type", "")
        cats  = {r.category for r in records}
        if ctype in _HIGH_CRITICALITY_TYPES or cats & _HIGH_CRITICALITY_CATEGORIES:
            comp["criticality"] = "high"
        elif ctype in _LOW_CRITICALITY_TYPES or cats & _LOW_CRITICALITY_CATEGORIES:
            comp["criticality"] = "low"

    # metadata 보강 (없을 때만)
    meta = comp.setdefault("metadata", {})
    if not meta.get("vendor") and records[0].vendor:
        meta["vendor"] = records[0].vendor
    if not meta.get("category") and records[0].category:
        meta["category"] = records[0].category
    if not meta.get("license_type"):
        meta["license_type"] = records[0].license_type

    return comp
