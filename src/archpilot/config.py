"""전역 설정 관리 — .env 파일 기반."""

from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 전역 설정 디렉토리: ~/.archpilot/
GLOBAL_CONFIG_DIR = Path.home() / ".archpilot"
GLOBAL_ENV_FILE = GLOBAL_CONFIG_DIR / "config.env"


class ConfigError(Exception):
    """설정 오류 (API 키 미설정 등) — CLI/서버 양쪽에서 except Exception으로 처리 가능."""


class Settings(BaseSettings):
    # OpenAI
    # AliasChoices: OPENAI_API_KEY(접두어 없음) 또는 ARCHPILOT_OPENAI_API_KEY 모두 허용
    # pydantic-settings가 .env 파일을 직접 파싱해 두 이름 모두 검색하므로
    # os.environ 주입 없이도 동작한다.
    openai_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices("OPENAI_API_KEY", "ARCHPILOT_OPENAI_API_KEY"),
    )
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 4096

    # Output
    output_dir: Path = Path("./output")
    diagram_format: str = "png"

    # UI Server
    server_host: str = "127.0.0.1"
    server_port: int = 8080

    model_config = SettingsConfigDict(
        # 전역 설정 → 로컬 .env 순서로 로드 (로컬이 전역을 오버라이드)
        env_file=(GLOBAL_ENV_FILE, ".env"),
        env_prefix="ARCHPILOT_",
        extra="ignore",
        env_ignore_empty=True,
    )

    @field_validator("output_dir", mode="after")
    @classmethod
    def _resolve_output_dir(cls, v: Path) -> Path:
        """상대 경로를 절대 경로로 변환 — 실행 위치에 무관하게 동일한 경로 보장."""
        return v.expanduser().resolve()

    def require_api_key(self) -> None:
        """API 키 미설정 시 ConfigError를 raise한다.

        - CLI 명령: 각 명령의 except Exception 핸들러가 잡아 typer.Exit(1)로 처리
        - FastAPI SSE 제너레이터: except Exception이 잡아 SSE error 이벤트로 전송
        sys.exit()을 호출하면 uvicorn 프로세스 자체가 죽으므로 사용하지 않는다.
        """
        if not self.openai_api_key.get_secret_value():
            raise ConfigError(
                "OPENAI_API_KEY가 설정되지 않았습니다.\n"
                "  1. archpilot init 을 실행해 .env 파일을 생성하거나\n"
                "  2. .env 파일에 OPENAI_API_KEY=sk-... 를 직접 추가하세요."
            )


settings = Settings()
