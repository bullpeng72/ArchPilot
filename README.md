# ArchPilot

![version](https://img.shields.io/badge/version-0.2.5-blue)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

Legacy 시스템을 AI로 심층 진단하고, 현대화된 아키텍처를 자동 설계·시각화하는 CLI 도구.

---

## ArchPilot이란

ArchPilot은 레거시 시스템 현대화 프로젝트에서 반복되는 세 가지 병목을 해소합니다:

| 병목 | 기존 방식 | ArchPilot |
|------|----------|-----------|
| **시스템 현황 파악** | 수작업 인터뷰·문서화 (수주~수개월) | YAML/draw.io 입력 → AI 심층 분석 (수분) |
| **현대화 설계** | 아키텍트 주관적 판단, 누락·환각 빈번 | 397개 기술 온톨로지 + 27개 패턴 그라운딩으로 구체적 설계 |
| **의사결정 공유** | PPT 반복 수정 | Web UI + reveal.js 슬라이드 자동 생성 |

**핵심 차별화 요소:**

- **3-Phase AI 분석**: 핵심 진단 → 8대 관점 교차 검증 → RMC 자기검토로 분석 품질 계층화
- **기술 온톨로지 397개**: 기술명만 입력해도 EOL·벤더·라이선스·criticality 자동 추론
- **LLM 그라운딩 아키텍처**: 레거시 사실 + 분석 결과를 4-계층으로 주입해 환각 방지
- **6R 컴포넌트 전략**: 모든 컴포넌트에 keep/rehost/replatform/refactor/replace/retire 결정
- **DX/AX 패턴 27개**: 시스템 특성에 맞는 디지털·AI 전환 패턴 자동 매칭
- **draw.io 완전 통합**: Desktop 편집 → 파일 감시 → 자동 반영 워크플로우

---

## 전체 파이프라인

```
입력                  Phase 1          Phase 2          출력
────                  ───────          ───────          ────

YAML/JSON ──┐
draw.io   ──┤  ingest    analyze    modernize    serve / export
텍스트    ──┤  ───────   ───────    ─────────    ─────────────
채팅 입력 ──┘     │          │           │              │
            온톨로지   6R 결정      현대화 설계    Web UI +
            자동 보강  시나리오     마이그레이션   Slides
                       품질점수     플랜
```

---

## 설치

```bash
pip install archpilot
```

## 빠른 시작

```bash
# 1. 초기화 (.env 생성 — OpenAI API Key 입력)
archpilot init

# 2. 레거시 시스템 입력
archpilot ingest examples/legacy_ecommerce.yaml

# 3. AI 분석 (현대화 목표 포함 권장)
archpilot analyze output/system.json \
  -r "AWS EKS 전환, Oracle 라이선스 제거, 제로 다운타임 배포"

# 4. 현대화 설계
archpilot modernize output/system.json \
  -r "AWS EKS 전환, Aurora PostgreSQL, Redis 캐싱 도입"

# 5. Web UI + 발표 슬라이드 서버
archpilot serve output/
```

---

## 핵심 기능

### 1. AI 분석 리포트 — 3-Phase 심층 진단

단순한 LLM 원시 출력이 아닌 **3단계 품질 계층화** 분석을 제공합니다.

#### Phase 1 — 핵심 분석 (AnalysisResult)

```
health_score: 42 / 100       ← 100점에서 EOL·SPOF·보안 갭 차감
legacy_quality: 5차원 점수   ← 성능·확장성·비용·보안·운영성
recommended_scenario: full_replace  ← EOL 비율·health_score 기반 자동 권고
```

모든 컴포넌트에 대해 **6R 전략**을 결정합니다:

| 전략 | 의미 | 적용 기준 |
|------|------|-----------|
| **keep** | 변경 없이 유지 | 최신 기술, 안정 운영 중 |
| **rehost** | Lift & Shift | 클라우드 이전, 기능 변경 불필요 |
| **replatform** | 최소 수정 전환 | 앱서버 → Docker/컨테이너 |
| **refactor** | 재설계 | 과도한 결합·순환 의존·SPOF |
| **replace** | 대체 | EOL 기술 → 관리형 서비스 |
| **retire** | 폐기 | 고립·중복·비즈니스 가치 없음 |

각 결정에 `rationale`(근거), `risks`(위험), `dependencies`(처리 순서)가 함께 제공됩니다.

또한 연결 토폴로지를 분석해 **허브 컴포넌트(SPOF), 순환 의존성, 레거시 프로토콜, 고립 컴포넌트**를 자동으로 탐지합니다.

#### Phase 2 — 8대 관점 교차 검증 (Web UI)

8명의 전문가 관점에서 독립적으로 분석하고, 합의 결론과 우선 조치를 도출합니다:

| 관점 | 검토 초점 |
|------|----------|
| **SA** 솔루션 아키텍처 | 비즈니스 목표·ROI·시나리오 정합성 |
| **AA** 애플리케이션 | 서비스 분해·결합도·API 설계 |
| **DA** 데이터 | 데이터 소유권·사일로·마이그레이션 경로 |
| **IA** 인프라 | SPOF·고가용성·클라우드 네이티브 |
| **TA** 기술 | EOL/EOS·DevSecOps·기술 표준화 |
| **SWA** 소프트웨어 | SOLID·헥사고날·테스트 가능성 |
| **DBA** 데이터베이스 | DB 유형 적합성·폴리글랏 퍼시스턴스 |
| **QA** 품질 | 관찰 가능성·SLO·비기능 요구사항 |

관점 간 충돌(예: 보안 강화 vs 성능 오버헤드)은 `conflict_areas`로 명시됩니다.

#### Phase 3 — RMC 자기검토 (Web UI)

LLM이 자신의 분석을 재귀적으로 검토합니다:

```json
{
  "coverage_score": 72,
  "assumptions": ["COBOL 로직 복잡도를 중간으로 가정"],
  "blind_spots":  ["야간 배치 처리 볼륨 데이터 없음"],
  "verification_questions": [
    "Oracle RAC의 피크 TPS와 평균 응답 시간은?",
    "COBOL 프로그램 총 LOC는?"
  ],
  "confidence_level": "medium"
}
```

`verification_questions`는 현장 확인 체크리스트로, `blind_spots`는 프로젝트 리스크 레지스터에 직접 활용할 수 있습니다.

> 분석 리포트 상세 가이드: [`docs/8_ANALYSIS_REPORT.md`](./docs/8_ANALYSIS_REPORT.md)

---

### 2. 기술 온톨로지 — 입력 자동 보강

**397개 기술 엔트리**로 구성된 내장 온톨로지가 LLM 호출 전에 입력 데이터를 자동으로 보강합니다.

```yaml
# 사용자 입력 (최소)
- id: oracle_primary
  label: Oracle 운영 DB
  tech: ["Oracle 11g"]

# 온톨로지 자동 보강 결과
- id: oracle_primary
  label: Oracle 운영 DB
  tech: ["Oracle 11g"]
  type: database           ← 자동 추론
  vintage: 2013            ← EOL - 7년 (보수적 추정)
  lifecycle_status: eol    ← EOL 2020 ≤ 현재 연도
  criticality: high        ← rdbms 카테고리 → 자동 추론
  metadata:
    vendor: Oracle
    category: rdbms
    license_type: commercial
```

기술명 → 속성 매핑은 "버전 스트리핑" 알고리즘으로 동작합니다. `"Amazon ElastiCache Redis 7.2"`처럼 상세 버전을 입력해도 `"amazon elasticache redis"` 엔트리에 자동 매칭됩니다.

온톨로지가 커버하는 주요 영역:

| 영역 | 대표 기술 | 엔트리 수 |
|------|----------|---------|
| 언어·런타임·프레임워크 | Java 8~21, Python 3.x, Spring Boot 2/3, FastAPI | ~33 |
| 웹·앱 서버 | IIS 6/7/8.5, Tomcat 6/7, WebLogic, WebSphere, JBoss | ~16 |
| RDBMS·메인프레임 DB | Oracle 9i~19c, MySQL 5.5~8, DB2, Sybase, IBM IMS, VSAM | ~19 |
| 클라우드 관리형 DB | Aurora, DynamoDB, Cosmos DB, BigQuery, Snowflake, Pinecone | ~32 |
| 메시지 큐·ESB | Kafka, IBM MQ, TIBCO, RabbitMQ, MuleSoft, BizTalk | ~33 |
| 메인프레임 | COBOL, CICS, JCL, RPG, AS/400, HP NonStop (z/OS) | ~9 |
| 보안 | HSM, Keycloak, Okta, WAF, RACF, OAuth 2.0, SAML, FIDO2 | ~26 |
| 모니터링·관찰 가능성 | Prometheus, Grafana, Datadog, CloudWatch, Jaeger, ELK | ~22 |
| 클라우드 네이티브·컨테이너 | EKS/GKE/AKS, Lambda, Fargate, Istio, Dapr, Kubernetes | ~20 |
| 데이터·AI 플랫폼 | Spark, Flink, SageMaker, Vertex AI, MLflow, dbt | ~18 |
| 특화 프로토콜 | HL7 FHIR, DICOM, OPC-UA, ISO 8583, PROFINET, MQTT | ~15 |

> 온톨로지 상세: [`docs/4_GROUNDING.md §13`](./docs/4_GROUNDING.md#13-기술-온톨로지--입력-자동-보강)

---

### 3. LLM 그라운딩 아키텍처 — 환각 방지

ArchPilot은 **이중 그라운딩**으로 LLM 환각을 방지합니다:

```
Grounding 1: Legacy SystemModel JSON
  ← 실제 컴포넌트·연결·엔터프라이즈 메타데이터

Grounding 2: AnalysisResult
  ← component_decisions (6R 결정) ← 가장 중요
  ← recommended_scenario + rationale
  ← pain_points, legacy_quality

↓ 4-계층으로 modernize LLM에 동시 주입

출력: 레거시와 1:1 대응하는 현대화 설계 (환각 없음)
```

그라운딩 없으면 34개 컴포넌트가 6개로 붕괴되는 "Large System Collapse" 문제가 발생합니다. ArchPilot은 `component_decisions`로 컴포넌트별 처리 지시를 명시하고, 컴포넌트 수 검증 + 자동 재시도로 이를 방지합니다.

> 그라운딩 아키텍처 상세: [`docs/4_GROUNDING.md`](./docs/4_GROUNDING.md)

---

### 4. DX / AX 패턴 27개 — 자동 매칭 그라운딩

시스템 특성(컴포넌트 유형·기술 스택 키워드)을 분석해 **관련 패턴만 선별**해 LLM 컨텍스트에 주입합니다. 범용 권고가 아닌, 해당 시스템에 최적화된 현대화 방향을 제시합니다.

**DX 패턴 16개** — 디지털 트랜스포메이션:

| 카테고리 | 패턴 | 핵심 적용 상황 |
|---------|------|--------------|
| 점진적 전환 | Strangler Fig | 모놀리스·메인프레임 단계적 교체 |
| 서비스 분해 | 마이크로서비스 분해 | 모놀리스 → DDD Bounded Context |
| 비동기 통신 | 이벤트 기반 아키텍처 | 동기 REST → Kafka/Kinesis |
| 데이터 패턴 | CQRS + 이벤트 소싱 | 금융·규제 환경의 감사 추적 |
| API 레이어 | API Gateway / BFF | 다채널 클라이언트, 파트너 API |
| 서비스 운영 | 서비스 메시 (Istio) | 20개+ MSA Zero-Trust 보안 |
| 데이터 플랫폼 | 데이터 레이크하우스 | ETL 레거시 DW → 실시간+배치 통합 |
| 데이터 조직 | 데이터 메시 | 중앙 데이터 팀 병목 해소 |
| 보안 | 제로 트러스트 | 내부망 신뢰 모델 제거, PCI·HIPAA |
| 관찰 가능성 | OpenTelemetry 통합 | 분산 추적·메트릭·로그 3기둥 |
| 데이터 분리 | 서비스별 독립 DB | 공유 DB 제거 + Saga 패턴 |
| 배포 | 피처 플래그 | Canary/Blue-Green 롤아웃 |
| 트랜잭션 | Saga 패턴 | 분산 MSA 트랜잭션 일관성 |
| 자동화 | CI/CD / DevOps | 수동 배포 → 일 수회 자동 배포 |
| 인프라 | 코드형 인프라 (IaC) | Terraform/Pulumi 클라우드 전환 |
| 성능 | Cache-Aside 패턴 | DB 읽기 부하 절감, 세션 외부화 |

**AX 패턴 11개** — AI/ML 트랜스포메이션:

| 패턴 | 핵심 적용 상황 |
|------|--------------|
| RAG (검색 증강 생성) | 기업 내부 문서 기반 AI 어시스턴트 |
| MLOps 파이프라인 | ML 모델 학습·배포·모니터링 자동화 |
| 피처 스토어 | Training-Serving Skew 제거, 피처 재사용 |
| AI 모델 게이트웨이 | 다중 LLM 비용·보안·라우팅 중앙화 |
| 시맨틱 캐시 | LLM API 비용 40~80% 절감 |
| 에이전틱 AI 플랫폼 | 복잡한 다단계 업무 자율 자동화 |
| Human-in-the-Loop | 고위험 AI 결정에 인간 검토 게이트 |
| AI 증강 레거시 | 교체 불가 레거시에 AI 레이어 추가 |
| LLM 가드레일 | 프롬프트 인젝션·PII 유출 방어 |
| LLM 파인튜닝 (PEFT) | 도메인 특화 분류·추출 성능 향상 |
| AI 관찰 가능성 | LLM 품질·비용·환각률 추적 |

---

### 5. draw.io 완전 통합

draw.io를 시스템 입력·편집·출력의 모든 단계에서 활용할 수 있습니다.

#### 입력 — 4가지 방법

**방법 1: CLI 직접 주입**
```bash
archpilot ingest my-architecture.drawio
```

**방법 2: diagrams.net (웹)**
```bash
# File → Export As → XML 저장 후
archpilot ingest ~/Downloads/my-diagram.drawio
```

**방법 3: Web UI 내장 편집기**
```bash
archpilot serve output/ --open
# 좌측 상단 🖊 편집 탭 → 내장 draw.io 에디터
```

**방법 4: draw.io Desktop 연동 (지속적 편집)**
```bash
archpilot drawio setup        # ArchPilot 팔레트 설치 (최초 1회)
archpilot drawio edit         # Desktop으로 편집 + 저장 시 자동 반영
archpilot drawio watch my.drawio  # 특정 파일 감시
```

#### 출력 — draw.io XML 생성

모든 현대화 설계 결과가 Mermaid / PNG / **draw.io XML** 3가지 포맷으로 동시 생성됩니다.

```bash
archpilot drawio export output/modern/system.json  # system.json → .drawio
```

draw.io Desktop에서는 **클라우드 호스트 환경별 Swimlane**으로 컴포넌트를 자동 그룹화합니다:

| 환경 | 색상 |
|------|------|
| On-Premise | 회색 (#E6E6E6) |
| AWS | 주황 (#FFE6CC) |
| GCP | 파랑 (#E8F0FE) |
| Azure | 하늘 (#CCE5F5) |
| Hybrid | 초록 (#d5e8d4) |

> 엔터프라이즈 메타데이터 보완: draw.io는 `criticality`, `lifecycle_status`, `data_classification`, `owner` 등을 저장할 수 없습니다. `archpilot ingest` 후 `output/system.json`을 편집해 보완하면 분석 품질이 향상됩니다. → [`docs/5_DRAWIO.md §10.5`](./docs/5_DRAWIO.md)

> draw.io 통합 완전 가이드: [`docs/5_DRAWIO.md`](./docs/5_DRAWIO.md)

---

## 전체 CLI 명령어

```
archpilot init                         .env 초기화 마법사 (OpenAI API Key 설정)
archpilot ingest <file>                레거시 시스템 입력 (YAML/JSON/텍스트/.drawio)
archpilot analyze <system.json>        AI 분석 리포트 생성 [-r 현대화 목표]
archpilot modernize <system.json>      AI 현대화 설계 생성 [-r 요구사항]
archpilot serve <output_dir>           Web UI + 발표 슬라이드 서버 실행
archpilot export [output_dir]          발표 슬라이드 → 정적 HTML (dist/)
archpilot drawio setup                 draw.io Desktop에 ArchPilot 팔레트 설치
archpilot drawio edit                  draw.io Desktop으로 편집 (저장 시 자동 반영)
archpilot drawio watch <file>          파일 변경 자동 감시·반영
archpilot drawio export [system.json]  system.json → draw.io XML 내보내기
```

---

## 팀 협업

ArchPilot은 **아키텍트·개발팀·경영진이 같은 산출물로 협업**할 수 있도록 설계되었습니다.

| 역할 | 활용 방법 |
|------|----------|
| **아키텍트** | draw.io로 토폴로지 설계 → ArchPilot AI 분석으로 깊이 추가 |
| **개발팀** | `system.json` + `migration_plan.md`를 Git에서 버전 관리 |
| **경영진** | `archpilot serve`로 인터랙티브 리포트 공유, `archpilot export`로 발표 슬라이드 |
| **전체 팀** | Web UI에서 분석 결과·현대화 설계를 브라우저로 공동 검토 |

```bash
archpilot serve output/ --host 0.0.0.0 --port 8080  # 팀 내부 네트워크 공유
archpilot export output/                              # 경영진 발표용 정적 HTML
```

---

## 문서

| 문서 | 내용 |
|------|------|
| [`docs/1_OVERVIEW.md`](./docs/1_OVERVIEW.md) | 개요, 핵심 개념, 전체 파이프라인 |
| [`docs/2_SCHEMA.md`](./docs/2_SCHEMA.md) | YAML/JSON 스키마 완전 가이드 |
| [`docs/3_USER_GUIDE.md`](./docs/3_USER_GUIDE.md) | 설치부터 발표까지 단계별 워크플로우 |
| [`docs/4_GROUNDING.md`](./docs/4_GROUNDING.md) | LLM 그라운딩 체계, DX/AX 패턴, 기술 온톨로지 |
| [`docs/5_DRAWIO.md`](./docs/5_DRAWIO.md) | draw.io 통합 완전 가이드 |
| [`docs/6_ARCHITECTURE.md`](./docs/6_ARCHITECTURE.md) | 내부 아키텍처 (개발자용) |
| [`docs/7_SPEC.md`](./docs/7_SPEC.md) | 기능 명세 |
| [`docs/8_ANALYSIS_REPORT.md`](./docs/8_ANALYSIS_REPORT.md) | 분석 리포트 이해 및 실무 활용 가이드 |

---

## 요구사항

- Python 3.11+
- OpenAI API Key
- Graphviz (PNG 출력 시)
- draw.io Desktop (drawio 통합 기능 사용 시)

---

## 변경 이력

### v0.2.5 (2026-03-16)

- **draw.io 클라우드 Swimlane 시각화**: AWS(주황)·GCP(파랑)·Azure(하늘)·On-Premise(회색)·Hybrid(초록) 색상으로 호스트 환경 구분
- **컴포넌트 라이브러리 확장**: draw.io Desktop 라이브러리 14개→20개 (Unknown 추가, Swimlane 컨테이너 5종 신규)
- **GCP·Azure·Kubernetes shape 인식**: drawio_parser에 43개 신규 패턴 추가 (GCP 16·Azure 18·K8s 7)
- **serve UI 컴포넌트 패널 현행화**: 10개→15개 + Swimlane 5개, STYLE_MAP 완전 동기화, Alpine.js x-show 버그 수정
- **분석 리포트 문서 신규**: `docs/8_ANALYSIS_REPORT.md` — 3-Phase 분석 구조, 실무 활용 가이드
- **온톨로지 문서 추가**: `docs/4_GROUNDING.md §13` — 397개 엔트리, enrich_component() 동작 상세
- 기술 부채 개선: `busy()` asyncio.Lock 교체, `collect_stream()` 중복 제거, `llm/prompts` 패키지 분리 — **391개** 테스트 통과

### v0.2.4 (2026-03-15)

- **부분 수정(Patch) 모드**: 현대화 결과에 `feedback`을 입력하면 기존 아키텍처 기반으로 최소 수정만 적용. 분석의 keep/rehost 결정과 design_philosophy를 패치 LLM에 자동 주입해 설계 일관성 유지
- **시스템 모델 다운로드**: Web UI에서 현대화/레거시 모델을 YAML·JSON·draw.io 형식으로 직접 다운로드
- 데이터 흐름 개선: 압축 시 strategy/reason 보존, multi_perspective 요약 보존
- `busy()` 컨텍스트 매니저: 스트리밍 중 ingest 충돌 방지 (HTTP 409)
- DT 패턴 4개 + AI 패턴 3개 신규 추가 (총 27개) — **313개** 테스트 통과

### v0.2.3 (2026-03-15)

- 우측 360px 아코디언 리포트 패널로 UI 전면 개편 (Progressive Reveal, 드래그 리사이즈)
- UI 라우터 분리: `ui/routers/` 하위 ingest/analyze/modernize 독립 파일
- 대형 시스템(20개+ 컴포넌트) Skeleton→Enrich 2-phase 자동 적용
- defusedxml XXE/DTD 보안 패치 (`drawio_parser`) — **181개** 테스트 통과

### v0.2.2 (2026-03-14)

- 시나리오 기반 현대화: full_replace / partial / additive 3종 전략 선택
- 컴포넌트별 6R 전략 결정 (Keep/Rehost/Replatform/Refactor/Replace/Retire)
- 5차원 아키텍처 품질 점수 (성능·확장성·비용·보안·운영성)

### v0.2.1 (2026-03-13)

- 실행 위치 독립성 개선: 전역 설정 `~/.archpilot/config.env` 도입
- `archpilot init`이 어느 디렉토리에서든 동일하게 동작

### v0.2.0 (2026-03-13)

- draw.io XML → SystemModel 역방향 파서 (`drawio_parser`)
- draw.io Desktop LevelDB 설정 자동 주입 (`drawio_config`)
- Flask → FastAPI + SSE 스트리밍 전환
- TechOntology — 기술 스택 자동 타입 추론
- PyPI 배포용 메타데이터 완성
