# ArchPilot — CLAUDE.md `v0.2.3`

## 프로젝트 개요

Legacy 시스템 구성을 코드화(다이어그램)하고, 자연어 요구사항을 기반으로 현대화된 신규 시스템을 설계·시각화하는 CLI 도구.

- **패키지명**: `archpilot`
- **PyPI**: `pip install archpilot`
- **진입점**: `archpilot` CLI (Typer 기반)
- **Python**: 3.11+
- **LLM**: OpenAI GPT-4o (`OPENAI_API_KEY` via `.env`)

---

## 디렉토리 구조

```
archpilot/
├── src/
│   └── archpilot/
│       ├── __init__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py          # Typer app 진입점
│       │   ├── _utils.py        # CLI 공통 유틸 (progress, error formatting)
│       │   ├── cmd_init.py      # archpilot init
│       │   ├── cmd_ingest.py    # archpilot ingest
│       │   ├── cmd_analyze.py   # archpilot analyze
│       │   ├── cmd_modernize.py # archpilot modernize
│       │   ├── cmd_serve.py     # archpilot serve / export
│       │   └── cmd_drawio.py    # archpilot drawio (setup/edit/watch/export)
│       ├── core/
│       │   ├── models.py        # Pydantic SystemModel, Component, Connection, AnalysisResult
│       │   ├── parser.py        # YAML/JSON/텍스트 → SystemModel
│       │   ├── diff.py          # Legacy vs Modern 비교 유틸
│       │   ├── tech_ontology.py # 기술 스택 온톨로지 (자동 타입 추론)
│       │   └── drawio_config.py # draw.io Desktop 설정/LevelDB 통합
│       ├── llm/
│       │   ├── client.py        # OpenAI 비동기 클라이언트 래퍼 (스트리밍 지원)
│       │   ├── prompts.py       # 프롬프트 템플릿 (상수)
│       │   ├── utils.py         # LLM 관련 상수 (MAX_ANALYZE_TOKENS 등)
│       │   ├── analyzer.py      # 레거시 시스템 분석
│       │   ├── modernizer.py    # 현대화 설계 생성
│       │   └── parser_agent.py  # 자연어 텍스트 → SystemModel
│       ├── renderers/
│       │   ├── base.py          # BaseRenderer 추상 클래스
│       │   ├── mermaid.py       # SystemModel → Mermaid DSL
│       │   ├── mingrammer.py    # SystemModel → diagrams(mingrammer) → PNG/SVG
│       │   ├── drawio.py        # SystemModel → draw.io XML
│       │   ├── drawio_parser.py # draw.io XML → SystemModel (역방향 파서)
│       │   └── drawio_library.py# ArchPilot 컴포넌트 라이브러리 파일 생성
│       ├── ui/
│       │   ├── server.py        # FastAPI 앱 팩토리 + 페이지/다이어그램 라우트
│       │   ├── session.py       # 인메모리 세션 관리 (AppSession)
│       │   ├── helpers.py       # SSE 응답 빌더, 공통 유틸
│       │   ├── schemas.py       # FastAPI 요청/응답 Pydantic 스키마
│       │   ├── routers/
│       │   │   ├── __init__.py
│       │   │   ├── ingest.py    # POST /api/ingest, /api/ingest/file, /api/ingest/drawio, SSE chat
│       │   │   ├── analyze.py   # GET  /api/analyze/stream (SSE)
│       │   │   └── modernize.py # POST /api/modernize/stream (SSE)
│       │   └── templates/
│       │       ├── app.html.j2      # 인터랙티브 웹 앱 (우측 아코디언 리포트 패널)
│       │       └── slides.html.j2   # reveal.js 발표 슬라이드
│       └── config.py            # pydantic-settings, .env 로드
├── tests/
│   ├── conftest.py
│   ├── test_parser.py
│   ├── test_renderers.py
│   ├── test_drawio_parser.py
│   ├── test_drawio_config.py
│   ├── test_mingrammer.py
│   ├── test_ui_server.py
│   └── test_diff.py
├── examples/
│   ├── legacy_ecommerce.yaml
│   ├── legacy_bank.yaml
│   ├── hybrid_cloud_government.yaml
│   └── hybrid_cloud_manufacturing.yaml
├── docs/
│   ├── 1_OVERVIEW.md            # ArchPilot 개요, 핵심 개념, 전체 파이프라인
│   ├── 2_SCHEMA.md              # YAML/JSON 스키마 완전 가이드, 레거시 시스템 작성법
│   ├── 3_USER_GUIDE.md          # 설치부터 발표까지 단계별 워크플로우
│   ├── 4_GROUNDING.md           # LLM 지식·그라운딩 체계, 분석→현대화→RMC 파이프라인
│   ├── 5_DRAWIO.md              # draw.io 통합 완전 가이드
│   ├── 6_ARCHITECTURE.md        # 내부 아키텍처 (개발자용)
│   └── 7_SPEC.md                # 기능 명세
├── pyproject.toml
├── .env.example
└── README.md
```

