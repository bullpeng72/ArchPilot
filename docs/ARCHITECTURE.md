# ArchPilot — 내부 아키텍처

버전: 0.2.1
최종 수정: 2026-03-13

---

## 1. 전체 구조 다이어그램

```
┌──────────────────────────────────────────────────────────────────────┐
│                            CLI Layer                                 │
│  typer app                                                           │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌─────────┐  │
│  │  ingest  │ │ analyze  │ │ modernize  │ │  serve   │ │ drawio  │  │
│  └────┬─────┘ └────┬─────┘ └─────┬──────┘ │  export  │ │(subgrp) │  │
│       │            │             │        └────┬─────┘ └────┬────┘  │
└───────┼────────────┼─────────────┼─────────────┼────────────┼───────┘
        │            │             │             │            │
┌───────▼────────────▼─────────────▼─────────────▼────────────▼───────┐
│                           Core Layer                                 │
│  ┌─────────────────┐  ┌──────────────┐  ┌─────────────────────────┐  │
│  │  SystemParser   │  │  SystemModel │  │       DiffEngine        │  │
│  │ (YAML/JSON/LLM) │  │  (Pydantic)  │  │    (legacy↔modern)      │  │
│  └────────┬────────┘  └──────┬───────┘  └────────────┬────────────┘  │
│           │                  │                        │              │
│  ┌────────▼────────┐  ┌──────▼───────┐  ┌────────────▼────────────┐  │
│  │  TechOntology   │  │  DrawioConfig│  │       DrawioParser      │  │
│  │  (타입 자동추론) │  │ (LevelDB 통합)│  │   (XML → SystemModel)   │  │
│  └─────────────────┘  └──────────────┘  └─────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
        │                    │
┌───────▼────────────────────▼─────────────────────────────────────────┐
│                     LLM / Renderer Layer                             │
│                                                                      │
│  LLM Layer                       Renderer Layer                      │
│  ┌───────────┐                   ┌──────────┐ ┌────────┐ ┌────────┐  │
│  │LLMClient  │                   │ Mermaid  │ │diagrams│ │drawio  │  │
│  │(OpenAI)   │                   │Renderer  │ │Renderer│ │Renderer│  │
│  ├───────────┤                   └──────────┘ └────────┘ └────────┘  │
│  │ Analyzer  │                   ┌──────────────────────────────────┐ │
│  │Modernizer │──────────────────▶│     DrawioLibraryRenderer        │ │
│  │ LLMParser │                   │  (컴포넌트 라이브러리 XML 생성)   │ │
│  └───────────┘                   └──────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
        │                    │
┌───────▼────────────────────▼─────────────────────────────────────────┐
│                       UI / Output Layer                              │
│                                                                      │
│  FastAPI Server (ui/server.py)       output/                         │
│  ┌──────────────────────────────┐    ├── system.json                 │
│  │ GET  /                       │    ├── legacy/                     │
│  │ GET  /slides                 │    ├── analysis.json               │
│  │ POST /api/ingest             │    ├── modern/                     │
│  │ GET  /api/analyze/stream SSE │    └── slides/                     │
│  │ POST /api/modernize/stream   │                                    │
│  │ GET  /api/diagram/{step}     │    Session Layer (ui/session.py)   │
│  └──────────────────────────────┘    ┌──────────────────────────────┐│
│                                      │  인메모리 세션 관리           ││
│  Templates (Jinja2)                  │  system/analysis/modern 상태  ││
│  ├── app.html.j2  (인터랙티브 UI)    └──────────────────────────────┘│
│  └── slides.html.j2 (reveal.js)                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. 모듈별 책임 분리

### 2.1 `config.py` — 설정 중앙화

```python
from pydantic_settings import BaseSettings

GLOBAL_CONFIG_DIR = Path.home() / ".archpilot"
GLOBAL_ENV_FILE = GLOBAL_CONFIG_DIR / "config.env"

class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 4096
    output_dir: Path = Path("./output")   # validator가 절대 경로로 변환
    diagram_format: str = "png"
    server_host: str = "127.0.0.1"
    server_port: int = 8080

    model_config = SettingsConfigDict(
        # 전역 설정 → 로컬 .env 순서로 로드 (로컬이 전역을 오버라이드)
        env_file=(GLOBAL_ENV_FILE, ".env"),
        env_prefix="ARCHPILOT_",
        extra="ignore",
    )

    @field_validator("output_dir", mode="after")
    @classmethod
    def _resolve_output_dir(cls, v: Path) -> Path:
        return v.expanduser().resolve()

