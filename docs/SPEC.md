# ArchPilot — 기능 명세 (SPEC)

버전: 0.2.0
최종 수정: 2026-03-13

---

## 1. 개요

### 1.1 목적

레거시 시스템의 구성 정보를 표준화된 다이어그램 코드로 변환하고,
OpenAI LLM을 활용하여 자연어 요구사항 기반의 현대화된 시스템 아키텍처를 설계·시각화한다.

### 1.2 대상 사용자

- 시스템 아키텍트, 솔루션 아키텍트
- DevOps / SRE 엔지니어
- 레거시 현대화 프로젝트 담당자
- 기술 문서화 담당자

### 1.3 핵심 가치

| 가치 | 설명 |
|------|------|
| **코드로서의 아키텍처** | 다이어그램을 텍스트/코드로 버전 관리 가능 |
| **AI 기반 설계** | 자연어 요구사항 → 구체적 아키텍처 자동 생성 |
| **멀티 포맷 출력** | Mermaid, PNG, draw.io 동시 생성 |
| **발표 즉시 가능** | reveal.js 슬라이드 자동 생성 |
| **draw.io 양방향 통합** | draw.io Desktop ↔ ArchPilot 라운드트립 |

---

## 2. 기능 요구사항

### 2.1 FR-01: 레거시 시스템 주입 (ingest)

#### 2.1.1 입력 포맷

| 포맷 | 확장자 | 파싱 방식 |
|------|--------|-----------|
| YAML | `.yaml`, `.yml` | PyYAML 직접 파싱 |
| JSON | `.json` | 표준 라이브러리 |
| 자연어 텍스트 | `.txt` | LLM 파싱 (GPT-4o) |
| draw.io XML | `.drawio` | drawio_parser (역방향 파서) |

#### 2.1.2 YAML 스키마

```yaml
name: string                    # 필수. 시스템 이름
description: string             # 선택. 시스템 설명

components:                     # 필수. 1개 이상
  - id: string                  # 필수. snake_case 고유 식별자
    type: enum                  # 필수. 아래 ComponentType 참조
    label: string               # 필수. 표시 이름
    tech: [string]              # 선택. 기술 스택 목록
    host: enum                  # 선택. 기본값: on-premise
    specs:                      # 선택. 자유 형식 메타데이터
      cpu: int
      memory: string
      version: string

connections:                    # 선택.
  - from_id: component_id       # 필수. 출발 컴포넌트 ID
    to_id: component_id         # 필수. 도착 컴포넌트 ID
    protocol: string            # 선택. 기본값: HTTP
    label: string               # 선택. 엣지 레이블
    bidirectional: bool         # 선택. 기본값: false
```

#### 2.1.3 ComponentType Enum

```
server | database | cache | queue | storage |
cdn | loadbalancer | gateway | service | client | unknown
```

#### 2.1.4 Host Enum

```
on-premise | aws | gcp | azure | hybrid
```

#### 2.1.5 출력

- `output/system.json` — 파싱된 SystemModel (이후 명령어 재사용)
- `output/legacy/diagram.mmd` — Mermaid 다이어그램
- `output/legacy/diagram.png` — PNG (`--format png` 지정 시)
- `output/legacy/diagram.drawio` — draw.io XML

#### 2.1.6 CLI 옵션

```
archpilot ingest <file>
  --output, -o     출력 디렉토리 (기본: ./output)
  --format, -f     출력 포맷. 복수 지정 가능: mermaid,png,drawio (기본: mermaid)
  --no-llm         LLM 사용 안 함 (구조화 파일 전용)
```

---

### 2.2 FR-02: 레거시 시스템 분석 (analyze)

#### 2.2.1 입력

- `output/system.json` (ingest 결과)

#### 2.2.2 LLM 분석 항목

| 항목 | 설명 |
|------|------|
| `pain_points` | 현상 → 근본 원인 → 비즈니스 영향 구조의 문제점 목록 (최소 5개) |
| `tech_debt` | 기술 부채 항목 — EOL/EOS 날짜, CVE, 마이그레이션 복잡도 포함 (최소 4개) |
| `risk_areas` | 고위험 컴포넌트 — 발생 가능성·피해 규모, 단기/장기 대응 구분 (최소 4개) |
| `modernization_opportunities` | 현재→목표 기술 스택 대비, 기대 효과 수치 포함 (최소 5개) |
| `recommended_patterns` | 권장 아키텍처 패턴 및 선택 근거 (최소 4개) |
| `estimated_effort` | 난이도 및 예상 공수 (S/M/L/XL) |

