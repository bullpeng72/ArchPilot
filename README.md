# ArchPilot

![version](https://img.shields.io/badge/version-0.2.3-blue)
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
archpilot drawio export <file>        draw.io → system.json 변환
```

## 요구사항

- Python 3.11+
- OpenAI API Key
- Graphviz (PNG 출력 시)
- draw.io Desktop (drawio 통합 기능 사용 시)

## 변경 이력

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
