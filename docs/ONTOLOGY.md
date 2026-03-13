# ArchPilot — 입력 표준화 및 기술 온톨로지

버전: 0.2.0
최종 수정: 2026-03-13

---

## 개요

ArchPilot은 5가지 이상의 서로 다른 입력 방식을 지원합니다. 입력 형태가 달라도 AI(LLM)는 항상 동일한 구조화된 데이터(`SystemModel`)를 전달받습니다. 이를 가능하게 하는 핵심 메커니즘이 **표준화 파이프라인**이며, 기술 온톨로지(`TechOntology`)는 그 중심에 있습니다.

```
YAML 파일
JSON 파일          ─────┐
자연어 텍스트             │
draw.io Desktop   ────────▶  [파서 레이어]  ──▶  SystemModel  ──▶  LLM
draw.io Web            │
인터랙티브 채팅       ─────┘
```

---

## 1. SystemModel — 공통 표현 구조

모든 입력은 최종적으로 `SystemModel`로 변환됩니다. 이 모델이 AI가 다루는 유일한 데이터 형식입니다.

```python
class SystemModel(BaseModel):
    name: str                        # 시스템 이름
    description: str                 # 시스템 설명
    components: list[Component]      # 컴포넌트 목록
    connections: list[Connection]    # 연결 목록
    metadata: dict[str, Any]         # 도메인·스케일·컴플라이언스 등 추가 정보
```

```python
class Component(BaseModel):
    id: str                          # 시스템 내 고유 snake_case 식별자
    type: ComponentType              # server|database|cache|queue|... (11종)
    label: str                       # 사람이 읽기 쉬운 이름
    tech: list[str]                  # 기술 스택 목록 (["MySQL 5.7", "Java 11"])
    host: HostType                   # on-premise|aws|gcp|azure|hybrid
    specs: dict[str, Any]            # 스펙 정보 (CPU, 메모리 등)
    metadata: dict[str, Any]         # 벤더, 카테고리, EOL, criticality 등
```

```python
class Connection(BaseModel):
    from_id: str                     # 출발 컴포넌트 ID
    to_id: str                       # 도착 컴포넌트 ID
    protocol: str                    # HTTP|TCP|JDBC|gRPC|AMQP 등
    label: str                       # 연결 설명
    bidirectional: bool              # 양방향 여부
```

### ComponentType 열거형 (11종)

| 값 | 의미 | 예시 |
|---|---|---|
| `server` | 웹/앱 서버 | IIS, Tomcat, Nginx |
| `database` | 데이터베이스 | Oracle, MySQL, PostgreSQL |
| `cache` | 캐시 | Redis, Memcached, Ehcache |
| `queue` | 메시지 큐/브로커 | Kafka, RabbitMQ, IBM MQ |
| `storage` | 파일/오브젝트 스토리지 | S3, HDFS, NFS |
| `cdn` | CDN | CloudFront, Akamai, Cloudflare |
| `loadbalancer` | 로드밸런서 | ELB, HAProxy, F5 BIG-IP |
| `gateway` | API 게이트웨이 | Kong, API Gateway, Zuul |
| `service` | 마이크로서비스 | 도메인별 서비스 단위 |
| `client` | 클라이언트 | React SPA, Flutter 앱 |
| `unknown` | 미분류 | 불명확한 컴포넌트 |

### HostType 열거형 (5종)

| 값 | 의미 |
|---|---|
| `on-premise` | 자체 데이터센터 |
| `aws` | Amazon Web Services |
| `gcp` | Google Cloud Platform |
| `azure` | Microsoft Azure |
| `hybrid` | 혼합 환경 |

---

## 2. 기술 온톨로지 (TechOntology)

`core/tech_ontology.py`의 `TECH_ONTOLOGY` 테이블은 기술 키워드를 정규화된 메타데이터로 변환합니다.

### TechRecord 구조

```python
@dataclass(frozen=True)
class TechRecord:
    canonical: str          # 정규화된 공식 기술명 (예: "MySQL 5.7")
    component_type: str     # ComponentType 값
    category: str           # 세부 분류 (rdbms, nosql-doc, web-server 등)
    vendor: str             # 공식 벤더명
    eol_year: Optional[int] # EOL 연도 (None = 현재 지원 중)
```

