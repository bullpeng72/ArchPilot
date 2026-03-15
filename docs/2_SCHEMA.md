# ArchPilot — 시스템 스키마 작성 가이드

> 레거시 시스템을 ArchPilot 규격 YAML/JSON으로 작성하는 방법

**Version**: 0.2.3 | **Last Updated**: 2026-03-15

---

## 목차

1. [YAML 스키마 전체 구조](#1-yaml-스키마-전체-구조)
2. [name / description](#2-name--description)
3. [components — 컴포넌트 배열](#3-components--컴포넌트-배열)
4. [connections — 연결 배열](#4-connections--연결-배열)
5. [ComponentType 선택 가이드](#5-componenttype-선택-가이드)
6. [HostType 선택 가이드](#6-hosttype-선택-가이드)
7. [엔터프라이즈 필드](#7-엔터프라이즈-필드)
8. [metadata 관례](#8-metadata-관례)
9. [완전한 예제: 온프레미스 뱅킹 시스템](#9-완전한-예제-온프레미스-뱅킹-시스템)
10. [완전한 예제: 하이브리드 클라우드 시스템](#10-완전한-예제-하이브리드-클라우드-시스템)
11. [자주 하는 실수](#11-자주-하는-실수)
12. [검증 규칙](#12-검증-규칙)

---

## 1. YAML 스키마 전체 구조

```yaml
# ──────────────────────────────────────────────
# ArchPilot System Schema v0.2.3
# ──────────────────────────────────────────────

name: string                    # 필수. 시스템 이름
description: string             # 권장. 구축 연도, 목적, 특이사항 설명

components:                     # 필수. 1개 이상
  - id: string                  # 필수. snake_case 고유 식별자
    type: ComponentType         # 권장. 생략 시 tech[]에서 자동 추론
    label: string               # 필수. 표시 이름 (한국어 가능)
    tech: [string]              # 권장. 버전 포함 기술 스택 목록
    host: HostType              # 선택. 기본값: on-premise

    # 엔터프라이즈 필드 (분석 품질에 직접 영향)
    criticality: high|medium|low               # 선택. 기본값: medium
    lifecycle_status: active|deprecated|eol|sunset|decommissioned  # 선택. 기본값: active
    data_classification: public|internal|confidential|restricted   # 선택. 기본값: 없음
    owner: string               # 선택. 담당팀 또는 담당자

    # 상세 사양 (LLM 컨텍스트 절약을 위해 핵심만)
    specs:
      cpu: int
      memory: string            # "32GB", "128GB" 등
      storage: string           # "2TB SAN", "50TB" 등
      nodes: string             # "3 Primary + 3 Replica" 등
      instances: int
      version: string
      [기타 자유 형식 키]

    # 추가 정보 (자유 형식, 분석에 활용됨)
    metadata:
      [자유 형식 키-값]         # 예: provider, operator, zone, compliance 등

connections:                    # 선택. 없으면 빈 배열
  - from_id: component_id       # 필수. components.id 중 하나
    to_id: component_id         # 필수. components.id 중 하나
    protocol: string            # 권장. HTTP | JDBC | gRPC | Kafka | REST 등
    label: string               # 선택. 연결 레이블
    bidirectional: bool         # 선택. 기본값: false
    data_format: string         # 선택. JSON | XML | Protobuf | CSV 등
    api_version: string         # 선택. "v2", "SOAP 1.1" 등
```

---

## 2. name / description

```yaml
name: "Core Banking Legacy System"
description: "2010년 구축된 온프레미스 은행 코어 시스템.
              주요 거래 처리, 계좌 관리, 대출 심사를 담당.
              피크 시간대 Oracle RAC 락 경합 이슈 존재."
```

**description 작성 팁:**
- 구축 연도 명시 (AI 분석의 EOL 계산에 사용)
- 알려진 문제점이나 특이사항을 직접 기록하면 분석 품질이 높아짐
- 시스템의 비즈니스 목적 설명

---

## 3. components — 컴포넌트 배열

### 3.1 id

```yaml
# ✅ 올바른 형식: snake_case, 영문+숫자+언더스코어
id: core_banking_server
id: oracle_rac_primary
id: ibm_mq_broker
id: legacy_esb

# ❌ 잘못된 형식
id: "Core Banking"       # 공백 불가
id: core-banking         # 하이픈 불가 (연결에서 혼동)
id: CoreBanking          # camelCase 비권장
```

**규칙:**
- 시스템 전체에서 고유해야 함 (중복 시 Pydantic 오류)
- 영문 소문자, 숫자, 언더스코어만 사용
- 의미 있는 이름 사용 (ai가 id 기반으로 컴포넌트를 참조)

### 3.2 type

`type`은 생략 가능하지만 명시하면 파싱 속도와 정확도가 올라갑니다.

```yaml
# 명시적 type (권장)
- id: payment_db
  type: database
  label: "결제 DB"
  tech: ["Oracle 12c"]

# 자동 추론 (tech에서 추론)
- id: payment_db
  label: "결제 DB"
  tech: ["Oracle 12c"]   # → type: database 자동 추론
```

자동 추론 가능한 기술명은 70개 이상입니다. `core/tech_ontology.py` 참조.

### 3.3 tech

```yaml
tech: ["Java 17", "Spring Boot 3", "Tomcat 10"]   # 구체적 버전 명시 권장
tech: ["COBOL", "CICS", "DB2 z/OS"]              # 레거시 기술도 정확히 기술
tech: ["IBM MQ 8.0"]                              # 단일 기술도 배열로
tech: []                                           # 미상일 경우 빈 배열
```

**버전 포함 권장 이유:**
- AI가 EOL 날짜를 정확히 계산 (예: Java 8 EOS 2030-12)
- 보안 취약점(CVE) 식별에 활용
- 마이그레이션 복잡도 추정에 활용

---

## 4. connections — 연결 배열

```yaml
connections:
  - from_id: portal          # 출발 컴포넌트 id
    to_id: core_server       # 도착 컴포넌트 id
    protocol: HTTP/SOAP      # 프로토콜
    label: "거래 요청"        # 선택. 레이블
    bidirectional: false     # 선택. 기본값 false

  - from_id: core_server
    to_id: oracle_db
    protocol: JDBC

  - from_id: kafka_cluster
    to_id: notification_svc
    protocol: Kafka Consumer
    data_format: JSON
```

**protocol 작성 팁:**
- 표준 프로토콜: `HTTP`, `HTTPS`, `gRPC`, `JDBC`, `REST`, `SOAP`, `WebSocket`
- 메시지: `Kafka Producer`, `Kafka Consumer`, `IBM MQ`, `AMQP`, `STOMP`
- DB: `JDBC`, `ODBC`, `ADO.NET`, `ORM`
- 레거시: `CICS CTG`, `SAP RFC`, `ISO 8583`, `EDIFACT`, `FTP`, `FIX`
- 보안: `SSL-VPN`, `mTLS`, `IPSec/BGP`, `SAML 2.0`

**호환 키워드:** `from`/`to`를 써도 됩니다 (내부에서 `from_id`/`to_id`로 변환).

```yaml
# 구버전 호환 (OK)
connections:
  - from: portal
    to: core_server
    protocol: HTTP
```

---

## 5. ComponentType 선택 가이드

### 5.1 server vs service

```yaml
# server: 독립 실행 가능한 애플리케이션 서버
- id: portal
  type: server
  label: "웹 포털 (IIS)"
  tech: ["IIS 8.5", "ASP.NET 4.5"]

# service: 내부 마이크로서비스 (다른 서비스에 종속)
- id: auth_service
  type: service
  label: "인증 서비스"
  tech: ["Java 17", "Spring Boot"]
```

### 5.2 mainframe — 반드시 mainframe 사용

```yaml
# ✅ 올바름
- id: core_mainframe
  type: mainframe           # mainframe 전용 type 사용
  label: "메인프레임"
  tech: ["IBM z/OS", "COBOL", "CICS", "DB2"]

# ❌ 잘못됨 — mainframe을 server로 분류하면 분석 품질 저하
- id: core_mainframe
  type: server              # ❌
  label: "메인프레임"
  tech: ["IBM z/OS", "COBOL"]
```

### 5.3 security — HSM, WAF, Firewall

```yaml
- id: hsm
  type: security            # security 전용 type
  label: "HSM (암호화 모듈)"
  tech: ["Thales HSM", "PKCS#11"]
  criticality: high

- id: waf
  type: security
  label: "웹 방화벽 (WAF)"
  tech: ["Piolink WEBFRONT-K"]
```

### 5.4 esb — 통합 미들웨어

```yaml
- id: legacy_esb
  type: esb                 # esb 전용 type
  label: "행정정보 공동이용 ESB"
  tech: ["Tibco BusinessWorks", "SOAP/WSDL"]
```

### 5.5 gateway — API GW, VPN, DMZ

```yaml
- id: api_gw
  type: gateway
  label: "API 게이트웨이"
  tech: ["Kong", "OAuth 2.0"]

- id: ssl_vpn
  type: gateway
  label: "SSL-VPN"
  tech: ["F5 BIG-IP APM", "FIDO2"]
  metadata:
    zone: DMZ
```

---

## 6. HostType 선택 가이드

```yaml
# 온프레미스 (자체 데이터센터)
host: on-premise

# 클라우드
host: aws      # AWS (NCP, 네이버 클라우드도 aws로 표기하고 metadata.provider로 구분)
host: azure    # Microsoft Azure
host: gcp      # Google Cloud Platform
host: hybrid   # 애매한 복합 환경 전체를 hybrid 하나로 표기 (드물게 사용)
```

**하이브리드 시스템 작성법:**

```yaml
# 각 컴포넌트에 실제 호스팅 위치를 기록 (hybrid 최소화)
components:
  - id: scada
    host: on-premise      # OT망

  - id: erp_sap
    host: azure           # Azure에 있음

  - id: ncp_db
    host: aws             # NCP (Naver Cloud) → host는 aws로, metadata로 구분
    metadata:
      provider: NCP

  - id: dmz_gw
    host: on-premise      # DMZ는 온프레미스
    metadata:
      zone: DMZ
```

---

## 7. 엔터프라이즈 필드

이 필드들은 `metadata` 하위가 아니라 **컴포넌트 최상위 레벨**에 기록해야 합니다.

### 7.1 criticality

```yaml
# high: 장애 시 매출·규제 직접 영향
- id: payment_db
  criticality: high       # 결제 DB, 인증 서버, 핵심 거래 엔진

# medium: 장애 시 일부 기능 저하 (기본값)
- id: report_server
  criticality: medium

# low: 장애 시 비즈니스 영향 미미
- id: monitoring
  criticality: low
```

**분석에서 criticality가 높은 컴포넌트는:**
- `health_score` 계산에 가중치 부여
- `risk_areas`에서 우선 언급
- `component_decisions`에서 retire 판단 시 신중히 처리

### 7.2 lifecycle_status

```yaml
- id: legacy_portal
  lifecycle_status: deprecated   # 지원 중단 예고 (벤더 공지)
  tech: ["IIS 8.5"]              # Microsoft IIS 8.5: 2018년 mainstream 지원 종료

- id: mysql_master
  lifecycle_status: eol          # End of Life — 완전 종료
  tech: ["MySQL 5.7"]            # MySQL 5.7: 2023년 EOL

- id: new_redis
  lifecycle_status: active       # 기본값, 생략 가능
```

| 상태 | 의미 | Mermaid 표시 |
|------|------|-------------|
| `active` | 정상 운영 (기본) | 없음 |
| `deprecated` | 지원 중단 예고 | 주황 배경, `⚠ Deprecated` |
| `eol` | 벤더 지원 완전 만료 | 빨간 배경, `⚠ EOL` |
| `sunset` | 내부 종료 예정 | `↓ Sunset` |
| `decommissioned` | 폐기 완료 (레퍼런스) | 없음 |

### 7.3 data_classification

```yaml
- id: customer_db
  data_classification: restricted    # PII·금융·의료 — Mermaid에 🔒 RESTRICTED

- id: audit_log
  data_classification: confidential  # 기밀 — 🔒 CONFIDENTIAL

- id: product_catalog
  data_classification: public        # 공개 데이터

# 생략 시: 분류 없음 (internal로 취급)
```

### 7.4 owner

```yaml
- id: payment_gateway
  owner: "결제플랫폼팀"

- id: erp_sap
  owner: "ERP운영팀/IT인프라"

# 미상이면 생략
```

---

## 8. metadata 관례

`metadata`는 자유 형식 딕셔너리입니다. 자주 사용하는 키 관례:

### 8.1 운영 정보

```yaml
metadata:
  zone: DMZ                      # 네트워크 존: DMZ | OT | IT | Admin
  provider: NCP                  # 클라우드 프로바이더 (AWS 이외)
  operator: "행정안전부"           # 운영 기관 (자체 운영이 아닌 경우)
  network: "행정전산망 (분리망)"   # 네트워크 명칭
  compliance: ["전자서명법", "개인정보보호법"]  # 준수 규제
  retention: "10년 (공공기록물법)" # 데이터 보관 기한
  users: "MAU 320만"              # 사용자 규모
  daily_issuance: "18만 건"       # 처리량
  note: "ActiveX 의존성으로 Chrome/Firefox 미지원"  # 특이사항
```

### 8.2 LLM 생성 메타데이터 (modernize 출력에 포함)

`archpilot modernize` 실행 후 생성된 `modern/system.json`의 각 컴포넌트에 포함되는 필드들:

```yaml
metadata:
  is_new: true                   # 현대화로 새로 추가된 컴포넌트
  removed: true                  # 레거시에서 제거된 컴포넌트
  reason: "Oracle 라이선스 비용 절감 및 관리형 서비스 전환"  # 변경 이유
  strategy: "replace"            # 6R 전략 (마이그레이션 플랜에 활용)
  replaces: "oracle_rac"         # 대체하는 레거시 컴포넌트 id
```

이 필드들은 직접 작성할 필요 없이 AI가 생성합니다. 단, 레거시 YAML 작성 시 미리 기록하면 AI 분석 품질이 향상됩니다.

---

## 9. 완전한 예제: 온프레미스 뱅킹 시스템

실제로 자주 볼 수 있는 2010년대 구축 온프레미스 은행 시스템입니다.

```yaml
name: "Core Banking Legacy System"
description: "2010년 구축된 온프레미스 은행 코어 시스템.
              주요 거래 처리(COBOL 메인프레임), 계좌 관리, 대출 심사 담당.
              IIS + ASP.NET 포털, JBoss EAP 미들웨어, Oracle 11g 운영.
              알려진 문제: 피크 시간대 Oracle RAC 락 경합 응답 지연,
              보안 패치 2년째 지연 중."

components:
  # ── 클라이언트 / 포털 ────────────────────────────────────────
  - id: portal
    type: server
    label: "웹 포털 (IIS)"
    tech: ["IIS 8.5", "ASP.NET 4.5", "Windows Server 2012"]
    host: on-premise
    lifecycle_status: deprecated    # IIS 8.5: mainstream 지원 종료
    criticality: medium

  # ── 코어 서버 ────────────────────────────────────────────────
  - id: core_server
    type: server
    label: "코어 뱅킹 서버"
    tech: ["Java EE 6", "JBoss EAP 4", "COBOL 인터페이스"]
    host: on-premise
    criticality: high              # 핵심 거래 처리
    specs:
      cpu: 32
      memory: "128GB"

  # ── 메인프레임 ───────────────────────────────────────────────
  - id: mainframe
    type: mainframe                # mainframe 전용 type 필수
    label: "메인프레임 (IBM z14)"
    tech: ["IBM z/OS", "COBOL", "DB2 z/OS", "CICS"]
    host: on-premise
    criticality: high
    specs:
      model: "IBM z14"

  # ── 배치 서버 ────────────────────────────────────────────────
  - id: batch_server
    type: server
    label: "배치 처리 서버"
    tech: ["Spring Batch", "Java 7", "Quartz"]
    host: on-premise
    lifecycle_status: deprecated   # Java 7 EOS 2022
    owner: "배치운영팀"

  # ── 데이터베이스 ─────────────────────────────────────────────
  - id: oracle_primary
    type: database
    label: "Oracle DB (운영)"
    tech: ["Oracle 11g", "RAC"]
    host: on-premise
    criticality: high
    lifecycle_status: eol          # Oracle 11g: 2020년 Extended Support 종료
    data_classification: restricted # 금융 고객 데이터
    owner: "DB운영팀"
    specs:
      cpu: 16
      memory: "64GB"
      storage: "20TB SAN"

  - id: oracle_dr
    type: database
    label: "Oracle DB (DR)"
    tech: ["Oracle 11g", "Data Guard"]
    host: on-premise
    criticality: high
    data_classification: restricted

  # ── 메시지 큐 ────────────────────────────────────────────────
  - id: ibm_mq
    type: queue
    label: "IBM MQ (대외 연계)"
    tech: ["IBM MQ 8.0"]
    host: on-premise
    metadata:
      note: "전금융기관 표준 메시지 연계"

  # ── 파일 서버 ────────────────────────────────────────────────
  - id: ftp_server
    type: server
    label: "FTP 서버 (전문 연계)"
    tech: ["vsftpd", "Linux"]
    host: on-premise
    lifecycle_status: deprecated

  # ── 보안 장비 ────────────────────────────────────────────────
  - id: hsm
    type: security                 # security 전용 type
    label: "HSM (암호화 모듈)"
    tech: ["Thales HSM", "PKCS#11"]
    host: on-premise
    criticality: high

connections:
  # 포털 → 코어
  - from_id: portal
    to_id: core_server
    protocol: HTTP/SOAP
    data_format: XML

  # 코어 → 메인프레임
  - from_id: core_server
    to_id: mainframe
    protocol: CICS CTG
    label: "핵심 거래 처리"

  # 코어 → DB
  - from_id: core_server
    to_id: oracle_primary
    protocol: JDBC
    label: "계좌/거래 데이터"

  # DB 이중화
  - from_id: oracle_primary
    to_id: oracle_dr
    protocol: Oracle Data Guard
    bidirectional: false

  # 코어 → MQ
  - from_id: core_server
    to_id: ibm_mq
    protocol: IBM MQ
    label: "전문 메시지"

  # 배치 → DB
  - from_id: batch_server
    to_id: oracle_primary
    protocol: JDBC

  # 배치 → FTP
  - from_id: batch_server
    to_id: ftp_server
    protocol: FTP
    label: "배치 파일 전송"

  # 코어 → HSM
  - from_id: core_server
    to_id: hsm
    protocol: PKCS#11
    label: "암호화/복호화"
```

---

## 10. 완전한 예제: 하이브리드 클라우드 시스템

온프레미스 + 클라우드 혼합 구조입니다. `examples/hybrid_cloud_manufacturing.yaml` 참조.

```yaml
name: "Hybrid Cloud Manufacturing MES"
description: "2018년 구축된 제조 실행 시스템 (MES).
              공장 내 온프레미스 OT망과 Azure 클라우드를 VPN으로 연결한 하이브리드.
              ERP·SCM은 클라우드, 생산 제어·SCADA는 내부망에 격리."

components:
  # ── OT망 (on-premise) ──────────────────────────────────────────
  - id: scada
    type: server
    label: "SCADA 서버"
    tech: ["Wonderware InTouch", "OPC-UA", "Windows Server 2016"]
    host: on-premise
    criticality: high              # 공장 생산 직접 제어
    metadata:
      zone: OT

  - id: plc_line1
    type: server
    label: "PLC 제어기 (라인 1)"
    tech: ["Siemens S7-1500", "PROFINET"]
    host: on-premise
    criticality: high
    lifecycle_status: active
    metadata:
      zone: OT

  # ── DMZ (on-premise) ───────────────────────────────────────────
  - id: dmz_gateway
    type: gateway
    label: "DMZ 게이트웨이 (OT↔IT 경계)"
    tech: ["Palo Alto Firewall", "Fortinet"]
    host: on-premise
    metadata:
      zone: DMZ

  - id: vpn_gw
    type: gateway
    label: "Site-to-Site VPN 게이트웨이"
    tech: ["Cisco ASA", "IPSec IKEv2"]
    host: on-premise

  # ── Azure 클라우드 ─────────────────────────────────────────────
  - id: az_vpn
    type: gateway
    label: "Azure VPN Gateway"
    tech: ["Azure VPN Gateway", "BGP"]
    host: azure

  - id: az_apim
    type: gateway
    label: "Azure API Management"
    tech: ["Azure APIM", "OAuth 2.0"]
    host: azure

  - id: erp_sap
    type: server
    label: "SAP S/4HANA (ERP)"
    tech: ["SAP S/4HANA 2021", "ABAP", "HANA DB"]
    host: azure
    criticality: high

  - id: az_event_hub
    type: queue
    label: "Azure Event Hubs (IoT 스트림)"
    tech: ["Azure Event Hubs", "Apache Kafka 2.6"]
    host: azure

connections:
  # OT 내부
  - from_id: plc_line1
    to_id: scada
    protocol: OPC-UA

  # OT → IT (DMZ 경유)
  - from_id: scada
    to_id: dmz_gateway
    protocol: HTTPS/REST

  - from_id: dmz_gateway
    to_id: az_event_hub
    protocol: HTTPS/AMQP

  # VPN 터널
  - from_id: vpn_gw
    to_id: az_vpn
    protocol: IPSec/BGP

  # Azure 내부
  - from_id: az_vpn
    to_id: az_apim
    protocol: HTTPS

  - from_id: az_apim
    to_id: erp_sap
    protocol: HTTPS/OData
```

---

## 11. 자주 하는 실수

### ❌ 실수 1: 엔터프라이즈 필드를 metadata 안에 기록

```yaml
# ❌ 잘못됨
- id: main_db
  metadata:
    criticality: high          # ← metadata 안에 넣으면 분석에 반영 안 됨
    lifecycle_status: eol

# ✅ 올바름
- id: main_db
  criticality: high            # ← 최상위 필드로
  lifecycle_status: eol
```

### ❌ 실수 2: mainframe을 server로 분류

```yaml
# ❌ 잘못됨 — AI가 메인프레임 특성(COBOL 마이그레이션 복잡도 등)을 인식 못함
- id: mainframe
  type: server
  tech: ["IBM z/OS", "COBOL"]

# ✅ 올바름
- id: mainframe
  type: mainframe
  tech: ["IBM z/OS", "COBOL", "CICS"]
```

### ❌ 실수 3: connection id가 component id와 불일치

```yaml
# ❌ 오류 — 'web_server'라는 id가 없으면 connection이 무시됨
components:
  - id: web           # ← id는 'web'
connections:
  - from_id: web_server  # ← 없는 id 참조 → 무시됨

# ✅ 올바름
connections:
  - from_id: web         # ← 정확히 일치
```

### ❌ 실수 4: 기술 버전 누락

```yaml
# ❌ 버전 없음 — EOL 계산, CVE 식별 불가
tech: ["Java", "MySQL"]

# ✅ 버전 포함 — 정확한 분석 가능
tech: ["Java 8", "MySQL 5.7"]
```

### ❌ 실수 5: 하이브리드 시스템에서 모든 컴포넌트를 hybrid로

```yaml
# ❌ 정보 손실 — AI가 실제 위치를 모름
- id: scada
  host: hybrid

# ✅ 실제 위치 명시
- id: scada
  host: on-premise    # OT망에 있음
  metadata:
    zone: OT
```

---

## 12. 검증 규칙

ArchPilot은 ingest 시 Pydantic 유효성 검사를 실행합니다:

| 규칙 | 결과 |
|------|------|
| `components.id` 중복 | 오류, 즉시 종료 |
| `connection.from_id` 미존재 | 경고 출력 후 해당 connection 무시 |
| `connection.to_id` 미존재 | 경고 출력 후 해당 connection 무시 |
| `type` 미지원 값 | 오류, `unknown` 제안 |
| `host` 미지원 값 | 오류 |
| `lifecycle_status` 미지원 값 | 오류 |
| `criticality` 미지원 값 | 오류 |

**유효성 검사 우회 없이 파싱 성공하는 것이 최선**이지만, 특정 connection이 무시되더라도 전체 파이프라인은 계속 동작합니다.

---

## 참고

- 실제 예제 파일: `examples/` 디렉토리
- ComponentType 자동 추론 상세: `src/archpilot/core/tech_ontology.py`
- LLM 그라운딩 활용: [`GROUNDING.md`](./4_GROUNDING.md)
- draw.io에서 직접 작성: [`DRAWIO.md`](./5_DRAWIO.md)
