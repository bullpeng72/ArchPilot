# ArchPilot

![version](https://img.shields.io/badge/version-0.2.4-blue)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

Legacy 시스템 구성을 다이어그램으로 코드화하고, AI 기반으로 현대화된 아키텍처를 설계·시각화하는 CLI 도구.

## 설치

```bash
pip install archpilot
```

## 빠른 시작

```bash
# 1. 초기화 (.env 생성 — OpenAI API Key 입력)
archpilot init

# 2. 레거시 시스템 다이어그램화
archpilot ingest examples/legacy_ecommerce.yaml

# 3. AI 분석
archpilot analyze output/system.json

# 4. 현대화 설계
archpilot modernize output/system.json -r "AWS 마이크로서비스, Kubernetes, Redis"

# 5. 인터랙티브 UI + 발표 자료 서버
archpilot serve output/
```

## draw.io Desktop 통합

draw.io에서 직접 아키텍처를 그리고 ArchPilot으로 분석할 수 있습니다.

```bash
# ArchPilot 컴포넌트 라이브러리를 draw.io Desktop에 설치
archpilot drawio setup

# draw.io Desktop으로 다이어그램 열기 + 변경 자동 감지
archpilot drawio edit --output output/

# draw.io 파일 변경 감시 (저장 시 자동 반영)
archpilot drawio watch output/legacy/diagram.drawio
```

**복잡한 시스템:** draw.io는 시스템 토폴로지(구조·연결·호스트)를 빠르게 그리는 데 최적입니다. `criticality`, `lifecycle_status`, `specs`, `owner` 등 엔터프라이즈 메타데이터는 `archpilot ingest` 후 생성된 `output/system.json`을 직접 편집해 보완할 수 있습니다. 자세한 내용은 [docs/5_DRAWIO.md §10.5](./docs/5_DRAWIO.md#105-복잡한-시스템--drawio--systemjson-직접-편집-워크플로우)를 참조하세요.

## 전체 CLI 명령어

```
archpilot init                        .env 초기화 마법사
archpilot ingest <file>               레거시 시스템 파일 주입 (YAML/JSON/텍스트)
archpilot analyze <system.json>       LLM 분석 보고서 생성
archpilot modernize <system.json>     LLM 현대화 설계 생성
archpilot serve <output_dir>          인터랙티브 UI 서버 실행
archpilot export [output_dir]         발표 슬라이드 → 정적 HTML 내보내기 (dist/)
archpilot drawio setup                draw.io Desktop 라이브러리 설치
archpilot drawio edit                 draw.io Desktop으로 편집
archpilot drawio watch <file>         파일 변경 자동 감시
archpilot drawio export [system.json]  system.json → draw.io XML 내보내기
```

## DX / AX 패턴 자동 그라운딩

ArchPilot은 시스템 분석 시 **27개 아키텍처 패턴**을 자동으로 매칭해 LLM 그라운딩 컨텍스트로 주입합니다. 컴포넌트 유형과 기술 스택 키워드를 기반으로 관련 패턴을 선별하므로, 범용적 권고가 아닌 **해당 시스템에 최적화된 현대화 방향**을 제시합니다.

**DX 패턴 (16개)** — 디지털 트랜스포메이션 아키텍처 전략:

| 카테고리 | 패턴 | 핵심 적용 상황 |
|---------|------|--------------|
| 점진적 전환 | Strangler Fig | 모놀리스·메인프레임 단계적 교체 |
| 서비스 분해 | 마이크로서비스 분해 | 모놀리스 → DDD Bounded Context 분리 |
| 비동기 통신 | 이벤트 기반 아키텍처 (EDA) | 동기 REST → Kafka/Kinesis 이벤트 스트림 |
| 데이터 패턴 | CQRS + 이벤트 소싱 | 금융·규제 환경의 감사 추적 요구 |
| API 레이어 | API Gateway / BFF | 다채널 클라이언트, 파트너 API 공개 |
| 서비스 운영 | 서비스 메시 (Istio) | 20개+ 마이크로서비스 Zero-Trust 보안 |
| 데이터 플랫폼 | 데이터 레이크하우스 | ETL 레거시 DW → 실시간+배치 통합 |
| 데이터 조직 | 데이터 메시 | 중앙 데이터 팀 병목 해소 |
| 보안 | 제로 트러스트 보안 | 내부망 신뢰 모델 제거, PCI·HIPAA 대응 |
| 관찰 가능성 | OpenTelemetry 통합 | 분산 추적·메트릭·로그 3기둥 |
| 데이터 분리 | 서비스별 독립 DB | 공유 DB 제거 후 Saga 패턴 |
| 배포 | 피처 플래그 | Canary/Blue-Green 점진적 롤아웃 |
| 트랜잭션 | Saga 패턴 | 분산 마이크로서비스 트랜잭션 일관성 |
| 자동화 | CI/CD / DevOps | 수동 배포 → 일 수회 자동 배포 |
| 인프라 | 코드형 인프라 (IaC) | Terraform/Pulumi 클라우드 전환 |
| 성능 | Cache-Aside 패턴 | DB 읽기 부하 절감, 세션 외부화 |

**AX 패턴 (11개)** — AI/ML 트랜스포메이션 전략:

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

## 8대 아키텍처 관점 분석

분석 완료 후 **8개 전문가 관점**에서 교차 검증합니다. 각 관점은 독립적인 LLM 패스로 평가되며, 관점 간 충돌과 합의 사항을 자동으로 도출합니다.

| 관점 | 평가 초점 |
|------|---------|
| 🔒 **보안 (Security)** | 취약점·인증·암호화·컴플라이언스 갭 |
| ⚡ **성능 (Performance)** | 응답 지연·처리량·병목·캐싱 전략 |
| 📈 **확장성 (Scalability)** | 수평/수직 확장·트래픽 급증 대응 |
| 💰 **비용 (Cost)** | 라이선스·운영비·클라우드 비용 최적화 |
| 🔧 **유지보수성 (Maintainability)** | 기술 부채·코드 복잡도·팀 역량 |
| 📋 **거버넌스 (Governance)** | 규제 준수·감사·데이터 주권·GDPR |
| 🔗 **통합 (Integration)** | 외부 시스템 연동·API 호환성·레거시 인터페이스 |
| 🛡️ **복원력 (Resilience)** | 장애 격리·Circuit Breaker·DR·가용성 |

8개 관점의 분석 결과는 `consensus_summary`(합의 결론)와 `priority_actions`(우선 조치)로 통합됩니다.

## 팀 협업

ArchPilot은 **아키텍트·개발팀·경영진이 같은 산출물을 바탕으로 협업**할 수 있도록 설계되었습니다.

| 역할 | 활용 방법 |
|------|---------|
| **아키텍트** | draw.io로 시스템 토폴로지 설계 → ArchPilot으로 AI 분석 |
| **개발팀** | `system.json` + `migration_plan.md`를 Git에서 공유·버전 관리 |
| **경영진** | `archpilot serve`로 인터랙티브 UI 공유, `archpilot export`로 발표 슬라이드 |
| **전체 팀** | 웹 UI(`archpilot serve`)에서 브라우저로 공동 검토 |

```bash
# 팀 공유 워크플로우 예시
archpilot serve output/ --host 0.0.0.0 --port 8080  # 팀 내부 네트워크 공유
archpilot export output/                              # 경영진 발표용 정적 HTML
```

## 요구사항

- Python 3.11+
- OpenAI API Key
- Graphviz (PNG 출력 시)
- draw.io Desktop (drawio 통합 기능 사용 시)

## 변경 이력

### v0.2.4 (2026-03-15)

- **부분 수정(Patch) 모드**: 현대화 결과에 `feedback`을 입력하면 기존 아키텍처 기반으로 최소 수정만 적용. 분석의 keep/rehost 결정과 design_philosophy를 패치 LLM에 자동 주입해 설계 일관성 유지
- **시스템 모델 다운로드**: Web UI에서 현대화/레거시 모델을 YAML·JSON·draw.io 형식으로 직접 다운로드 (`/api/download/{step}?fmt=yaml|json|drawio`)
- 데이터 흐름 개선: 압축 시 strategy/reason 보존, multi_perspective 요약 보존
- busy() 컨텍스트 매니저: 스트리밍 중 ingest 충돌 방지 (HTTP 409)
- draw.io ingest에 tech_ontology 보강 적용
- dropped connections / missing components warning SSE 방출
- DT 패턴 4개 + AI 패턴 3개 신규 추가 (총 27개) — 총 313개 테스트 통과

### v0.2.3 (2026-03-15)

- 우측 360px 아코디언 리포트 패널로 UI 전면 개편 (Progressive Reveal, 드래그 리사이즈)
- UI 라우터 분리: `ui/routers/` 하위 ingest/analyze/modernize 독립 파일
- defusedxml XXE/DTD 보안 패치 (`drawio_parser`)
- 신규 테스트 103개 추가 (mingrammer, drawio_config, ui_server, llm_utils, modernizer) — 총 181개 통과

### v0.2.2 (2026-03-14)

- 시나리오 기반 현대화: full_replace / partial / additive 3종 전략 선택
- 컴포넌트별 6R 전략 결정 (Keep/Rehost/Replatform/Refactor/Replace/Retire)
- 5차원 아키텍처 품질 점수 (성능·확장성·비용·보안·운영성)
- `analyze_stream` / 마이그레이션 플랜 `max_tokens` 누락 버그 수정
- 세션 `reset_modernization()` 중앙화로 시나리오 초기화 누락 버그 수정

### v0.2.1 (2026-03-13)

- 실행 위치 독립성 개선: 전역 설정 `~/.archpilot/config.env` 도입
- `archpilot init`이 어느 디렉토리에서든 동일하게 동작
- 모든 `--output` 옵션이 `settings.output_dir` (절대 경로) 기준으로 동작

### v0.2.0 (2026-03-13)

- draw.io XML → SystemModel 역방향 파서 (`drawio_parser`)
- draw.io Desktop LevelDB 설정 자동 주입 (`drawio_config`)
- Flask → FastAPI + SSE 스트리밍 전환
- `archpilot drawio export` 커맨드 추가
- TechOntology — 70+ 기술 스택 자동 타입 추론
- PyPI 배포용 메타데이터 완성
