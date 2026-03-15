# ArchPilot — draw.io 통합 완전 가이드

> draw.io Desktop ↔ ArchPilot 양방향 워크플로우

**Version**: 0.2.4 | **Last Updated**: 2026-03-15

---

## 목차

1. [통합 개요](#1-통합-개요)
2. [draw.io Desktop 설치 및 초기 설정](#2-drawio-desktop-설치-및-초기-설정)
3. [ArchPilot 컴포넌트 팔레트](#3-archpilot-컴포넌트-팔레트)
4. [draw.io에서 시스템 그리기](#4-drawio에서-시스템-그리기)
5. [draw.io → ArchPilot 가져오기](#5-drawio--archpilot-가져오기)
6. [ArchPilot → draw.io 내보내기](#6-archpilot--drawio-내보내기)
7. [양방향 편집 워크플로우](#7-양방향-편집-워크플로우)
8. [draw.io XML 파싱 원리](#8-drawio-xml-파싱-원리)
9. [Web 앱에서 draw.io 사용](#9-web-앱에서-drawio-사용)
10. [제한사항 및 주의사항](#10-제한사항-및-주의사항)
    - [10.5 복잡한 시스템 — draw.io + system.json 직접 편집 워크플로우](#105-복잡한-시스템--drawio--systemjson-직접-편집-워크플로우)
11. [문제 해결](#11-문제-해결)

---

## 1. 통합 개요

ArchPilot과 draw.io는 두 방향으로 통합됩니다:

```
                    ArchPilot
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
  ingest (가져오기)  export (내보내기)  Web UI
  .drawio → system   system → .drawio  drawio XML 탭
  .json + .mmd        .drawio 파일
        │                               │
        └───────────────┬───────────────┘
                        │
                   draw.io Desktop
                   diagrams.net (Web)
```

**4가지 통합 명령어:**

| 명령어 | 방향 | 용도 |
|--------|------|------|
| `archpilot drawio setup` | 설정 | draw.io Desktop에 ArchPilot 라이브러리 설치 |
| `archpilot drawio edit` | 양방향 | draw.io Desktop으로 다이어그램 열기 + 변경 감시 |
| `archpilot drawio watch <file>` | draw.io → AP | draw.io 파일 변경 자동 반영 |
| `archpilot drawio export <system.json>` | AP → draw.io | system.json → .drawio 파일 변환 |

---

## 2. draw.io Desktop 설치 및 초기 설정

### 2.1 draw.io Desktop 설치

draw.io Desktop이 없으면 먼저 설치합니다:

- **macOS**: `brew install --cask drawio` 또는 공식 사이트에서 `.dmg` 다운로드
- **Windows**: `winget install JGraph.Draw` 또는 공식 사이트에서 `.exe` 다운로드
- **Linux (deb)**: `sudo apt install drawio` 또는 `.deb` 패키지
- **Linux (Snap)**: `sudo snap install drawio`

> **참고**: draw.io Desktop이 없어도 [diagrams.net](https://app.diagrams.net) (웹 버전)으로 대부분의 기능을 사용할 수 있습니다.

### 2.2 ArchPilot 라이브러리 설치 (최초 1회)

```bash
# draw.io Desktop이 완전히 종료된 상태에서 실행
archpilot drawio setup
```

**무엇이 일어나는가:**

1. draw.io Desktop 설치 경로를 OS별로 자동 탐색
2. ArchPilot 컴포넌트 팔레트 XML 생성: `~/.archpilot/archpilot-library.drawio.xml`
3. Electron localStorage(LevelDB)에 라이브러리 경로를 직접 주입
4. draw.io Desktop을 다시 시작하면 좌측 사이드바에 **ArchPilot** 팔레트 등장

**성공 출력:**
```
⚙️  draw.io Desktop 통합 설정

✅ draw.io 발견: /Applications/draw.io.app
✅ 라이브러리 생성: /Users/yourname/.archpilot/archpilot-library.drawio.xml
✅ localStorage 등록: ~/Library/Application Support/draw.io/Local Storage/leveldb

┌──────────────────────────────────────────────────┐
│                   설치 완료                       │
│  draw.io Desktop을 재시작하면 팔레트가 표시됩니다  │
└──────────────────────────────────────────────────┘
```

### 2.3 OS별 경로

| OS | draw.io 실행파일 | LevelDB 경로 |
|----|----------------|-------------|
| macOS | `/Applications/draw.io.app` | `~/Library/Application Support/draw.io/Local Storage/leveldb` |
| Windows | `%ProgramFiles%\draw.io\draw.io.exe` | `%APPDATA%\draw.io\Local Storage\leveldb` |
| Linux (deb) | `/usr/bin/drawio` | `~/.config/draw.io/Local Storage/leveldb` |
| Linux (Snap) | `/snap/bin/drawio` | `~/snap/drawio/common/.config/draw.io/Local Storage/leveldb` |

---

## 3. ArchPilot 컴포넌트 팔레트

`archpilot drawio setup` 후 draw.io Desktop 사이드바에 다음 팔레트가 등장합니다:

| 팔레트 아이콘 | ComponentType | 기본 스타일 |
|-------------|--------------|------------|
| 직사각형 (파란 테두리) | `server` | roundedRectangle |
| 직사각형 (녹색 테두리) | `service` | roundedRectangle |
| 실린더 | `database` | cylinder |
| 원형 (주황) | `cache` | ellipse |
| 구름 (노란) | `storage` | cloud |
| 마름모 | `loadbalancer` | rhombus |
| 육각형 | `gateway` | hexagon |
| 큐 모양 | `queue` | parallelogram |
| 방패 | `security` | shield |
| 모니터 | `monitoring` | monitor |
| PC 아이콘 | `client` | client |
| 빈 사각형 (회색) | `mainframe` | darkGray |
| 파이프 | `esb` | mxgraph.cisco.routers.generic_router |
| 구름 (흰색) | `cdn` | cloud |

---

## 4. draw.io에서 시스템 그리기

### 4.1 기본 규칙

**컴포넌트 레이블 작성:**
```
첫 번째 줄: 컴포넌트 이름 (예: MySQL Master)
두 번째 줄: 기술 스택 (예: MySQL 5.7)  ← TechOntology 자동 추론에 사용
세 번째 줄: 추가 기술 (선택)
```

예시:
```
Oracle DB
Oracle 11g
RAC
```

**HostType 표현 — 수영 레인(swimlane) 사용:**

| 수영 레인 레이블 | HostType 추론 |
|----------------|--------------|
| `on-premise` | `on-premise` |
| `On-Premise` | `on-premise` |
| `onprem` | `on-premise` |
| `AWS Cloud` | `aws` |
| `aws` | `aws` |
| `GCP Cloud` | `gcp` |
| `Azure` | `azure` |
| `Microsoft Azure` | `azure` |

수영 레인 추가 방법: Extras 메뉴 → Edit Style → `swimlane` 타입 선택 후 레이블 설정.

**연결선 레이블 — 프로토콜:**
화살표를 그린 후 레이블에 프로토콜을 입력합니다:
```
HTTP      JDBC      gRPC
REST      Kafka     SOAP
HTTPS     IBM MQ    FTP
```

### 4.2 ComponentType 자동 추론

레이블 둘째 줄에 기술명을 입력하면 `type`이 자동 추론됩니다.

| 기술명 | 자동 추론 type |
|--------|--------------|
| MySQL, Oracle, PostgreSQL, MongoDB | `database` |
| Redis, Memcached, Hazelcast | `cache` |
| Kafka, RabbitMQ, IBM MQ, SQS | `queue` |
| Nginx, HAProxy, AWS ALB, Kong | `gateway` 또는 `loadbalancer` |
| React, Flutter, iOS, Android | `client` |
| IBM z/OS, COBOL, CICS | `mainframe` |
| Grafana, Datadog, Prometheus | `monitoring` |
| WAF, HSM, Firewall, PKCS | `security` |
| Tibco, MuleSoft, ESB | `esb` |
| S3, NFS, HDFS, GCS | `storage` |

---

## 5. draw.io → ArchPilot 가져오기

### 5.1 파일로 직접 ingest

```bash
# draw.io Desktop에서 저장한 파일
archpilot ingest ~/Desktop/my-system.drawio --format mermaid,drawio

# 결과
# output/system.json
# output/legacy/diagram.mmd
# output/legacy/diagram.drawio (ArchPilot 스타일로 재생성)
```

### 5.2 diagrams.net (Web)에서 가져오기

1. diagrams.net에서 다이어그램 완성
2. `File → Export As → XML` 또는 `Extras → Edit Diagram → 전체 복사`
3. `.drawio` 파일로 저장 후:
   ```bash
   archpilot ingest ~/Downloads/my-diagram.drawio
   ```

### 5.3 Web 앱에서 직접 붙여넣기

```bash
archpilot serve output/ --open
```
브라우저 Web 앱 → "draw.io XML" 탭 → XML 붙여넣기 → "분석 시작"

### 5.4 API로 직접 주입

```bash
curl -X POST http://localhost:8080/api/ingest/drawio \
  -H "Content-Type: application/json" \
  -d '{
    "xml": "<mxGraphModel>...</mxGraphModel>",
    "system_name": "My System"
  }'
```

---

## 6. ArchPilot → draw.io 내보내기

### 6.1 ingest 시 자동 생성

```bash
archpilot ingest my-system.yaml --format mermaid,drawio
# → output/legacy/diagram.drawio 생성
```

### 6.2 drawio export 명령

```bash
archpilot drawio export output/system.json
# → output/legacy/diagram.drawio 생성 (기존 system.json에서)
```

### 6.3 현대화 설계 draw.io 내보내기

`archpilot modernize` 실행 시 자동으로 `output/modern/diagram.drawio`가 생성됩니다.

### 6.4 draw.io XML 생성 구조

ArchPilot이 생성하는 draw.io XML은 mxGraph 표준을 따릅니다:

```xml
<mxGraphModel>
  <root>
    <mxCell id="0"/>
    <mxCell id="1" parent="0"/>

    <!-- 호스트별 swimlane 컨테이너 -->
    <mxCell id="host_aws" value="AWS Cloud"
            style="swimlane;..." parent="1">
      <mxGeometry .../>
    </mxCell>

    <!-- 컴포넌트 노드 (ComponentType별 스타일) -->
    <mxCell id="aurora_db" value="Aurora PostgreSQL&#10;AWS Aurora 15"
            style="shape=mxgraph.azure2.azure_sql_database;..."
            parent="host_aws">
      <mxGeometry .../>
    </mxCell>

    <!-- 연결선 -->
    <mxCell id="conn_1" value="JDBC"
            style="edgeStyle=orthogonalEdgeStyle;..."
            source="app_server" target="aurora_db">
      <mxGeometry relative="1"/>
    </mxCell>
  </root>
</mxGraphModel>
```

**ComponentType별 draw.io 스타일:**

| ComponentType | draw.io style |
|--------------|--------------|
| `server` | `rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf` |
| `database` | `shape=cylinder3;fillColor=#f5f5f5` |
| `cache` | `ellipse;fillColor=#fff2cc;strokeColor=#d6b656` |
| `queue` | `shape=mxgraph.flowchart.delay;fillColor=#f8cecc` |
| `storage` | `shape=mxgraph.flowchart.stored_data;fillColor=#e1d5e7` |
| `loadbalancer` | `rhombus;fillColor=#d5e8d4;strokeColor=#82b366` |
| `gateway` | `rounded=1;arcSize=50;fillColor=#e1d5e7;strokeColor=#9673a6` |
| `mainframe` | `rounded=0;fillColor=#ccccff;strokeColor=#36393d` |
| `security` | `shape=mxgraph.flowchart.decision;fillColor=#ffcccc` |
| `monitoring` | `fillColor=#fffacd;strokeColor=#d6b656` |
| `esb` | `rounded=1;arcSize=30;fillColor=#f0d0ff;strokeColor=#9500d3` |
| `client` | `shape=mxgraph.cisco.computers.pc;fillColor=#dae8fc` |
| `cdn` | `ellipse;fillColor=#d5e8d4;strokeColor=#82b366` |
| `service` | `rounded=1;fillColor=#d5e8d4;strokeColor=#82b366` |

---

## 7. 양방향 편집 워크플로우

### 7.1 전체 흐름

```
YAML 작성
    ↓
archpilot ingest my-system.yaml --format drawio
    ↓
output/legacy/diagram.drawio 생성
    ↓
archpilot drawio edit --output ./output
    ↓  (draw.io Desktop 자동 실행)
draw.io에서 컴포넌트 추가/수정/삭제
    ↓  (Ctrl+S 저장 시 watchdog이 감지)
output/system.json 자동 갱신
output/legacy/diagram.mmd 자동 갱신
    ↓
archpilot analyze output/system.json -r "요구사항"
archpilot modernize output/system.json -r "요구사항"
```

### 7.2 edit 명령

```bash
archpilot drawio edit --output ./output
```

- `output/legacy/diagram.drawio`를 draw.io Desktop으로 자동 실행
- 파일 변경(저장) 감시 시작
- Ctrl+S 저장 시 즉시 `system.json` 갱신

**옵션:**
```
--output, -o    감시할 출력 디렉토리 (기본: settings.output_dir)
--format, -f    갱신 시 생성할 포맷 (기본: mermaid)
```

### 7.3 watch 명령

특정 파일만 감시합니다:

```bash
archpilot drawio watch ~/Desktop/my-diagram.drawio --output ./output
```

- 지정한 `.drawio` 파일을 감시
- 저장 시 `output/system.json`과 `output/legacy/diagram.mmd` 갱신
- draw.io Desktop은 자동 실행 안 함 (직접 실행 필요)

### 7.4 파일 감시 종료

`Ctrl+C`로 감시를 종료합니다. 종료 후 재분석:

```bash
archpilot analyze output/system.json -r "현대화 목표"
archpilot modernize output/system.json -r "현대화 목표"
archpilot serve output/ --open
```

---

## 8. draw.io XML 파싱 원리

`archpilot ingest *.drawio` 또는 Web 앱에서 draw.io XML을 주입하면 `renderers/drawio_parser.py`가 동작합니다.

### 8.1 mxCell style → ComponentType 매핑

draw.io의 각 노드는 `style` 문자열을 가집니다. ArchPilot은 이 문자열에서 키워드를 찾아 ComponentType을 추론합니다.

| style 키워드 | ComponentType |
|------------|--------------|
| `aws4.aurora`, `aws4.rds`, `cylinder`, `flowchart.database`, `disk_storage` | `database` |
| `aws4.s3`, `aws4.glacier`, `flowchart.stored_data` | `storage` |
| `aws4.sqs`, `aws4.mq`, `flowchart.delay`, `bpmn` | `queue` |
| `aws4.elasticache`, `aws4.redis` | `cache` |
| `aws4.cloudfront` | `cdn` |
| `aws4.api_gateway` | `gateway` |
| `aws4.elb`, `aws4.alb`, `rhombus` | `loadbalancer` |
| `flowchart.decision` | `security` |
| `flowchart.terminator`, `cisco.computers`, `peripherals.pc` | `client` |
| `arcSize=50` + `#e1d5e7` (연보라) | `gateway` |
| `arcSize=30` + `#f0d0ff` (보라) | `esb` |
| `#ccccff` (남보라) | `mainframe` |
| `#fffacd` (연노랑) | `monitoring` |
| `ellipse` + `#fff2cc`/`#d6b656` | `cache` |
| `ellipse` + `#d5e8d4`/`#82b366` | `cdn` |

**매핑 안 되는 경우:** TechOntology로 레이블 텍스트를 분석해 재추론. 여전히 모르면 `unknown`.

### 8.2 swimlane → HostType 매핑

| swimlane 레이블 | HostType |
|----------------|---------|
| `on-premise`, `On-Premise`, `onprem` | `on-premise` |
| `aws`, `AWS Cloud`, `Amazon` | `aws` |
| `gcp`, `GCP Cloud`, `Google Cloud` | `gcp` |
| `azure`, `Azure`, `Microsoft Azure` | `azure` |
| 매핑 안 되면 | `on-premise` (기본) |

### 8.3 레이블 파싱

mxCell `value` 속성에서 컴포넌트 이름과 기술 스택을 추출합니다:

```
value="MySQL Master&#10;MySQL 5.7&#10;RAC"
         └─ label        └─ tech[0]     └─ tech[1]
```

HTML 태그(`<b>`, `<br>` 등)는 자동 제거됩니다.

---

## 9. Web 앱에서 draw.io 사용

### 9.1 draw.io XML 탭

```bash
archpilot serve output/ --open
```

브라우저 Web 앱에서:
1. 상단 탭 → "draw.io XML" 선택
2. XML 텍스트 영역에 붙여넣기
3. "분석 시작" 클릭

### 9.2 draw.io 다이어그램 다운로드

분석·현대화 완료 후 Web 앱에서 draw.io 파일을 다운로드할 수 있습니다:

```
GET /api/diagram/legacy   → legacy/diagram.drawio 다운로드
GET /api/diagram/modern   → modern/diagram.drawio 다운로드
```

또는 Web 앱 UI의 다운로드 버튼 사용.

---

## 10. 제한사항 및 주의사항

### 10.1 엔터프라이즈 필드 미보존

draw.io XML은 ArchPilot의 엔터프라이즈 필드를 직접 인코딩하지 않습니다:

| 필드 | draw.io에서 | ArchPilot 반환 시 |
|------|------------|-----------------|
| `criticality` | 미보존 | 기본값 `medium` |
| `lifecycle_status` | 미보존 | 기본값 `active` |
| `data_classification` | 미보존 | `null` |
| `owner` | 미보존 | `""` |
| `specs` | 미보존 | `{}` |

**대응:** draw.io로 시스템 구조(topology)를 그리고, 엔터프라이즈 필드는 ingest 후 `output/system.json`을 직접 편집해 보완합니다. 자세한 워크플로우는 [§10.5](#105-복잡한-시스템--drawio--systemjson-직접-편집-워크플로우)를 참조하세요.

### 10.2 양방향 roundtrip 주의

```
YAML (criticality: high 있음)
    ↓ ingest → export
diagram.drawio (criticality 없음)
    ↓ watch (저장)
system.json (criticality: medium으로 초기화됨!)
```

중요한 엔터프라이즈 정보가 있는 경우, YAML 파일을 원본으로 유지하고 draw.io는 시각적 편집 용도로만 사용하세요.

### 10.3 대형 다이어그램

컴포넌트가 50개 이상인 draw.io 파일은 파싱 시간이 길어질 수 있습니다. LLM 컨텍스트 최적화가 자동 적용됩니다.

### 10.4 draw.io Desktop이 실행 중일 때 setup 금지

`archpilot drawio setup`은 draw.io Desktop이 **완전히 종료된 상태**에서만 실행해야 합니다. 실행 중에는 LevelDB가 잠겨 쓰기 실패합니다.

---

### 10.5 복잡한 시스템 — draw.io + system.json 직접 편집 워크플로우

draw.io가 저장할 수 없는 엔터프라이즈 메타데이터(criticality, lifecycle_status, specs, owner 등)를 보완하는 권장 패턴입니다.

#### 전체 흐름

```
① draw.io로 시스템 토폴로지 그리기
        ↓
② archpilot ingest my-diagram.drawio
        ↓
   output/system.json 생성 (구조 + 기술스택 자동 추론)
        ↓
③ output/system.json 직접 편집
   → criticality, lifecycle_status, specs, owner 등 추가
        ↓
④ archpilot analyze output/system.json -r "..."
   archpilot modernize output/system.json -r "..."
   archpilot serve output/ --open
```

#### 1단계: draw.io로 토폴로지 그리기

draw.io는 시스템 구조(컴포넌트 배치·연결·호스트 구분)를 빠르게 표현하는 데 최적입니다. 이 단계에서는 컴포넌트 배치, 연결선, swimlane(호스트), 레이블(이름 + 기술스택)에 집중합니다.

#### 2단계: ingest → system.json 생성

```bash
archpilot ingest my-system.drawio --format mermaid,drawio
# → output/system.json 생성
# → output/legacy/diagram.mmd 생성
```

#### 3단계: system.json 직접 보완

JSON 편집기로 `output/system.json`을 열고, 각 컴포넌트에 draw.io에서 입력할 수 없었던 필드를 추가합니다:

```json
{
  "id": "oracle_db",
  "type": "database",
  "label": "Oracle DB (운영)",
  "tech": ["Oracle 11g"],
  "host": "on-premise",

  "criticality": "high",
  "lifecycle_status": "eol",
  "data_classification": "restricted",
  "owner": "DB운영팀",
  "specs": {
    "cpu": 16,
    "memory": "64GB",
    "storage": "20TB SAN",
    "instance_type": "Oracle Exadata X6"
  },
  "metadata": {
    "compliance": "PCI-DSS Level 1",
    "last_patch": "2022-03",
    "known_cve": ["CVE-2021-2351"]
  }
}
```

추가 가능한 모든 필드 목록: [`SCHEMA.md`](./2_SCHEMA.md) 참조.

**편집 팁:**

| 필드 | 가능한 값 |
|------|----------|
| `criticality` | `low` / `medium` / `high` / `critical` |
| `lifecycle_status` | `active` / `deprecated` / `eol` |
| `data_classification` | `public` / `internal` / `confidential` / `restricted` |
| `owner` | 자유 문자열 (예: `"DB운영팀"`, `"Platform-A"`) |
| `specs` | 자유 key-value (예: `{"cpu": 8, "memory": "32GB"}`) |
| `metadata` | 자유 key-value (규정준수, 패치이력, 계약만료 등) |

#### 4단계: 분석·현대화 실행

보완된 system.json으로 분석을 실행하면 AI가 criticality·lifecycle_status·specs를 참조해 더 정밀한 `component_decisions`를 생성합니다:

```bash
archpilot analyze output/system.json \
  -r "AWS 전환, Oracle 비용 절감, PCI-DSS 준수 유지"

archpilot modernize output/system.json \
  -r "AWS 전환, Oracle 비용 절감, PCI-DSS 준수 유지"

archpilot serve output/ --open
```

#### ⚠️ draw.io 재편집 시 주의

system.json을 직접 편집한 후 draw.io에서 다시 수정·저장하면 watch/edit 기능이 system.json을 **덮어씁니다** — 직접 편집한 내용이 사라집니다:

```
draw.io에서 저장 (watch 활성 상태)
    ↓
⚠️  output/system.json 재생성 → 직접 추가한 필드 소실!
```

**안전한 순서:**

```
draw.io 편집 완료 (Ctrl+C로 watch 종료)
    ↓
output/system.json 직접 편집 (엔터프라이즈 필드 추가)
    ↓
archpilot analyze / modernize
```

draw.io 수정이 필요해지면: 다시 ingest 후 system.json을 재편집하거나, 원본 YAML에 엔터프라이즈 필드를 기록해 두고 YAML로 ingest하는 방식을 권장합니다.

---

## 11. 문제 해결

### setup 실패: "draw.io를 찾을 수 없습니다"

```
❌ draw.io Desktop이 설치되지 않았거나 탐색 경로에 없습니다.
```

draw.io Desktop을 설치 후 한 번 실행한 다음 종료하세요. 비표준 경로에 설치된 경우:
```bash
# 실행파일 경로를 직접 확인 후 PATH에 추가
which drawio    # Linux
ls /Applications | grep draw    # macOS
```

### setup 실패: "LevelDB 쓰기 실패"

draw.io Desktop이 실행 중이면 LevelDB가 잠깁니다.
```bash
# draw.io 프로세스 종료 후 재시도
pkill -f draw.io   # macOS/Linux
# Windows: 작업 관리자에서 draw.io 종료
```

### setup 후 팔레트가 안 보임

draw.io Desktop을 완전히 종료 후 재시작하세요. 메뉴 → View → Reset View도 시도해보세요.

### setup이 처음 실행이어서 LevelDB가 없음

draw.io Desktop을 최초로 실행한 후 종료하면 LevelDB가 생성됩니다. 그 후 `archpilot drawio setup` 실행.

### watch/edit 중 "파일을 열 수 없습니다"

```bash
# 파일 존재 확인
ls output/legacy/diagram.drawio

# 없으면 먼저 ingest 실행
archpilot ingest my-system.yaml --format drawio
```

### draw.io 파싱 시 컴포넌트 type이 모두 unknown

draw.io에서 기본 도형(직사각형 등)을 사용하면 스타일 키워드가 없어서 추론이 어렵습니다.
각 노드의 **레이블 둘째 줄에 기술명을 추가**하면 TechOntology로 추론됩니다:
```
Oracle DB
Oracle 11g    ← 이 줄이 있으면 type: database 자동 추론
```

### Connection이 무시된다는 경고

```
⚠ Connection 출발지 'web_server'가 components에 없어 무시됩니다.
```

draw.io에서 엣지가 노드에 정확히 연결(attach)되지 않으면 파서가 id를 찾지 못합니다. draw.io에서 엣지 끝점이 노드 위에 붙어(연결점에 파란 원이 표시) 있는지 확인하세요.

---

## 참고

- YAML 스키마 작성 가이드: [`SCHEMA.md`](./2_SCHEMA.md)
- 전체 사용 가이드: [`USER_GUIDE.md`](./3_USER_GUIDE.md) — 시나리오 B, C, D
- 내부 구현:
  - `src/archpilot/renderers/drawio.py` — SystemModel → draw.io XML
  - `src/archpilot/renderers/drawio_parser.py` — draw.io XML → SystemModel
  - `src/archpilot/renderers/drawio_library.py` — 컴포넌트 팔레트 XML 생성
  - `src/archpilot/core/drawio_config.py` — Electron LevelDB 직접 조작
  - `src/archpilot/cli/cmd_drawio.py` — draw.io CLI 서브커맨드