### 온톨로지 테이블 범위 (v0.2.0 기준, 총 70+ 엔트리)

| 카테고리 | 포함 기술 |
|---|---|
| Web/App 서버 | IIS 6/7/8.5, Apache 2.2, Nginx, Tomcat 6/7, JBoss 4/5, WildFly, WebLogic, WebSphere |
| RDBMS | Oracle 9i/10g/11g/12c, MySQL 5.5/5.7, PostgreSQL, SQL Server, IBM DB2, Sybase |
| NoSQL | MongoDB, Cassandra, DynamoDB, HBase, CouchDB |
| 캐시 | Redis, Memcached, Ehcache, Hazelcast |
| 메시지 큐 | Kafka, RabbitMQ, ActiveMQ 5, IBM MQ, SQS, Azure Service Bus, Google Pub/Sub |
| 스토리지 | S3, GCS, Azure Blob, HDFS, NFS |
| CDN | CloudFront, Akamai, Fastly, Cloudflare |
| 로드밸런서 | ELB, ALB, HAProxy, F5 BIG-IP |
| API 게이트웨이 | API Gateway, Kong, Apigee, Zuul, Traefik |
| 클라이언트 | React, Vue.js, Angular, Flutter, React Native |

### enrich_component() 동작

```python
def enrich_component(comp: dict) -> dict:
    """tech[] 배열을 조회해 type·vintage·vendor·category를 자동 보완.
    기존 값이 있으면 절대 덮어쓰지 않음 (보완만).
    """
```

**처리 순서:**

1. `tech` 배열의 각 항목을 소문자로 정규화해 `TECH_ONTOLOGY` 조회
2. `type`이 미지정(`None`, `"unknown"`, `""`)이면 → 첫 번째 매치의 `component_type`으로 설정
3. `vintage`가 미지정이고 EOL 정보가 있으면 → `min(eol_years) - 7`로 보수적 추정
4. `metadata.vendor`, `metadata.category`가 비어있으면 → 온톨로지 값으로 채움

**예시:**

```python
# 입력 (draw.io 셀 파싱 결과)
comp = {
    "id":    "db_primary",
    "type":  "unknown",
    "label": "Primary DB",
    "tech":  ["oracle 11g"],
    "host":  "on-premise",
}

# enrich_component 처리 후
comp = {
    "id":    "db_primary",
    "type":  "database",          # TechRecord.component_type 추론
    "label": "Primary DB",
    "tech":  ["oracle 11g"],
    "host":  "on-premise",
    "metadata": {
        "vendor":   "Oracle",     # TechRecord.vendor
        "category": "rdbms",      # TechRecord.category
        # vintage: 2010년경 (EOL 2020 - 7 = 2013, 실제론 11g 출시 2007)
    },
}
```

---

## 3. 입력별 표준화 파이프라인

### 3.1 YAML / JSON 파일

```
사용자 파일 (YAML/JSON)
  ↓ SystemParser.from_file()
  ↓ _parse_yaml() / _parse_json()
  ↓ _dict_to_model()
    ├── 필드 누락 시 기본값 적용
    ├── ComponentType / HostType enum 변환 (문자열 → Enum)
    └── enrich_component() 호출 (tech 배열 기반 보완)
  ↓ SystemModel ✅
```

**YAML 입력 예시:**

```yaml
name: 레거시 이커머스 시스템
components:
  - id: web_server
    label: 웹 서버
    tech: [iis 8.5]
    host: on-premise
    # type 미지정 → "server" 자동 추론
```

**변환 결과 (system.json):**

```json
{
  "id": "web_server",
  "type": "server",
  "label": "웹 서버",
  "tech": ["iis 8.5"],
  "host": "on-premise",
  "metadata": {
    "vendor": "Microsoft",
    "category": "web-server"
  }
}
```

---

### 3.2 draw.io XML (Desktop / Web 공통)

draw.io Desktop에서 저장하거나 Web(diagrams.net)에서 내보낸 XML을 모두 처리합니다.

