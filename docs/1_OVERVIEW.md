# ArchPilot — 개요 및 핵심 개념

**Version**: 0.2.3 | **Last Updated**: 2026-03-15

---

## 1. ArchPilot이란

ArchPilot은 레거시 시스템을 분석하고 현대화된 아키텍처를 자동 설계하는 CLI 도구입니다.

**핵심 가치:**

| 가치 | 설명 |
|------|------|
| **코드로서의 아키텍처** | 시스템 구성을 YAML로 버전 관리 |
| **AI 기반 설계** | 자연어 요구사항 → 구체적 아키텍처 자동 생성 |
| **그라운딩 기반 품질** | 레거시 사실 + 분석 결과를 LLM 입력으로 제공해 환각 방지 |
| **멀티 포맷 출력** | Mermaid · PNG · draw.io 동시 생성 |
| **발표 즉시 가능** | reveal.js 슬라이드 자동 생성 |

---

## 2. 전체 파이프라인

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ArchPilot 파이프라인                             │
│                                                                         │
│  입력                   Phase 1          Phase 2          출력           │
│  ──────                 ────────         ────────         ────          │
│                                                                         │
│  YAML/JSON ──┐                                                           │
│  draw.io   ──┤  ingest    analyze    modernize    serve                  │
│  텍스트    ──┤  ───────   ───────    ─────────    ─────                 │
│  채팅 입력 ──┘     │          │           │           │                 │
│                    ▼          ▼           ▼           ▼                 │
│              system.json  analysis.json  modern/   http://              │
│              legacy/      (6R결정        system.json localhost          │
│              diagram.*    시나리오       diagram.*  :8080               │
│                           품질점수)      plan.md    /slides             │
└─────────────────────────────────────────────────────────────────────────┘
```

### 최소 실행 흐름 (5개 명령)

```bash
# 1. 초기화 (최초 1회)
archpilot init

# 2. 레거시 시스템 입력
archpilot ingest examples/legacy_bank.yaml --format mermaid,drawio

# 3. AI 분석 (현대화 목표를 알려주면 더 정확한 component_decisions 생성)
archpilot analyze output/system.json -r "AWS 클라우드 전환, 마이크로서비스"

# 4. 현대화 설계 생성
archpilot modernize output/system.json -r "AWS 클라우드 전환, 마이크로서비스"

# 5. 발표 자료 서버 실행
archpilot serve output/ --open
```

---

## 3. 핵심 개념

### 3.1 SystemModel — 모든 것의 기반

ArchPilot의 모든 데이터는 `SystemModel` Pydantic 객체로 통일됩니다.

```
SystemModel
  ├── name, description, version, created_at
  ├── components: list[Component]
  │     ├── id           — snake_case 고유 식별자
  │     ├── type         — ComponentType enum (14종)
  │     ├── label        — 표시 이름
  │     ├── tech         — 기술 스택 목록
  │     ├── host         — HostType (on-premise | aws | gcp | azure | hybrid)
  │     ├── criticality  — 비즈니스 중요도 (high | medium | low)
  │     ├── lifecycle_status — 운영 상태 (active | deprecated | eol | sunset)
  │     ├── data_classification — 데이터 민감도
  │     ├── owner        — 담당팀
  │     ├── specs        — 자유 형식 사양 (cpu, memory, storage 등)
  │     └── metadata     — LLM 메타데이터 (is_new, removed, reason, strategy)
  └── connections: list[Connection]
        ├── from_id, to_id  — 컴포넌트 id 참조
        ├── protocol        — HTTP | JDBC | gRPC | Kafka 등
        ├── label           — 엣지 레이블
        ├── bidirectional   — 양방향 여부
        └── data_format     — JSON | XML | Protobuf 등