---

## 개발 규칙

### 언어 & 포맷
- Python 3.11, 타입 힌트 필수
- 포매터: `ruff format`, 린터: `ruff check`
- 타입 체커: `mypy --strict` (llm/, core/ 우선)
- 커밋 전 `pre-commit run --all-files` 통과 필수

### 데이터 모델
- 모든 내부 모델은 `core/models.py`의 `SystemModel` 사용
- 렌더러는 반드시 `BaseRenderer`를 상속하고 `render(model) -> str` 구현
- LLM 응답은 항상 스트리밍 SSE + Pydantic 파싱

### LLM 호출
- `llm/client.py`의 `LLMClient` / `get_async_client()` 만 사용 (직접 `openai.OpenAI()` 호출 금지)
- 프롬프트는 `llm/prompts.py`에 상수로 정의 (하드코딩 금지)
- API 오류는 `tenacity`로 최대 3회 재시도

### CLI
- 모든 커맨드는 `cmd_*.py`에 분리
- 출력은 `rich` 사용 (print 직접 사용 금지)
- 에러는 `typer.echo(err=True)` + `raise typer.Exit(1)`

### 테스트
- LLM 호출은 `pytest-mock`으로 모킹
- 렌더러 테스트는 출력 문자열 스냅샷 비교
- `pytest -x` 기준 전체 통과 유지

### 환경 변수
- `.env` 파일로만 관리, 코드에 키 하드코딩 금지
- `config.py`의 `Settings` 객체를 통해서만 접근
- `.env`는 절대 커밋 금지 (`.gitignore` 등록)

---

## 핵심 CLI 명령어

```bash
archpilot init                        # .env 초기화 마법사
archpilot ingest <file> [options]     # 레거시 시스템 파일 주입
archpilot analyze <system.json>       # LLM 분석 보고서 생성
archpilot modernize <system.json>     # LLM 현대화 설계 생성
archpilot serve <output_dir>          # 인터랙티브 UI + reveal.js 서버 실행
archpilot export [output_dir]         # 발표 슬라이드 → 정적 HTML 내보내기 (dist/)

# draw.io Desktop 통합 서브커맨드
archpilot drawio setup                # draw.io Desktop에 ArchPilot 라이브러리 설치
archpilot drawio edit [--output]      # draw.io Desktop으로 다이어그램 편집
archpilot drawio watch <file>         # draw.io 파일 변경 자동 감시·반영
archpilot drawio export <system.json> # system.json → .drawio 내보내기
```

---

## 의존성 (주요)

| 패키지 | 용도 |
|--------|------|
| `typer[all]` | CLI 프레임워크 |
| `rich` | 터미널 출력 |
| `openai>=1.30` | LLM 클라이언트 (비동기 스트리밍) |
| `python-dotenv` | .env 로드 |
| `pydantic>=2.0` | 데이터 모델 |
| `pydantic-settings` | 설정 관리 |
| `pyyaml` | YAML 파싱 |
| `diagrams>=0.23` | mingrammer 다이어그램 |
| `jinja2` | HTML 템플릿 |
| `fastapi>=0.111` | 인터랙티브 UI + API 서버 |
| `uvicorn[standard]` | ASGI 서버 |
| `python-multipart` | 파일 업로드 |
| `tenacity` | LLM 재시도 |
| `watchdog>=4.0` | draw.io 파일 변경 감시 |
| `defusedxml>=0.7` | XXE/DTD 보안 XML 파싱 |

---