```
.drawio XML 파일
  ↓ drawio_parser.parse_drawio_xml()
  │
  ├── 1단계: swimlane 셀 → HostType 매핑
  │     swimlane label "AWS Cloud" → HostType.AWS
  │     swimlane label "on-premise" → HostType.ON_PREMISE
  │     DrawioRenderer 생성 ID "group_aws" → HostType.AWS (정확도 우선)
  │
  ├── 2단계: vertex 셀 → Component
  │     mxCell.style → _style_to_type() → ComponentType
  │     mxCell.value → _parse_value() → (label, tech[])
  │     parent ID → swimlane_host 조회 → HostType
  │     enrich_component() → type·vendor·category 보완
  │
  └── 3단계: edge 셀 → Connection
        source/target → id_map 조회 → from_id/to_id
        mxCell.value → protocol (없으면 "HTTP" 기본값)

  ↓ SystemModel ✅
```

#### mxCell style → ComponentType 매핑 규칙

draw.io의 `style` 속성은 세미콜론으로 구분된 키-값 문자열입니다. `_style_to_type()`은 이 문자열에서 패턴을 탐지해 타입을 추론합니다.

| style 패턴 | ComponentType | 매핑 근거 |
|---|---|---|
| `disk_storage` | DATABASE | ArchPilot 기본 DB 심볼 |
| `cylinder` | DATABASE | 국제 표준 DB 심볼 |
| `flowchart.database` | DATABASE | Flowchart DB 심볼 |
| `aws4.aurora`, `aws4.rds` | DATABASE | AWS 관리형 DB |
| `flowchart.stored_data` | STORAGE | 저장소 심볼 |
| `aws4.s3`, `aws4.glacier` | STORAGE | AWS S3/Glacier |
| `flowchart.terminator` | CLIENT | 단말 심볼 |
| `cisco.computers` | CLIENT | PC/단말 심볼 |
| `flowchart.delay`, `bpmn` | QUEUE | 지연/이벤트 심볼 |
| `aws4.sqs`, `aws4.mq` | QUEUE | AWS 메시지 큐 |
| `aws4.elasticache`, `aws4.redis` | CACHE | AWS 캐시 서비스 |
| `aws4.cloudfront` | CDN | AWS CDN |
| `aws4.api_gateway` | GATEWAY | AWS API Gateway |
| `rhombus` | LOADBALANCER | 다이아몬드 LB 심볼 |
| `aws4.elb`, `aws4.alb` | LOADBALANCER | AWS LB |
| `ellipse` + `#fff2cc` | CACHE | ArchPilot 캐시 색상 |
| `ellipse` + `#d5e8d4` | CDN | ArchPilot CDN 색상 |
| `arcsize=50` 또는 보라색(`e1d5e7`) | GATEWAY | ArchPilot 게이트웨이 색상 |
| `#d5e8d4`/`82b366` | SERVICE | ArchPilot 서비스 색상 |
| `#dae8fc`/`6c8ebf` | SERVER | ArchPilot 서버 색상 (기본값) |

#### mxCell value → label + tech[] 파싱

DrawioRenderer가 생성한 셀의 `value`는 `"레이블\ntech1\ntech2"` 형식입니다.
diagrams.net에서 직접 편집한 HTML 형식도 처리합니다.

```
"주문 DB\nOracle 11g\nRAC"
         ↓ _parse_value()
label = "주문 DB"
tech  = ["Oracle 11g", "RAC"]

"<b>주문 DB</b><br>Oracle 11g"  (diagrams.net HTML)
         ↓ _strip_html() + _parse_value()
label = "주문 DB"
tech  = ["Oracle 11g"]
```

---

### 3.3 자연어 텍스트 (LLM 파서)

```
사용자 텍스트 설명
  ↓ archpilot ingest --text 또는 /api/chat/ingest/stream
  ↓ LLMParser.from_text()
  ↓ PARSE_SYSTEM_PROMPT + 사용자 텍스트 → GPT-4o
  │
  │  프롬프트 추론 규칙 (LLM이 적용):
  │  ├── host 추론: AWS 서비스명 → "aws", GCP 서비스명 → "gcp" 등
  │  ├── domain 추론: 뱅킹 키워드 → "banking", 물류 키워드 → "logistics"
  │  ├── vintage 추론: "Java EE 6" → ~2013, "Oracle 11g" → ~2010
  │  ├── criticality: 결제/인증/핵심DB → "high", 모니터링/로깅 → "low"
  │  └── compliance: 뱅킹 → PCI-DSS, 의료 → HIPAA (불확실하면 생략)
  │
  ↓ JSON 응답 → _dict_to_model()
  ↓ enrich_component() 보완
  ↓ SystemModel ✅
```