```

`system.json`은 이 모델의 직렬화 형태이며, 모든 CLI 명령어가 이 파일을 공유합니다.

---

### 3.2 ComponentType — 14가지 컴포넌트 유형

| 유형 | 설명 | 예시 |
|------|------|------|
| `server` | 애플리케이션 서버, 일반 서버 | Tomcat, Spring Boot, Node.js |
| `database` | 관계형/NoSQL DB | MySQL, Oracle, MongoDB |
| `cache` | 인메모리 캐시 | Redis, Memcached, Hazelcast |
| `queue` | 메시지 큐, 이벤트 버스 | Kafka, RabbitMQ, IBM MQ |
| `storage` | 파일 저장소, 오브젝트 스토리지 | S3, NFS, HDFS |
| `cdn` | 콘텐츠 전송 네트워크 | CloudFront, Akamai, Nginx (CDN) |
| `loadbalancer` | 로드 밸런서 | HAProxy, AWS ALB, Nginx |
| `gateway` | API 게이트웨이, VPN | AWS API GW, Kong, SSL-VPN |
| `service` | 마이크로서비스, 내부 서비스 | 인증 서비스, 알림 서비스 |
| `client` | 클라이언트, 프론트엔드 | React SPA, 모바일 앱, 브라우저 |
| `mainframe` | 메인프레임, COBOL 시스템 | IBM z/OS, CICS, JES2 |
| `esb` | 엔터프라이즈 서비스 버스 | Tibco BW, MuleSoft, IBM ESB |
| `security` | 보안 장비, IAM | HSM, WAF, Firewall, FIDO |
| `monitoring` | 모니터링, 로그 | Grafana, Datadog, CloudWatch |

> **자동 추론**: `tech` 배열에 기술명이 있으면 `type`을 생략해도 됩니다.
> `["MySQL 5.7"]` → `database`, `["Redis 7.0"]` → `cache`, `["Kafka 3.4"]` → `queue` 등.

---

### 3.3 HostType — 호스팅 환경

| 값 | 의미 |
|----|------|
| `on-premise` | 자체 데이터센터 (기본값) |
| `aws` | Amazon Web Services |
| `gcp` | Google Cloud Platform |
| `azure` | Microsoft Azure |
| `hybrid` | 복합 환경 |

Mermaid 다이어그램에서 host별 `subgraph`로 그룹핑됩니다.
NCP, 네이버 클라우드 등 특정 클라우드는 `metadata.provider`로 표기하고 `host`는 `aws` 사용 가능합니다.

---

### 3.4 ModernizationScenario — 3가지 현대화 방향

AI 분석 후 시스템 상태에 따라 가장 적합한 방향을 자동 권고합니다.

| 시나리오 | 적합한 상황 | 접근법 |
|---------|-----------|--------|
| **full_replace** (전체 교체) | EOL 50%+, 헬스 점수 ≤ 60 | 아키텍처 완전 재설계 |
| **partial** (일부 보존) | 일부 건강, 일부 교체 필요 | `component_decisions`의 6R 전략별 선택적 전환 |
| **additive** (신규 추가) | 기존 시스템 안정, 새 채널 필요 | 기존 유지 + 신규 ≤30% 추가 |

---

### 3.5 6R 전략 — 컴포넌트별 결정

AI가 각 컴포넌트에 할당하는 현대화 전략:

| 전략 | 의미 | 예시 |
|------|------|------|
| **keep** | 변경 없이 유지 | 최근 도입한 Redis, 안정적인 Nginx |
| **rehost** | Lift & Shift | On-premise 서버 → EC2 |
| **replatform** | 플랫폼 전환 (코드 최소 변경) | Tomcat → ECS |
| **refactor** | 서비스 분리·재설계 | 모놀리스 → 마이크로서비스 |
| **replace** | 관리형 서비스로 대체 | Oracle → Aurora PostgreSQL |
| **retire** | 폐기 | 미사용 레거시 리포트 시스템 |

분석 결과 `analysis.json`의 `component_decisions`에서 컴포넌트별로 확인할 수 있습니다.

---

### 3.6 LLM 그라운딩 — 품질의 핵심

ArchPilot은 두 가지 정보를 LLM에 제공해 환각(hallucination)을 방지합니다:

```
Grounding 1: Legacy SystemModel JSON
  → 실제 컴포넌트, 연결, 기술 스택 사실 제공
  → "존재하지 않는 컴포넌트를 만들지 마라"