#### 2.2.3 출력

- `output/analysis.json` — 구조화된 분석 결과
- 터미널: Rich 패널로 요약 출력

#### 2.2.4 CLI 옵션

```
archpilot analyze <system.json>
  --output, -o    출력 디렉토리 (기본: 입력 파일 위치)
  --verbose, -v   상세 출력
  --format, -f    출력 포맷: json|markdown (기본: json)
```

---

### 2.3 FR-03: 현대화 설계 생성 (modernize)

#### 2.3.1 입력

- `output/system.json` (ingest 결과)
- `--requirements` 자연어 현대화 요구사항

#### 2.3.2 요구사항 예시

```
"AWS 기반 마이크로서비스로 전환, Kubernetes 컨테이너화,
RDS Aurora 도입, ElastiCache Redis, S3 스토리지,
CloudFront CDN, API Gateway, CI/CD 파이프라인"
```

#### 2.3.3 LLM 처리 과정

```
1. Legacy SystemModel + 요구사항 → 현대화 SystemModel JSON 생성
2. 각 컴포넌트 변경 사유 (metadata.reason) 포함
3. 새로 추가된 컴포넌트 표시 (metadata.is_new: true)
4. 제거된 컴포넌트 표시 (metadata.removed: true)
5. 마이그레이션 플랜 (Markdown) 별도 생성
```

#### 2.3.4 출력

- `output/modern/system.json` — 현대화된 SystemModel
- `output/modern/diagram.mmd` — 신규 Mermaid 다이어그램
- `output/modern/diagram.png` — 신규 PNG (요청 시)
- `output/modern/diagram.drawio` — 신규 draw.io XML
- `output/modern/migration_plan.md` — 마이그레이션 로드맵

#### 2.3.5 CLI 옵션

```
archpilot modernize <system.json>
  --requirements, -r   자연어 현대화 요구사항 (필수)
  --output, -o         출력 디렉토리
  --format, -f         출력 포맷: mermaid,png,drawio (기본: mermaid)
  --analysis           기존 analysis.json 참조 여부 (기본: True)
```

---

### 2.4 FR-04: 인터랙티브 UI 서버 (serve)

#### 2.4.1 기술 구성

- **서버**: FastAPI + uvicorn (ASGI, 비동기)
- **슬라이드 엔진**: reveal.js 5.x (CDN)
- **다이어그램 렌더링**: mermaid.js (CDN, 슬라이드 내 인라인, viewBox 기반 클릭 확대)
- **스트리밍**: Server-Sent Events (SSE)
- **템플릿**: Jinja2

#### 2.4.2 웹 앱 기능 (`/`)

- 대화형 채팅으로 시스템 구성 입력 (`POST /api/chat/ingest/stream`)
- YAML/JSON 파일 업로드 (`POST /api/ingest/file`)
- draw.io XML 붙여넣기 주입 (`POST /api/ingest/drawio`)
- 실시간 LLM 분석 스트리밍 (`GET /api/analyze/stream`)
- 실시간 현대화 설계 스트리밍 (`POST /api/modernize/stream`)

#### 2.4.3 발표 슬라이드 구성 (`/slides`)

| 슬라이드 | 내용 |
|----------|------|
| 1 | 프로젝트명 + 시스템 설명 (표지) |
| 2 | 현재 Legacy 아키텍처 다이어그램 (Mermaid, 클릭 확대 모달) |
| 3 | 레거시 분석 결과 요약 + 주요 문제점 + 현대화 기회 (세로 슬라이드) |
| 4 | 현대화 시스템 다이어그램 (Mermaid, 클릭 확대 모달) |
| 5 | Before/After 컴포넌트 비교표 |
| 6 | 마이그레이션 로드맵 (Markdown 렌더링) |
| 7 | 마무리 |

#### 2.4.4 CLI 옵션

```
archpilot serve <output_dir>
  --port, -p    포트 번호 (기본: 8080)
  --host        호스트 (기본: 127.0.0.1)
  --open        브라우저 자동 오픈 (기본: True)
  --theme       reveal.js 테마: black|white|moon|sky (기본: black)
```

---

### 2.5 FR-05: 정적 HTML 내보내기 (export)

```
archpilot export <system.json>
  --dest, -d    저장 경로 (기본: <system.json 위치>/legacy/diagram.drawio)
```

---

### 2.6 FR-06: 초기화 (init)

```
archpilot init
```

- `.env` 파일 생성 마법사 (OPENAI_API_KEY 입력 프롬프트)
- 이미 `.env` 존재 시 덮어쓰기 여부 확인

