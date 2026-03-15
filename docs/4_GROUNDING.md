# ArchPilot — LLM 지식·그라운딩 체계

> AI 분석과 현대화 설계의 품질이 결정되는 원리

**Version**: 0.2.4 | **Last Updated**: 2026-03-15

---

## 목차

1. [그라운딩이란](#1-그라운딩이란)
2. [이중 그라운딩 아키텍처](#2-이중-그라운딩-아키텍처)
3. [Phase 1 — 분석 (analyze)](#3-phase-1--분석-analyze)
4. [Phase 2 — 현대화 (modernize)](#4-phase-2--현대화-modernize)
5. [Phase 3 — RMC 자기검토](#5-phase-3--rmc-자기검토)
6. [CLI 경로 vs Web UI 경로](#6-cli-경로-vs-web-ui-경로)
7. [컨텍스트 윈도우 관리](#7-컨텍스트-윈도우-관리)
8. [그라운딩 품질 높이기](#8-그라운딩-품질-높이기)
9. [출력 결과 읽는 방법](#9-출력-결과-읽는-방법)
10. [DX 패턴 16개 상세](#10-dx-패턴-16개-상세)
11. [AX 패턴 11개 상세](#11-ax-패턴-11개-상세)
12. [8대 아키텍처 관점 — 멀티 퍼스펙티브](#12-8대-아키텍처-관점--멀티-퍼스펙티브)

---

## 1. 그라운딩이란

LLM은 프롬프트에 포함된 사실 정보를 **닻(anchor)**으로 삼아 출력을 구성합니다. 이 사실 정보를 **그라운딩(grounding)**이라고 합니다.

**그라운딩이 없으면:**
- LLM이 존재하지 않는 컴포넌트를 만들어냄 (환각)
- 34개 레거시 컴포넌트를 6개로 과도하게 통합
- 현대화 설계가 레거시 시스템과 무관하게 생성됨

**그라운딩이 있으면:**
- 실제 레거시 컴포넌트를 기반으로 현대화 설계
- 각 컴포넌트의 6R 결정(keep/replace/retire 등)이 논리적으로 연결됨
- 마이그레이션 플랜이 실제 변경 사항을 반영

---

## 2. 이중 그라운딩 아키텍처

ArchPilot은 두 가지 그라운딩을 조합합니다:

```
┌──────────────────────────────────────────────────────────────┐
│                   ArchPilot 그라운딩 구조                      │
│                                                              │
│  Grounding 1: Legacy SystemModel JSON                        │
│  ┌────────────────────────────────────────┐                 │
│  │ 실제 컴포넌트 목록 (id, type, tech...)  │                 │
│  │ 실제 연결 관계 (from_id → to_id)        │                 │
│  │ 엔터프라이즈 필드 (criticality, EOL...) │                 │
│  └────────────────────────────────────────┘                 │
│                                                              │
│         ↓ analyze 실행 후                                    │
│                                                              │
│  Grounding 2: AnalysisResult                                 │
│  ┌────────────────────────────────────────┐                 │
│  │ component_decisions (6R 결정, 핵심)     │  ← 가장 중요    │
│  │ recommended_scenario + rationale       │                 │
│  │ health_score, legacy_quality           │                 │
│  │ pain_points, compliance_gaps           │                 │
│  └────────────────────────────────────────┘                 │
│                                                              │
│         ↓ modernize에 두 그라운딩 동시 제공                   │
│                                                              │
│  출력: 현대화 SystemModel (환각 없는 구체적 설계)              │
└──────────────────────────────────────────────────────────────┘
```

**핵심 원칙:** `analyze` 결과(특히 `component_decisions`)가 `modernize`의 품질을 결정합니다.

---

## 3. Phase 1 — 분석 (analyze)

### 3.1 입력 그라운딩

```
analyze 입력
├── 분석할 시스템: {compress_model(legacy)}    ← Grounding 1
└── 현대화 목표 (-r 옵션):  {requirements}      ← v0.2.3 신규
```

**현대화 목표 없이 분석:**
```bash
archpilot analyze output/system.json
```
→ 레거시 상태만 보고 6R 결정. "이 컴포넌트를 무엇으로 대체할지" 목표 없음.

**현대화 목표 포함해서 분석 (권장):**
```bash
archpilot analyze output/system.json -r "AWS EKS 전환, Oracle 비용 절감, 제로 다운타임 배포"
```
→ 목표를 알고 6R 결정. `component_decisions`가 요구사항을 반영.

| 분석 방식 | component_decisions 품질 |
|----------|------------------------|
| 요구사항 없음 | 현재 상태 기반 일반적 판단 |
| 요구사항 포함 | 목표 기반 맞춤 전략 판단 |

### 3.2 출력 — analysis.json

```json
{
  "system_name": "Core Banking Legacy System",
  "health_score": 42,

  "recommended_scenario": "full_replace",
  "scenario_rationale": "EOL 컴포넌트 비율 78%, 헬스 점수 42/100으로 전체 재설계가 최적. JBoss EAP 4, Oracle 11g 모두 EOL 상태.",

  "component_decisions": [
    {
      "component_id": "oracle_primary",
      "action": "replace",
      "rationale": "Oracle 11g EOL, AWS 전환 목표에 따라 Aurora PostgreSQL로 관리형 전환",
      "target_component_id": "aurora_postgres",
      "risks": ["데이터 마이그레이션 복잡도", "SQL 방언 차이"],
      "dependencies": ["core_server"]
    },
    {
      "component_id": "mainframe",
      "action": "refactor",
      "rationale": "COBOL 비즈니스 로직을 Java/Spring으로 점진적 재작성. 완전 대체는 리스크 과다.",
      "risks": ["COBOL 로직 이해 부족", "기간계 안정성"],
      "dependencies": []
    },
    {
      "component_id": "hsm",
      "action": "keep",
      "rationale": "PKCS#11 표준, 물리 보안 요구사항 충족. AWS CloudHSM으로 비용 증가 예상.",
      "risks": [],
      "dependencies": []
    }
  ],

  "legacy_quality": {
    "performance":  {"score": 45, "rationale": "Oracle RAC 락 경합, 배치 처리 병목"},
    "scalability":  {"score": 30, "rationale": "수평 확장 구조 없음, 온프레미스 용량 고정"},
    "cost":         {"score": 40, "rationale": "Oracle, IBM z14 유지비 연 수십억"},
    "security":     {"score": 55, "rationale": "HSM 존재하나 EOL 컴포넌트 보안 패치 미적용"},
    "operability":  {"score": 50, "rationale": "배포 자동화 없음, 수동 배치 관리"}
  },

  "pain_points": ["..."],
  "tech_debt": ["..."],
  "estimated_effort": "XL"
}
```

### 3.3 component_decisions가 핵심인 이유

`component_decisions`는 컴포넌트별 6R 결정입니다. 이것이 없으면 modernize 시 LLM이 어떤 컴포넌트를 어떻게 처리할지 판단할 기준이 없습니다.

```
component_decisions 없는 modernize:
  → LLM이 임의로 컴포넌트 통합/생략
  → 34개 → 6개로 붕괴하는 "Large System Collapse" 문제

component_decisions 있는 modernize:
  → 각 컴포넌트에 대해 "keep", "replace", "retire" 등 명확한 지시
  → 레거시 규모와 유사한 현대화 설계 유지
```

---

## 4. Phase 2 — 현대화 (modernize)

### 4.1 4-계층 그라운딩 구조

modernize에는 4개 층의 그라운딩이 순서대로 주입됩니다:

```
┌── Layer 1: 규모 어노테이션 (계약) ────────────────────────────┐
│  [레거시 규모: 9개 컴포넌트 — 현대화 출력도 동등한 수를 생성] │
│  [현대화 설계 최소 컴포넌트 수: 8개 이상 (retire 1개 제외)]  │
└───────────────────────────────────────────────────────────────┘
              ↓
┌── Layer 2: 현대화 요구사항 ────────────────────────────────────┐
│  요구사항: "AWS EKS 전환, Aurora PostgreSQL, 제로 다운타임"    │
│  scenario: full_replace                                       │
│  시나리오 설명: 아키텍처를 완전히 새로 설계                    │
└───────────────────────────────────────────────────────────────┘
              ↓
┌── Layer 3: 분석 결과 그라운딩 (핵심) ──────────────────────────┐
│  추천 시나리오 근거: {scenario_rationale}                      │
│  컴포넌트별 전략 결정:                                        │
│    - oracle_primary: replace → aurora_postgres               │
│    - mainframe: refactor                                     │
│    - hsm: keep                                               │
│  전체 분석: {compress_analysis(analysis)}                    │
└───────────────────────────────────────────────────────────────┘
              ↓
┌── Layer 4: 레거시 시스템 그라운딩 ─────────────────────────────┐
│  Legacy 시스템:                                               │
│  {compress_model(legacy)} — 실제 컴포넌트·연결 JSON            │
└───────────────────────────────────────────────────────────────┘
```

### 4.2 각 레이어의 역할

**Layer 1 — 규모 계약:**
MODERNIZE_SYSTEM_PROMPT와 연동되는 계약. 프롬프트에 "레거시 규모: N개 컴포넌트" 어노테이션이 있을 때만 컴포넌트 수 강제가 활성화됩니다. 이 어노테이션이 없으면 LLM이 컴포넌트를 임의로 통합할 수 있습니다.

**Layer 2 — 요구사항:**
"무엇을 만들어야 하는가"를 정의합니다. 시나리오 레이블도 포함됩니다.

**Layer 3 — 분석 그라운딩 (가장 중요):**
`component_decisions`의 6R 결정이 컴포넌트별 처리 방식을 구체화합니다. `compress_analysis()`로 크기를 제어하되, `component_decisions`는 항상 보존됩니다.

**Layer 4 — 레거시 사실:**
실제 시스템 구조. LLM이 어떤 컴포넌트가 존재하고 어떻게 연결되어 있는지 정확히 알게 합니다. `compress_model()`로 크기 제어.

### 4.3 출력 — modern/system.json

```json
{
  "name": "Core Banking Modern System",
  "components": [
    {
      "id": "aurora_postgres",
      "type": "database",
      "label": "Aurora PostgreSQL",
      "tech": ["AWS Aurora PostgreSQL 15", "Multi-AZ"],
      "host": "aws",
      "metadata": {
        "is_new": true,
        "strategy": "replace",
        "replaces": "oracle_primary",
        "reason": "Oracle 11g EOL 대응, AWS 전환으로 관리 부담 제거, 비용 60% 절감"
      }
    },
    {
      "id": "hsm",
      "type": "security",
      "label": "HSM (암호화 모듈)",
      "tech": ["Thales HSM", "PKCS#11"],
      "host": "on-premise",
      "metadata": {
        "strategy": "keep",
        "reason": "물리 보안 요구사항 충족, 마이그레이션 위험 대비 유지"
      }
    }
  ]
}
```

### 4.4 후처리 검증

modernize 완료 후 자동으로 컴포넌트 수를 검증합니다:

```
retire_count = (retire 결정된 컴포넌트 수)
min_expected = max(1, legacy_count - retire_count)

if modern_count < min_expected * 0.6:
    ⚠ "현대화 컴포넌트 수 부족: 레거시 34개 → 현대 6개 (retire 2개 제외 최소 32개 기대)"
```

이 경고가 나오면 `--requirements`에 더 구체적인 요구사항을 추가하거나, 분석을 먼저 실행해 `component_decisions`를 생성하세요.

---

## 5. Phase 3 — RMC 자기검토

Web UI에서만 실행되는 3개의 추가 LLM 패스입니다. 이전 패스의 출력을 검토해 품질을 높입니다.

### 5.1 분석 RMC (Pass 1.5)

analyze 직후 실행. 분석 결과의 완성도를 LLM이 스스로 평가합니다.

```
입력: 레거시 시스템 + 방금 생성한 analysis.json
출력: AnalysisRMC {
  coverage_score: 72,        # 분석 커버리지 (0-100)
  assumptions: ["COBOL 로직 복잡도를 중간으로 가정"],
  blind_spots: ["야간 배치 처리 볼륨 데이터 없음"],
  verification_questions: ["Oracle RAC 락 경합 빈도와 피해 규모?"],
  confidence_level: "medium"
}
```

### 5.2 설계 해설 (Pass 3) — Design Rationale

modernize 후 실행. "왜 이런 설계를 했는가"를 자세히 설명합니다.

```
입력 그라운딩:
  시나리오: full_replace
  요구사항: {requirements}
  레거시 시스템: {compress_system_dict(legacy)}
  현대화 설계: {compress_for_plan(modern)}
  분석 참고: {component_decisions + pain_points + recommended_patterns + compliance_gaps}

출력: DesignRationale {
  design_philosophy: "레거시 한계를 클라우드 네이티브로 근본 해결...",
  key_decisions: [
    {
      area: "데이터 레이어",
      decision: "Oracle RAC → Aurora PostgreSQL 전환",
      rationale: "EOL 대응, 비용 60% 절감, AWS 네이티브 통합",
      alternatives_rejected: ["Oracle AWS RDS — 라이선스 비용 그대로", "PostgreSQL on EC2 — 관리 부담"],
      tradeoffs: ["PL/SQL → PL/pgSQL 마이그레이션 필요"]
    }
  ],
  arch_quality_eval: {
    maintainability: 85, performance: 80, scalability: 90, ...
  },
  rmc_self_eval: {
    completeness_score: 78,
    coverage_gaps: ["HSM 온프레미스 유지와 AWS 서비스 간 레이턴시 검토 부족"],
    design_risks: ["COBOL 재작성 시 비즈니스 로직 누락 위험"]
  }
}
```

### 5.3 마이그레이션 계획 자기평가 (Pass 4) — Plan RMC

migration_plan.md 작성 후 실행. 계획의 완성도를 평가합니다.

```
입력 그라운딩:
  시스템: "Core Banking Legacy System"
  시나리오: full_replace
  시스템 분석 컨텍스트:
    헬스 스코어: 42/10
    예상 공수: XL
    주요 문제점: Oracle 11g EOL; JBoss EAP 4 지원 종료; 배치 수동 관리
    컴포넌트: 레거시 9개 → 현대 12개
  마이그레이션 계획: {migration_plan[:8000]}

출력: MigrationPlanRMC {
  completeness_score: 74,
  well_covered_phases: ["Phase 1 인프라", "데이터 마이그레이션"],
  missing_aspects: ["COBOL 재작성 교육 계획", "현업 담당자 변경 관리"],
  risk_blind_spots: ["야간 배치 처리 중단 시 비즈니스 영향"],
  rollback_adequacy: "Blue/Green 전략 명시되나 DB 롤백 절차 부족",
  confidence_level: "medium"
}
```

---

## 6. CLI 경로 vs Web UI 경로

두 경로는 같은 그라운딩 원칙을 사용하지만 구현 수준이 다릅니다.

| 항목 | CLI (`modernizer.py`) | Web UI (`routers/modernize.py`) |
|------|----------------------|---------------------------------|
| Layer 1 규모 어노테이션 | ✅ | ✅ (컴포넌트 수 + 최소 수 모두) |
| Layer 3 component_decisions | ✅ (indent=2 명시) | ✅ (indent=2 명시) |
| Layer 3 전체 분석 | ✅ `compress_analysis()` | ✅ `compress_analysis()` |
| Layer 4 레거시 시스템 | ✅ `compress_model()` | ✅ `compress_system_dict()` |
| 분석 RMC | ❌ | ✅ |
| 설계 해설 (Design Rationale) | ❌ | ✅ |
| 마이그레이션 계획 자기평가 | ❌ | ✅ |
| 시나리오 수동 선택 | ❌ (analysis.json 자동) | ✅ (드롭다운) |

**결론: 품질 중심이면 Web UI를 사용하세요.** CLI는 자동화/배치 처리에 적합합니다.

---

## 7. 컨텍스트 윈도우 관리

LLM 컨텍스트 창 크기는 유한합니다. 대형 시스템에서 모든 정보를 그대로 보내면 초과합니다. ArchPilot은 3단계 압축 전략을 사용합니다.

### 7.1 compress_model() — 레거시/현대 시스템 압축

```
상한: MAX_SYSTEM_CHARS = 20,000자 (modernize용)
      MAX_PAYLOAD_CHARS = 24,000자 (analyze용)

단계 1: indent=2 JSON → 제한 이하면 그대로
단계 2: indent 제거 → ~30% 절감
단계 3: components의 metadata·specs 제거 + 경고 출력

⚠ "대형 시스템: 12개 컴포넌트의 strategy/reason까지 제거했습니다"
```

**대응:** 중요한 `specs`/`metadata`가 있는 컴포넌트는 그 시스템만 별도 YAML로 분리해 분석하세요.

### 7.2 compress_analysis() — 분석 결과 압축

```
상한: MAX_ANALYSIS_CHARS = 8,000자

단계 1: compact JSON → 제한 이하면 그대로
단계 2: 목록 필드 축약
  pain_points → 3개, tech_debt → 3개, risk_areas → 3개
  modernization_opportunities → 3개, recommended_patterns → 3개
  compliance_gaps → 5개, security_findings → 5개

단계 3: 핵심 필드만 보존 (component_decisions 반드시 보존)
  system_name, health_score, recommended_scenario, scenario_rationale,
  estimated_effort, legacy_quality, component_decisions,
  pain_points[:3], compliance_gaps[:3], security_findings[:3]

⚠ "분석 결과 압축: 상세 항목 제거, component_decisions(N개)·시나리오 보존"
```

`component_decisions`는 절대 제거되지 않습니다. 이것이 현대화의 핵심 신호이기 때문입니다.

### 7.3 compress_for_plan() — 마이그레이션 플랜용 압축

```
상한: MAX_PLAN_SYSTEM_CHARS = 15,000자 (레거시·현대 각각)

단계 1: indent=2 → OK면 반환
단계 2: indent 제거
단계 3: specs 제거 + metadata는 핵심 키만 보존
  보존 키: strategy, replaces, reason, is_new
단계 4 (최후): 핵심 metadata도 제거 + 경고
```

### 7.4 출력 토큰 상한

| 단계 | 상한 | 비고 |
|------|------|------|
| analyze | 6,000 토큰 | 분석 JSON |
| modernize | 16,000 토큰 | 30개+ 컴포넌트 대응 |
| migration plan | 6,000 토큰 | 11개 섹션 |
| design rationale | 10,000 토큰 | 12차원 품질 평가 포함 |
| RMC (분석/계획) | 4,000 토큰 | 자기평가 JSON |

---

## 8. 그라운딩 품질 높이기

### 권장 워크플로우

```bash
# 1. 요구사항을 포함해서 분석 (핵심)
archpilot analyze output/system.json \
  -r "AWS EKS 전환, Aurora PostgreSQL, 마이크로서비스 분리, 제로 다운타임"

# 2. 분석 결과 확인 (component_decisions 검토)
cat output/analysis.json | python -m json.tool | grep -A5 "component_decisions"

# 3. 동일 요구사항으로 현대화
archpilot modernize output/system.json \
  -r "AWS EKS 전환, Aurora PostgreSQL, 마이크로서비스 분리, 제로 다운타임"
```

### YAML 품질이 그라운딩에 미치는 영향

| YAML 정보 | 분석 품질 향상 |
|----------|-------------|
| `tech` 버전 명시 (`Java 8` vs `Java`) | EOL 날짜 정확, CVE 식별 |
| `lifecycle_status: eol` | health_score 정확 계산, risk_areas 포함 |
| `criticality: high` | component_decisions에서 retire 신중 처리 |
| `data_classification: restricted` | compliance_gaps에서 PII 보호 요구사항 생성 |
| `description`에 알려진 문제 기술 | pain_points에 반영 |
| `type: mainframe` 정확 사용 | COBOL 마이그레이션 복잡도 인식 |

### 대형 시스템 (30개+ 컴포넌트) 대응

1. **요구사항 필수 포함**: `analyze -r` 없이는 component_decisions 품질 저하
2. **Web UI 사용 권장**: 4-pass RMC로 각 결과를 교차 검증
3. **서브시스템 분리**: 인프라, 비즈니스 로직, 데이터 레이어를 별도 YAML로 분리 후 통합
4. **metadata 최소화**: compress 시 자동 제거되므로 핵심 정보는 최상위 필드에 기록

---

## 9. 출력 결과 읽는 방법

### analysis.json 주요 항목

```json
{
  "health_score": 42,                // 0(위험)~100(건강). 60 이하면 full_replace 권고
  "recommended_scenario": "full_replace",
  "scenario_rationale": "...",       // 시나리오 선택 이유 — 설득력 있는 설명인지 확인

  "component_decisions": [           // 컴포넌트별 6R 결정 — 핵심 검토 대상
    {
      "component_id": "oracle_primary",
      "action": "replace",           // keep|rehost|replatform|refactor|replace|retire
      "rationale": "...",            // 결정 근거 — 납득할 수 있는지 확인
      "target_component_id": "aurora_postgres",  // replace/refactor 시
      "risks": ["..."],              // 위험 요소
      "dependencies": ["..."]        // 먼저 처리해야 할 컴포넌트 id
    }
  ],

  "legacy_quality": {                // 5차원 품질 (0-100)
    "performance":  {"score": 45, "rationale": "..."},
    "scalability":  {"score": 30, "rationale": "..."},
    "cost":         {"score": 40, "rationale": "..."},
    "security":     {"score": 55, "rationale": "..."},
    "operability":  {"score": 50, "rationale": "..."}
  }
}
```

### design_rationale.json 주요 항목 (Web UI)

```json
{
  "key_decisions": [                 // 핵심 아키텍처 결정 목록
    {
      "area": "데이터 레이어",
      "decision": "Oracle → Aurora PostgreSQL",
      "rationale": "...",
      "alternatives_rejected": ["Oracle RDS", "PostgreSQL on EC2"],
      "tradeoffs": ["PL/SQL 재작성 필요"]
    }
  ],
  "arch_quality_eval": {             // 12차원 품질 평가 (현대화 설계 기준)
    "maintainability": 85,
    "scalability": 90,
    "security": 80,
    ...
  },
  "rmc_self_eval": {                 // AI의 자기평가
    "completeness_score": 78,
    "coverage_gaps": ["..."],        // 검토 부족 영역
    "design_risks": ["..."]          // 잠재적 설계 위험
  }
}
```

`rmc_self_eval.coverage_gaps`와 `design_risks`는 실제로 중요한 내용이 담기는 경우가 많습니다. 설계 검토 시 반드시 확인하세요.

---

## 참고

- YAML 작성 가이드: [`SCHEMA.md`](./2_SCHEMA.md)
- 전체 사용 흐름: [`USER_GUIDE.md`](./3_USER_GUIDE.md)
- 내부 구현 상세: [`ARCHITECTURE.md`](./6_ARCHITECTURE.md) — Section 2.5~2.6 (패턴·그라운딩), 2.7 (LLM Client)
- 소스 코드:
  - `src/archpilot/core/transformation_patterns.py` — DT/AI 패턴 27개 정의
  - `src/archpilot/llm/grounding.py` — build_pattern_grounding() 패턴 선별
  - `src/archpilot/llm/analyzer.py` — analyze() 구현
  - `src/archpilot/llm/modernizer.py` — modernize() CLI 경로
  - `src/archpilot/ui/routers/analyze.py` — 분석 Web UI 경로 (3-pass: analyze + 멀티퍼스펙티브 + RMC)
  - `src/archpilot/ui/routers/modernize.py` — 현대화 Web UI 경로 (5-phase)
  - `src/archpilot/llm/utils.py` — compress_model/compress_analysis/compress_for_plan

---

## 10. DX 패턴 16개 상세

시스템의 컴포넌트 타입과 기술 스택을 기반으로 아래 16개 DT 패턴 중 관련도 높은 패턴이 자동 선별되어 LLM 그라운딩에 주입됩니다.

### 점진적 전환 패턴

#### Strangler Fig

```
적용 상황: 레거시 모놀리스·메인프레임·ESB를 빅뱅 없이 안전하게 교체
트리거 기술: cobol, mainframe, esb, oracle forms, websphere
핵심 아이디어: API Gateway가 레거시 앞에 위치 → 기능별로 신규 마이크로서비스로 점진 이관
              → 레거시는 모든 기능 이관 완료 시 퇴역

장점: 무중단 전환, 리스크 분산, 언제든 롤백 가능
트레이드오프: 병행 운영 비용 증가, 데이터 동기화 복잡도
```

### 서비스 아키텍처 패턴

#### 마이크로서비스 분해 (Microservices Decomposition)

```
적용 상황: 단일 코드베이스 결합도 해소, 팀별 독립 배포·확장 필요
트리거 기술: monolith, spring, django, rails, tomcat, j2ee
핵심 아이디어: DDD Bounded Context로 서비스 분리
              → 각 서비스: 독립 DB + 독립 배포 파이프라인
              → API Gateway가 진입점 통일

장점: 독립 확장, 팀 자율성, 장애 격리
트레이드오프: 분산 시스템 복잡도, 네트워크 지연, 분산 트랜잭션 관리
```

#### 서비스별 독립 DB (Database-per-Service)

```
적용 상황: 마이크로서비스 분해 후 공유 DB 제거, Polyglot Persistence 도입
트리거 기술: oracle, sql server, shared database, monolith db
핵심 아이디어: 서비스별 DB 선택 자유도
              → 서비스 간 데이터 공유는 API 또는 이벤트로만
              → Saga Pattern으로 분산 트랜잭션 관리

장점: 서비스 독립성, Polyglot Persistence, 장애 격리
트레이드오프: 조인 불가, Saga 복잡도, DB 운영 비용 증가
```

#### Saga 패턴 (Saga Pattern)

```
적용 상황: 마이크로서비스별 독립 DB 환경에서 다단계 트랜잭션 일관성 보장
트리거 기술: kafka, rabbitmq, 2pc, xa, activemq, jms
핵심 아이디어:
  Choreography Saga: 각 서비스가 이벤트로 다음 단계 트리거
                     → 실패 시 보상 이벤트 발행으로 이전 상태 롤백
  Orchestration Saga: 중앙 사가 오케스트레이터가 각 서비스에 명령 전달

장점: 데이터 최종 일관성, 서비스 독립성, 2PC 없이 분산 트랜잭션
트레이드오프: 보상 트랜잭션 설계 복잡도, 즉시 일관성 불가, 디버깅 어려움
```

### 이벤트 & 데이터 패턴

#### 이벤트 기반 아키텍처 (EDA)

```
적용 상황: 동기 REST의 강한 결합 해소, 높은 처리량, 피크 부하 완충
트리거 기술: soap, rpc, corba, mq, tibco, activemq, jms
핵심 아이디어: 이벤트 브로커(Kafka/Kinesis/Pub/Sub)를 허브로
              → 서비스는 이벤트를 발행만 하고 소비자는 독립 처리
              → Outbox Pattern으로 트랜잭션 원자성 보장

장점: 느슨한 결합, 비동기 확장성, 이벤트 재처리·감사
트레이드오프: 최종 일관성, 디버깅 복잡도, 이벤트 스키마 관리
```

#### CQRS + 이벤트 소싱

```
적용 상황: 강력한 감사 추적(금융·규제), 복잡한 비즈니스 규칙, 읽기 부하 압도적
트리거 기술: audit, compliance, banking, finance, accounting, trading
핵심 아이디어: Command 사이드 → 이벤트를 이벤트 스토어에 저장
              Query 사이드 → 읽기 최적화된 프로젝션 유지
              이벤트 리플레이로 상태 재구성·타임 트래블 디버깅

장점: 완전한 감사 추적, 읽기/쓰기 독립 최적화
트레이드오프: 최종 일관성, 구현 복잡도, 이벤트 스키마 진화 어려움
```

#### 데이터 레이크하우스 (Data Lakehouse)

```
적용 상황: 레거시 DW와 Data Lake를 단일 플랫폼으로 통합, ML 데이터 준비
트리거 기술: hadoop, hive, teradata, netezza, oracle dw, etl
핵심 아이디어: Delta Lake/Iceberg/Hudi로 오브젝트 스토리지에 ACID 레이어
              Bronze(원시) → Silver(정제) → Gold(집계) 3계층 구조
              Spark/Trino 통합 쿼리 엔진

장점: 단일 데이터 플랫폼, 실시간+배치 통합, 비용 효율적 스토리지
트레이드오프: 운영 복잡도, 메타데이터 관리, 초기 설계 중요
```

#### 데이터 메시 (Data Mesh)

```
적용 상황: 대규모 조직에서 중앙 데이터 팀 병목, 도메인별 데이터 요구사항 다양
트리거 기술: data warehouse, data lake, analytics, reporting, bi
핵심 아이디어: 도메인별 데이터 제품 팀이 데이터를 소유·제공
              셀프서비스 데이터 플랫폼(인프라 추상화)
              연합 거버넌스(공통 표준 + 도메인 자율성)

장점: 도메인 자율성, 데이터 품질 책임 명확화, 조직 확장성
트레이드오프: 거버넌스 복잡도, 표준화 어려움, 조직 변화 관리 필요
```

### API & 게이트웨이 패턴

#### API Gateway / BFF (Backend for Frontend)

```
적용 상황: 다양한 클라이언트(모바일·웹·파트너)가 각각 다른 API 형태 요구
트리거 기술: mobile, web, partner api, public api, multiple clients
핵심 아이디어: API Gateway로 인증·라우팅·속도 제한 통일
              클라이언트 유형별 BFF 서비스로 응답 집계·변환
              GraphQL Federation 또는 REST 집계

장점: 클라이언트 분리, 중앙화된 보안·정책, 백엔드 API 단순화
트레이드오프: 단일 장애점 가능성, BFF 증식, 캐싱 레이어 관리
```

#### 서비스 메시 (Service Mesh)

```
적용 상황: 20개 이상 마이크로서비스, Kubernetes 환경, Zero-Trust 보안 요구
트리거 기술: kubernetes, k8s, microservices, docker, container
핵심 아이디어: Istio/Linkerd/Envoy 사이드카 프록시
              → 트래픽 관리·mTLS·분산 추적을 인프라 레벨로 분리
              → 중앙 컨트롤 플레인으로 정책 통일

장점: Zero-Trust 트래픽 보안, 관찰 가능성 자동화, 트래픽 제어
트레이드오프: 운영 복잡도, 사이드카 오버헤드, 러닝 커브
```

### 보안 패턴

#### 제로 트러스트 보안 (Zero Trust)

```
적용 상황: 금융·의료·공공 등 규제 환경, 원격근무, 내부망 신뢰 모델 한계
트리거 기술: firewall, vpn, iam, ldap, active directory, pci, hipaa
핵심 아이디어: "신뢰하지 말고 항상 검증"
              Identity-centric 접근 제어
              마이크로 세그멘테이션으로 폭발 반경 제한
              JIT/PAM 최소 권한 + ZTNA·mTLS·디바이스 상태 지속 검증

장점: 내부자 위협 방어, 규제 컴플라이언스, 침해 시 폭발 반경 최소화
트레이드오프: 사용자 경험 마찰, 구현 비용, 레거시 통합 어려움
```

### 관찰 가능성 & 운영 패턴

#### 관찰 가능성 — OpenTelemetry

```
적용 상황: 마이크로서비스 전환 후, SRE 조직 도입, 분산 시스템 장애 대응
트리거 기술: log, logging, monitor, apm, nagios, zabbix, sentry
핵심 아이디어: OpenTelemetry SDK로 계측 표준화
              Distributed Tracing(Jaeger/Zipkin)으로 요청 흐름 추적
              Prometheus+Grafana 메트릭 시각화
              중앙 로그 집계(ELK/Loki)

장점: MTTR 단축, 프로액티브 이상 탐지, SLO/SLA 측정 기반
트레이드오프: 스토리지 비용, 계측 코드 추가, 데이터 보존 정책
```

#### 피처 플래그 / 점진적 롤아웃 (Feature Flag)

```
적용 상황: 배포 빈도 높음, 대규모 사용자 기반, A/B 실험 필요
트리거 기술: jenkins, gitlab, bamboo, teamcity, canary, blue-green
핵심 아이디어: LaunchDarkly/OpenFeature 피처 플래그 시스템
              → 코드 배포와 기능 출시를 런타임에 분리
              → Canary/Blue-Green/A-B 배포와 연동
              → 킬 스위치로 즉각 롤백

장점: 무위험 배포, 사용자 세그먼트 실험, 즉시 롤백
트레이드오프: 플래그 부채 관리, 테스트 복잡도, 코드 분기 증가
```

#### CI/CD / DevOps 자동화

```
적용 상황: 수동 배포 프로세스, 긴 릴리스 주기(월·분기), 배포 공포가 있는 조직
트리거 기술: jenkins, gitlab, svn, cvs, ant, maven, ftp, manual, bamboo
핵심 아이디어: 소스 제어(Git) → 자동 빌드 → 자동 테스트 →
              컨테이너 이미지 빌드 → GitOps(Argo CD/Flux) 자동 배포
              환경별 파이프라인(dev→staging→prod) + 품질 게이트

장점: 배포 빈도 향상(일 수회), 인적 오류 제거, 환경 일관성
트레이드오프: 파이프라인 구축 초기 비용, 테스트 커버리지 투자 필요
```

#### 코드형 인프라 (Infrastructure as Code)

```
적용 상황: 클라우드 전환, 멀티 환경 일관성, 수동 서버 구성이 병목인 조직
트리거 기술: vmware, vsphere, datacenter, ansible, puppet, chef, aws, azure
핵심 아이디어: Terraform/Pulumi/CloudFormation으로 선언형 인프라 코드
              Git 버전 관리 + CI/CD로 인프라 변경을 코드 리뷰 후 자동 적용
              불변 인프라(Immutable Infrastructure) 원칙으로 Snowflake Server 제거

장점: 환경 완전 재현성, 인프라 변경 감사 추적, 클라우드 전환 가속
트레이드오프: IaC 코드 학습 비용, Terraform 상태 파일 관리
```

#### Cache-Aside 패턴

```
적용 상황: 읽기/쓰기 비율 > 3:1, DB 과부하, 세션 상태 외부화 필요
트리거 기술: oracle, sql, mysql, session, performance, bottleneck, slow
핵심 아이디어: 애플리케이션이 캐시를 우선 조회 → 미스 시 DB 조회 후 캐시 저장
              Redis/Memcached를 세션·쿼리 결과·정적 데이터 캐시로 도입
              TTL 기반 만료와 명시적 캐시 무효화 전략 설계

장점: 응답 지연 대폭 감소, DB 부하 절감(읽기 요청의 70~90%)
트레이드오프: 캐시 스탈리니스, TTL 튜닝 필요, 분산 환경 무효화 복잡도
```

---

## 11. AX 패턴 11개 상세

AI/ML 관련 기술 스택(LLM, machine learning, embedding 등)이 감지될 때 자동으로 선별됩니다.

### 지식 증강 & 검색 패턴

#### RAG (Retrieval-Augmented Generation)

```
적용 상황: 기업 내부 문서 기반 AI 어시스턴트, 고객 지원 자동화, 규제 QA
트리거 기술: document, knowledge base, search, faq, chatbot, content
핵심 아이디어: Vector DB(Pinecone/Weaviate/pgvector)에 기업 문서 임베딩 인덱싱
              질의 시 관련 청크를 검색해 LLM 컨텍스트에 주입
              Reranker로 검색 품질 향상

장점: 환각 감소, 도메인 특화 정확도, 지식 최신성
트레이드오프: 검색 지연, 임베딩 비용, 청크 전략 튜닝 필요
```

#### 시맨틱 캐시 (Semantic Cache)

```
적용 상황: 반복적 질의 패턴이 많은 서비스, LLM 비용이 주요 부담
트리거 기술: llm, gpt, openai, chatbot, claude, gemini, embedding, vector
핵심 아이디어: 질의를 임베딩해 Vector DB에서 유사도 검색
              cosine similarity > 0.95이면 캐시 응답 반환
              GPTCache/Redis Vector 활용

장점: LLM 비용 40~80% 절감, 응답 지연 감소, 처리량 향상
트레이드오프: 임계값 튜닝, 캐시 무효화 전략, 임베딩 비용
```

### MLOps & 모델 운영 패턴

#### MLOps 파이프라인

```
적용 상황: 다수 ML 모델 운영, 모델 배포 주기 단축, 데이터·모델 드리프트 탐지
트리거 기술: machine learning, ml, model, training, prediction, analytics
핵심 아이디어: Feature Store → 학습 파이프라인(Kubeflow/SageMaker) →
              모델 레지스트리(MLflow) → 서빙(Triton/TorchServe) →
              모니터링(데이터·모델 드리프트 탐지)

장점: 실험 재현성, 자동 배포, 드리프트 조기 탐지
트레이드오프: 인프라 복잡도, 초기 설정 비용, 플랫폼 학습 비용
```

#### 피처 스토어 (Feature Store)

```
적용 상황: 여러 ML 모델이 동일 피처 공유, 실시간 추론 < 100ms, 피처 중복 계산 문제
트리거 기술: machine learning, ml, feature engineering, real-time prediction
핵심 아이디어: 온라인 스토어(Redis/DynamoDB) — 저지연 실시간 피처
              오프라인 스토어(S3/BigQuery) — 학습 데이터셋 생성
              피처 버전 관리·계보 추적

장점: Training-Serving Skew 제거, 피처 재사용, 실험 가속
트레이드오프: 추가 인프라, 피처 거버넌스 필요, 초기 마이그레이션
```

#### LLM 파인튜닝 / PEFT

```
적용 상황: 특정 형식 출력·분류·추출 태스크, RAG로 해결 안 되는 패턴 인식
트리거 기술: huggingface, bert, transformers, nlp, classification, extraction, llm
핵심 아이디어: LoRA/QLoRA로 파라미터 효율적 파인튜닝 (전체의 0.1~1% 파라미터만)
              도메인 데이터 수집 → SFT → RLHF/DPO 선호도 정렬
              OpenAI Fine-tuning, AWS Bedrock, Hugging Face PEFT 활용

장점: 도메인 특화 정확도, 응답 일관성, 작은 모델로 동등 이상 성능
트레이드오프: 데이터 수집·레이블링 비용, 재학습 주기, 모델 업그레이드 시 재파인튜닝
```

### AI 거버넌스 & 안전 패턴

#### AI 모델 게이트웨이 (AI Model Gateway)

```
적용 상황: 여러 서비스가 LLM 사용, AI 비용 통제, 기업 보안·컴플라이언스
트리거 기술: openai, llm, gpt, claude, gemini, ai api, language model
핵심 아이디어: 중앙 AI Gateway(LiteLLM/OpenRouter/자체 구축)
              모델 라우팅(비용·지연·능력 기반)
              PII 마스킹·콘텐츠 필터링
              사용량 추적·청구

장점: 중앙화된 AI 거버넌스, 비용 최적화, 모델 교체 투명화
트레이드오프: 단일 장애점, 추가 지연, 게이트웨이 유지보수
```

#### LLM 가드레일 (LLM Guardrails)

```
적용 상황: 고객 대면 AI 서비스, 금융·의료·공공 규제 산업, 다중 사용자 AI 플랫폼
트리거 기술: llm, gpt, openai, claude, pii, gdpr, hipaa, injection
핵심 아이디어:
  입력 가드레일: 프롬프트 인젝션 탐지, PII 마스킹, 입력 길이·토큰 제한
  출력 가드레일: 유해 콘텐츠 필터(NeMo Guardrails), 구조 검증, 사실 기반 점수
  AI Gateway에 통합해 단일 진입점으로 적용
  모든 입출력 감사 로그 보존

장점: 프롬프트 인젝션 방어, PII 유출 방지, 규제 컴플라이언스
트레이드오프: 추가 지연(10~50ms), 과도 필터링 오탐, 필터 규칙 유지보수
```

#### AI 관찰 가능성 (AI Observability)

```
적용 상황: 프로덕션 LLM 서비스, AI 품질 SLA, 멀티 모델 비용 비교, 프롬프트 버전 관리
트리거 기술: llm, gpt, openai, claude, langchain, llamaindex, chatbot, embedding
핵심 아이디어: LLM 추적: 모든 프롬프트·응답·토큰·지연·모델 버전 로깅 (LangFuse/Helicone)
              품질 자동 평가: 응답 관련성·사실성·독성을 LLM-as-Judge로 측정
              프롬프트 버전 관리: A/B 테스트·롤백 가능
              비용 대시보드: 모델별·기능별 토큰 비용 분석

장점: 환각 조기 감지, 프롬프트 최적화 근거, 비용 이상 조기 경보
트레이드오프: 추가 로깅 비용, PII 보존 규정 충돌 가능, 계측 코드 추가
```

### 자동화 & 레거시 통합 패턴

#### 에이전틱 AI 플랫폼 (Agentic AI Platform)

```
적용 상황: 반복적 복잡 업무 자동화, RPA 한계 돌파, 지식 집약적 프로세스
트리거 기술: automation, workflow, rpa, process, bpm, orchestration
핵심 아이디어: ReAct/Plan-and-Execute 패턴으로 LLM이 도구를 자율 선택·실행
              도구: 검색·코드 실행·DB 쿼리·외부 API
              멀티 에이전트 오케스트레이션(LangGraph/CrewAI)
              인간 승인 게이트 통합

장점: 복잡 업무 자동화, 24/7 운영, 인간 오류 감소
트레이드오프: 비결정론적 동작, 비용 예측 어려움, 안전 장치 설계 필요
```

#### Human-in-the-Loop (HITL)

```
적용 상황: 금융·의료·법무 고위험 의사결정, 규제 감사, AI 신뢰도 구축 초기
트리거 기술: compliance, audit, medical, financial, legal, fraud, kyc, aml
핵심 아이디어: 신뢰도 임계값 기반 자동/수동 분기
              검토 큐(대시보드)로 불확실 케이스를 인간에게 라우팅
              인간 피드백을 Active Learning으로 모델 개선에 활용

장점: AI 오류 안전망, 규제 컴플라이언스, 모델 지속 개선
트레이드오프: 처리 지연, 인간 리뷰 비용, 큐 적체 관리
```

#### AI 증강 레거시 서비스 (AI-Augmented Legacy)

```
적용 상황: 레거시 교체 불가(규제·비용·위험), 빠른 AI 도입 요구, 단계적 현대화
트리거 기술: mainframe, cobol, legacy, esb, soap, as400, rpg
핵심 아이디어: 레거시 API 앞에 AI 레이어 삽입(Facade)
              자연어 → 레거시 명령 변환
              레거시 출력에 AI 분석·요약 추가
              이상 탐지·예측 분석을 별도 서비스로 추가

장점: 레거시 투자 보호, 빠른 AI 가치 실현, 단계적 현대화
트레이드오프: 두 레이어 유지보수, 레거시 결합 유지, 성능 오버헤드
```

---

## 12. 8대 아키텍처 관점 — 멀티 퍼스펙티브

`analyze` 완료 후 실행되는 **2차 LLM 패스**입니다. 8개 전문가 관점에서 동일한 레거시 시스템과 1차 분석 결과를 교차 검증해, 단일 LLM 패스의 편향을 보정합니다.

### 12.1 분석 흐름

```
1차 분석 완료 (analyze_stream Pass 1)
   └─ ANALYZE_SYSTEM_PROMPT → AnalysisResult (health_score, component_decisions, ...)

8대 관점 2차 분석 (analyze_stream Pass 2)
   └─ MULTI_PERSPECTIVE_PROMPT 입력:
        - 레거시 시스템: {compress_system_dict(system, MAX_SYSTEM_CHARS)}
        - 1차 분석 요약: health_score, recommended_scenario, pain_points[:5], tech_debt[:5]
      출력: MultiPerspectiveAnalysis
        ├── perspectives: list[PerspectiveView]  ← 8개 관점 각각
        ├── consensus_summary                    ← 합의 결론 (1~2문단)
        ├── priority_actions                     ← 즉시 조치 상위 5개
        └── conflict_areas                       ← 관점 간 충돌·트레이드오프

현대화 검증 (modernize_stream 중 별도 패스)
   └─ MULTI_PERSPECTIVE_DESIGN_PROMPT → 8대 관점에서 현대화 설계 검증
```

### 12.2 8대 관점 상세

#### 🔒 보안 (Security)

```
평가 초점:
  - 인증·인가 취약점 (BasicAuth, 평문 전송, 세션 고정)
  - 암호화 갭 (전송·저장 시 미암호화, 약한 알고리즘)
  - CVE 보유 EOL 컴포넌트 (OpenSSL, Log4j 취약 버전)
  - 컴플라이언스 갭 (PCI-DSS, HIPAA, ISO27001, GDPR)
  - 내부 네트워크 취약점 (과도한 내부망 신뢰, 포트 노출)
  - 권한 관리 (과도한 DB 권한, 공유 계정, 비밀 하드코딩)

출력 예시:
  findings: ["Oracle 11g에 CVE-2023-xxxx 미패치", "HTTP BasicAuth 평문 전송"]
  recommendations: ["WAF 도입", "비밀 관리자(AWS Secrets Manager) 도입"]
  priority: high
```

#### ⚡ 성능 (Performance)

```
평가 초점:
  - 응답 지연 병목 (N+1 쿼리, 인덱스 부재, 락 경합)
  - 처리량 한계 (단일 서버, 수평 확장 불가)
  - 캐싱 부재 (매 요청 DB 풀 조회, 세션 서버 내 저장)
  - 배치 처리 병목 (야간 배치가 OLTP와 리소스 경쟁)
  - 네트워크 지연 (원거리 DB 호출, 동기 체이닝)

출력 예시:
  findings: ["Oracle RAC 락 경합으로 P99 응답 8초", "세션 메모리 수평 확장 불가"]
  recommendations: ["Redis 세션 외부화", "읽기 전용 레플리카 도입"]
```

#### 📈 확장성 (Scalability)

```
평가 초점:
  - 수평 확장 가능성 (Stateful vs Stateless 서버)
  - 데이터베이스 확장 한계 (수직 확장 의존, 샤딩 부재)
  - 트래픽 급증 대응 (Auto-scaling, 서킷 브레이커)
  - 스토리지 확장성 (로컬 파일시스템 의존)
  - 큐 기반 부하 분산 (동기 처리로 인한 처리량 한계)
```

#### 💰 비용 (Cost)

```
평가 초점:
  - 라이선스 비용 (Oracle, WebSphere, IBM 라이선스 규모)
  - 운영 비용 (온프레미스 데이터센터 유지비, 인력)
  - 클라우드 전환 비용 절감 예상 (Managed Service 도입)
  - 과잉 리소스 프로비저닝 (고정 용량 vs 탄력적 과금)
  - 기술 부채 유지 비용 (EOL 컴포넌트 보안 패치 비용)

출력 예시:
  findings: ["Oracle RAC + WebSphere 라이선스 연 50억+", "온프레미스 데이터센터 연 20억"]
  recommendations: ["Aurora PostgreSQL 전환으로 라이선스 60% 절감 예상"]
```

#### 🔧 유지보수성 (Maintainability)

```
평가 초점:
  - 기술 부채 (레거시 코드 복잡도, 문서 부재)
  - 팀 역량 (COBOL 개발자 수급, 레거시 기술 의존)
  - 테스트 커버리지 (자동화 테스트 부재, 수동 회귀 테스트)
  - 배포 복잡도 (수동 배포, 빌드 자동화 부재)
  - 모니터링·디버깅 용이성 (로그 분산, 추적 불가)
```

#### 📋 거버넌스 (Governance)

```
평가 초점:
  - 데이터 규제 (GDPR 개인정보 처리, 데이터 주권)
  - 감사 추적 (변경 이력, 접근 로그 보존 기간)
  - 데이터 분류 (PII·기밀 데이터 식별 및 보호)
  - 변경 관리 프로세스 (승인 워크플로우, 변경 기록)
  - 규제 준수 보고 (SOC2, ISO27001, PCI-DSS 감사)

출력 예시:
  findings: ["GDPR 데이터 삭제 요청 처리 메커니즘 부재", "접근 로그 30일만 보존"]
  recommendations: ["감사 로그 장기 보존(7년)", "데이터 분류 레이블링 도입"]
```

#### 🔗 통합 (Integration)

```
평가 초점:
  - 외부 시스템 연동 (ESB/SOA 기반 레거시 인터페이스)
  - API 호환성 (구버전 SOAP/XML API 유지 필요성)
  - 파트너 연동 (EDI, B2B 게이트웨이, 표준 프로토콜)
  - 내부 시스템 의존성 (밀결합 인터페이스, 공유 DB)
  - 이벤트 스트리밍 가능성 (실시간 데이터 공유 요구)

출력 예시:
  findings: ["SOAP/XML 인터페이스 40개, 파트너 10곳 의존"]
  recommendations: ["API Gateway로 인터페이스 통일", "이벤트 브로커로 실시간 연동 전환"]
```

#### 🛡️ 복원력 (Resilience)

```
평가 초점:
  - 단일 장애점 (SPOF — 이중화 없는 핵심 컴포넌트)
  - 장애 격리 (하나의 장애가 전체로 전파되는 구조)
  - Circuit Breaker (연쇄 장애 방지 메커니즘)
  - DR 계획 (RTO/RPO 목표, 백업·복구 절차)
  - 가용성 SLA (99.9% vs 99.99% 요구사항)

출력 예시:
  findings: ["단일 Oracle RAC SPOF", "배치 실패 시 수동 재기동 필요"]
  recommendations: ["Multi-AZ 배포", "배치 실패 자동 재시도·알림 구성"]
```

### 12.3 출력 — MultiPerspectiveAnalysis

```json
{
  "perspectives": [
    {
      "perspective": "security",
      "findings": ["Oracle 11g CVE-2023-xxxx 미패치", "BasicAuth 평문 전송"],
      "recommendations": ["WAF 도입", "TLS 강제화", "Secrets Manager 도입"],
      "priority": "high"
    },
    {
      "perspective": "cost",
      "findings": ["Oracle+WebSphere 라이선스 연 50억+"],
      "recommendations": ["Aurora PostgreSQL 전환으로 60% 절감 예상"],
      "priority": "high"
    }
    // ... 8개 관점 전체
  ],
  "consensus_summary": "시스템 전반에 걸쳐 보안·비용·확장성이 가장 시급한 과제입니다. Oracle 11g EOL과 WebSphere 레거시가 보안·라이선스 양면에서 최대 위험 요인이며, 마이크로서비스 전환과 클라우드 이전이 8개 관점 중 6개에서 공통 권고됩니다.",
  "priority_actions": [
    "Oracle 11g → Aurora PostgreSQL 전환 (보안·비용·성능 동시 해결)",
    "WebSphere → ECS/Fargate 컨테이너화 (배포 자동화·확장성)",
    "BasicAuth → OAuth2/OIDC 전환 (보안·거버넌스)",
    "단일 장애점 이중화 (복원력 SLA 99.9% 달성)",
    "CI/CD 파이프라인 도입 (유지보수성·배포 속도)"
  ],
  "conflict_areas": [
    "보안 강화(Zero Trust, mTLS)와 성능 오버헤드 간 트레이드오프",
    "CQRS 도입의 감사 추적 이점 vs 구현 복잡도 vs 팀 역량"
  ]
}
```

### 12.4 현대화 설계 검증 (Design Perspective)

modernize 완료 후 추가로 **현대화된 설계를 8대 관점에서 재검증**합니다.

```
입력: 레거시 시스템 + 현대화 설계 + 1차 분석 결과
프롬프트: MULTI_PERSPECTIVE_DESIGN_PROMPT
출력 저장: AppSession.design_perspective
웹 UI 위치: 아코디언 리포트 패널 "설계 검증" 섹션
```

**활용**: 현대화 설계에서 놓친 관점(예: 비용 초과, 거버넌스 갭)을 사전에 발견하고 `design_rationale.json`에 반영합니다.

> **팀 협업 활용**: `priority_actions`는 스프린트 계획의 우선순위 입력으로, `conflict_areas`는 아키텍처 의사결정 회의의 의제로 활용하세요.
