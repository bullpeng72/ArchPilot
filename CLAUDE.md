# ArchPilot — CLAUDE.md `v0.2.0`

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
│       │   ├── server.py        # FastAPI 인터랙티브 UI 서버 (SSE 스트리밍)
│       │   ├── session.py       # 인메모리 세션 관리
│       │   └── templates/
│       │       ├── app.html.j2      # 인터랙티브 웹 앱
│       │       └── slides.html.j2   # reveal.js 발표 슬라이드
│       └── config.py            # pydantic-settings, .env 로드
├── tests/
│   ├── conftest.py
│   ├── test_parser.py
│   ├── test_renderers.py
│   ├── test_drawio_parser.py
│   └── test_diff.py
├── examples/
│   ├── legacy_ecommerce.yaml
│   └── legacy_bank.yaml
├── docs/
│   ├── SPEC.md                  # 기능 명세
│   ├── ARCHITECTURE.md          # 내부 아키텍처
│   ├── ONTOLOGY.md              # 기술 온톨로지 & 입력 표준화 상세
│   └── USER_GUIDE.md            # 입력 → 발표까지 사용자 가이드
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
archpilot export <system.json>        # system.json → .drawio 파일 내보내기

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
