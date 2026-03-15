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
    license_type: str = "open-source"  # commercial | open-source | managed | proprietary


# ── 온톨로지 테이블 ──────────────────────────────────────────────────────────
TECH_ONTOLOGY: dict[str, TechRecord] = {
    # ── Languages & Runtimes ──────────────────────────────────────────────
    "java":           TechRecord("Java",            "server", "app-framework","Oracle",     None, "commercial"),
    "java 8":         TechRecord("Java 8",          "server", "app-framework","Oracle",     2030, "commercial"),
    "java 11":        TechRecord("Java 11",         "server", "app-framework","Oracle",     2026, "commercial"),
    "java 17":        TechRecord("Java 17",         "server", "app-framework","Oracle",     2029, "commercial"),
    "java 21":        TechRecord("Java 21",         "server", "app-framework","Oracle",     2031, "commercial"),
    "java ee 6":      TechRecord("Java EE 6",       "server", "app-framework","Oracle",     2016, "commercial"),
    "jakarta ee":     TechRecord("Jakarta EE",      "server", "app-framework","Eclipse",    None),
    "python":         TechRecord("Python",          "service","app-framework","PSF",        None),
    "python 3.9":     TechRecord("Python 3.9",      "service","app-framework","PSF",        2025),
    "python 3.10":    TechRecord("Python 3.10",     "service","app-framework","PSF",        2026),
    "python 3.11":    TechRecord("Python 3.11",     "service","app-framework","PSF",        2027),
    "python 3.12":    TechRecord("Python 3.12",     "service","app-framework","PSF",        2028),
    "go":             TechRecord("Go",              "service","app-framework","Google",     None),
    "go 1.21":        TechRecord("Go 1.21",         "service","app-framework","Google",     None),
    "go 1.22":        TechRecord("Go 1.22",         "service","app-framework","Google",     None),
    "node.js":        TechRecord("Node.js",         "service","app-framework","OpenJS",     None),
    "node.js 18":     TechRecord("Node.js 18",      "service","app-framework","OpenJS",     2025),
    "node.js 20":     TechRecord("Node.js 20",      "service","app-framework","OpenJS",     2026),
    "node.js 22":     TechRecord("Node.js 22",      "service","app-framework","OpenJS",     2027),
    "typescript":     TechRecord("TypeScript",      "client", "spa",          "Microsoft",  None),
    "swift":          TechRecord("Swift",           "client", "mobile",       "Apple",      None),
    "swift 5":        TechRecord("Swift 5",         "client", "mobile",       "Apple",      None),
    "kotlin":         TechRecord("Kotlin",          "client", "mobile",       "JetBrains",  None),
    "android":        TechRecord("Android",         "client", "mobile",       "Google",     None),
    "ios":            TechRecord("iOS",             "client", "mobile",       "Apple",      None),

    # ── Frameworks ────────────────────────────────────────────────────────
    "spring boot 2":  TechRecord("Spring Boot 2",  "server", "app-framework","VMware",     2025),
    "spring boot 2.5":TechRecord("Spring Boot 2.5","server", "app-framework","VMware",     2023),
    "spring boot 2.7":TechRecord("Spring Boot 2.7","server", "app-framework","VMware",     2025),
    "spring boot 3":  TechRecord("Spring Boot 3",  "server", "app-framework","VMware",     None),
    "spring batch":   TechRecord("Spring Batch",   "server", "batch",        "VMware",     None),
    "spring mvc":     TechRecord("Spring MVC",     "server", "app-framework","VMware",     None),
    "fastapi":        TechRecord("FastAPI",         "service","app-framework","Tiangolo",   None),
    "django":         TechRecord("Django",          "server", "app-framework","DSF",        None),
    "flask":          TechRecord("Flask",           "server", "app-framework","Pallets",    None),
    "quartz":         TechRecord("Quartz Scheduler","server", "batch",        "Terracotta", None),
    "next.js":        TechRecord("Next.js",         "client", "ssr-framework","Vercel",     None),

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

    # ── Healthcare / Industrial / Financial Protocols ─────────────────────
    "hl7 v2.x":       TechRecord("HL7 v2.x",       "server",   "health-protocol","HL7",    None),
    "dicom 3.0":      TechRecord("DICOM 3.0",       "server",   "medical-imaging","NEMA",   None),
    "opc-da":         TechRecord("OPC-DA",          "server",   "iot-protocol","OPC Fdn",   None),
    "opc-hda":        TechRecord("OPC-HDA",         "server",   "iot-protocol","OPC Fdn",   None),
    "mqtt":           TechRecord("MQTT",            "service",  "iot-protocol","OASIS",      None),
    "coap":           TechRecord("CoAP",            "service",  "iot-protocol","IETF",       None),
    "lte-m":          TechRecord("LTE-M",           "service",  "iot-protocol","3GPP",       None),
    "websocket":      TechRecord("WebSocket",       "service",  "protocol",   "IETF",        None),
    "grpc":           TechRecord("gRPC",            "service",  "rpc-framework","Google",    None),
    "graphql":        TechRecord("GraphQL",         "gateway",  "api-gw",     "Meta",        None),
    "webrtc":         TechRecord("WebRTC",          "service",  "media-protocol","W3C",      None),
    "php":            TechRecord("PHP",             "server",   "web-framework","PHP Group", None),
    "php 7":          TechRecord("PHP 7",           "server",   "web-framework","PHP Group", 2022),
    "php 7.2":        TechRecord("PHP 7.2",         "server",   "web-framework","PHP Group", 2020),
    "php 8":          TechRecord("PHP 8",           "server",   "web-framework","PHP Group", None),
    "windows server": TechRecord("Windows Server",  "server",   "os",         "Microsoft",  None, "commercial"),
    "windows server 2008":TechRecord("Windows Server 2008","server","os","Microsoft",2020,"commercial"),
    "windows server 2012":TechRecord("Windows Server 2012","server","os","Microsoft",2023,"commercial"),
    "windows server 2016":TechRecord("Windows Server 2016","server","os","Microsoft",2027,"commercial"),
    "windows server 2019":TechRecord("Windows Server 2019","server","os","Microsoft",2029,"commercial"),
    "linux":          TechRecord("Linux",           "server",   "os",         "Community",   None),
    "c++":            TechRecord("C++",             "server",   "app-framework","ISO",       None),
    "wcf":            TechRecord("WCF",             "server",   "app-framework","Microsoft", None, "commercial"),
    "ibm mq 8":       TechRecord("IBM MQ 8",        "queue",    "message-broker","IBM",     None, "commercial"),
    "ibm mq 9":       TechRecord("IBM MQ 9",        "queue",    "message-broker","IBM",     None, "commercial"),
    "amqp":           TechRecord("AMQP",            "queue",    "message-broker","OASIS",   None),
    "azure stream analytics":TechRecord("Azure Stream Analytics","service","stream-processing","Microsoft",None,"managed"),
    "google bigquery":TechRecord("Google BigQuery", "database","data-warehouse","GCP",       None, "managed"),
    "google dataflow":TechRecord("Google Dataflow", "service", "stream-processing","GCP",    None, "managed"),
    "looker studio":  TechRecord("Looker Studio",   "service",  "bi-platform","Google",     None),
    "parquet":        TechRecord("Apache Parquet",  "storage",  "columnar-format","Apache",  None),
    "xgboost":        TechRecord("XGBoost",         "service",  "ml-framework","Community",  None),
    "lightgbm":       TechRecord("LightGBM",        "service",  "ml-framework","Microsoft",  None),
    "prophet":        TechRecord("Prophet",         "service",  "ml-framework","Meta",        None),
    "opensearch":     TechRecord("OpenSearch",      "database", "nosql-search","AWS",        None, "managed"),
    "opentelemetry":  TechRecord("OpenTelemetry",   "monitoring","observability","CNCF",     None),
    "stripe":         TechRecord("Stripe",          "service",  "payment",    "Stripe",      None, "commercial"),
    "golden gate":    TechRecord("Oracle GoldenGate","service", "cdc",        "Oracle",      None, "commercial"),
    "goldengate":     TechRecord("Oracle GoldenGate","service", "cdc",        "Oracle",      None, "commercial"),
    "tibero":         TechRecord("Tibero",          "database", "rdbms",      "TmaxSoft",    None, "commercial"),

    # ── Databases: Managed/Cloud Features ────────────────────────────────
    "dax":            TechRecord("Amazon DAX",      "cache",    "in-memory",  "AWS",        None, "managed"),
    "amazon elasticache":TechRecord("ElastiCache",  "cache",    "in-memory",  "AWS",        None, "managed"),
    "amazon elasticache redis":TechRecord("ElastiCache Redis","cache","in-memory","AWS",   None, "managed"),
    "elasticache":    TechRecord("ElastiCache",     "cache",    "in-memory",  "AWS",        None, "managed"),
    "amazon dynamodb":TechRecord("DynamoDB",        "database", "nosql-kv",   "AWS",        None, "managed"),
    "amazon timestream":TechRecord("Amazon Timestream","database","timeseries","AWS",       None, "managed"),
    "amazon redshift":TechRecord("Amazon Redshift", "database", "data-warehouse","AWS",    None, "managed"),
    "amazon redshift ra3":TechRecord("Amazon Redshift","database","data-warehouse","AWS",  None, "managed"),
    "amazon kinesis analytics":TechRecord("Kinesis Analytics","service","stream-processing","AWS",None,"managed"),
    "azure synapse analytics":TechRecord("Azure Synapse","database","data-warehouse","Microsoft",None,"managed"),
    "multi-az":       TechRecord("Multi-AZ",        "database", "ha",         "AWS",        None, "managed"),
    "global tables":  TechRecord("DynamoDB Global Tables","database","nosql-kv","AWS",     None, "managed"),
    "kcl":            TechRecord("Kinesis Client Library","service","event-streaming","AWS",None, "managed"),
    "aws ses":        TechRecord("Amazon SES",      "service",  "email",      "AWS",        None, "managed"),
    "fcm":            TechRecord("Firebase Cloud Messaging","service","push-notification","Google",None,"managed"),
    "apns":           TechRecord("Apple Push Notifications","service","push-notification","Apple",None,"managed"),
    "iso 8583":       TechRecord("ISO 8583",        "server",   "financial-protocol","ISO", None),
    "hl7 fhir":       TechRecord("HL7 FHIR",        "gateway",  "health-api", "HL7",        None),
    "hl7 v2":         TechRecord("HL7 v2",          "server",   "health-protocol","HL7",    None),
    "dicom":          TechRecord("DICOM",           "server",   "medical-imaging","NEMA",   None),
    "opc-ua":         TechRecord("OPC UA",          "server",   "iot-protocol","OPC Fdn",  None),
    "profinet":       TechRecord("PROFINET",        "server",   "industrial-net","Siemens", None),
    "siemens":        TechRecord("Siemens S7",      "server",   "plc",        "Siemens",   None, "commercial"),
    "aws shield advanced":TechRecord("AWS Shield Adv","security","ddos",      "AWS",        None, "managed"),
    "asp.net":        TechRecord("ASP.NET",         "server",   "web-framework","Microsoft",None, "commercial"),
    "asp.net core":   TechRecord("ASP.NET Core",    "server",   "web-framework","Microsoft",None),
    "c#":             TechRecord("C#",              "server",   "app-framework","Microsoft",None),
    "c# .net":        TechRecord("C# .NET",         "server",   "app-framework","Microsoft",None),
    "hana db":        TechRecord("SAP HANA",        "database", "rdbms",      "SAP",        None, "commercial"),
    "sap hana":       TechRecord("SAP HANA",        "database", "rdbms",      "SAP",        None, "commercial"),
    "sap s/4hana":    TechRecord("SAP S/4HANA",     "server",   "erp",        "SAP",        None, "commercial"),
    "abap":           TechRecord("ABAP",            "server",   "erp",        "SAP",        None, "commercial"),
    "sap":            TechRecord("SAP",             "server",   "erp",        "SAP",        None, "commercial"),
    "ffmpeg":         TechRecord("FFmpeg",          "service",  "media-processing","Community",None),
    "ssl offload":    TechRecord("SSL Offload",     "loadbalancer","lb",       "Various",   None),
    "kql":            TechRecord("KQL",             "monitoring","query-lang", "Microsoft", None),
    "aws sns":        TechRecord("Amazon SNS",      "queue",    "managed-queue","AWS",      None, "managed"),
    "aws cloudtrail": TechRecord("AWS CloudTrail",  "security", "audit-log",  "AWS",        None, "managed"),

    # ── Databases: Cloud Managed ──────────────────────────────────────────
    "aurora":         TechRecord("Amazon Aurora",   "database", "rdbms",      "AWS",        None, "managed"),
    "aurora mysql":   TechRecord("Aurora MySQL",    "database", "rdbms",      "AWS",        None, "managed"),
    "aurora postgresql":TechRecord("Aurora PostgreSQL","database","rdbms",    "AWS",        None, "managed"),
    "cloud sql":      TechRecord("Cloud SQL",       "database", "rdbms",      "GCP",        None, "managed"),
    "azure sql":      TechRecord("Azure SQL",       "database", "rdbms",      "Microsoft",  None, "managed"),
    "cosmos db":      TechRecord("Azure Cosmos DB", "database", "nosql-doc",  "Microsoft",  None, "managed"),
    "firestore":      TechRecord("Firestore",       "database", "nosql-doc",  "GCP",        None, "managed"),
    "bigtable":       TechRecord("Cloud Bigtable",  "database", "nosql-wide", "GCP",        None, "managed"),
    "redshift":       TechRecord("Amazon Redshift", "database", "data-warehouse","AWS",     None, "managed"),
    "synapse":        TechRecord("Azure Synapse",   "database", "data-warehouse","Microsoft",None,"managed"),
    "bigquery":       TechRecord("BigQuery",        "database", "data-warehouse","GCP",     None, "managed"),
    "snowflake":      TechRecord("Snowflake",       "database", "data-warehouse","Snowflake",None,"commercial"),
    "timestream":     TechRecord("Amazon Timestream","database","timeseries", "AWS",        None, "managed"),
    "influxdb":       TechRecord("InfluxDB",        "database", "timeseries", "InfluxData", None, "commercial"),
    "pinecone":       TechRecord("Pinecone",        "database", "vector-db",  "Pinecone",   None, "managed"),
    "qdrant":         TechRecord("Qdrant",          "database", "vector-db",  "Qdrant",     None),
    "weaviate":       TechRecord("Weaviate",        "database", "vector-db",  "Weaviate",   None),
    "milvus":         TechRecord("Milvus",          "database", "vector-db",  "Zilliz",     None),
    "pgvector":       TechRecord("pgvector",        "database", "vector-db",  "Community",  None),
    "delta lake":     TechRecord("Delta Lake",      "storage",  "data-lake",  "Databricks", None),
    "apache iceberg": TechRecord("Apache Iceberg",  "storage",  "data-lake",  "Apache",     None),
    "apache parquet": TechRecord("Apache Parquet",  "storage",  "columnar-format","Apache", None),

    # ── Databases: DB Features (warn on unknown) ──────────────────────────
    # RAC, Data Guard, Multi-AZ 등은 Oracle/DB 기능이므로 database로 처리
    "rac":            TechRecord("Oracle RAC",      "database", "rdbms",      "Oracle",     None, "commercial"),
    "data guard":     TechRecord("Oracle Data Guard","database","rdbms",      "Oracle",     None, "commercial"),
    "always on":      TechRecord("SQL Server Always On","database","rdbms",   "Microsoft",  None, "commercial"),

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
    "amazon msk":     TechRecord("Amazon MSK",      "queue", "message-broker","AWS",        None, "managed"),
    "kinesis":        TechRecord("Amazon Kinesis",  "queue", "event-streaming","AWS",       None, "managed"),
    "amazon kinesis": TechRecord("Amazon Kinesis",  "queue", "event-streaming","AWS",       None, "managed"),
    "event hubs":     TechRecord("Azure Event Hubs","queue", "event-streaming","Microsoft", None, "managed"),
    "azure event hubs":TechRecord("Azure Event Hubs","queue","event-streaming","Microsoft", None, "managed"),
    "google pubsub":  TechRecord("Google Pub/Sub",  "queue", "managed-queue", "GCP",       None, "managed"),
    "pubsub":         TechRecord("Google Pub/Sub",  "queue", "managed-queue", "GCP",       None, "managed"),
    "sns":            TechRecord("Amazon SNS",      "queue", "managed-queue", "AWS",       None, "managed"),
    "amazon sns":     TechRecord("Amazon SNS",      "queue", "managed-queue", "AWS",       None, "managed"),
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
    "vault":          TechRecord("HashiCorp Vault", "security","secrets-mgmt","HashiCorp",  None, "commercial"),
    "hashicorp vault":TechRecord("HashiCorp Vault", "security","secrets-mgmt","HashiCorp",  None, "commercial"),
    "aws kms":        TechRecord("AWS KMS",         "security","kms",         "AWS",        None, "managed"),
    "kms":            TechRecord("KMS",             "security","kms",         "Various",    None, "managed"),
    "azure key vault":TechRecord("Azure Key Vault", "security","kms",         "Microsoft",  None, "managed"),
    "aws iam":        TechRecord("AWS IAM",         "security","iam",         "AWS",        None, "managed"),
    "azure ad":       TechRecord("Azure AD",        "security","iam",         "Microsoft",  None, "managed"),
    "azure ad b2c":   TechRecord("Azure AD B2C",    "security","iam",         "Microsoft",  None, "managed"),
    "keycloak":       TechRecord("Keycloak",        "security","iam",         "Red Hat",    None),
    "okta":           TechRecord("Okta",            "security","iam",         "Okta",       None, "commercial"),
    "aws waf":        TechRecord("AWS WAF",         "security","waf",         "AWS",        None, "managed"),
    "aws shield":     TechRecord("AWS Shield",      "security","ddos",        "AWS",        None, "managed"),
    "cloudtrail":     TechRecord("AWS CloudTrail",  "security","audit-log",   "AWS",        None, "managed"),
    "oauth 2.0":      TechRecord("OAuth 2.0",       "security","auth-protocol","IETF",      None),
    "jwt":            TechRecord("JWT",             "security","auth-protocol","IETF",      None),
    "fido2":          TechRecord("FIDO2",           "security","auth-protocol","FIDO Alliance",None),
    "mtls":           TechRecord("mTLS",            "security","transport-sec","IETF",      None),
    "pkcs#11":        TechRecord("PKCS#11",         "security","hsm-interface","OASIS",     None),
    "saml":           TechRecord("SAML 2.0",        "security","auth-protocol","OASIS",     None),
    "openid connect": TechRecord("OpenID Connect",  "security","auth-protocol","OpenID Fdn",None),
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
    "pagerduty":      TechRecord("PagerDuty",       "monitoring","alerting",  "PagerDuty",  None, "commercial"),
    "cloudwatch":     TechRecord("Amazon CloudWatch","monitoring","observability","AWS",    None, "managed"),
    "amazon cloudwatch":TechRecord("Amazon CloudWatch","monitoring","observability","AWS",  None, "managed"),
    "azure monitor":  TechRecord("Azure Monitor",   "monitoring","observability","Microsoft",None,"managed"),
    "google cloud monitoring":TechRecord("GCP Monitoring","monitoring","observability","GCP",None,"managed"),
    "jaeger":         TechRecord("Jaeger",          "monitoring","tracing",   "CNCF",       None),
    "x-ray":          TechRecord("AWS X-Ray",       "monitoring","tracing",   "AWS",        None, "managed"),
    "aws x-ray":      TechRecord("AWS X-Ray",       "monitoring","tracing",   "AWS",        None, "managed"),
    "cloud logging":  TechRecord("GCP Cloud Logging","monitoring","log-analytics","GCP",   None, "managed"),
    "loki":           TechRecord("Grafana Loki",    "monitoring","log-analytics","Grafana",  None),
    "tempo":          TechRecord("Grafana Tempo",   "monitoring","tracing",   "Grafana",    None),
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
    "amazon s3":      TechRecord("Amazon S3",       "storage","object-store",  "AWS",       None, "managed"),
    "azure blob storage":TechRecord("Azure Blob",   "storage","object-store",  "Microsoft", None, "managed"),
    "adls":           TechRecord("Azure Data Lake Storage","storage","data-lake","Microsoft",None,"managed"),
    "gcs bucket":     TechRecord("GCS Bucket",      "storage","object-store",  "GCP",      None, "managed"),
    "efs":            TechRecord("Amazon EFS",      "storage","file-server",   "AWS",       None, "managed"),
    "worm":           TechRecord("WORM Storage",    "storage","immutable",     "Various",   None),
    "gcs":            TechRecord("Google GCS",      "storage","object-store",  "GCP",       None, "managed"),
    "azure blob":     TechRecord("Azure Blob",      "storage","object-store",  "Microsoft", None, "managed"),
    "hdfs":           TechRecord("HDFS",            "storage","distributed-fs","Apache",    None),
    "nfs":            TechRecord("NFS",             "storage","file-server",   "Community", None),
    "san":            TechRecord("SAN",             "storage","block-storage", "Various",   None, "commercial"),
    "nas":            TechRecord("NAS",             "storage","file-storage",  "Various",   None, "commercial"),
    "netapp":         TechRecord("NetApp",          "storage","enterprise-nas","NetApp",    None, "commercial"),

    # ── CDN ───────────────────────────────────────────────────────────────
    "cloudfront":     TechRecord("CloudFront",      "cdn","cdn",              "AWS",        None, "managed"),
    "aws cloudfront": TechRecord("CloudFront",      "cdn","cdn",              "AWS",        None, "managed"),
    "azure cdn":      TechRecord("Azure CDN",       "cdn","cdn",              "Microsoft",  None, "managed"),
    "cloud cdn":      TechRecord("Google Cloud CDN","cdn","cdn",              "GCP",        None, "managed"),
    "akamai":         TechRecord("Akamai",          "cdn","cdn",              "Akamai",     None, "commercial"),
    "fastly":         TechRecord("Fastly",          "cdn","cdn",              "Fastly",     None, "commercial"),
    "cloudflare":     TechRecord("Cloudflare",      "cdn","cdn",              "Cloudflare", None, "commercial"),

    # ── Load Balancer ─────────────────────────────────────────────────────
    "elb":            TechRecord("AWS ELB",         "loadbalancer","lb",      "AWS",        None, "managed"),
    "alb":            TechRecord("AWS ALB",         "loadbalancer","lb",      "AWS",        None, "managed"),
    "aws alb":        TechRecord("AWS ALB",         "loadbalancer","lb",      "AWS",        None, "managed"),
    "nlb":            TechRecord("AWS NLB",         "loadbalancer","lb",      "AWS",        None, "managed"),
    "aws nlb":        TechRecord("AWS NLB",         "loadbalancer","lb",      "AWS",        None, "managed"),
    "azure load balancer":TechRecord("Azure LB",   "loadbalancer","lb",      "Microsoft",  None, "managed"),
    "gcp load balancing":TechRecord("GCP LB",      "loadbalancer","lb",      "GCP",        None, "managed"),
    "haproxy":        TechRecord("HAProxy",         "loadbalancer","lb",      "Community",  None),
    "f5":             TechRecord("F5 BIG-IP",       "loadbalancer","lb",      "F5",         None, "commercial"),
    "f5 big-ip":      TechRecord("F5 BIG-IP",       "loadbalancer","lb",      "F5",         None, "commercial"),
    "citrix adc":     TechRecord("Citrix ADC",      "loadbalancer","lb",      "Citrix",     None, "commercial"),

    # ── API Gateway ───────────────────────────────────────────────────────
    "api gateway":    TechRecord("API Gateway",     "gateway","api-gw",       "AWS",        None, "managed"),
    "aws api gateway":TechRecord("AWS API Gateway", "gateway","api-gw",       "AWS",        None, "managed"),
    "aws api gateway v2":TechRecord("AWS API GW v2","gateway","api-gw",       "AWS",        None, "managed"),
    "azure apim":     TechRecord("Azure APIM",      "gateway","api-gw",       "Microsoft",  None, "managed"),
    "azure api management":TechRecord("Azure APIM","gateway","api-gw",        "Microsoft",  None, "managed"),
    "aws direct connect":TechRecord("AWS Direct Connect","gateway","dedicated-link","AWS",  None, "managed"),
    "aws vpn":        TechRecord("AWS VPN Gateway", "gateway","vpn",          "AWS",        None, "managed"),
    "azure vpn gateway":TechRecord("Azure VPN GW",  "gateway","vpn",          "Microsoft",  None, "managed"),
    "expressroute":   TechRecord("Azure ExpressRoute","gateway","dedicated-link","Microsoft",None,"managed"),
    "cloud interconnect":TechRecord("GCP Interconnect","gateway","dedicated-link","GCP",   None, "managed"),
    "cisco asa":      TechRecord("Cisco ASA",       "gateway","firewall",     "Cisco",      None, "commercial"),
    "palo alto":      TechRecord("Palo Alto FW",    "gateway","firewall",     "Palo Alto",  None, "commercial"),
    "fortinet":       TechRecord("Fortinet",        "gateway","firewall",     "Fortinet",   None, "commercial"),
    "bgp":            TechRecord("BGP",             "gateway","network-protocol","IETF",    None),
    "kong":           TechRecord("Kong",            "gateway","api-gw",       "Kong",       None, "commercial"),
    "apigee":         TechRecord("Apigee",          "gateway","api-gw",       "Google",     None, "managed"),
    "zuul":           TechRecord("Netflix Zuul",    "gateway","api-gw",       "Netflix",    None),
    "traefik":        TechRecord("Traefik",         "gateway","api-gw",       "Traefik",    None),
    "3scale":         TechRecord("3scale",          "gateway","api-gw",       "Red Hat",    None, "commercial"),

    # ── Service / Cloud-Native Compute ────────────────────────────────────
    # 마이크로서비스·컨테이너 런타임·서버리스 → SERVICE 타입
    "lambda":           TechRecord("AWS Lambda",       "service","serverless",            "AWS",        None, "managed"),
    "aws lambda":       TechRecord("AWS Lambda",       "service","serverless",            "AWS",        None, "managed"),
    "sagemaker":        TechRecord("Amazon SageMaker", "service","ml-platform",           "AWS",        None, "managed"),
    "amazon sagemaker": TechRecord("Amazon SageMaker", "service","ml-platform",           "AWS",        None, "managed"),
    "azure machine learning":TechRecord("Azure ML",    "service","ml-platform",           "Microsoft",  None, "managed"),
    "azure ml":         TechRecord("Azure ML",         "service","ml-platform",           "Microsoft",  None, "managed"),
    "vertex ai":        TechRecord("Vertex AI",        "service","ml-platform",           "GCP",        None, "managed"),
    "databricks":       TechRecord("Databricks",       "service","data-platform",         "Databricks", None, "commercial"),
    "azure databricks": TechRecord("Azure Databricks", "service","data-platform",         "Databricks", None, "commercial"),
    "dataflow":         TechRecord("Google Dataflow",  "service","stream-processing",     "GCP",        None, "managed"),
    "glue":             TechRecord("AWS Glue",         "service","etl",                   "AWS",        None, "managed"),
    "aws glue":         TechRecord("AWS Glue",         "service","etl",                   "AWS",        None, "managed"),
    "data factory":     TechRecord("Azure Data Factory","service","etl",                  "Microsoft",  None, "managed"),
    "azure data factory":TechRecord("Azure Data Factory","service","etl",                 "Microsoft",  None, "managed"),
    "apache flink":     TechRecord("Apache Flink",     "service","stream-processing",     "Apache",     None),
    "flink":            TechRecord("Apache Flink",     "service","stream-processing",     "Apache",     None),
    "apache spark":     TechRecord("Apache Spark",     "service","batch-processing",      "Apache",     None),
    "spark":            TechRecord("Apache Spark",     "service","batch-processing",      "Apache",     None),
    "apache beam":      TechRecord("Apache Beam",      "service","stream-processing",     "Apache",     None),
    "mlflow":           TechRecord("MLflow",           "service","ml-platform",           "Databricks", None),
    "onnx":             TechRecord("ONNX",             "service","ml-runtime",            "Microsoft",  None),
    "tensorflow":       TechRecord("TensorFlow",       "service","ml-framework",          "Google",     None),
    "pytorch":          TechRecord("PyTorch",          "service","ml-framework",          "Meta",       None),
    "aws datasync":     TechRecord("AWS DataSync",     "service","data-transfer",         "AWS",        None, "managed"),
    "aws iot core":     TechRecord("AWS IoT Core",     "service","iot-platform",          "AWS",        None, "managed"),
    "looker":           TechRecord("Looker",           "service","bi-platform",           "Google",     None, "commercial"),
    "power bi":         TechRecord("Power BI",         "service","bi-platform",           "Microsoft",  None, "commercial"),
    "dbt":              TechRecord("dbt",              "service","data-transform",        "dbt Labs",   None),
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
    """대소문자·공백 무시 온톨로지 조회.

    매칭 우선순위:
    1. 정확한 소문자 매치
    2. 뒤에서부터 단어를 하나씩 제거한 접두어 매치 (버전 스트리핑)
       예) "Amazon ElastiCache Redis 7.2" → 순차적으로 단축하여
           "amazon elasticache redis" 매치
    """
    key = tech_name.lower().strip()
    if key in TECH_ONTOLOGY:
        return TECH_ONTOLOGY[key]

    # 단어를 뒤에서부터 한 개씩 제거하며 재시도 (최소 1단어)
    parts = key.split()
    for n in range(len(parts) - 1, 0, -1):
        shorter = " ".join(parts[:n])
        if shorter in TECH_ONTOLOGY:
            return TECH_ONTOLOGY[shorter]

    return None


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