**예시 자연어 입력:**

```
우리 시스템은 IIS 8.5로 구동되는 ASP.NET 웹 앱이고,
Oracle 11g 데이터베이스에 JDBC로 연결됩니다.
Redis를 세션 캐시로 쓰고 있고 모두 온프레미스입니다.
```

**LLM이 생성하는 JSON:**

```json
{
  "name": "ASP.NET 레거시 시스템",
  "components": [
    { "id": "web_app", "type": "server", "label": "웹 앱 서버",
      "tech": ["IIS 8.5", "ASP.NET"], "host": "on-premise" },
    { "id": "oracle_db", "type": "database", "label": "Oracle DB",
      "tech": ["Oracle 11g"], "host": "on-premise", "criticality": "high" },
    { "id": "redis_cache", "type": "cache", "label": "Redis 세션 캐시",
      "tech": ["Redis"], "host": "on-premise" }
  ],
  "connections": [
    { "from": "web_app", "to": "oracle_db", "protocol": "JDBC" },
    { "from": "web_app", "to": "redis_cache", "protocol": "TCP" }
  ]
}
```

---

### 3.4 인터랙티브 채팅 (Chat Ingest)

웹 앱(`/api/chat/ingest/stream`)을 통한 대화형 시스템 입력입니다.

```
사용자가 채팅 메시지 입력
  ↓ CHAT_INGEST_SYSTEM_PROMPT 적용
  │
  │  AI가 대화로 수집하는 정보:
  │  ├── 시스템 이름 및 비즈니스 도메인
  │  ├── 컴포넌트 타입과 주요 기술
  │  ├── 호스팅 환경 (온프레미스/클라우드)
  │  ├── 시스템 구축 연도 (vintage)
  │  ├── 알려진 장애/문제점 (known_issues)
  │  ├── 규제 요건 (compliance)
  │  └── 시스템 규모 (DAU, TPS)
  │
  │  충분한 정보가 모이면 → JSON 자동 출력 ({"__system__": true, ...})
  │  정보 부족 시 → 한국어로 추가 질문
  │
  ↓ __system__ 신호 감지 → _dict_to_model()
  ↓ enrich_component() 보완
  ↓ SystemModel + 세션 저장 ✅
```

---

### 3.5 draw.io Web (diagrams.net) 에서 직접 붙여넣기

draw.io Web에서 Extras > Edit Diagram으로 XML을 복사해 웹 앱에 붙여넣는 방식입니다.

```
diagrams.net XML (클립보드 또는 파일)
  ↓ POST /api/ingest/drawio
  ↓ parse_drawio_xml()  (동일한 파서 사용)
  ↓ SystemModel ✅
```

draw.io Desktop과 Web(diagrams.net)은 동일한 mxGraph XML 포맷을 사용하므로 **단일 파서가 양쪽을 모두 처리**합니다.

---

## 4. 표준화 계층 요약

