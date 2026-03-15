# ArchPilot — LLM 지식·그라운딩 체계

> AI 분석과 현대화 설계의 품질이 결정되는 원리

**Version**: 0.2.3 | **Last Updated**: 2026-03-15

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

⚠ "대형 시스템: 12개 컴포넌트의 metadata/specs를 제거했습니다"
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
- 내부 구현 상세: [`ARCHITECTURE.md`](./6_ARCHITECTURE.md) — Section 2.5 (LLM Client), 2.11 (Web UI)
- 소스 코드:
  - `src/archpilot/llm/analyzer.py` — analyze() 구현
  - `src/archpilot/llm/modernizer.py` — modernize() CLI 경로
  - `src/archpilot/ui/routers/analyze.py` — 분석 Web UI 경로
  - `src/archpilot/ui/routers/modernize.py` — 현대화 Web UI 경로 (4-pass RMC)
  - `src/archpilot/llm/utils.py` — compress_model/compress_analysis/compress_for_plan