Grounding 2: AnalysisResult (component_decisions 중심)
  → "이 컴포넌트는 replace해야 한다"는 6R 결정 제공
  → 시나리오 근거, 품질 점수, 보안 위험 제공
```

자세한 내용은 `docs/4_GROUNDING.md` 참조.

---

### 3.7 RMC — 재귀적 메타 인지

Web UI에서 현대화 설계는 4개의 LLM 패스로 이루어집니다:

```
Pass 1: 현대화 SystemModel 생성
  └→ grounding: [규모 어노테이션] + [시나리오] + [component_decisions] + [legacy JSON]

Pass 2: 마이그레이션 플랜 작성 (11개 섹션)
  └→ grounding: legacy + modern + analysis (전체)

Pass 3: 설계 해설 (Design Rationale) — 왜 이렇게 설계했는가
  └→ grounding: legacy + modern + component_decisions + pain_points

Pass 4: 마이그레이션 계획 자기평가 (Plan RMC)
  └→ grounding: 계획 텍스트 + 헬스 점수 + 주요 문제점
```

각 패스가 이전 패스의 출력을 검토·개선해 최종 품질을 높입니다.

---

## 4. 입력 방법 선택 가이드

| 상황 | 권장 입력 방법 |
|------|--------------|
| 이미 YAML/JSON 있음 | `archpilot ingest my-system.yaml` |
| draw.io 다이어그램 있음 | `archpilot ingest my-diagram.drawio` |
| 메모/텍스트 문서만 있음 | `archpilot ingest description.txt` |
| draw.io로 직접 그리고 싶음 | `archpilot drawio setup` → draw.io Desktop |
| 브라우저에서 모두 처리 | `archpilot serve output/` |
| 팀이 채팅으로 설명 | 웹 앱 AI 채팅 탭 |

---

## 5. 출력 파일 구조

```
output/
├── system.json              # 파싱된 SystemModel (모든 명령어의 입력·출력 공유)
├── legacy/
│   ├── diagram.mmd          # Mermaid DSL (GitHub/Notion 임베드 가능)
│   ├── diagram.png          # PNG (--format png 시, Graphviz 필요)
│   └── diagram.drawio       # draw.io XML (Desktop/Web에서 편집 가능)
├── analysis.json            # LLM 분석 결과 (시나리오·6R결정·품질 포함)
├── modern/
│   ├── system.json          # 현대화된 SystemModel
│   ├── diagram.mmd
│   ├── diagram.png
│   ├── diagram.drawio
│   ├── migration_plan.md    # 마이그레이션 로드맵 (11개 섹션)
│   └── design_rationale.json# 설계 해설 (Web UI에서만 생성)
└── slides/
    └── index.html           # reveal.js 정적 HTML (export 시)
```

---

## 6. 관련 문서

| 문서 | 내용 |
|------|------|
| [`SCHEMA.md`](./2_SCHEMA.md) | YAML 스키마 완전 가이드, 레거시 시스템 작성 방법 |
| [`GROUNDING.md`](./4_GROUNDING.md) | LLM 지식·그라운딩 체계 상세 |
| [`DRAWIO.md`](./5_DRAWIO.md) | draw.io 통합 완전 가이드 |
| [`USER_GUIDE.md`](./3_USER_GUIDE.md) | 설치부터 발표까지 단계별 워크플로우 |
| [`ARCHITECTURE.md`](./6_ARCHITECTURE.md) | 내부 아키텍처 (개발자용) |
| [`SPEC.md`](./7_SPEC.md) | 기능 명세 |