---

### 2.7 FR-07: draw.io Desktop 통합 (drawio)

#### 2.7.1 서브커맨드

| 명령어 | 설명 |
|--------|------|
| `drawio setup` | ArchPilot 컴포넌트 라이브러리를 draw.io Desktop에 설치 |
| `drawio edit` | 현재 다이어그램을 draw.io Desktop으로 열고 변경 감시 |
| `drawio watch <file>` | draw.io 파일 저장 시 ArchPilot에 자동 반영 |
| `drawio export <system.json>` | system.json → .drawio 파일 변환 |

#### 2.7.2 setup 동작

```
1. draw.io Desktop 설치 확인 (OS별 경로 탐색)
2. ~/.archpilot/archpilot-library.drawio.xml 생성
3. Electron localStorage(LevelDB)에 라이브러리 경로 등록
4. built-in 섹션 숨김 (libraries: "" 설정)
```

#### 2.7.3 draw.io XML → SystemModel 역방향 파싱

- mxCell style 문자열 → ComponentType 자동 추론
- swimlane 레이블 → HostType 자동 추론
- ArchPilot 생성 XML 및 diagrams.net 수동 편집 XML 모두 지원
- 기존 세션 semantic 메타데이터 보존 (roundtrip 시 분석 정보 유지)

#### 2.7.4 지원 OS

| OS | 실행 파일 탐색 | LevelDB 경로 |
|----|---------------|-------------|
| macOS | `/Applications/draw.io.app`, `~/Applications/draw.io.app` | `~/Library/Application Support/draw.io/Local Storage/leveldb` |
| Windows | `Program Files`, `LOCALAPPDATA\Programs\draw.io` | `%APPDATA%\draw.io\Local Storage\leveldb` |
| Linux (deb) | `/opt/draw.io`, `/usr/bin/drawio`, `~/.local/bin/drawio` | `~/.config/draw.io/Local Storage/leveldb` |
| Linux (Snap) | `/snap/bin/drawio` | `~/snap/drawio/common/.config/draw.io/Local Storage/leveldb` |

---

## 3. 비기능 요구사항

### 3.1 성능

| 항목 | 목표 |
|------|------|
| YAML 파싱 (구조화) | < 1초 |
| LLM 파싱 (자연어) | < 15초 |
| Mermaid 렌더링 | < 1초 |
| diagrams PNG 생성 | < 10초 |
| analyze LLM 호출 | < 20초 |
| modernize LLM 호출 | < 30초 |

### 3.2 안정성

- LLM API 오류: `tenacity` 지수 백오프 3회 재시도
- LLM JSON 파싱 실패: 재요청 1회 후 오류 보고
- 네트워크 타임아웃: 60초

### 3.3 호환성

- OS: macOS, Linux, Windows
- Python: 3.11, 3.12
- diagrams 라이브러리: Graphviz 설치 필요 (문서 안내)

### 3.4 보안

- API 키: `.env` 파일, 환경변수 경유만 허용
- `.env` 파일 `.gitignore` 등록 강제
- LLM 입력에 민감정보(IP, 비밀번호) 마스킹 권고 안내

---

## 4. 데이터 모델 명세

### 4.1 SystemModel

```python
class SystemModel(BaseModel):
    name: str
    description: str = ""
    version: str = "1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    components: list[Component]
    connections: list[Connection] = Field(default_factory=list)
    metadata: dict[str, Any] = {}
```

### 4.2 Component

```python
class Component(BaseModel):
    id: str                          # snake_case, 시스템 내 고유
    type: ComponentType
    label: str
    tech: list[str] = []
    host: HostType = HostType.ON_PREMISE
    specs: dict[str, Any] = {}
    metadata: dict[str, Any] = {}   # is_new, removed, reason 등 LLM 메타데이터
```

### 4.3 Connection

```python
class Connection(BaseModel):
    from_id: str
    to_id: str
    protocol: str = "HTTP"
    label: str = ""
    bidirectional: bool = False
    metadata: dict[str, Any] = {}
```

### 4.4 AnalysisResult

```python
class AnalysisResult(BaseModel):
    system_name: str
    analyzed_at: datetime
    pain_points: list[str]
    tech_debt: list[TechDebtItem]
    risk_areas: list[RiskArea]
    modernization_opportunities: list[Opportunity]
    recommended_patterns: list[str]
    estimated_effort: EffortLevel   # S | M | L | XL
```

---

## 5. LLM 프롬프트 명세

### 5.1 자연어 → SystemModel 파싱