## .env 구조

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_MAX_TOKENS=4096
ARCHPILOT_OUTPUT_DIR=./output
ARCHPILOT_DIAGRAM_FORMAT=png
ARCHPILOT_SERVER_HOST=127.0.0.1
ARCHPILOT_SERVER_PORT=8080
```

---

## 출력 디렉토리 구조 (output/)

```
output/
├── system.json              # 파싱된 SystemModel (중간 산출물)
├── legacy/
│   ├── diagram.mmd          # Mermaid DSL
│   ├── diagram.png          # diagrams 렌더링
│   └── diagram.drawio       # draw.io XML
├── analysis.json            # LLM 분석 결과
├── modern/
│   ├── system.json          # 현대화된 SystemModel
│   ├── diagram.mmd
│   ├── diagram.png
│   ├── diagram.drawio
│   └── migration_plan.md    # 마이그레이션 로드맵 (마크다운)
└── slides/
    └── index.html           # reveal.js 발표 자료 (정적 export 시)
```

---

## UI 서버 API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 인터랙티브 웹 앱 |
| GET | `/slides` | reveal.js 발표 슬라이드 |
| GET | `/api/state` | 현재 세션 상태 조회 |
| DELETE | `/api/state` | 세션 초기화 |
| POST | `/api/ingest` | YAML/JSON/텍스트 주입 |
| POST | `/api/ingest/file` | 파일 업로드 주입 |
| POST | `/api/ingest/drawio` | draw.io XML 주입 |
| POST | `/api/chat/ingest/stream` | 대화형 시스템 입력 (SSE) |
| GET | `/api/analyze/stream` | LLM 분석 스트리밍 (SSE) |
| POST | `/api/modernize/stream` | LLM 현대화 설계 스트리밍 (SSE) |
| GET | `/api/diagram/{step}` | 다이어그램 다운로드 (mermaid/drawio) |

---

## 📝 변경 이력

### v0.2.3 (2026-03-15) — UI 리포트 패널 개편 & 대형 시스템 현대화 강화

- ✨ `ui/templates/app.html.j2` — 하단 220px 탭 → 360px 우측 아코디언 패널 전면 개편 (Progressive Reveal, 드래그 리사이즈, 섹션별 클립보드 복사)
- ✨ `ui/routers/` — APIRouter 분리: ingest, analyze, modernize 라우터 독립 파일로 분리
- ✨ `ui/helpers.py` / `ui/schemas.py` — 공통 유틸·요청 스키마 분리 신규 생성
- ✨ `llm/client.py` — `BaseLLMClient` ABC 추가 (LLMClient/AsyncLLMClient 공통 초기화 추상화)
- ✨ `llm/modernizer.py` — A1 체크리스트 주입: 레거시 컴포넌트 전체 목록을 프롬프트에 명시적 삽입
- ✨ `llm/modernizer.py` — A2 재시도 루프: 현대화 후 누락 컴포넌트 검증, 자동 재시도 (`_MAX_RETRY=1`)
- ✨ `llm/modernizer.py` — A3 2단계 분할: 20개 초과 대형 시스템에 Skeleton→Enrich 2-phase 자동 적용
- ✨ `llm/prompts.py` — `MODERNIZE_SKELETON_PROMPT` 신규: Phase 1 스켈레톤 전용 경량 프롬프트
- ✨ `llm/utils.py` — `LARGE_SYSTEM_THRESHOLD=20`, `MAX_SKELETON_TOKENS=4000` 상수 추가
- ✨ `ui/routers/modernize.py` — SSE 스트리밍에 A1/A2/A3 전략 통합
- 🔧 `renderers/drawio_parser.py` — defusedxml XXE/DTD 보안 패치
- 🔧 `llm/modernizer.py` — `MAX_PLAN_TOKENS` 상수 적용 (하드코딩 제거)
- 🔧 `core/drawio_config.py` — `except` 범위 축소, CRC32C magic number 주석 추가
- 🔧 `ui/routers/ingest.py` — `asyncio.to_thread()` 로 동기 파서 호출 비동기 처리
- 📝 `examples/` — 8개 예제 YAML 전수 검증·교정: 스키마 필드 위치, 컴포넌트 타입, 호스트 타입, lifecycle_status, 엔터프라이즈 필드
- ✅ `tests/test_mingrammer.py` — 22 테스트 신규 (safe_var, resolve_class, build_imports)
- ✅ `tests/test_drawio_config.py` — 20 테스트 신규 (varint, CRC32C, LDB record)
- ✅ `tests/test_ui_server.py` — 23 테스트 신규 (page routes, ingest, state API)
- ✅ `tests/test_llm_utils.py` — 17 테스트 신규 (compress_system_dict 3단계·compress_model·compress_analysis 3단계·compress_for_plan 4단계)
- ✅ `tests/test_modernizer.py` — 21 테스트 신규 (resolve_scenario, checklist, check_missing, A3 임계값 라우팅, A2 재시도, A3 2단계) — 총 181개 통과

### v0.2.2 (2026-03-14) — 시나리오 기반 현대화 & 버그 수정

- ✨ `core/models.py` — `ModernizationAction` (6R enum), `ModernizationScenario` (full_replace/partial/additive) 신규
- ✨ `core/models.py` — `ComponentDecision`, `QualityDimension`, `ArchitectureQuality` 모델 신규
- ✨ `core/models.py` — `AnalysisResult`에 `recommended_scenario`, `scenario_rationale`, `component_decisions`, `legacy_quality` 필드 추가
- ✨ `core/models.py` — `DiffResult`에 `inferred_scenario`, `modern_quality` 필드 추가
- ✨ `llm/prompts.py` — `ANALYZE_SYSTEM_PROMPT`에 시나리오 권고·컴포넌트 전략(6R)·5차원 품질 평가 섹션 추가
- ✨ `llm/prompts.py` — `MODERNIZE_SYSTEM_PROMPT`에 시나리오별 설계 원칙 추가 (full_replace/partial/additive 분기)
- ✨ `llm/modernizer.py` — `modernize()`에 `scenario` 파라미터 추가, 분석 결과 `component_decisions` 강조 전달
- ✨ `ui/session.py` — `AppSession`에 `scenario` 필드 + `reset_modernization()` 메서드 추가
- ✨ `ui/server.py` — `ModernizeRequest`에 `scenario` 필드 추가, 시나리오 컨텍스트 LLM 전달
- ✨ `ui/templates/app.html.j2` — 시나리오 선택 드롭다운, 권고 시나리오 배지, 레거시 품질 5차원 바 차트, 컴포넌트 전략 테이블 UI 추가
- 🐛 `ui/server.py` — `analyze_stream` `max_tokens` 누락 버그 수정 (`MAX_ANALYZE_TOKENS=6000`)
- 🐛 `ui/server.py` — 마이그레이션 플랜 `max_tokens` 누락 버그 수정 (`MAX_PLAN_TOKENS=6000`)
- 🔧 `llm/utils.py` — `MAX_ANALYZE_TOKENS`, `MAX_PLAN_TOKENS` 상수 추가

### v0.2.1 (2026-03-13) — 실행 위치 독립성 개선

- 🔧 `config.py` — 전역 설정 디렉토리 `~/.archpilot/config.env` 추가 (로컬 `.env`가 오버라이드)
- 🔧 `config.py` — `output_dir` field_validator로 항상 절대 경로 보장
- 🔧 `cmd_init.py` — 전역 `~/.archpilot/config.env`에 저장, `ARCHPILOT_OUTPUT_DIR` 절대 경로 기록
- 🔧 `cmd_ingest.py`, `cmd_serve.py`, `cmd_drawio.py` — `--output` 기본값 `settings.output_dir`로 통일 (CWD 무관)
- 📝 `docs/ARCHITECTURE.md` — `config.py` 코드 예시 현행화
- 📝 `docs/SPEC.md`, `docs/USER_GUIDE.md` — `init` 동작 설명 현행화

### v0.2.0 (2026-03-13) — 아키텍처 문서화 완료 및 PyPI 배포 준비

- ✨ `core/tech_ontology.py` — TechOntology 설계 (70+ 기술 스택 자동 타입 추론)
- ✨ `renderers/drawio_parser.py` — draw.io XML → SystemModel 역방향 파서
- ✨ `renderers/drawio_library.py` — draw.io Desktop 컴포넌트 라이브러리 생성
- ✨ `core/drawio_config.py` — Electron LevelDB 직접 주입으로 draw.io Desktop 설정 자동화
- ✨ `ui/server.py` — Flask → FastAPI + SSE 스트리밍 전환
- ✨ `ui/session.py` — 인메모리 세션 관리
- ✨ `archpilot drawio export` — draw.io → system.json 변환 커맨드 추가
- 📝 `docs/ARCHITECTURE.md` — TechOntology·DrawioParser·DrawioConfig·FastAPI 섹션 신규 작성
- 📝 `docs/ONTOLOGY.md` — 입력 표준화 파이프라인 및 온톨로지 상세 문서 신규 작성
- 📝 `docs/USER_GUIDE.md` — 5가지 입력 시나리오 실전 가이드 신규 작성
- 🔧 `pyproject.toml` — PyPI 배포용 메타데이터 완성 (classifiers, keywords, authors)