settings = Settings()
```

- 모든 모듈은 `from archpilot.config import settings`로 접근
- 직접 `os.environ` 또는 `dotenv` 접근 금지
- `archpilot init`은 `~/.archpilot/config.env`에 전역 설정 저장 (절대 경로)
- 로컬 `.env`가 있으면 전역 설정을 오버라이드

---

### 2.2 `core/models.py` — 중앙 데이터 모델

모든 레이어가 공유하는 단일 진실 공급원(Single Source of Truth).

```
SystemModel
  ├── components: list[Component]
  │     ├── id, type, label, tech, host
  │     └── metadata (LLM 메타데이터 포함)
  └── connections: list[Connection]
        ├── from_id, to_id, protocol
        └── metadata
```

#### 불변 규칙
- `Component.id`는 시스템 내 고유해야 함 (`@validator`로 검증)
- `Connection.from_id`, `to_id`는 실제 존재하는 Component.id여야 함
- 렌더러는 모델을 수정하지 않음 (read-only 사용)

---

### 2.3 `core/parser.py` — 입력 통합 파서

```
from_file(path)
  ├── .yaml/.yml  → _parse_yaml() → _dict_to_model()
  ├── .json       → _parse_json() → _dict_to_model()
  ├── .drawio     → DrawioParser.parse_drawio_xml() → SystemModel
  └── .txt        → LLMParser.from_text()

_dict_to_model(data: dict) → SystemModel
  - 공통 변환 로직
  - 누락 필드 기본값 처리
  - ComponentType/HostType enum 변환
```

---

### 2.4 `core/tech_ontology.py` — 기술 스택 온톨로지

```python
# 키워드 기반 ComponentType 자동 추론
TECH_ONTOLOGY: dict[str, ComponentType] = {
    "mysql": ComponentType.DATABASE,
    "postgresql": ComponentType.DATABASE,
    "redis": ComponentType.CACHE,
    "kafka": ComponentType.QUEUE,
    "nginx": ComponentType.GATEWAY,
    ...
}

def infer_component_type(tech: str | None, label: str) -> ComponentType: ...
```

draw.io XML 파싱 및 자연어 입력 시 타입 자동 추론에 사용됨.

---

### 2.5 `llm/client.py` — LLM 단일 진입점

```python
class LLMClient:
    """OpenAI 클라이언트 싱글턴. 모든 LLM 호출은 이 클래스를 통해"""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def chat(
        self,
        system_prompt: str,
        user_message: str,
        json_mode: bool = True,
        max_tokens: int | None = None,
    ) -> str: ...

    async def chat_stream(
        self,
        system_prompt: str,
        user_message: str,
    ) -> AsyncIterator[str]: ...
```

#### 호출 흐름

```
llm/analyzer.py      → LLMClient.chat_stream(ANALYZE_SYSTEM_PROMPT, system_json)
llm/modernizer.py    → LLMClient.chat_stream(MODERNIZE_SYSTEM_PROMPT, payload)
llm/parser_agent.py  → LLMClient.chat(PARSE_SYSTEM_PROMPT, user_text)
```

---

### 2.6 `renderers/base.py` — 렌더러 인터페이스

```python
class BaseRenderer(ABC):
    name: ClassVar[str]       # "mermaid" | "diagrams" | "drawio"
    output_ext: ClassVar[str] # ".mmd" | ".png" | ".drawio"

    @abstractmethod
    def render(self, model: SystemModel) -> str: ...

    def save(self, model: SystemModel, output_dir: Path) -> Path:
        content = self.render(model)
        path = output_dir / f"diagram{self.output_ext}"
        path.write_text(content)
        return path
```

#### 렌더러 등록 레지스트리

```python
RENDERER_REGISTRY: dict[str, type[BaseRenderer]] = {
    "mermaid": MermaidRenderer,
    "png":     MingrammerRenderer,
    "svg":     MingrammerRenderer,
    "drawio":  DrawioRenderer,
}

