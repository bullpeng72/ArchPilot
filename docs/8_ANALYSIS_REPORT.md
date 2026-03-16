# ArchPilot — 분석 리포트 이해 가이드

> 분석 결과의 각 섹션이 무엇을 의미하고 실무에서 어떻게 활용하는가

**Version**: 0.2.5 | **Last Updated**: 2026-03-16

---

## 목차

1. [분석 리포트란](#1-분석-리포트란)
2. [분석 실행 방법](#2-분석-실행-방법)
3. [리포트 3-Phase 구조](#3-리포트-3-phase-구조)
4. [Phase 1 — 핵심 분석 (AnalysisResult)](#4-phase-1--핵심-분석-analysisresult)
   - [4.1 헬스 스코어](#41-헬스-스코어)
   - [4.2 레거시 5차원 품질 평가](#42-레거시-5차원-품질-평가)
   - [4.3 현대화 시나리오 권고](#43-현대화-시나리오-권고)
   - [4.4 컴포넌트별 6R 결정](#44-컴포넌트별-6r-결정)
   - [4.5 핵심 문제점 (pain_points)](#45-핵심-문제점-pain_points)
   - [4.6 기술 부채 (tech_debt)](#46-기술-부채-tech_debt)
   - [4.7 위험 영역 (risk_areas)](#47-위험-영역-risk_areas)
   - [4.8 현대화 기회 (modernization_opportunities)](#48-현대화-기회-modernization_opportunities)
   - [4.9 보안 취약점 (security_findings)](#49-보안-취약점-security_findings)
   - [4.10 컴플라이언스 갭 (compliance_gaps)](#410-컴플라이언스-갭-compliance_gaps)
5. [Phase 2 — 8대 관점 분석 (MultiPerspectiveAnalysis)](#5-phase-2--8대-관점-분석)
6. [Phase 3 — RMC 자기검토 (AnalysisRMC)](#6-phase-3--rmc-자기검토)
7. [실무 활용 가이드](#7-실무-활용-가이드)
   - [7.1 경영진 보고용 요약](#71-경영진-보고용-요약)
   - [7.2 기술팀 현대화 계획](#72-기술팀-현대화-계획)
   - [7.3 우선순위 결정 체계](#73-우선순위-결정-체계)
   - [7.4 현대화 피해야 할 함정](#74-현대화-피해야-할-함정)
8. [분석 품질 높이기](#8-분석-품질-높이기)

---

## 1. 분석 리포트란

`archpilot analyze` (CLI) 또는 Web UI의 **분석 실행** 버튼을 실행하면 LLM이 레거시 시스템을 심층 진단하고 구조화된 JSON 보고서를 생성합니다.

분석 리포트는 **단순한 기술 목록이 아닙니다.** 시스템 구조(컴포넌트·연결 토폴로지)와 엔터프라이즈 메타데이터(도메인·빈티지·규모·규제)를 종합해 아래 세 질문에 답합니다:

| 질문 | 리포트 섹션 |
|------|------------|
| **지금 얼마나 위험한가?** | health_score, risk_areas, security_findings |
| **무엇을 어떻게 바꿔야 하는가?** | component_decisions (6R), recommended_scenario |
| **얼마나 걸리고 어디서 시작해야 하는가?** | modernization_opportunities, estimated_effort |

---

## 2. 분석 실행 방법

### CLI

```bash
# 기본 분석 (현대화 목표 없음)
archpilot analyze output/system.json

# 현대화 목표 포함 (권장 — component_decisions 품질 대폭 향상)
archpilot analyze output/system.json \
  -r "AWS 전환, Oracle 라이선스 제거, 제로 다운타임 배포, PCI-DSS 준수"

# 분석 결과를 특정 경로에 저장
archpilot analyze output/system.json -o output/analysis.json
```

### Web UI

`archpilot serve` 실행 후 브라우저에서:
1. **시스템 입력** 탭에서 YAML/JSON/텍스트 주입
2. **분석 실행** 버튼 클릭 → SSE 스트리밍으로 실시간 진행 확인
3. 우측 아코디언 패널에서 분석 결과 즉시 확인

> **현대화 목표를 입력할수록 분석 품질이 높아집니다.** 요구사항 없이 분석하면 LLM이 현재 상태만 보고 "이 컴포넌트를 무엇으로 바꿔야 하는가"를 답하기 어렵습니다.

---

## 3. 리포트 3-Phase 구조

분석 실행 시 LLM이 최대 3-Phase로 동작합니다:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         분석 파이프라인                                   │
│                                                                         │
│  Phase 1: 핵심 분석                                                      │
│  ┌─────────────────────────────────────────────────────────┐            │
│  │  입력: system.json + 현대화 요구사항                      │            │
│  │  출력: AnalysisResult (health_score, component_decisions │            │
│  │         pain_points, risk_areas, opportunities ...)     │            │
│  └─────────────────────────────────────────────────────────┘            │
│                        ↓ (Web UI에서만)                                  │
│  Phase 2: 8대 관점 분석                                                  │
│  ┌─────────────────────────────────────────────────────────┐            │
│  │  입력: system.json + Phase 1 결과                        │            │
│  │  출력: MultiPerspectiveAnalysis (8개 전문가 관점 독립 분석)│            │
│  └─────────────────────────────────────────────────────────┘            │
│                        ↓ (Web UI에서만)                                  │
│  Phase 3: RMC 자기검토                                                   │
│  ┌─────────────────────────────────────────────────────────┐            │
│  │  입력: system.json + Phase 1 결과                        │            │
│  │  출력: AnalysisRMC (분석 품질 자기평가, 사각지대, 검증 질문)│            │
│  └─────────────────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────────────┘
```

Phase 2, 3는 CLI에서는 실행되지 않으며 Web UI(`archpilot serve`)에서만 스트리밍됩니다.

---

## 4. Phase 1 — 핵심 분석 (AnalysisResult)

### 4.1 헬스 스코어

```
health_score: 42  (0~100)
```

100점에서 아래 항목을 차감한 **종합 위험 지표**입니다:

| 차감 항목 | 감점 |
|----------|------|
| EOL 컴포넌트 1개당 | -8점 |
| Deprecated 컴포넌트 1개당 | -4점 |
| HIGH criticality이면서 EOL인 컴포넌트 1개당 | 추가 -5점 |
| 보안 컴포넌트와 restricted 데이터 간 직접 연결 부재 | -10점 |
| MAINFRAME 또는 ESB 타입 컴포넌트 존재 | -5점 |
| 허브 컴포넌트(연결 수 3개 이상) 존재 | -5점 |
| vintage 2015년 이전 컴포넌트 비율 50% 초과 | -10점 |
| known_issues 3개 이상 | -5점 |

**실무 해석:**

| 범위 | 의미 | 권고 조치 |
|------|------|-----------|
| 80~100 | 건강한 시스템 | 모니터링 + additive 현대화 가능 |
| 60~79 | 부분 위험 | EOL 컴포넌트 우선 대응, partial 시나리오 검토 |
| 40~59 | 위험 구간 | 현대화 착수 시점. 핵심 기능 안정성 리스크 존재 |
| 0~39 | 위기 상태 | full_replace 또는 긴급 조치 필요. SLA/보안 위반 가능성 |

> health_score는 시스템의 **현재 상태**를 반영합니다. 현대화 계획 수립 전 기준선으로 활용하고, 현대화 완료 후 재측정해 개선 효과를 검증하세요.

---

### 4.2 레거시 5차원 품질 평가

```json
"legacy_quality": {
  "performance":  { "score": 45, "rationale": "Oracle RAC 락 경합, 배치 병목" },
  "scalability":  { "score": 30, "rationale": "수평 확장 불가, 온프레미스 고정 용량" },
  "cost":         { "score": 40, "rationale": "Oracle+IBM 라이선스 연 수십억" },
  "security":     { "score": 55, "rationale": "HSM 존재하나 EOL 컴포넌트 패치 불가" },
  "operability":  { "score": 50, "rationale": "배포 자동화 없음, 수동 배치 관리" }
}
```

5가지 차원으로 현재 시스템의 품질을 수치화합니다:

| 차원 | 평가 기준 |
|------|----------|
| **performance** | 응답 시간·처리량·병목 — EOL DB, 허브 컴포넌트, 레거시 프로토콜 |
| **scalability** | 수평 확장 가능성 — 모놀리식·메인프레임·수동 스케일링 |
| **cost** | TCO 효율 — 상용 라이선스 집중·오버프로비저닝 |
| **security** | 보안 성숙도 — EOL 기술·패치 불가·암호화 부재 |
| **operability** | 운영 편의성 — CI/CD 부재·모니터링 미흡·수동 배포 |

**실무 활용:**
- Web UI에서 **레이더 차트**로 시각화되어 약점 차원이 한눈에 보입니다
- 현대화 목표 설정 시 가장 낮은 2개 차원을 우선 개선 목표로 지정하세요
- 현대화 설계 완료 후 `modern_quality`와 비교해 개선 폭을 정량화할 수 있습니다

---

### 4.3 현대화 시나리오 권고

```json
"recommended_scenario": "full_replace",
"scenario_rationale": "EOL 컴포넌트 비율 78%, 헬스 스코어 42로 전체 재설계 최적. 메인프레임과 Oracle 11g 모두 EOL 상태로 점진 현대화 시 위험 누적."
```

LLM이 시스템 상태를 분석해 3가지 시나리오 중 하나를 권고합니다:

| 시나리오 | 조건 | 의미 |
|----------|------|------|
| **full_replace** | EOL 비율 > 50% 또는 health_score < 50 | 아키텍처 전체를 새로 설계 (MSA 전환, 클라우드 네이티브) |
| **partial** | EOL 비율 20~50%, 핵심 컴포넌트는 건재 | 핵심은 유지, 주변부·통합 레이어만 교체 |
| **additive** | EOL 비율 < 20%, health_score > 70 | 기존 시스템 안정적, 신규 기능·채널만 추가 |

**실무 포인트:**
- 권고 시나리오는 **시작점**입니다. 비즈니스 제약(예산, 일정, 팀 규모)에 따라 partial로 조정할 수 있습니다.
- Web UI에서 현대화 실행 시 시나리오를 직접 선택할 수 있으며, 선택한 시나리오가 현대화 설계의 방향을 결정합니다.
- `scenario_rationale`을 경영진 보고 시 "왜 전면 재구축인가"의 근거로 활용하세요.

---

### 4.4 컴포넌트별 6R 결정

```json
"component_decisions": [
  {
    "component_id": "oracle_primary",
    "action": "replace",
    "rationale": "Oracle 11g EOL, Aurora PostgreSQL로 전환 시 라이선스 60% 절감",
    "target_component_id": "aurora_postgres",
    "risks": ["SQL 방언 차이", "데이터 마이그레이션 복잡도"],
    "dependencies": ["core_app_server"]
  },
  {
    "component_id": "mainframe",
    "action": "refactor",
    "rationale": "COBOL 비즈니스 로직 점진적 Java/Spring 재작성. 완전 대체는 위험 과다.",
    "risks": ["COBOL 로직 문서화 부족"],
    "dependencies": []
  }
]
```

각 컴포넌트에 대해 6가지 전략(6R) 중 하나를 결정합니다:

| 전략 | 의미 | 적용 기준 |
|------|------|-----------|
| **keep** | 변경 없이 유지 | 최신 기술, 안정 운영 중, 변경 필요 없음 |
| **rehost** | Lift & Shift | 기술은 레거시이나 클라우드 이전이 쉽고 기능 변경 불필요 |
| **replatform** | 최소 수정 전환 | 앱서버 → Docker, 소규모 설정 변경으로 클라우드/컨테이너 전환 가능 |
| **refactor** | 재설계 | 과도한 결합, 순환 의존성, SPOF — 구조적 재작성 필요 |
| **replace** | 대체 | EOL 기술 또는 더 나은 관리형 서비스로 완전 교체 |
| **retire** | 폐기 | 고립 컴포넌트, 중복 기능, 비즈니스 가치 없음 |

**실무 활용:**

1. **작업 범위 산정**: `replace` + `refactor` 컴포넌트 수 × 평균 공수로 마이그레이션 기간 추산
2. **실행 순서 결정**: `dependencies` 배열을 따라 선행 작업 완료 후 후속 작업 실행
3. **예산 배분**: `replace` = 신규 서비스 조달 비용, `refactor` = 개발 공수 비용으로 분리 산정
4. **리스크 관리**: `risks` 배열을 마이그레이션 리스크 레지스터에 직접 입력

> **이 섹션이 분석 결과에서 가장 중요합니다.** `component_decisions`가 없으면 현대화 설계 시 LLM이 어떤 컴포넌트를 어떻게 처리할지 판단 기준이 없어 설계 품질이 크게 저하됩니다.

---

### 4.5 핵심 문제점 (pain_points)

```
"pain_points": [
  "주문 처리 지연(현상): Oracle 11g R2 RAC 2-node 구성에서 분산 트랜잭션 락 경합 발생(원인)
   → 피크 시 주문 완료율 23% 저하 및 고객 이탈 직접 유발(영향)"
]
```

각 항목은 **현상 → 근본 원인 → 비즈니스 영향** 구조로 작성됩니다.

**실무 활용:**
- **경영진 보고**: 기술 문제를 비즈니스 영향(매출 손실, 고객 이탈, 운영 비용)과 연결해 현대화 투자 정당성 확보
- **현장 검증**: 분석이 기록되지 않은 문제를 발굴했다면 실제 담당팀에 확인 요청
- **우선순위**: 비즈니스 영향이 가장 큰 항목부터 현대화 시작점으로 결정

---

### 4.6 기술 부채 (tech_debt)

```json
"tech_debt": [
  {
    "component_id": "jboss_eap4",
    "description": "JBoss EAP 4 — Red Hat EOS 2012년 완료. Jakarta EE 직접 마이그레이션 불가(API 단절),
                    Spring Boot 3.x 재작성 필요. 다수 CVE 패치 미적용 상태.",
    "severity": "high"
  }
]
```

| 심각도 | 의미 | 권고 조치 |
|--------|------|-----------|
| **high** | EOL/EOS 완료, 알려진 CVE 미패치, 즉각적 비즈니스 위험 | 즉시 착수 |
| **medium** | 지원 종료 임박(1~2년), 기술 부채 누적 중 | 다음 분기 내 계획 수립 |
| **low** | 구형 기술이나 당장 위험 없음, 점진적 개선 가능 | 백로그 등록 |

---

### 4.7 위험 영역 (risk_areas)

```json
"risk_areas": [
  {
    "component_id": "payment_gateway",
    "risk": "발생 가능성 높음: 결제 서버에 7개 연결 집중 — 장애 시 전체 트랜잭션 중단 (일 거래액 50억 손실)",
    "mitigation": "단기: Circuit Breaker 패턴 도입, 결제 트랜잭션 별도 큐 분리(담당: 결제팀)
                   장기: 결제 마이크로서비스 분리, 다중화 구성으로 SPOF 제거"
  }
]
```

**단기/장기 조치를 구분**해 제시합니다:
- **단기**: 현대화 완료 전 즉시 적용 가능한 위험 완화 조치
- **장기**: 현대화 완료 후 구조적으로 해결하는 조치

**실무 활용:**
- 연결 토폴로지 분석으로 자동 탐지된 위험이 포함됩니다 (허브 컴포넌트, 순환 의존성, 레거시 프로토콜)
- `owner` 필드가 있는 컴포넌트는 `mitigation`에 책임 팀이 명시됩니다
- 리스크 레지스터 작성 시 이 섹션을 직접 입력 데이터로 활용하세요

---

### 4.8 현대화 기회 (modernization_opportunities)

```json
"modernization_opportunities": [
  {
    "area": "데이터베이스 현대화",
    "description": "Oracle RAC → Aurora PostgreSQL + Read Replica:
                    라이선스 비용 연 60~70% 절감, 읽기 처리량 3배 향상,
                    자동 페일오버 RTO 30초 이하 달성 가능",
    "priority": 1
  },
  {
    "area": "배포 자동화",
    "description": "수동 배포 → GitLab CI + ECS Blue/Green:
                    배포 시간 4시간 → 15분 단축, 롤백 5분 이내",
    "priority": 2
  }
]
```

| 우선순위 | 의미 |
|----------|------|
| 1 | 즉시 착수 필요 — 비용·보안·안정성 직접 영향 |
| 2 | 중기 과제 — 3~6개월 내 착수 권장 |
| 3 | 장기 개선 — 여력 생기면 순차 진행 |

**실무 활용:**
- `description`은 현재→목표 기술 스택 대비와 **기대 효과 수치**를 포함하므로 투자 제안서의 ROI 섹션에 직접 인용 가능합니다
- priority 1 항목들의 합산 절감 비용으로 현대화 프로젝트 예산을 정당화하는 데 활용하세요

---

### 4.9 보안 취약점 (security_findings)

```
"security_findings": [
  "운영 DB (Oracle 11g R2): restricted 데이터 처리 + EOL로 보안 패치 불가 — 데이터 유출 위험 높음",
  "인증 서버: BasicAuth 평문 전송 — 중간자 공격(MITM) 취약, OAuth 2.0 전환 필요"
]
```

`data_classification: restricted/confidential` 컴포넌트와 보안 컴포넌트에서 발견된 취약점을 나열합니다.

분석 항목: TLS 버전(EOL 기술에서 추론), 저장 데이터 암호화, 인증 방식, 알려진 CVE, 접근 통제 갭

**실무 활용:**
- 보안 감사 보고서의 발견 사항(Findings) 초안으로 활용
- `compliance_gaps`와 교차 검토해 규제 위반 여부 판단

---

### 4.10 컴플라이언스 갭 (compliance_gaps)

```
"compliance_gaps": [
  "PCI-DSS Req.6.3: Oracle 11g R2(EOL) 상에서 카드번호 처리 — 취약점 패치 불가로 위반 위험 높음",
  "GDPR Art.32: 개인정보 처리 컴포넌트 암호화 부재 — 정보보호 조치 미흡"
]
```

`metadata.compliance`에 명시된 규제별 현재 시스템의 준수 갭을 서술합니다. compliance가 없으면 도메인으로 유추 가능한 규제 갭을 포함합니다 (banking → PCI-DSS/ISO 27001, healthcare → HIPAA, ecommerce → GDPR).

**실무 활용:**
- 규제 대응 로드맵 작성 시 "규제명 + 요건 번호"로 문서화
- 컴플라이언스 감사 대응 시 현재 갭 현황 파악의 출발점으로 활용

---

## 5. Phase 2 — 8대 관점 분석

Web UI에서 Phase 1 완료 후 자동으로 실행되는 추가 LLM 패스입니다.

8명의 독립적인 전문가가 각자의 도메인 관점에서 시스템을 검토합니다:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     8대 아키텍처 관점 위원회                               │
│                                                                          │
│  SA  솔루션 아키텍처  비즈니스 목표·ROI 정합성                              │
│  AA  애플리케이션     서비스 분해·결합도·API 설계                           │
│  DA  데이터          데이터 소유권·사일로·마이그레이션 경로                   │
│  IA  인프라          SPOF·고가용성·클라우드 네이티브                        │
│  TA  기술            EOL/EOS 위험·DevSecOps·기술 표준화                   │
│  SWA 소프트웨어      SOLID·헥사고날·테스트 가능성                          │
│  DBA 데이터베이스    DB 유형 적합성·쿼리 성능·폴리글랏                       │
│  QA  품질            관찰 가능성·SLO·비기능 요구사항                       │
└──────────────────────────────────────────────────────────────────────────┘
```

### 각 관점 출력 구조

```json
{
  "perspective": "ia",
  "score": 35,
  "rationale": "단일 온프레미스 데이터센터, 재해 복구 없음",
  "concerns": [
    "단일 장애점(SPOF): 결제 서버 7개 연결 집중",
    "재해 복구 계획(DRP) 없음 — RTO/RPO 미정의"
  ],
  "recommendations": [
    "결제 서버 로드밸런서 + Active-Standby 구성",
    "AWS Multi-AZ 또는 2개 가용영역 분산 배치"
  ],
  "risks": [
    "데이터센터 화재·침수 시 전체 서비스 중단, 복구 수일 소요 가능"
  ]
}
```

### consensus_summary와 priority_actions 활용

```
"consensus_summary": "8개 관점 공통 합의 — Oracle 11g EOL과 단일 장애점이
                      보안·비용·안정성 모든 면에서 가장 시급한 위험 요인"

"priority_actions": [
  "Oracle 11g → Aurora PostgreSQL 전환 (보안·비용·성능 동시 해결)",
  "결제 서버 SPOF 제거 (Circuit Breaker + 다중화)",
  "BasicAuth → OAuth2/OIDC 전환"
]
```

**실무 활용:**
- `consensus_summary` = 경영진 브리핑의 "핵심 요약" 1단락
- `priority_actions` = 스프린트 1 백로그의 시작점
- `conflict_areas` = 아키텍처 의사결정 회의의 토론 의제 (예: 보안 강화 vs 성능 오버헤드)
- 관점별 `score` = 레이더 차트로 시각화해 기술 부채 프로파일 공유

---

## 6. Phase 3 — RMC 자기검토

RMC(Recursive Meta-Cognition, 재귀적 메타 인지): LLM이 자신의 분석을 스스로 비판적으로 검토합니다.

```json
{
  "coverage_score": 72,
  "assumptions": [
    "COBOL 비즈니스 로직이 중간 복잡도라고 가정 — 실제 코드 라인 수 확인 필요",
    "야간 배치 처리 볼륨을 평균 수준으로 추정 — 월말 피크 볼륨 미고려"
  ],
  "blind_spots": [
    "야간 배치 처리 상세 볼륨 데이터 없음 — Oracle 배치 쿼리 성능 영향 불확실",
    "인프라 오버프로비저닝 여부 미파악 — 비용 절감 기회 과소평가 가능성"
  ],
  "verification_questions": [
    "Oracle RAC의 피크 TPS와 평균 응답 시간은 얼마입니까?",
    "COBOL 프로그램 총 LOC(라인 수)와 개발팀 보유 현황은?",
    "현재 RTO/RPO 목표치가 SLA로 정의되어 있습니까?"
  ],
  "confidence_level": "medium",
  "confidence_rationale": "핵심 컴포넌트는 모두 커버했으나 실제 성능 데이터 없이 추정한 항목이 다수."
}
```

### RMC의 3가지 실무 가치

**1. 분석 신뢰도 교정**
`confidence_level`과 `coverage_score`로 이 분석을 얼마나 신뢰할 수 있는지 판단합니다.
- `high` + score 85 이상 → 현대화 계획 바로 착수 가능
- `low` + score 60 이하 → `verification_questions` 먼저 현장 확인 후 재분석 권장

**2. 현장 확인 체크리스트**
`verification_questions`는 클라이언트·담당팀에 확인해야 할 구체적 질문 목록입니다. 킥오프 미팅이나 현황 파악 워크숍의 질문지로 직접 활용하세요.

**3. 위험 인식 공유**
`blind_spots`과 `assumptions`는 "이 분석이 무엇을 모른다고 인식하는가"를 명시합니다. 프로젝트 리스크 관리에서 "알려진 미지(known unknown)"를 문서화하는 데 활용합니다.

---

## 7. 실무 활용 가이드

### 7.1 경영진 보고용 요약

분석 결과에서 경영진 보고에 직접 활용 가능한 섹션:

```
1. health_score → "현재 시스템 건강도: 42/100 (위험 구간)"
2. legacy_quality 5차원 → 레이더 차트로 시각화
3. recommended_scenario + scenario_rationale → "왜 전면 재구축인가"
4. modernization_opportunities priority 1~2 → "현대화로 달성 가능한 효과"
   예: "Oracle 전환으로 연 라이선스 비용 60~70% 절감"
5. estimated_effort → 대략적인 프로젝트 규모
6. consensus_summary (Phase 2) → 8개 관점 합의된 최우선 과제
```

**발표 흐름:**
> "현재 시스템은 EOL 컴포넌트가 78%로 건강도 42점입니다. Oracle과 메인프레임이 동시 EOL 상태로 보안 패치가 불가능하며, PCI-DSS Req.6.3 위반 위험이 있습니다. 전면 재구축 시 Oracle 라이선스만 연 X억 절감, 배포 시간 4시간→15분 단축이 가능합니다."

---

### 7.2 기술팀 현대화 계획

분석 결과를 현대화 계획 수립에 활용하는 순서:

```
Step 1: component_decisions 검토
  → replace/refactor 컴포넌트 목록이 작업 대상
  → dependencies 순서대로 마이그레이션 WBS 작성

Step 2: risk_areas.mitigation 검토
  → 단기 조치는 현대화 착수 전 즉시 실행
  → 장기 조치는 마이그레이션 Epic에 포함

Step 3: tech_debt severity 순으로 정렬
  → high → medium → low 순서로 스프린트 배정

Step 4: modernization_opportunities priority 순 정렬
  → priority 1 기회가 첫 번째 릴리즈 목표

Step 5: verification_questions (RMC) 현장 확인
  → 불확실 항목 해소 후 계획 확정
```

---

### 7.3 우선순위 결정 체계

분석 결과만으로 우선순위를 결정하기 어려울 때 아래 매트릭스를 활용하세요:

```
           비즈니스 영향
           낮음   중간   높음
기술       ┌────┬────┬────┐
위험  낮음 │ 4  │ 3  │ 2  │
      중간 │ 3  │ 2  │ 1  │
      높음 │ 2  │ 1  │ 1  │
           └────┴────┴────┘

우선순위 1 → pain_points + risk_areas의 HIGH + opportunity priority 1
우선순위 2 → tech_debt MEDIUM + opportunity priority 2
우선순위 3 → tech_debt LOW + opportunity priority 3
우선순위 4 → keep 컴포넌트 모니터링
```

---

### 7.4 현대화 피해야 할 함정

**함정 1: health_score만 보고 판단**
health_score가 낮아도 비즈니스 연속성 제약이 있으면 full_replace 대신 partial이 현실적일 수 있습니다. `scenario_rationale`과 `risk_areas`를 함께 검토하세요.

**함정 2: component_decisions 없이 modernize 실행**
분석을 건너뛰고 바로 현대화를 실행하면 LLM이 컴포넌트를 임의로 통합·생략합니다. 반드시 analyze → modernize 순서를 지키세요.

**함정 3: blind_spots 무시**
RMC의 `blind_spots`에 "데이터 볼륨 미확인"이 있다면, 현대화 설계의 성능 목표가 현실과 다를 수 있습니다. `verification_questions`를 현장 확인 없이 건너뛰지 마세요.

**함정 4: 모든 replace를 즉시 실행**
`dependencies` 필드를 무시하고 replace 컴포넌트를 동시에 진행하면 연쇄 장애가 발생할 수 있습니다. 의존성 순서대로 단계별로 진행하세요.

---

## 8. 분석 품질 높이기

분석 품질은 입력 데이터의 풍부도에 비례합니다:

| 입력 항목 | 없을 때 | 있을 때 |
|----------|--------|--------|
| `metadata.domain` | 일반적 분석 | 도메인별 규제(PCI-DSS, HIPAA) 자동 적용 |
| `metadata.vintage` | 기술 부채 추정 | EOL 연도 기반 정확한 부채 심각도 |
| `metadata.scale` | 병목 일반 언급 | "TPS 2000에서 Oracle RAC 한계" 구체 수치 |
| `metadata.compliance` | 도메인 추정 규제 | 명시된 규제별 정확한 갭 분석 |
| `metadata.known_issues` | 외부 관찰만 | 내부 알려진 문제 + 근본 원인 분석 |
| `criticality` 필드 | 모두 동등 취급 | HIGH 컴포넌트 위험도 2배 가중 |
| `lifecycle_status` | 추정 EOL | 확정 EOL 기반 tech_debt 자동 생성 |
| `data_classification` | 보안 일반 분석 | restricted 컴포넌트 집중 보안 취약점 발굴 |
| `-r` 현대화 요구사항 | 현재 상태만 분석 | 목표 기반 맞춤 6R 결정 |

> 전체 필드를 채우기 어려울 때는 `metadata.known_issues`와 `criticality`부터 시작하세요. 이 두 필드만 있어도 분석 품질이 크게 향상됩니다.

YAML 작성 가이드는 [`docs/2_SCHEMA.md`](./2_SCHEMA.md)를 참조하세요.