- **모델**: gpt-4o
- **응답 형식**: JSON
- **최대 토큰**: 2048

### 5.2 레거시 분석

- **모델**: gpt-4o
- **응답 형식**: JSON
- **최대 토큰**: 4096
- **출력 언어**: 한국어
- **항목별 최소 개수**: pain_points ≥ max(컴포넌트×1.5, 5), tech_debt ≥ 4, risk_areas ≥ 4, modernization_opportunities ≥ 5, recommended_patterns ≥ 4

### 5.3 현대화 설계

- **모델**: gpt-4o
- **응답 형식**: JSON (SystemModel 스키마 준수)
- **최대 토큰**: 4096
- **입력**: Legacy SystemModel + AnalysisResult + 사용자 요구사항

### 5.4 마이그레이션 플랜

- **모델**: gpt-4o
- **응답 형식**: Markdown
- **포함 항목**: 완료 기준, 의존성, 롤백 계획, KPI, 위험 매트릭스

---

## 6. 렌더러 명세

### 6.1 공통 인터페이스

```python
class BaseRenderer(ABC):
    @abstractmethod
    def render(self, model: SystemModel) -> str:
        """SystemModel을 문자열(DSL/XML)로 변환"""

    def save(self, model: SystemModel, path: Path) -> Path:
        """render() 결과를 파일로 저장"""
```

### 6.2 Mermaid 렌더러

- 출력: `flowchart LR` DSL
- 호스트별 `subgraph` 그룹핑
- ComponentType별 노드 모양 매핑 (서버=사각형, DB=실린더 등)
- tech 스택 레이블 포함

### 6.3 diagrams(mingrammer) 렌더러

- 출력: Graphviz 기반 PNG/SVG
- 컴포넌트 (type + host + tech) → diagrams 아이콘 클래스 매핑
- 호스트별 `Cluster` 그룹핑
- AWS/GCP/Azure 공식 아이콘 우선, fallback: 제네릭 아이콘
- Graphviz 미설치 시 명확한 오류 메시지 출력

### 6.4 draw.io 렌더러

- 출력: mxGraph XML 형식
- ComponentType별 shape 스타일 매핑 (10종)
- 호스트별 swimlane 그룹핑
- 자동 격자 배치

### 6.5 draw.io 역방향 파서 (drawio_parser)

- draw.io XML → SystemModel 복원
- mxCell style → ComponentType 추론 (ArchPilot 스타일 + 범용 shape 지원)
- swimlane 레이블/ID → HostType 추론
- HTML 태그 제거 및 value 파싱

---

## 7. 오류 처리

| 오류 상황 | 처리 방식 |
|-----------|-----------|
| OPENAI_API_KEY 미설정 | 명확한 메시지 + `archpilot init` 안내 |
| 잘못된 YAML 스키마 | 파싱 오류 위치 표시 (line:col) |
| 존재하지 않는 component ID (connection) | 경고 후 해당 connection 스킵 |
| LLM JSON 파싱 실패 | 1회 재시도, 실패 시 raw 응답 저장 후 오류 |
| Graphviz 미설치 | png 포맷 건너뛰고 mermaid만 생성 + 안내 |
| draw.io Desktop 미설치 | 설치 URL 안내 후 종료 |
| LevelDB 쓰기 실패 | draw.io 종료 후 재시도 안내 |

---

## 8. PyPI 배포 명세

### 8.1 pyproject.toml 핵심

```toml
[project]
name = "archpilot"
version = "0.2.0"
requires-python = ">=3.11"
dependencies = [
    "typer[all]>=0.12",
    "rich>=13.0",
    "openai>=1.30",
    "python-dotenv>=1.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "pyyaml>=6.0",
    "diagrams>=0.23",
    "jinja2>=3.1",
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",
    "python-multipart>=0.0.9",
    "tenacity>=8.0",
    "watchdog>=4.0",
]

[project.scripts]
archpilot = "archpilot.cli.main:app"
```

### 8.2 배포 파이프라인 (GitHub Actions)

```
push to main → ruff + mypy → pytest → build wheel → upload to PyPI (Test)
tag v*.*.* → ruff + mypy → pytest → build wheel → upload to PyPI (Prod)
```

---

## 9. 미지원 범위 (v0.2.0)

- PlantUML / C4 모델 출력
- 실시간 협업 편집
- 다중 시스템 비교 (3개 이상)
- 비용 추정 자동화
- Terraform / CloudFormation 코드 생성
- Linux Flatpak 설치 draw.io 자동 인식