def get_renderer(fmt: str) -> BaseRenderer:
    cls = RENDERER_REGISTRY.get(fmt)
    if not cls:
        raise ValueError(f"Unknown format: {fmt}")
    return cls()
```

---

### 2.7 `renderers/drawio_parser.py` — draw.io 역방향 파서

draw.io XML → SystemModel 변환. `archpilot drawio watch` 및 web API에서 사용.

```python
def parse_drawio_xml(xml: str) -> SystemModel:
    """mxGraph XML을 파싱해 SystemModel을 반환한다."""
    # mxCell의 style 속성 → ComponentType 매핑
    # swimlane label → HostType 추론
    # edge source/target → Connection
```

#### mxCell style → ComponentType 매핑

| style 키워드 | ComponentType |
|---|---|
| `shape=mxgraph.aws4.*` | SERVICE / DATABASE / CACHE 등 |
| `swimlane` | (그룹/호스트 컨테이너) |
| `cylinder` | DATABASE |
| `rhombus` | QUEUE |
| `#ccccff` (파란보라 배경) | MAINFRAME |
| `arcSize=30` + `#f0d0ff` (보라 배경) | ESB |
| `flowchart.decision` 또는 `shape=rhombus` | SECURITY |
| `#fffacd` (밝은노랑 배경) | MONITORING |

---

### 2.8 `renderers/drawio_library.py` — 컴포넌트 라이브러리

`archpilot drawio setup` 시 draw.io Desktop 사이드바에 표시될 컴포넌트 팔레트 XML을 생성.

```python
def write_library_file(path: Path) -> None:
    """~/.archpilot/archpilot-library.drawio.xml 생성"""
```

---

### 2.9 `core/drawio_config.py` — draw.io Desktop 통합

OS별 경로 탐색 및 Electron localStorage(LevelDB) 직접 조작.

```
find_drawio_executable()      → macOS .app / Windows .exe / Linux snap|deb
find_drawio_localstorage_path() → OS별 LevelDB 디렉토리
inject_custom_library(lib_path) → LevelDB WAL에 WriteBatch 추가
```

#### LevelDB 직접 조작 원리

draw.io Desktop(Electron)은 `customLibraries` 설정을 Chromium의 localStorage(LevelDB)에 저장한다.
draw.io가 종료된 상태에서 WAL(`.log`) 파일에 새 WriteBatch 레코드를 추가해 설정을 주입한다.

```
key:   b"_file://\x00\x01.drawio-config"
value: b"\x01" + json.dumps(config).encode()

record 구조:
  [CRC32C: 4B][length: 2B][type=0x01: 1B]
  [seq: 8B][count: 4B]
  [PUT: 1B][key_varint_len][key][val_varint_len][value]
```

#### OS별 경로

| OS | 실행파일 | LevelDB |
|---|---|---|
| macOS | `/Applications/draw.io.app` | `~/Library/Application Support/draw.io/Local Storage/leveldb` |
| Windows | `C:\Program Files\draw.io\draw.io.exe` 또는 `%LOCALAPPDATA%\Programs\draw.io\draw.io.exe` | `%APPDATA%\draw.io\Local Storage\leveldb` |
| Linux (deb) | `/usr/bin/drawio` | `~/.config/draw.io/Local Storage/leveldb` |
| Linux (Snap) | `/snap/bin/drawio` | `~/snap/drawio/common/.config/draw.io/Local Storage/leveldb` |

---

### 2.10 `core/diff.py` — Before/After 비교 엔진

```python
class SystemDiff:
    def compare(
        self, legacy: SystemModel, modern: SystemModel
    ) -> DiffResult: ...
```

```python
class DiffResult(BaseModel):
    added: list[Component]       # modern에만 존재
    removed: list[Component]     # legacy에만 존재
    modified: list[ComponentChange]  # 양쪽 존재, 변경됨
    unchanged: list[Component]   # 동일
    connection_changes: list[ConnectionChange]
```

변경 감지 필드 (7종): `type`, `label`, `tech`, `host`, `criticality`, `lifecycle_status`, `data_classification`

reveal.js 슬라이드의 "Before/After 비교표"에 사용.

---

### 2.11 `ui/server.py` — FastAPI 인터랙티브 서버

