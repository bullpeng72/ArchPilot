"""DT/AI 전환 패턴 라이브러리 — ArchPilot 온톨로지 기반 지식 그라운딩.

패턴은 두 카테고리로 구성된다:
- DT_PATTERNS: 디지털 트랜스포메이션 16개 핵심 패턴
- AI_PATTERNS: AI 트랜스포메이션 11개 핵심 패턴

각 패턴은 ComponentType·기술 키워드 기반으로 시스템에 자동 매칭된다.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TransformationPattern:
    """단일 DT/AI 전환 패턴."""

    id: str
    category: str          # "DT" | "AI"
    name: str
    summary: str           # 한 줄 요약
    problem: str           # 해결하는 문제
    solution: str          # 핵심 해법
    components_needed: list[str] = field(default_factory=list)   # ComponentType 키워드
    tech_triggers: list[str] = field(default_factory=list)       # 기술 키워드 (소문자)
    benefits: list[str] = field(default_factory=list)
    tradeoffs: list[str] = field(default_factory=list)
    when_to_apply: str = ""


# ── 디지털 트랜스포메이션 패턴 (12) ───────────────────────────────────────────

DT_PATTERNS: list[TransformationPattern] = [
    TransformationPattern(
        id="strangler_fig",
        category="DT",
        name="Strangler Fig",
        summary="레거시를 점진적으로 교체 — 새 서비스가 구 시스템을 감싸며 대체",
        problem="모놀리식 레거시를 빅뱅 방식으로 교체하면 위험이 너무 크다",
        solution=(
            "API Gateway/Facade로 레거시 앞에 라우팅 레이어를 두고,"
            " 기능별로 신규 마이크로서비스로 점진적 이관. 레거시는 기능이 모두 이관되면 퇴역."
        ),
        components_needed=["server", "gateway", "service", "mainframe", "esb"],
        tech_triggers=["monolith", "cobol", "mainframe", "esb", "oracle forms", "websphere"],
        benefits=["무중단 전환", "리스크 분산", "롤백 용이"],
        tradeoffs=["병행 운영 비용 증가", "데이터 동기화 복잡도", "전환 기간 장기화 가능"],
        when_to_apply="레거시 비즈니스 로직이 복잡하고 빅뱅 교체가 불가능한 경우",
    ),
    TransformationPattern(
        id="microservices_decomposition",
        category="DT",
        name="마이크로서비스 분해 (Microservices Decomposition)",
        summary="모놀리스를 도메인 경계(DDD Bounded Context)로 분해해 독립 배포·확장",
        problem="단일 코드베이스의 결합도·배포 리스크·팀 병목",
        solution=(
            "DDD Bounded Context 기반으로 서비스를 분리."
            " 각 서비스는 독립 DB, 독립 배포 파이프라인."
            " API Gateway가 진입점 통일."
        ),
        components_needed=["server", "service", "gateway", "queue", "database"],
        tech_triggers=["monolith", "spring", "django", "rails", "laravel", "tomcat", "j2ee"],
        benefits=["독립 확장", "팀 자율성", "장애 격리"],
        tradeoffs=["분산 시스템 복잡도", "네트워크 지연", "분산 트랜잭션 관리"],
        when_to_apply="팀 규모 확대, 기능별 독립 스케일링 필요, 배포 빈도 증가 요구 시",
    ),
    TransformationPattern(
        id="event_driven_architecture",
        category="DT",
        name="이벤트 기반 아키텍처 (EDA)",
        summary="서비스 간 동기 호출을 이벤트 스트림으로 전환해 결합도 제거",
        problem="동기 REST 호출의 강한 결합, 연쇄 장애, 확장 한계",
        solution=(
            "이벤트 브로커(Kafka/Kinesis/Pub/Sub)를 허브로."
            " 서비스는 이벤트를 발행만 하고 소비자는 독립적으로 처리."
            " Outbox Pattern으로 트랜잭션 원자성 보장."
        ),
        components_needed=["queue", "service", "server"],
        tech_triggers=["http", "rest", "soap", "mq", "tibco", "activemq", "corba", "rpc", "jms"],
        benefits=["느슨한 결합", "비동기 확장성", "이벤트 재처리·감사"],
        tradeoffs=["최종 일관성", "디버깅 복잡도", "이벤트 스키마 관리"],
        when_to_apply="높은 처리량, 여러 소비자가 동일 이벤트에 반응, 피크 부하 완충 필요 시",
    ),
    TransformationPattern(
        id="cqrs_event_sourcing",
        category="DT",
        name="CQRS + 이벤트 소싱",
        summary="쓰기/읽기 모델 분리 + 상태 변경을 이벤트로 영속화",
        problem="복잡한 도메인에서 읽기·쓰기 요구사항의 충돌, 감사 추적 부재",
        solution=(
            "Command 사이드는 이벤트를 이벤트 스토어에 저장."
            " Query 사이드는 읽기 최적화된 프로젝션(읽기 DB) 유지."
            " 이벤트 리플레이로 상태 재구성 가능."
        ),
        components_needed=["service", "database", "queue", "cache"],
        tech_triggers=["audit", "compliance", "banking", "finance", "accounting", "trading"],
        benefits=["완전한 감사 추적", "읽기/쓰기 독립 최적화", "시간 여행 디버깅"],
        tradeoffs=["최종 일관성", "구현 복잡도 높음", "이벤트 스키마 진화 어려움"],
        when_to_apply="강력한 감사 요구(금융·규제), 복잡한 비즈니스 규칙, 읽기 부하가 훨씬 높은 경우",
    ),
    TransformationPattern(
        id="api_gateway_bff",
        category="DT",
        name="API Gateway / BFF (Backend for Frontend)",
        summary="클라이언트 유형별 최적화 API 레이어로 백엔드 복잡도 은닉",
        problem="다양한 클라이언트(모바일·웹·파트너)가 각각 다른 API 형태를 요구",
        solution=(
            "API Gateway로 인증·라우팅·속도 제한 통일."
            " 클라이언트 유형별 BFF 서비스로 응답 집계·변환."
            " GraphQL Federation 또는 REST 집계 활용 가능."
        ),
        components_needed=["gateway", "service", "client", "loadbalancer"],
        tech_triggers=["mobile", "web", "partner api", "public api", "multiple clients"],
        benefits=["클라이언트 분리", "중앙화된 보안·정책", "백엔드 API 단순화"],
        tradeoffs=["단일 장애점 가능성", "BFF 증식", "캐싱 레이어 관리"],
        when_to_apply="다양한 클라이언트 채널, 파트너 API 공개, 마이크로서비스 진입점 통일 필요 시",
    ),
    TransformationPattern(
        id="service_mesh",
        category="DT",
        name="서비스 메시 (Service Mesh)",
        summary="사이드카 프록시로 서비스 간 통신 제어·관찰·보안을 인프라 레벨로 분리",
        problem="마이크로서비스가 많아질수록 서비스 간 mTLS·재시도·서킷브레이커·추적을 각 서비스가 구현해야 함",
        solution=(
            "Istio/Linkerd/Envoy 등 서비스 메시 도입."
            " 사이드카 프록시가 트래픽 관리·mTLS·분산 추적을 투명하게 처리."
            " 중앙 컨트롤 플레인으로 정책 통일."
        ),
        components_needed=["service", "monitoring", "security"],
        tech_triggers=["kubernetes", "k8s", "microservices", "docker", "container"],
        benefits=["Zero-Trust 트래픽 보안", "관찰 가능성 자동화", "트래픽 제어"],
        tradeoffs=["운영 복잡도", "사이드카 오버헤드", "러닝 커브"],
        when_to_apply="20개 이상 마이크로서비스, Kubernetes 환경, Zero-Trust 보안 요구 시",
    ),
    TransformationPattern(
        id="data_lakehouse",
        category="DT",
        name="데이터 레이크하우스 (Data Lakehouse)",
        summary="Data Lake의 유연성 + Data Warehouse의 ACID 트랜잭션·쿼리 성능 결합",
        problem="레거시 DW는 비정형 데이터 처리 불가, Data Lake는 ACID·BI 분석 어려움",
        solution=(
            "Delta Lake/Iceberg/Hudi로 오브젝트 스토리지에 ACID 트랜잭션 레이어."
            " Bronze(원시)→Silver(정제)→Gold(집계) 레이어 구조."
            " Spark/Trino로 통합 쿼리 엔진."
        ),
        components_needed=["storage", "database", "service", "queue"],
        tech_triggers=["data warehouse", "hadoop", "hive", "teradata", "netezza", "oracle dw", "etl"],
        benefits=["단일 데이터 플랫폼", "실시간·배치 통합", "비용 효율적 스토리지"],
        tradeoffs=["운영 복잡도", "메타데이터 관리", "초기 설계 중요"],
        when_to_apply="데이터 사일로 통합, ML 데이터 준비, 실시간+배치 분석 통합 필요 시",
    ),
    TransformationPattern(
        id="data_mesh",
        category="DT",
        name="데이터 메시 (Data Mesh)",
        summary="중앙 집중식 데이터 팀 대신 도메인 팀이 데이터 제품을 소유·제공",
        problem="중앙 데이터 팀이 병목, 데이터 품질 책임 불명확, 도메인 컨텍스트 손실",
        solution=(
            "도메인별 데이터 제품 팀."
            " 셀프서비스 데이터 플랫폼(인프라 추상화)."
            " 연합 거버넌스(공통 표준 + 도메인 자율성)."
        ),
        components_needed=["service", "storage", "database"],
        tech_triggers=["data warehouse", "data lake", "analytics", "reporting", "bi"],
        benefits=["도메인 자율성", "데이터 품질 책임 명확화", "조직 확장성"],
        tradeoffs=["거버넌스 복잡도", "표준화 어려움", "조직 변화 관리 필요"],
        when_to_apply="대규모 조직, 중앙 데이터 팀 병목, 도메인별 데이터 요구사항 다양 시",
    ),
    TransformationPattern(
        id="zero_trust_security",
        category="DT",
        name="제로 트러스트 보안 (Zero Trust)",
        summary="'신뢰하지 말고 항상 검증' — 네트워크 위치와 무관하게 모든 접근을 인증·인가",
        problem="내부망 신뢰 가정으로 인한 내부자 위협·측면 이동 공격 취약",
        solution=(
            "Identity-centric 접근 제어."
            " 마이크로 세그멘테이션으로 폭발 반경 제한."
            " 최소 권한 원칙(JIT, PAM)."
            " 지속적 검증(ZTNA, mTLS, 디바이스 상태 점검)."
        ),
        components_needed=["security", "gateway", "service", "monitoring"],
        tech_triggers=["firewall", "vpn", "iam", "ldap", "active directory", "compliance", "pci", "hipaa"],
        benefits=["내부자 위협 방어", "규제 컴플라이언스", "침해 시 폭발 반경 최소화"],
        tradeoffs=["사용자 경험 마찰", "구현 비용", "레거시 통합 어려움"],
        when_to_apply="금융·의료·공공 등 높은 규제 환경, 원격근무 확대, 내부망 신뢰 모델 한계 시",
    ),
    TransformationPattern(
        id="observability_otel",
        category="DT",
        name="관찰 가능성 (Observability / OpenTelemetry)",
        summary="Metrics·Traces·Logs 3기둥으로 분산 시스템의 '내부 상태'를 외부에서 추론",
        problem="레거시 로그만으로는 분산 마이크로서비스 장애 원인 파악 불가",
        solution=(
            "OpenTelemetry SDK로 계측 표준화."
            " Distributed Tracing(Jaeger/Zipkin)으로 요청 흐름 추적."
            " Prometheus+Grafana로 메트릭 시각화."
            " 중앙 로그 집계(ELK/Loki)."
        ),
        components_needed=["monitoring", "service", "server"],
        tech_triggers=["log", "logging", "monitor", "apm", "alert", "sentry", "nagios", "zabbix"],
        benefits=["MTTR 단축", "프로액티브 이상 탐지", "SLO/SLA 측정 기반"],
        tradeoffs=["스토리지 비용", "계측 코드 추가", "데이터 보존 정책 필요"],
        when_to_apply="마이크로서비스 전환 후, 분산 시스템 장애 대응 개선, SRE 조직 도입 시",
    ),
    TransformationPattern(
        id="database_per_service",
        category="DT",
        name="서비스별 독립 데이터베이스 (Database-per-Service)",
        summary="각 마이크로서비스가 독립 DB를 소유 — 다른 서비스 DB에 직접 접근 금지",
        problem="공유 DB로 인한 스키마 결합, 독립 배포·확장 불가, 데이터 소유권 불명확",
        solution=(
            "서비스별 DB 선택 자유도(Polyglot Persistence)."
            " 서비스 간 데이터 필요 시 API 또는 이벤트로만 공유."
            " Saga Pattern으로 분산 트랜잭션 관리."
        ),
        components_needed=["database", "service", "queue"],
        tech_triggers=["shared database", "oracle", "sql server", "mysql", "monolith db"],
        benefits=["서비스 독립성", "Polyglot Persistence", "장애 격리"],
        tradeoffs=["조인 불가(API/이벤트로 보완)", "Saga 복잡도", "DB 운영 비용 증가"],
        when_to_apply="마이크로서비스 분해 시, 서비스별 다른 데이터 특성(그래프·시계열·문서) 필요 시",
    ),
    TransformationPattern(
        id="feature_flag",
        category="DT",
        name="피처 플래그 / 점진적 롤아웃 (Feature Flag)",
        summary="코드 배포와 기능 출시를 분리 — 런타임에 기능 켜기/끄기",
        problem="새 기능 배포가 곧 전체 사용자 노출 → 장애 발생 시 빠른 롤백 불가",
        solution=(
            "LaunchDarkly/OpenFeature 등 피처 플래그 시스템 도입."
            " Canary/Blue-Green/A-B 배포와 연동."
            " 킬 스위치로 즉각 롤백."
        ),
        components_needed=["service", "gateway", "server"],
        tech_triggers=["jenkins", "gitlab", "bamboo", "teamcity", "argo", "spinnaker", "canary", "blue-green"],
        benefits=["무위험 배포", "사용자 세그먼트 실험", "즉시 롤백"],
        tradeoffs=["플래그 부채 관리", "테스트 복잡도", "코드 분기 증가"],
        when_to_apply="배포 빈도 높음, 대규모 사용자 기반, A/B 실험 필요, 규제 환경 점진적 검증 시",
    ),
    TransformationPattern(
        id="saga_pattern",
        category="DT",
        name="사가 패턴 (Saga Pattern)",
        summary="분산 서비스 간 트랜잭션을 로컬 트랜잭션 시퀀스로 분해 — 실패 시 보상 트랜잭션으로 롤백",
        problem=(
            "마이크로서비스별 독립 DB 환경에서 여러 서비스를 아우르는 원자적 트랜잭션 보장 불가."
            " 2PC/XA 프로토콜은 분산 데드락·성능 저하·가용성 문제를 유발."
        ),
        solution=(
            "Choreography Saga: 각 서비스가 이벤트를 발행해 다음 단계를 트리거."
            " 실패 시 보상 이벤트를 발행해 이전 서비스가 상태를 롤백."
            " Orchestration Saga: 중앙 사가 오케스트레이터가 각 서비스에 순서대로 명령을 전달·조율."
            " 각 단계는 보상 트랜잭션(Compensating Transaction)을 쌍으로 설계."
        ),
        components_needed=["queue", "database", "service"],
        tech_triggers=["kafka", "rabbitmq", "2pc", "xa", "mq", "activemq", "jms", "distributed"],
        benefits=["데이터 최종 일관성 보장", "각 서비스 독립성 유지", "2PC 없이 분산 트랜잭션 처리"],
        tradeoffs=["보상 트랜잭션 설계 복잡도", "최종 일관성(즉시 일관성 불가)", "장애 추적·디버깅 어려움"],
        when_to_apply=(
            "마이크로서비스 분해 후 주문·결제·재고 등 다단계 비즈니스 트랜잭션이 존재하거나,"
            " 공유 DB 제거 후 서비스 간 트랜잭션 일관성이 필요할 때"
        ),
    ),
    TransformationPattern(
        id="cicd_devops",
        category="DT",
        name="CI/CD 파이프라인 / DevOps 자동화",
        summary="코드 커밋부터 프로덕션 배포까지 자동화 — 수동 빌드·배포·테스트 프로세스 제거",
        problem=(
            "수동 빌드·배포로 인한 인적 오류, 긴 릴리스 사이클(주·월 단위),"
            " 환경 불일치(개발-스테이징-운영), 배포 공포(Deploy Fear)."
        ),
        solution=(
            "소스 제어(Git Flow/Trunk) → 자동 빌드(Gradle/Maven) → 자동 테스트(단위·통합·E2E) →"
            " 컨테이너 이미지 빌드 → 아티팩트 저장소 → GitOps(Argo CD/Flux) 기반 자동 배포."
            " 환경별 파이프라인(dev→staging→prod) + 품질 게이트 + 승인 워크플로우."
        ),
        components_needed=["server", "service", "storage", "monitoring"],
        tech_triggers=["jenkins", "gitlab", "bamboo", "teamcity", "svn", "cvs", "ant", "maven", "ftp", "manual"],
        benefits=["배포 빈도 향상 (일 수회)", "인적 오류 제거", "환경 일관성", "빠른 피드백 루프"],
        tradeoffs=["파이프라인 구축 초기 비용", "테스트 커버리지 투자 필요", "복잡한 파이프라인 유지보수"],
        when_to_apply="수동 배포 프로세스, 긴 릴리스 주기(월·분기), 환경 간 불일치, 배포 공포가 있는 조직",
    ),
    TransformationPattern(
        id="infrastructure_as_code",
        category="DT",
        name="코드형 인프라 (Infrastructure as Code)",
        summary="인프라 프로비저닝을 선언형 코드로 정의 — 수동 서버 구성·클릭 운영에서 코드 기반 자동화로 전환",
        problem=(
            "수동 서버 구성으로 인한 환경 불일치(Snowflake Server),"
            " 재현 불가능한 인프라, 감사 추적 부재, 클라우드 전환 시 수작업 병목."
        ),
        solution=(
            "Terraform/Pulumi/CloudFormation으로 인프라를 선언형 코드(HCL/YAML)로 정의."
            " Git 버전 관리 + CI/CD 파이프라인으로 인프라 변경을 코드 리뷰 후 자동 적용."
            " Ansible/Chef/Puppet으로 서버 구성 관리(Configuration Management)."
            " 불변 인프라(Immutable Infrastructure) 원칙으로 Snowflake Server 제거."
        ),
        components_needed=["server", "storage", "security", "monitoring"],
        tech_triggers=["vmware", "vsphere", "datacenter", "ansible", "puppet", "chef", "aws", "azure", "gcp", "terraform"],
        benefits=["환경 완전 재현성", "인프라 변경 감사 추적", "클라우드 전환 가속", "프로비저닝 시간 단축"],
        tradeoffs=["IaC 코드 학습 비용", "Terraform 상태 파일 관리", "기존 레거시 인프라 임포트 복잡도"],
        when_to_apply="클라우드 전환 프로젝트, 멀티 환경(dev·staging·prod) 일관성 요구, 수동 서버 구성이 운영 병목인 조직",
    ),
    TransformationPattern(
        id="cache_aside",
        category="DT",
        name="캐시 계층 도입 (Cache-Aside / Read-Through)",
        summary="읽기 집약적 레거시 시스템 앞에 분산 캐시를 추가해 DB 부하 절감·응답속도 향상",
        problem=(
            "레거시 RDBMS가 읽기 부하를 감당 못해 응답 지연·DB 과부하 발생."
            " 세션 관리가 애플리케이션 서버에 묶여 수평 확장 불가."
        ),
        solution=(
            "Cache-Aside: 애플리케이션이 캐시를 우선 조회 → 미스 시 DB 조회 후 캐시 저장."
            " Read-Through: 캐시가 DB 조회를 위임 처리."
            " Redis/Memcached를 세션 캐시·쿼리 결과 캐시·정적 데이터 캐시로 도입."
            " TTL 기반 만료와 명시적 캐시 무효화 전략 설계."
        ),
        components_needed=["database", "server", "service", "cache"],
        tech_triggers=["oracle", "sql", "mysql", "postgresql", "session", "performance", "bottleneck", "slow"],
        benefits=["응답 지연 대폭 감소", "DB 부하 절감(읽기 요청의 70~90%)", "애플리케이션 수평 확장 용이"],
        tradeoffs=["캐시 스탈리니스(데이터 정합성)", "TTL 튜닝 필요", "캐시 무효화 복잡도(분산 환경)"],
        when_to_apply="읽기/쓰기 비율 > 3:1, DB 과부하, 세션 상태 외부화 필요, 정적 데이터 반복 조회 패턴",
    ),
]


# ── AI 트랜스포메이션 패턴 (11) ────────────────────────────────────────────────

AI_PATTERNS: list[TransformationPattern] = [
    TransformationPattern(
        id="rag",
        category="AI",
        name="RAG (Retrieval-Augmented Generation)",
        summary="LLM에 실시간 외부 지식을 검색·주입해 환각을 억제하고 도메인 특화 응답 생성",
        problem="범용 LLM은 기업 내부 지식 부재, 최신 정보 미반영, 환각(Hallucination) 위험",
        solution=(
            "Vector DB(Pinecone/Weaviate/pgvector)에 기업 문서 임베딩 인덱싱."
            " 질의 시 관련 청크를 검색해 LLM 컨텍스트에 주입."
            " Reranker로 검색 품질 향상."
        ),
        components_needed=["service", "database", "storage", "cache"],
        tech_triggers=["document", "knowledge base", "search", "faq", "chatbot", "content"],
        benefits=["환각 감소", "도메인 특화 정확도", "지식 최신성"],
        tradeoffs=["검색 지연", "임베딩 비용", "청크 전략 튜닝 필요"],
        when_to_apply="대규모 내부 문서, 고객 지원 자동화, 규제 컴플라이언스 QA 시스템 구축 시",
    ),
    TransformationPattern(
        id="mlops_pipeline",
        category="AI",
        name="MLOps 파이프라인",
        summary="ML 모델 개발-학습-배포-모니터링 사이클을 CI/CD처럼 자동화",
        problem="모델 실험·학습·배포가 수동, 재현 불가, 데이터 드리프트 미탐지",
        solution=(
            "Feature Store → 학습 파이프라인(Kubeflow/SageMaker Pipelines) → "
            "모델 레지스트리(MLflow) → 서빙(Triton/TorchServe) → "
            "모니터링(데이터·모델 드리프트 탐지)."
        ),
        components_needed=["service", "storage", "queue", "monitoring"],
        tech_triggers=["machine learning", "ml", "model", "training", "prediction", "analytics"],
        benefits=["실험 재현성", "자동 배포", "드리프트 조기 탐지"],
        tradeoffs=["인프라 복잡도", "초기 설정 비용", "플랫폼 학습 비용"],
        when_to_apply="다수의 ML 모델 운영, 모델 배포 주기 단축 필요, 데이터 과학팀과 엔지니어링팀 협업 시",
    ),
    TransformationPattern(
        id="feature_store",
        category="AI",
        name="피처 스토어 (Feature Store)",
        summary="ML 피처를 중앙에서 계산·저장·공유 — 학습/추론 피처 일관성 보장",
        problem="각 ML 팀이 동일 피처를 중복 계산, 학습·서빙 피처 불일치(Training-Serving Skew)",
        solution=(
            "온라인 스토어(Redis/DynamoDB)로 저지연 실시간 피처 제공."
            " 오프라인 스토어(S3/BigQuery)로 학습 데이터셋 생성."
            " 피처 버전 관리·계보 추적."
        ),
        components_needed=["service", "database", "cache", "storage"],
        tech_triggers=["machine learning", "ml", "feature engineering", "real-time prediction"],
        benefits=["Training-Serving Skew 제거", "피처 재사용", "실험 가속"],
        tradeoffs=["추가 인프라", "피처 거버넌스 필요", "초기 마이그레이션 비용"],
        when_to_apply="여러 ML 모델이 동일 피처 공유, 실시간 추론 < 100ms 요구, 피처 중복 계산 문제 시",
    ),
    TransformationPattern(
        id="ai_model_gateway",
        category="AI",
        name="AI 모델 게이트웨이 (AI Model Gateway)",
        summary="다양한 LLM/ML 모델 접근을 단일 게이트웨이로 통일 — 라우팅·보안·비용 제어",
        problem="각 서비스가 LLM API를 직접 호출 → 키 관리 분산, 비용 추적 불가, 모델 교체 어려움",
        solution=(
            "중앙 AI Gateway(LiteLLM/OpenRouter/자체 구축)."
            " 모델 라우팅(비용·지연·능력 기반)."
            " PII 마스킹·콘텐츠 필터링."
            " 사용량 추적·청구."
        ),
        components_needed=["gateway", "service", "monitoring", "security"],
        tech_triggers=["openai", "llm", "gpt", "claude", "gemini", "ai api", "language model"],
        benefits=["중앙화된 AI 거버넌스", "비용 최적화", "모델 교체 투명화"],
        tradeoffs=["단일 장애점", "추가 지연", "게이트웨이 유지보수"],
        when_to_apply="여러 서비스가 LLM 사용, AI 비용 통제 필요, 기업 보안·컴플라이언스 요구 시",
    ),
    TransformationPattern(
        id="semantic_cache",
        category="AI",
        name="시맨틱 캐시 (Semantic Cache)",
        summary="벡터 유사도 기반으로 의미적으로 유사한 LLM 질의를 캐싱해 비용·지연 절감",
        problem="동일 의미의 다른 표현 질의에도 매번 LLM API 호출 → 비용 낭비, 지연",
        solution=(
            "질의를 임베딩해 Vector DB에서 유사도 검색."
            " 임계값(예: cosine similarity > 0.95) 이상이면 캐시 응답 반환."
            " GPTCache/Redis Vector 등 활용."
        ),
        components_needed=["cache", "service", "database"],
        tech_triggers=["llm", "gpt", "openai", "chatbot", "claude", "gemini", "embedding", "vector"],
        benefits=["LLM 비용 40-80% 절감", "응답 지연 감소", "처리량 향상"],
        tradeoffs=["임계값 튜닝 필요", "캐시 무효화 전략", "임베딩 비용"],
        when_to_apply="반복적 질의 패턴이 많은 서비스(고객지원·검색), LLM 비용이 주요 부담인 경우",
    ),
    TransformationPattern(
        id="agentic_ai",
        category="AI",
        name="에이전틱 AI 플랫폼 (Agentic AI Platform)",
        summary="LLM이 도구를 자율 선택·실행하며 복잡한 다단계 작업을 자동화",
        problem="단순 챗봇으로는 다단계 업무(검색→분석→보고서 작성→이메일 발송) 처리 불가",
        solution=(
            "ReAct/Plan-and-Execute 패턴으로 LLM이 도구를 선택·실행."
            " 도구: 검색·코드 실행·DB 쿼리·외부 API."
            " 멀티 에이전트 오케스트레이션(LangGraph/CrewAI)."
            " 인간 승인 게이트 통합."
        ),
        components_needed=["service", "queue", "storage", "monitoring"],
        tech_triggers=["automation", "workflow", "rpa", "process", "bpm", "orchestration"],
        benefits=["복잡 업무 자동화", "24/7 운영", "인간 오류 감소"],
        tradeoffs=["비결정론적 동작", "비용 예측 어려움", "안전 장치 설계 필요"],
        when_to_apply="반복적 복잡 업무 자동화, RPA 한계 돌파, 지식 집약적 프로세스 자동화 시",
    ),
    TransformationPattern(
        id="human_in_the_loop",
        category="AI",
        name="Human-in-the-Loop (HITL)",
        summary="AI 결정의 불확실성·고위험 구간에 인간 검토·승인 게이트 삽입",
        problem="AI 오류가 비즈니스·규제·윤리적 위험을 초래할 수 있는 고위험 도메인",
        solution=(
            "신뢰도 임계값 기반 자동/수동 분기."
            " 검토 큐(대시보드)로 분류가 어려운 케이스를 인간에게 라우팅."
            " 인간 피드백을 Active Learning으로 모델 개선에 활용."
        ),
        components_needed=["service", "queue", "client", "monitoring"],
        tech_triggers=["compliance", "audit", "medical", "financial", "legal", "fraud", "kyc", "aml"],
        benefits=["AI 오류 안전망", "규제 컴플라이언스", "모델 지속 개선"],
        tradeoffs=["처리 지연", "인간 리뷰 비용", "큐 적체 관리"],
        when_to_apply="금융·의료·법무 등 고위험 의사결정, 규제 감사 요구, AI 신뢰도 구축 초기 단계",
    ),
    TransformationPattern(
        id="ai_augmented_legacy",
        category="AI",
        name="AI 증강 레거시 서비스 (AI-Augmented Legacy Service)",
        summary="레거시 시스템을 교체하지 않고 AI 레이어를 추가해 지능화",
        problem="레거시 교체는 수년·수백억 소요, 하지만 AI 능력은 즉시 필요",
        solution=(
            "레거시 API 앞에 AI 레이어 삽입(Facade)."
            " 자연어→레거시 명령 변환."
            " 레거시 출력에 AI 분석·요약 추가."
            " 이상 탐지·예측 분석을 별도 서비스로 추가."
        ),
        components_needed=["service", "mainframe", "esb", "gateway"],
        tech_triggers=["mainframe", "cobol", "legacy", "esb", "soap", "as400", "rpg"],
        benefits=["레거시 투자 보호", "빠른 AI 가치 실현", "단계적 현대화"],
        tradeoffs=["두 레이어 유지보수", "레거시 결합 유지", "성능 오버헤드"],
        when_to_apply="레거시 교체 불가(규제·비용·위험), 빠른 AI 도입 요구, 단계적 현대화 전략 채택 시",
    ),
    TransformationPattern(
        id="llm_guardrails",
        category="AI",
        name="LLM 가드레일 / AI 안전 레이어 (LLM Guardrails)",
        summary="AI 서비스 입출력을 검증·필터링하는 보안 레이어 — 프롬프트 인젝션·PII 유출·유해 콘텐츠 방어",
        problem=(
            "LLM은 프롬프트 인젝션, 탈옥(Jailbreak), PII 유출, 유해 출력에 취약."
            " 금융·의료·공공 등 규제 산업에서 무방비 LLM 배포는 법적·브랜드 위험."
        ),
        solution=(
            "입력 가드레일: 프롬프트 인젝션 탐지, PII 마스킹(이름·카드번호·주민번호), 입력 길이·토큰 제한."
            " 출력 가드레일: 유해 콘텐츠 필터(NeMo Guardrails/Guardrails.AI), 구조 검증, 사실 기반 점수."
            " AI Gateway 레이어에 통합해 모든 LLM 호출의 단일 진입점으로 적용."
            " 모든 입출력 감사 로그 보존(PII 처리 후)."
        ),
        components_needed=["service", "gateway", "security", "monitoring"],
        tech_triggers=["llm", "gpt", "openai", "claude", "gemini", "chatbot", "pii", "gdpr", "hipaa", "injection"],
        benefits=["프롬프트 인젝션 방어", "PII 유출 방지", "규제 컴플라이언스", "브랜드 안전 보호"],
        tradeoffs=["추가 지연(10~50ms)", "과도 필터링으로 인한 오탐", "필터 규칙 유지보수 비용"],
        when_to_apply="고객 대면 AI 서비스, 금융·의료·공공 규제 산업, PII 처리 시스템, 다중 사용자 AI 플랫폼",
    ),
    TransformationPattern(
        id="llm_finetuning",
        category="AI",
        name="LLM 파인튜닝 / PEFT (도메인 특화 모델 적응)",
        summary="범용 LLM을 기업 도메인 데이터로 추가 학습 — RAG로 해결 안 되는 전문 태스크 성능 향상",
        problem=(
            "RAG는 지식 검색엔 유효하지만, 특정 형식 출력·도메인 분류·엔티티 추출 등 구조적 태스크엔 한계."
            " 범용 LLM은 금융 약관·법률 문서·의료 코딩의 도메인 미묘한 패턴을 놓침."
        ),
        solution=(
            "LoRA/QLoRA로 파라미터 효율적 파인튜닝(전체 학습의 0.1~1% 파라미터만 업데이트)."
            " 도메인 데이터셋 수집 → 지도 파인튜닝(SFT) → RLHF/DPO로 선호도 정렬."
            " Hugging Face PEFT 라이브러리 또는 클라우드 파인튜닝 서비스(OpenAI Fine-tuning, AWS Bedrock) 활용."
            " 평가셋으로 베이스 모델 대비 성능 개선 측정."
        ),
        components_needed=["service", "storage", "monitoring"],
        tech_triggers=["huggingface", "bert", "transformers", "nlp", "classification", "extraction", "sentiment", "llm", "embedding"],
        benefits=["도메인 특화 정확도 향상", "범용 모델 대비 응답 일관성", "더 작은 모델로 동등 이상 성능"],
        tradeoffs=["학습 데이터 수집·레이블링 비용", "재학습 주기 관리", "기반 모델 업그레이드 시 재파인튜닝 필요"],
        when_to_apply=(
            "특정 형식 출력·분류·추출 태스크, 도메인 전문 용어 정확도 요구,"
            " RAG로 해결 안 되는 패턴 인식 태스크, 소규모 컨텍스트에서 정확한 응답이 필요할 때"
        ),
    ),
    TransformationPattern(
        id="ai_observability",
        category="AI",
        name="AI 관찰 가능성 / LLMOps 모니터링",
        summary="LLM 서비스의 프롬프트·응답·비용·품질을 추적 — 환각 감지·드리프트 대응·비용 최적화",
        problem=(
            "일반 APM은 LLM 응답 품질(환각률·관련성·편향)을 측정 못함."
            " 프롬프트 변경의 품질 영향 추적 불가."
            " 토큰 비용이 예측 불가능하게 급증해도 원인 파악 어려움."
        ),
        solution=(
            "LLM 추적: 모든 프롬프트·응답·토큰 수·지연·모델 버전 로깅(LangFuse/Helicone/Arize)."
            " 품질 자동 평가: 응답 관련성·사실성·독성을 LLM-as-Judge 또는 임베딩 유사도로 측정."
            " 프롬프트 버전 관리: 프롬프트를 코드처럼 A/B 테스트·롤백 가능하게 관리."
            " 비용 대시보드: 모델별·기능별·사용자별 토큰 비용 분석."
        ),
        components_needed=["monitoring", "service", "storage"],
        tech_triggers=["llm", "gpt", "openai", "claude", "gemini", "langchain", "llamaindex", "chatbot", "embedding"],
        benefits=["환각 조기 감지", "프롬프트 최적화 근거 확보", "비용 이상 조기 경보", "규제 감사 로그"],
        tradeoffs=["추가 로깅 비용", "PII 포함 프롬프트 보존 규정 충돌 가능", "계측 코드 추가 필요"],
        when_to_apply="프로덕션 LLM 서비스 운영, AI 품질 SLA 보장 필요, 멀티 모델 비용 비교, 프롬프트 버전 관리 필요 시",
    ),
]

# ── 매칭 함수 ──────────────────────────────────────────────────────────────────

ALL_PATTERNS: list[TransformationPattern] = DT_PATTERNS + AI_PATTERNS


def match_patterns(
    component_types: list[str],
    tech_keywords: list[str],
    top_k: int = 8,
) -> list[TransformationPattern]:
    """시스템 컴포넌트·기술 스택에 기반해 관련 패턴을 점수순 반환.

    Args:
        component_types: 시스템 내 ComponentType 값 목록 (예: ["server", "database"])
        tech_keywords:   기술 스택 키워드 목록 (소문자, 예: ["oracle", "cobol"])
        top_k:           반환할 최대 패턴 수 (기본 8)

    Returns:
        점수 높은 순으로 정렬된 패턴 목록 (최대 top_k개)
    """
    type_set = {t.lower() for t in component_types}
    tech_set = {t.lower() for t in tech_keywords}

    scores: list[tuple[int, TransformationPattern]] = []
    for pattern in ALL_PATTERNS:
        score = 0
        # ComponentType 매칭: 겹치는 타입당 2점
        matched_types = type_set & set(pattern.components_needed)
        score += len(matched_types) * 2
        # 기술 키워드 매칭: 겹치는 키워드당 3점 (더 구체적)
        for trigger in pattern.tech_triggers:
            if any(trigger in tech for tech in tech_set):
                score += 3
        if score > 0:
            scores.append((score, pattern))

    scores.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scores[:top_k]]
