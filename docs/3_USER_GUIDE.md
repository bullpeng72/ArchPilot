# ArchPilot — 사용자 가이드

> 설치부터 발표 자료까지 — 단계별 워크플로우

**Version**: 0.2.5 | **Last Updated**: 2026-03-16

---

## 목차

1. [설치 및 초기 설정](#1-설치-및-초기-설정)
2. [워크플로우 선택 가이드](#2-워크플로우-선택-가이드)
3. [시나리오 A — YAML 파일로 시작](#3-시나리오-a--yaml-파일로-시작)
4. [시나리오 B — draw.io Desktop으로 시작](#4-시나리오-b--drawio-desktop으로-시작)
5. [시나리오 C — 자연어 텍스트로 시작](#5-시나리오-c--자연어-텍스트로-시작)
6. [시나리오 D — 인터랙티브 웹 앱으로 시작](#6-시나리오-d--인터랙티브-웹-앱으로-시작)
7. [AI 분석 심화](#7-ai-분석-심화)
8. [현대화 설계 심화](#8-현대화-설계-심화)
9. [시나리오 기반 현대화](#9-시나리오-기반-현대화)
10. [발표 자료 생성](#10-발표-자료-생성)
11. [출력 파일 구조](#11-출력-파일-구조)
12. [FAQ](#12-faq)

> **새 기능 (v0.2.4)**: §8.5 [현대화 설계 부분 수정](#85-부분-수정-patch-모드)  — 기존 결과를 유지하며 피드백으로 최소 수정

---

## 1. 설치 및 초기 설정

### 1.1 설치

```bash
pip install archpilot

# PNG 다이어그램이 필요한 경우
pip install graphviz
brew install graphviz        # macOS
sudo apt install graphviz   # Ubuntu/Debian
```

### 1.2 초기화

```bash
archpilot init
```

실행하면 `~/.archpilot/config.env` 전역 설정 파일 생성 마법사가 시작됩니다:

```
ArchPilot 초기화 마법사

OpenAI API Key (sk-...):        ← 입력 내용이 화면에 표시되지 않습니다 (보안)
사용할 모델 [gpt-4o-mini]: ↵
출력 디렉토리 [/home/yourname/project/output]: ↵

✅ 설정 파일이 생성되었습니다: /home/yourname/.archpilot/config.env
```

생성된 `~/.archpilot/config.env`:
```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=4096
ARCHPILOT_OUTPUT_DIR=/home/yourname/project/output
ARCHPILOT_DIAGRAM_FORMAT=png
ARCHPILOT_SERVER_HOST=127.0.0.1
ARCHPILOT_SERVER_PORT=8080
```

> **고품질 분석이 필요한 경우** `OPENAI_MODEL=gpt-4o` 로 변경하세요.
> **팁**: 전역 설정은 어느 디렉토리에서 실행해도 자동 로드됩니다.
> 프로젝트별 다른 설정이 필요하면 해당 디렉토리에 `.env`를 만들면 전역 설정을 오버라이드합니다.

---

## 2. 워크플로우 선택 가이드

모든 시나리오는 동일한 3단계 파이프라인을 거칩니다:

```
입력 → ingest → analyze → modernize → serve → 발표
```

**입력 방법 선택:**

| 상황 | 시나리오 |
|------|---------|
| YAML/JSON 파일이 있음 | A — YAML 파일 |
| draw.io 다이어그램이 있음 | B — draw.io |
| 텍스트 문서/메모만 있음 | C — 자연어 텍스트 |
| 아무것도 없고 CLI 없이 진행 | D — 웹 앱 채팅 |

---

## 3. 시나리오 A — YAML 파일로 시작

가장 정확하고 권장되는 방법. YAML로 시스템을 직접 기술합니다.

### Step 1: YAML 작성

YAML 작성 방법은 [`SCHEMA.md`](./2_SCHEMA.md)를 참조하세요. 빠른 시작용 최소 예제:

```yaml
name: "E-Commerce Legacy System"
description: "2015년 구축된 온프레미스 모놀리식 쇼핑몰"

components:
  - id: web
    type: server
    label: "Apache Web Server"
    tech: ["Apache 2.4", "PHP 7.2"]
    host: on-premise
    lifecycle_status: deprecated

  - id: app
    type: server
    label: "Monolithic App Server"
    tech: ["Java 8", "Spring MVC", "Tomcat 8"]
    criticality: high

  - id: db_master
    type: database
    label: "MySQL Master"
    tech: ["MySQL 5.7"]
    lifecycle_status: eol
    data_classification: restricted

connections:
  - from_id: web
    to_id: app
    protocol: HTTP
  - from_id: app
    to_id: db_master
    protocol: JDBC
```

또는 제공된 예제 파일 사용:
```bash
ls examples/
# legacy_bank.yaml                    # 코어뱅킹 레거시 (9개 컴포넌트)
# legacy_ecommerce.yaml               # 온프레미스 쇼핑몰 모놀리스
# hybrid_cloud_government.yaml        # 공공기관 하이브리드 클라우드
# hybrid_cloud_hospital.yaml          # 의료기관 하이브리드 클라우드
# hybrid_cloud_manufacturing.yaml     # 제조업 MES/ERP 하이브리드
# large_scale_fintech.yaml            # 대규모 핀테크 (20개+ 컴포넌트)
# large_scale_logistics.yaml          # 대규모 물류 플랫폼
# large_scale_streaming_platform.yaml # 대규모 스트리밍 서비스
```

### Step 2: ingest

```bash
archpilot ingest examples/legacy_bank.yaml --format mermaid,drawio
```

**옵션:**
```
--output, -o    출력 디렉토리 (기본: settings.output_dir)
--format, -f    출력 포맷: mermaid,png,svg,drawio (기본: mermaid)
--no-llm        LLM 비활성화 (YAML/JSON 전용, .txt 불가)
--force         기존 출력 덮어쓰기 (확인 프롬프트 생략)
```

**출력:**
```
📂 파일 파싱 중: examples/legacy_bank.yaml
🎨 다이어그램 생성 중: mermaid, drawio

        ArchPilot — Ingest 완료
 항목          값
 시스템        Core Banking Legacy System
 설명          2005년 구축된 온프레미스 코어뱅킹 시스템
 컴포넌트 수   9
 연결 수        8
 system.json   output/system.json
 ──────────────────────────────────────
 mermaid        ✅ output/legacy/diagram.mmd
 drawio         ✅ output/legacy/diagram.drawio

⚠  EOL/Deprecated 컴포넌트 3개: Oracle DB (운영), 웹 포털 (IIS), 배치 처리 서버
🔴 HIGH 중요도 컴포넌트 2개: 코어 뱅킹 서버, HSM (암호화 모듈)
🔒 민감 데이터 컴포넌트 1개: Oracle DB (운영)

다음 단계: archpilot analyze output/system.json
```

### Step 3: analyze (현대화 목표 포함 권장)

```bash
archpilot analyze output/system.json \
  -r "AWS 클라우드 전환, 마이크로서비스 분리, Oracle 비용 절감, 제로 다운타임"
```

**옵션:**
```
--requirements, -r   현대화 목표 (component_decisions 품질에 직접 영향)
--output, -o         분석 결과 저장 디렉토리 (기본: system.json 위치)
--verbose, -v        문제점·기술부채·현대화 기회 전체 목록 출력
```

`-r`(요구사항) 없이 분석하면 AI가 목표를 모르는 상태에서 6R 결정을 내립니다.
동일한 요구사항으로 `analyze`와 `modernize`를 실행하면 결과의 일관성이 높아집니다.

### Step 4: modernize

```bash
archpilot modernize output/system.json \
  -r "AWS 클라우드 전환, 마이크로서비스 분리, Oracle 비용 절감, 제로 다운타임"
```

`output/analysis.json`이 있으면 자동으로 참조해 `recommended_scenario`와 `component_decisions`를 LLM에 제공합니다.

### Step 5: serve

```bash
archpilot serve output/ --open
```

---

## 4. 시나리오 B — draw.io 파일로 시작

draw.io로 작성된 다이어그램을 ArchPilot 입력으로 사용하는 방법입니다.
자세한 내용은 [`DRAWIO.md`](./5_DRAWIO.md)를 참조하세요.

> **이미 .drawio 파일이 있다면 빠른 시작:**
> ```bash
> archpilot ingest ~/Desktop/my-diagram.drawio
> archpilot analyze output/system.json -r "현대화 목표"
> archpilot modernize output/system.json -r "현대화 목표"
> archpilot serve output/ --open
> ```
> draw.io Desktop 설치 없이도 즉시 사용 가능합니다. → Step 3으로 바로 이동

---

### Step 0: draw.io에서 시스템 그리기 (신규 작성 시)

draw.io Desktop 또는 [diagrams.net](https://www.diagrams.net)에서 시스템 토폴로지를 그립니다.

**draw.io 파일 준비 방법별 안내:**

| 방법 | 설명 | Step |
|------|------|------|
| 이미 .drawio 파일 있음 | 파일 바로 사용 | Step 3으로 이동 |
| draw.io Desktop에서 새로 그리기 | Desktop 설치 후 ArchPilot 팔레트 활용 | Step 1 → Step 2 순서 |
| diagrams.net(웹)에서 그리기 | 브라우저에서 직접 그린 후 XML 저장 | Step 0.1 후 Step 3 |
| Web UI 내장 편집기 | `archpilot serve` 후 편집 탭 | Step 0.2 후 분석 진행 |

**Step 0.1 — diagrams.net(웹) 사용 시:**
```
diagrams.net에서 그리기
→ File → Export As → XML (또는 Extras → Edit Diagram → 전체 복사)
→ .drawio 파일로 저장
→ Step 3으로 이동
```

**Step 0.2 — Web UI 내장 편집기 사용 시:**
```bash
archpilot serve output/ --open
```
브라우저 → `🖊 편집` 탭 → draw.io 편집기에서 그리기 → **Save** 클릭
→ 자동으로 system.json 생성됨 → 분석/현대화 탭에서 바로 진행 가능

---

### Step 1: draw.io Desktop 초기 설정 (최초 1회, Desktop 사용 시)

```bash
# draw.io Desktop이 완전히 종료된 상태에서
archpilot drawio setup
```

### Step 2: draw.io Desktop에서 그리기 (Desktop 사용 시)

draw.io Desktop을 실행하면 ArchPilot 팔레트가 사이드바에 표시됩니다.

**핵심 규칙:**
- 레이블 둘째 줄에 기술명 입력 → ComponentType 자동 추론
- 수영 레인(swimlane) 레이블을 `on-premise`, `AWS Cloud`, `Azure` 등으로 설정 → HostType 자동 추론
- 화살표 레이블에 프로토콜 입력 (HTTP, JDBC, gRPC 등)

### Step 3: ArchPilot에 반영

**방법 1: 파일 직접 ingest** ← 이미 파일이 있는 경우 여기서 시작
```bash
archpilot ingest ~/Desktop/my-diagram.drawio
```

**방법 2: 자동 감시 (권장)**
```bash
archpilot drawio edit --output ./output
# draw.io에서 Ctrl+S 저장 시 자동으로 system.json 갱신
```

### Step 3.5: system.json 직접 보완 (복잡한 시스템 — 선택)

draw.io ingest 후 생성된 `output/system.json`에는 draw.io가 저장할 수 없는 엔터프라이즈 필드가 기본값으로만 채워집니다. 분석 품질을 높이려면 이 단계에서 직접 보완하세요.

**보완이 필요한 필드:**

| 필드 | 기본값 | 보완 예시 |
|------|--------|----------|
| `criticality` | `medium` | `"high"`, `"critical"` |
| `lifecycle_status` | `active` | `"eol"`, `"deprecated"` |
| `data_classification` | `null` | `"restricted"`, `"confidential"` |
| `owner` | `""` | `"DB운영팀"`, `"Core-Platform"` |
| `specs` | `{}` | `{"cpu": 16, "memory": "64GB"}` |
| `metadata` | `{}` | `{"compliance": "PCI-DSS", "last_patch": "2022-03"}` |

```bash
# watch를 종료한 후 편집
# (watch 활성 상태에서 draw.io를 저장하면 system.json이 덮어써짐)
vim output/system.json
```

> 자세한 편집 패턴과 주의사항: [`DRAWIO.md §10.5`](./5_DRAWIO.md#105-복잡한-시스템--drawio--systemjson-직접-편집-워크플로우)

### Step 4~5: 동일

```bash
archpilot analyze output/system.json -r "현대화 목표"
archpilot modernize output/system.json -r "현대화 목표"
archpilot serve output/ --open
```

---

## 5. 시나리오 C — 자연어 텍스트로 시작

다이어그램이나 YAML 없이 텍스트로 시스템을 설명하는 방법입니다.

### Step 1: 텍스트 파일 작성

```bash
cat > my-system.txt << 'EOF'
우리 시스템은 2010년에 구축된 금융권 온프레미스 시스템입니다.

프론트엔드: IIS 8.5 위에서 ASP.NET MVC로 구동
비즈니스 로직: WCF로 구현된 Windows Service
데이터베이스: Oracle 11g (2노드 RAC), ADO.NET으로 접근
파일 서버: NFS 기반 별도 서버에 첨부파일 저장
외부 연계: IBM MQ를 통한 비동기 메시지 처리

알려진 문제:
- 피크 시간대(오전 9~10시) Oracle RAC 락 경합으로 응답 지연
- 보안 패치가 2년째 지연 중
EOF
```

### Step 2: ingest (자동으로 LLM 파싱)

`.txt` 확장자를 감지해 자동으로 LLM 파싱 모드 실행:

```bash
archpilot ingest my-system.txt
```

```
📂 파일 파싱 중: my-system.txt

🤖 AI가 시스템을 분석하는 중...

✅ Ingest 완료: 5개 컴포넌트, 4개 연결
```

> LLM 파싱 비활성화는 `.txt` 파일에는 사용할 수 없습니다 (`--no-llm`은 YAML/JSON 전용).

### Step 3~5: 동일

```bash
archpilot analyze output/system.json -r "클라우드 전환, 마이크로서비스"
archpilot modernize output/system.json -r "클라우드 전환, 마이크로서비스"
archpilot serve output/ --open
```

---

## 6. 시나리오 D — 인터랙티브 웹 앱으로 시작

CLI 없이 브라우저만으로 모든 작업을 처리합니다.

### Step 1: 서버 실행

```bash
archpilot serve output/ --open
```

브라우저가 자동으로 `http://localhost:8080`을 엽니다.

### Step 2: 시스템 입력 (4가지 탭)

**탭 1 — YAML/JSON 텍스트 붙여넣기**

YAML 또는 JSON 텍스트를 입력창에 붙여넣고 "분석 시작" 클릭.

**탭 2 — 파일 업로드**

`.yaml`, `.json`, `.drawio`, `.txt` 파일을 드래그&드롭.

**탭 3 — draw.io XML**

diagrams.net에서 복사한 XML 붙여넣기:
```
diagrams.net → Extras → Edit Diagram → 전체 선택 → 복사
```

**탭 4 — AI 채팅 입력 (권장)**

채팅창에 시스템을 자유롭게 설명하면 AI가 질문하며 정보를 수집합니다:

```
사용자: 우리는 2008년부터 운영해온 물류 회사 시스템입니다.
        WebLogic 12c, EJB 3, Oracle 10g, 전부 온프레미스.
        하루 5만 건 주문, 배포 시 1-2시간 다운타임이 문제입니다.

AI: 감사합니다. 외부 시스템 연계가 있나요?
    (FTP, MQ, API 등)

사용자: IBM MQ로 물류 파트너사와 연계합니다.

AI: [분석 완료] 다음 시스템 모델을 생성했습니다...
    {"__system__": true, "name": "물류 레거시 시스템", ...}
```

JSON을 생성하면 자동으로 시스템 모델이 등록됩니다.

### Step 3: AI 분석 스트리밍

요구사항 입력창에 현대화 목표를 입력 후 "AI 분석 시작":

```
AWS EKS 전환, Oracle → Aurora PostgreSQL, 제로 다운타임 배포
```

실시간으로 스트리밍되는 분석 결과:
- **헬스 스코어** (0~100)
- **핵심 문제점** + **기술 부채** + **보안 취약점**
- **권장 시나리오 배지**: `전체 교체` / `일부 보존` / `신규 추가`
- **컴포넌트별 6R 전략표**
- **레거시 품질 5차원 차트** (성능·확장성·비용·보안·운영성)
- **RMC 자기평가**: 분석의 가정·사각지대·현장 확인 질문

### Step 4: 시나리오 선택 및 현대화

분석 탭 하단에서 시나리오 선택:

```
[ 자동 (AI 권고) ▼ ]   ← 분석 기반 자동 선택

  ○ 자동 (AI 권고)
  ○ 전체 교체 (full_replace)
  ○ 일부 보존 (partial)
  ○ 신규 추가 (additive)
```

"현대화 설계 생성" 클릭 → 5-pass RMC 파이프라인 실행:

**일반 시스템 (20개 미만):**
```
[10%] 새로운 아키텍처를 설계하고 있습니다...
[60%] 시스템 모델을 파싱하고 있습니다...
[65%] 🏛️ 8대 아키텍처 관점에서 설계안을 검증하고 있습니다...
[75%] 마이그레이션 플랜을 작성하고 있습니다...
[88%] 🧠 RMC: 설계 해설을 작성하고 있습니다...
[95%] 🧠 RMC: 마이그레이션 계획을 자기검토하고 있습니다...
[100%] 완료
```

**대형 시스템 (20개 이상 — 2단계 분할 생성):**
```
[8%]  🏗️ 대형 시스템 (N개) — Phase 1: 컴포넌트 구조 설계 중...
[30%] ✅ Phase 1 완료 — Phase 2: 상세 설계 및 연결 생성 중...
[60%] 시스템 모델을 파싱하고 있습니다...
[65%] 🏛️ 8대 아키텍처 관점 설계 검증...
[75%] 마이그레이션 플랜을 작성하고 있습니다...
[88%] 🧠 RMC: 설계 해설...
[95%] 🧠 RMC: 자기검토...
[100%] 완료
```

완료 후 표시되는 정보:
- 신규 아키텍처 Mermaid 다이어그램
- Before/After 컴포넌트 비교표
- 마이그레이션 플랜 (11개 섹션)
- 설계 해설 + 12차원 아키텍처 품질 평가
- 마이그레이션 계획 자기평가

---

## 7. AI 분석 심화

### 7.1 분석 결과 구조

`output/analysis.json` 주요 항목:

```json
{
  "health_score": 42,
  "recommended_scenario": "full_replace",
  "scenario_rationale": "EOL 컴포넌트 비율 78%, 헬스 점수 42/100...",

  "component_decisions": [
    {
      "component_id": "oracle_primary",
      "action": "replace",
      "rationale": "Oracle 11g EOL, Aurora PostgreSQL로 전환",
      "target_component_id": "aurora_postgres",
      "risks": ["데이터 마이그레이션 복잡도"],
      "dependencies": ["core_server"]
    }
  ],

  "legacy_quality": {
    "performance":  {"score": 45, "rationale": "..."},
    "scalability":  {"score": 30, "rationale": "..."},
    "cost":         {"score": 40, "rationale": "..."},
    "security":     {"score": 55, "rationale": "..."},
    "operability":  {"score": 50, "rationale": "..."}
  }
}
```

### 7.2 verbose 출력

```bash
archpilot analyze output/system.json -r "목표" --verbose
```

```
⚠ 문제점
  • Oracle 11g: 2020년 Extended Support 종료, 보안 패치 미적용 상태로 결제 데이터 운영...
  • JBoss EAP 4: 2016년 EOS, 알려진 보안 취약점 CVE-2021-XXXX...

🔧 기술 부채
  [high] oracle_primary: Oracle 11g EOL — CVE-2023-XXXX 미패치...
  [medium] portal: IIS 8.5 mainstream 지원 종료...

💡 현대화 기회
  P1. 데이터베이스: Oracle → Aurora PostgreSQL, 라이선스 비용 60% 절감...
```

### 7.3 분석 결과 검토 포인트

`component_decisions`가 가장 중요합니다. 각 컴포넌트의 `action`과 `rationale`이 실제 상황에 맞는지 확인하세요:

- `retire`로 분류됐지만 실제로 필요한 컴포넌트? → `analysis.json`에서 해당 항목 `action`을 직접 수정
- `keep`으로 분류됐지만 교체해야 하는 컴포넌트? → 마찬가지로 수정 후 modernize 재실행

---

## 8. 현대화 설계 심화

### 8.1 CLI 현대화

```bash
archpilot modernize output/system.json \
  -r "AWS 마이크로서비스, EKS, Aurora PostgreSQL, Redis, 제로 다운타임" \
  --format mermaid,drawio
```

**옵션:**
```
--requirements, -r   현대화 요구사항 (생략 시 대화형 입력)
--output, -o         출력 디렉토리 (기본: system.json 위치)
--format, -f         다이어그램 포맷: mermaid,png,svg,drawio (기본: mermaid)
--scenario, -s       현대화 시나리오: full_replace|partial|additive (미지정 시 분석 결과 권장값 사용)
--no-analysis        analysis.json 자동 참조 건너뜀
```

### 8.2 현대화 출력 확인

```
┌────────────────── ArchPilot — Modernize 완료 ──────────────────┐
│ 신규 시스템    │ E-Commerce Modern System                       │
│ 컴포넌트 수    │ 14                                             │
│ 연결 수        │ 18                                             │
├────────────────┼────────────────────────────────────────────────┤
│ mermaid        │ ✅ output/modern/diagram.mmd                   │
│ migration_plan │ ✅ output/modern/migration_plan.md             │
└────────────────┴────────────────────────────────────────────────┘
```

### 8.3 마이그레이션 플랜 구조 (11개 섹션)

`output/modern/migration_plan.md`:

1. 경영진 요약 (Executive Summary) — 현재 문제·기대 효과·비용 절감 수치
2. 현대화 아키텍처 개요 — Legacy/Modern 컴포넌트 대비표
3. 단계별 마이그레이션 로드맵 — Phase별 목표·작업·기간
4. 컴포넌트 전환 매핑 — 컴포넌트별 전략·위험도
5. 데이터 마이그레이션 계획 — CDC/Dual-write·PII·롤백
6. 보안·규제 준수 계획 — compliance_gaps 해소·security_findings 대응
7. CI/CD 파이프라인 구축
8. 위험 관리 매트릭스
9. 성공 기준 및 KPI
10. 팀 역량 및 교육 계획
11. 롤백 계획 — Blue/Green·Canary 전략

### 8.5 부분 수정 (Patch) 모드

현대화 결과가 이미 있을 때, 전체를 재생성하지 않고 **특정 부분만 수정**할 수 있습니다.

#### 언제 사용하나요?

- 전체 방향은 맞지만 특정 컴포넌트 선택이나 명명이 마음에 들지 않을 때
- 시나리오·요구사항은 그대로 두고 기술 스택만 바꾸고 싶을 때
- 여러 번 반복 수정으로 결과를 점진적으로 개선할 때

#### Web UI에서 사용하기

현대화 완료 후 Step 3 패널 하단에 **"부분 수정"** 토글이 나타납니다:

```
[ 전체 재생성 ]  [ 부분 수정 ← 클릭 ]

피드백 입력:
┌──────────────────────────────────────────────────────┐
│ API Gateway를 AWS API Gateway 대신 Kong으로 변경해줘. │
│ Redis는 ElastiCache 대신 자체 Redis Cluster로.       │
└──────────────────────────────────────────────────────┘

[ 부분 수정 적용 ]
```

#### 동작 방식

```
[10%] 📝 피드백을 반영해 기존 아키텍처를 수정하고 있습니다...
[55%] ✅ 시스템 모델 확정 — 마이그레이션 플랜 재생성 중...
[100%] 완료 (부분 수정)
```

- **변경 금지**: 분석에서 `keep`/`rehost`로 결정된 컴포넌트는 수정하지 않음
- **설계 일관성**: `design_philosophy`, `component_decisions`, `pain_points`를 자동으로 패치 LLM에 주입
- **이력 기록**: 수정 이력이 `patch_history`에 누적됨
- **RMC 재사용**: Design Rationale·자기평가 패스는 이전 결과 재사용 (속도 향상)

#### 현대화 결과 다운로드

부분 수정 후 또는 현대화 완료 후 결과 파일을 바로 다운로드할 수 있습니다:

```
[ YAML 저장 ]  [ draw.io 저장 ]  [ JSON 저장 ]
```

- **YAML**: ArchPilot 표준 입력 포맷으로 저장 (`from_id`/`to_id` → `from`/`to` 변환)
- **draw.io**: 현대화된 다이어그램 XML (draw.io Desktop에서 바로 열기 가능)
- **JSON**: `system.json` 원본 그대로 저장

---

### 8.4 대형 시스템 주의사항

컴포넌트가 **20개 이상**이면 Web UI에서 자동으로 **2단계 분할 생성(Skeleton → Enrich)** 이 실행됩니다:

```
[8%]  🏗️ 대형 시스템 (24개) — Phase 1: 컴포넌트 구조 설계 중...
[30%] ✅ Phase 1 완료 (26개) — Phase 2: 상세 설계 및 연결 생성 중...
```

컨텍스트 한도(`MAX_SYSTEM_CHARS = 40,000`) 초과 시 자동 압축 경고가 표시됩니다:

```
⚠ 대형 시스템: 12개 컴포넌트의 strategy/reason까지 제거했습니다 (LLM 컨텍스트 40,000자 제한)
```

이 경고가 반복되면:
1. 시스템을 서브시스템 단위로 분리해 별도 분석
2. 중요한 정보는 `specs`/`metadata`가 아닌 최상위 필드(`tech`, `criticality` 등)에 기록

---

## 9. 시나리오 기반 현대화

### 9.1 세 가지 시나리오

| 시나리오 | 키 | 적합한 상황 |
|---------|---|-----------|
| 전체 교체 | `full_replace` | EOL 50%+, 헬스 ≤60 |
| 일부 보존 | `partial` | 일부 건강, 일부 교체 |
| 신규 추가 | `additive` | 기존 안정, 새 기능 필요 |

### 9.2 CLI에서 시나리오 결정

CLI에서는 `analysis.json`의 `recommended_scenario`가 자동 적용됩니다.

수동 변경 방법:
```bash
# 1. --scenario 옵션으로 직접 지정 (가장 간단)
archpilot modernize output/system.json -r "요구사항" --scenario partial

# 2. analysis.json에서 직접 편집
vim output/analysis.json  # recommended_scenario 값 변경

# 3. 또는 analysis 건너뜀
archpilot modernize output/system.json -r "요구사항" --no-analysis
```

### 9.3 Web 앱에서 시나리오 수동 선택

분석 완료 후 시나리오 선택 드롭다운에서 변경 가능합니다:

```
AI 권고: 🔴 전체 교체 (full_replace)
         "EOL 비율 83% — 전체 재설계 권장"

[ 일부 보존 (partial) ▼ ]  ← 수동 오버라이드
```

선택 후 "현대화 설계 생성"을 다시 클릭하면 선택한 시나리오가 AI 권고보다 우선 적용됩니다.

### 9.4 시나리오별 현대화 접근법

**full_replace:** AI가 기존 컴포넌트에 구애받지 않고 현대 스택 중심으로 완전히 새로 설계합니다.

**partial:** `component_decisions`의 `keep`/`rehost` 컴포넌트는 유지하고, `replace`/`refactor` 컴포넌트만 교체합니다. `component_decisions`의 품질이 결과에 가장 큰 영향을 미칩니다.

**additive:** 기존 컴포넌트는 대부분 유지하고 신규 채널(모바일 앱, 새 API 레이어 등)만 추가합니다.

---

## 10. 발표 자료 생성

### 10.1 서버 실행

```bash
archpilot serve output/ --open
```

두 가지 URL:
- `http://localhost:8080/` — 인터랙티브 웹 앱
- `http://localhost:8080/slides` — reveal.js 발표 슬라이드

### 10.2 발표 슬라이드 구성 (7슬라이드)

| 슬라이드 | 내용 |
|---------|------|
| 1 | 표지: 시스템명, 분석일 |
| 2 | 레거시 아키텍처 다이어그램 (클릭 시 확대) |
| 3 | AI 분석 결과 (수직 슬라이드: 핵심 문제 → 기술부채 → 위험 → 기회) |
| 4 | 현대화 요구사항 및 선택 시나리오 |
| 5 | 현대화 아키텍처 다이어그램 (클릭 시 확대) |
| 6 | Before/After 컴포넌트 비교표 |
| 7 | 마이그레이션 로드맵 |

**키보드 조작:**
- `→` / `Space`: 다음 슬라이드
- `←`: 이전 슬라이드
- `↓` / `↑`: 수직 슬라이드 이동 (분석 섹션)
- `F`: 전체화면
- `O`: 개요 보기
- 다이어그램 클릭: 모달 확대

### 10.3 포트 및 옵션

```bash
archpilot serve output/ --port 9000 --host 0.0.0.0  # 팀 공유
archpilot serve output/ --no-open                    # 브라우저 자동 열기 끔
archpilot serve output/ --reload                     # 개발 모드 (코드 변경 시 자동 재시작)
```

`serve` 옵션:
```
--port, -p    서버 포트 (기본: 8080)
--host        서버 호스트 (기본: 127.0.0.1)
--open/--no-open  브라우저 자동 열기 (기본: --open)
--reload      개발 모드 자동 재시작
```

### 10.4 정적 HTML 내보내기

```bash
# output/ 디렉토리 전체를 읽어 정적 슬라이드 생성
archpilot export output/ --dest ./dist

# 테마 지정 (기본: black)
archpilot export output/ --dest ./dist --theme moon
```

테마 옵션: `black`(기본), `white`, `moon`, `sky`, `league`, `beige`, `serif`, `solarized`

```
dist/
└── index.html   # reveal.js 정적 슬라이드 (CDN 의존, 인터넷 필요)
```

> `export` 명령은 `output/` 디렉토리에서 `system.json`, `analysis.json`, `modern/system.json`,
> `modern/migration_plan.md`, `legacy/diagram.mmd`, `modern/diagram.mmd` 를 자동으로 읽습니다.

---

## 11. 출력 파일 구조

```
output/
├── system.json              # 레거시 SystemModel (모든 명령어 공유)
├── legacy/
│   ├── diagram.mmd          # Mermaid DSL
│   ├── diagram.png          # PNG (--format png 시)
│   └── diagram.drawio       # draw.io XML
├── analysis.json            # LLM 분석 결과 (시나리오·6R·품질 포함)
├── modern/
│   ├── system.json          # 현대화 SystemModel
│   ├── diagram.mmd
│   ├── diagram.png
│   ├── diagram.drawio
│   ├── migration_plan.md    # 마이그레이션 로드맵 (11섹션)
│   └── design_rationale.json# 설계 해설 (Web UI에서만 생성)
dist/                            # archpilot export 출력 (별도 디렉토리)
└── index.html               # reveal.js 정적 HTML (CDN 의존)
```

**`system.json` 주요 구조:**
```json
{
  "name": "Core Banking Legacy System",
  "components": [
    {
      "id": "oracle_primary",
      "type": "database",
      "label": "Oracle DB (운영)",
      "tech": ["Oracle 11g", "RAC"],
      "host": "on-premise",
      "criticality": "high",
      "lifecycle_status": "eol",
      "data_classification": "restricted",
      "owner": "DB운영팀",
      "specs": {"cpu": 16, "memory": "64GB", "storage": "20TB SAN"},
      "metadata": {}
    }
  ],
  "connections": [
    {"from_id": "core_server", "to_id": "oracle_primary", "protocol": "JDBC"}
  ]
}
```

---

## 12. FAQ

### Q. `-r` 없이 analyze와 modernize를 실행해도 되나요?

됩니다. 다만 `-r`을 포함하면 AI가 목표를 알고 `component_decisions`를 생성하므로 품질이 높아집니다. 특히 `partial` 시나리오에서 차이가 큽니다.

### Q. analyze와 modernize에 같은 `-r`을 써야 하나요?

같은 값을 쓰는 것이 권장됩니다. `analyze -r`의 목표가 `component_decisions`에 반영되고, 이 결정이 `modernize`의 그라운딩이 되기 때문입니다.

### Q. draw.io Desktop이 없어도 사용할 수 있나요?

네. YAML, JSON, 자연어 텍스트, diagrams.net (Web) 등으로 입력할 수 있습니다. draw.io Desktop은 `drawio edit/watch` 기능에서만 필요합니다.

### Q. 분석 후 시나리오를 바꾸고 싶으면?

- CLI: `output/analysis.json`에서 `recommended_scenario` 직접 편집 후 modernize 재실행
- Web 앱: 시나리오 선택 드롭다운에서 변경 후 "현대화 설계 생성" 다시 클릭

### Q. 대형 시스템(20개+ 컴포넌트)에서 component 수가 줄어들었어요

20개 이상이면 Web UI에서 2단계 분할 생성(Skeleton → Enrich)을 자동 적용합니다.
컴포넌트가 여전히 부족하게 생성되면 A2 교정 재생성이 자동 실행됩니다.

그래도 줄어든 경우:
1. `archpilot analyze -r "..."` 먼저 실행해 `component_decisions` 생성 (체크리스트로 활용)
2. Web UI 사용 (5-pass RMC + 자동 교정 강화)
3. 시스템을 서브시스템 단위로 분리

### Q. PNG 다이어그램을 생성하려면?

Graphviz가 필요합니다:
```bash
brew install graphviz     # macOS
sudo apt install graphviz # Ubuntu
winget install graphviz   # Windows
```

설치 후: `archpilot ingest my-system.yaml --format png`

### Q. 분석 결과가 한국어가 아닌 영어로 나옵니다

`.env`의 `OPENAI_MODEL`이 `gpt-4o` 이상인지 확인하세요. 구형 모델은 한국어 지시를 무시할 수 있습니다.

### Q. 서버 포트가 이미 사용 중입니다

```bash
archpilot serve output/ --port 8090
# 또는 ~/.archpilot/config.env에서 ARCHPILOT_SERVER_PORT=8090 설정
```

### Q. 세션/출력을 초기화하고 싶습니다

```bash
# 출력 디렉토리 삭제 (CLI)
rm -rf output/

# 웹 앱 세션만 초기화 (서버 실행 중)
curl -X DELETE http://localhost:8080/api/state
```

### Q. draw.io로 그렸는데 criticality·specs 같은 정보를 추가하고 싶습니다

draw.io는 시스템 토폴로지(구조·연결)를 시각화하는 데 최적화돼 있고, 엔터프라이즈 메타데이터는 저장하지 않습니다.

**권장 워크플로우:**

```bash
# 1. draw.io로 토폴로지 그리기 → ingest
archpilot ingest my-system.drawio

# 2. watch 종료 후 system.json 직접 편집
#    criticality, lifecycle_status, specs, owner, data_classification 추가
vim output/system.json

# 3. 보완된 정보로 분석 실행
archpilot analyze output/system.json -r "..."
```

> ⚠️ draw.io에서 재편집·저장하면 system.json이 덮어써집니다. draw.io 편집이 완전히 끝난 후 system.json을 편집하세요.
> 상세 패턴: [`DRAWIO.md §10.5`](./5_DRAWIO.md#105-복잡한-시스템--drawio--systemjson-직접-편집-워크플로우)

### Q. `from_id` / `to_id` 오류가 납니다

```yaml
# ❌ id 불일치
components:
  - id: web           # id는 'web'
connections:
  - from_id: web_server  # 없는 id → 오류

# ✅ 정확히 일치
connections:
  - from_id: web      # component id와 동일
```

이전 버전 호환: `from`/`to`도 허용됩니다.

---

## 참고 문서

| 문서 | 내용 |
|------|------|
| [`OVERVIEW.md`](./1_OVERVIEW.md) | ArchPilot 개요, 핵심 개념 |
| [`SCHEMA.md`](./2_SCHEMA.md) | YAML 스키마 작성 완전 가이드 |
| [`GROUNDING.md`](./4_GROUNDING.md) | LLM 지식·그라운딩 체계 |
| [`DRAWIO.md`](./5_DRAWIO.md) | draw.io 통합 완전 가이드 |
| [`ARCHITECTURE.md`](./6_ARCHITECTURE.md) | 내부 아키텍처 (개발자용) |
| [`SPEC.md`](./7_SPEC.md) | 기능 명세 |