```
archpilot serve output/
  ↓
1. FastAPI 앱 초기화 (uvicorn)
2. 세션 상태 관리 (ui/session.py, 인메모리)
3. Jinja2 → app.html.j2 / slides.html.j2 렌더링
4. SSE 스트리밍 (분석·현대화 결과 실시간 전달)
5. 브라우저 자동 오픈 (webbrowser.open)
```

#### 주요 API 엔드포인트

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

#### SSE 스트리밍 데이터 흐름

```
브라우저 EventSource → GET /api/analyze/stream
  → LLMClient.chat_stream() (AsyncGenerator)
  → SSE 청크 전송: data: {"type":"token","content":"..."}
  → 완료 시: data: {"type":"done","result":{...}}
  → 세션 상태 업데이트
```

---

### 2.12 `ui/session.py` — 인메모리 세션 관리

```python
class Session(BaseModel):
    system_model: SystemModel | None = None
    analysis_result: AnalysisResult | None = None
    modern_model: SystemModel | None = None
    requirements: str = ""

_session = Session()

def get_session() -> Session: ...
def update_session(**kwargs) -> None: ...
def reset_session() -> None: ...
```

단일 사용자 로컬 CLI 도구이므로 싱글턴 인메모리 세션으로 충분.

---

## 3. 의존성 흐름

```
cli/cmd_ingest.py
  └── core/parser.py
        ├── (YAML/JSON) → core/models.py
        ├── (drawio XML) → renderers/drawio_parser.py → core/tech_ontology.py
        └── (자연어) → llm/parser_agent.py → llm/client.py

cli/cmd_analyze.py
  └── llm/analyzer.py → llm/client.py
        └── core/models.py (입력)

cli/cmd_modernize.py
  └── llm/modernizer.py → llm/client.py
        ├── core/models.py (입력 + 출력)
        └── (출력) → renderers/

cli/cmd_serve.py
  └── core/diff.py → core/models.py
  └── ui/server.py → ui/session.py → ui/templates/

cli/cmd_drawio.py (drawio 서브커맨드 그룹)
  ├── setup → core/drawio_config.py + renderers/drawio_library.py
  ├── edit  → core/drawio_config.py + watchdog
  ├── watch → renderers/drawio_parser.py + renderers/mermaid.py
  └── export → core/parser.py + renderers/drawio.py
```

---

## 4. 에러 전파 전략

```
LLMClient (tenacity 3회 재시도)
  → LLM응답 파싱 실패: ArchPilotLLMError
  → API 오류: ArchPilotAPIError

Parser
  → 스키마 불일치: ArchPilotParseError (line/col 포함)
  → 파일 미존재: ArchPilotFileError

Renderer
  → Graphviz 미설치: ArchPilotDependencyError
  → 렌더링 실패: ArchPilotRenderError

DrawioConfig
  → draw.io 미설치: (경고 후 Exit 1)
  → LevelDB 쓰기 실패: (경고 후 Exit 1)

CLI (최상위)
  → 모든 ArchPilotError 캐치
  → Rich 패널로 에러 출력
  → Exit code 1
```

---

## 5. 병렬 처리

`archpilot ingest --format mermaid,png,drawio` 실행 시 렌더러를 병렬 실행합니다.

```python
import concurrent.futures

def run_renderers(model: SystemModel, formats: list[str], output: Path):
    renderers = [get_renderer(fmt) for fmt in formats]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(r.save, model, output): r.name
            for r in renderers
        }
        results = {}
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = e
    return results
```

MingrammerRenderer(PNG 생성)는 Graphviz 프로세스를 subprocess로 호출하므로 GIL 영향 없음.

---

## 6. 확장 포인트

| 확장 포인트 | 방법 |
|-------------|------|
| 새 렌더러 추가 | `BaseRenderer` 상속 + `RENDERER_REGISTRY` 등록 |
| 새 입력 포맷 추가 | `SystemParser.from_file()`에 분기 추가 |
| 다른 LLM 백엔드 | `LLMClient` 교체 (인터페이스 유지) |
| 새 슬라이드 테마 | `ui/templates/` 추가 + `--theme` 옵션 확장 |
| 새 분석 항목 | `AnalysisResult` 모델 + `ANALYZE_SYSTEM_PROMPT` 수정 |
| 새 draw.io 컴포넌트 | `renderers/drawio_library.py`의 팔레트 배열에 추가 |