```
┌─────────────────────────────────────────────────────────────────┐
│                      입력 다양성                                   │
│                                                                 │
│  YAML  JSON  .drawio  자연어 텍스트  채팅  draw.io Web XML          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    파서 레이어 (변환)                               │
│                                                                 │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │ SystemParser │  │  DrawioParser    │  │  LLMParser       │   │
│  │ (YAML/JSON)  │  │ (mxGraph XML)    │  │  (자연어/채팅)      │   │
│  └──────┬───────┘  └───────┬──────────┘  └────────┬─────────┘   │
│         │                  │                       │            │
└─────────┼──────────────────┼───────────────────────┼────────────┘
          │                  │                       │
┌─────────▼──────────────────▼───────────────────────▼────────────┐
│                  enrich_component()                             │
│                 [TechOntology 적용]                              │
│                                                                 │
│      type 추론  │  vintage 추정  │  vendor 보완  │  category 분류    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                   SystemModel (단일 표현)                         │
│                                                                 │
│  모든 입력이 동일한 구조 → LLM에 일관된 컨텍스트 제공                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. LLM이 SystemModel을 활용하는 방식

### 5.1 분석 (analyze)

`analysis.json` 생성 시 LLM은 다음 메타데이터를 활용합니다:

| 필드 | LLM 활용 방식 |
|---|---|
| `metadata.domain` | 도메인별 규제·패턴 적용 (banking → PCI-DSS 언급) |
| `metadata.vintage` | EOL 심각도 산정 (오래될수록 가중치 증가) |
| `metadata.scale.peak_tps` | 병목 지점·확장성 한계 수치로 언급 |
| `metadata.compliance` | 위험 완화 방안에 반드시 반영 |
| `metadata.known_issues` | pain_points에 포함, 근본 원인 분석 |
| `Component.metadata.criticality` | "high" → 위험도 가중치 2배 적용 |
| `Component.tech` + `TechRecord.eol_year` | tech_debt 항목에 EOL/EOS 날짜 명시 |
| `Component.metadata.vendor` | 구체적 벤더명으로 라이선스·지원 비용 언급 |

### 5.2 현대화 설계 (modernize)

```
SystemModel (레거시)
  + AnalysisResult
  + 사용자 요구사항 (--requirements)
  ↓
MODERNIZE_SYSTEM_PROMPT

LLM이 컴포넌트별로 결정하는 전략:
  Rehost    — 코드 변경 없이 클라우드 이전 (IaaS 전환)
  Replatform — 최소 수정 플랫폼 전환 (앱서버 → 컨테이너)
  Refactor  — 서비스 분리·재설계 (모놀리스 → MSA)
  Replace   — 매니지드 서비스로 대체 (Oracle → Aurora)
  Retire    — 기능 폐기 (출력에 미포함)

각 Component.metadata.strategy, .reason에 근거 기록
  ↓
SystemModel (현대화) + migration_plan.md
```

### 5.3 표준화가 AI 품질에 미치는 효과

**표준화 없을 때 (예: 원시 YAML 전달):**
```
LLM: "type 필드가 없어 DATABASE인지 알 수 없음"
LLM: "Oracle 11g가 EOL인지 판단 불가"
LLM: "호스팅 환경을 추론해야 해 오류 발생 가능"
```

**표준화 후 (SystemModel + 온톨로지 보완):**
```
LLM: type="database", category="rdbms", vendor="Oracle",
     eol_year=2020 → "Oracle 11g R2, 2020년 EOS 완료, 보안 패치 중단" 정확히 서술
LLM: host="on-premise", criticality="high" → 우선 마이그레이션 대상 식별
LLM: compliance=["PCI-DSS"] → 모든 권고안에 규제 준수 조건 자동 반영
```

---

## 6. 온톨로지 확장 방법

새 기술을 온톨로지에 추가하려면 `core/tech_ontology.py`의 `TECH_ONTOLOGY` 딕셔너리에 엔트리를 추가합니다:

```python
TECH_ONTOLOGY: dict[str, TechRecord] = {
    # ... 기존 엔트리 ...

    # 신규 추가 예시
    "spring boot 2":  TechRecord("Spring Boot 2",  "server",   "app-framework", "VMware",  2025),
    "elasticsearch":  TechRecord("Elasticsearch",  "database", "nosql-search",  "Elastic", None),
    "clickhouse":     TechRecord("ClickHouse",     "database", "olap",          "ClickHouse", None),
}
```

**키 작성 규칙:**
- 소문자 + 공백 정규화 (`lookup()`이 `.lower().strip()` 적용)
- 버전 포함 엔트리는 "name version" 형식 (예: `"tomcat 7"`)
- 버전 없는 엔트리도 별도 추가해 버전 미지정 시에도 매칭

**`eol_year` 결정 기준:**
- 공식 벤더 EOL/EOS 발표일 기준 연도
- 아직 지원 중이면 `None`
- 불명확하면 `None` (보수적으로 처리)
