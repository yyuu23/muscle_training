"""
Configuration management using Pydantic Settings (plan §11.1)

- Production refuses to start without required secrets.
- Missing model keys keep recording features working with an explicit
  "model not configured" capability state.
- MODEL_PROVIDER=fake and DEMO_MODE=true are forbidden in production.
"""

import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    python_env: Literal["development", "test", "production"] = "development"
    debug: bool = Field(default=False)
    app_base_url: str = "http://localhost:5173"
    app_timezone: str = "Asia/Shanghai"
    demo_mode: bool = False

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False

    # Security
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    session_expire_days: int = 7
    invite_code_expire_hours: int = 72

    # CORS
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
            "http://localhost:5176",
            "http://localhost:3000",
        ]
    )

    # Database (separate role DSNs per plan §11.1; fall back to DATABASE_URL).
    # Dev default keeps import-time settings usable (tests/CLI contract export);
    # production validation below rejects the default value.
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://muscle_training:dev_password@localhost:5432/muscle_training_dev"
    )
    migration_database_url: str | None = None
    job_database_url: str | None = None
    backup_database_url: str | None = None
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Model provider: "qwen" or "fake" (fake for dev/tests only)
    model_provider: Literal["qwen", "fake"] = "qwen"
    dashscope_api_key: str | None = None
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # Model Configuration
    default_chat_model: str = "qwen-plus-2025-12-01"
    default_embedding_model: str = "qwen3.7-text-embedding"
    default_asr_model: str = "paraformer-v2"
    embedding_dimension: int = 1024

    # Model Budget (RMB per month)
    monthly_ai_budget_cny: float = 100.0
    model_budget_warning_threshold: float = 0.8

    # Agent limits (plan §7.1)
    max_agent_model_calls: int = 3
    max_agent_tool_calls: int = 6
    interactive_timeout_seconds: int = 60
    plan_job_timeout_seconds: int = 180
    max_context_tokens: int = 12000

    # Storage
    storage_backend: Literal["filesystem", "oss"] = "filesystem"
    storage_base_path: Path = Field(default=Path("./storage"))

    # Alibaba Cloud OSS
    oss_region: str | None = None
    oss_endpoint: str | None = None
    oss_access_key_id: str | None = None
    oss_access_key_secret: str | None = None
    oss_bucket_name: str | None = None
    oss_backup_bucket_name: str | None = None

    # Media Processing
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    max_video_size_mb: int = 500
    max_video_duration_minutes: int = 60
    max_text_size_mb: int = 5
    temp_media_retention_days: int = 7
    chat_retention_days: int = 90

    # Background Jobs
    worker_poll_interval_seconds: int = 5
    worker_lease_timeout_seconds: int = 60
    worker_lease_renew_seconds: int = 20
    worker_max_attempts: int = 3
    worker_media_concurrency: int = 1
    worker_generation_concurrency: int = 2

    # Backup (age public-key encryption; private key stays on user machines)
    backup_schedule_hour: int = 3
    backup_retention_daily: int = 7
    backup_retention_weekly: int = 4
    backup_age_recipient: str | None = None
    backup_age_binary: str = "age"

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "text"] = "json"

    # Feature Flags
    enable_signup: bool = True
    enable_agent: bool = True
    enable_knowledge_import: bool = True
    enable_weekly_review: bool = True

    # Rate Limiting
    rate_limit_auth_attempts: int = 5
    rate_limit_auth_window_minutes: int = 15

    # Timezone
    default_timezone: str = "Asia/Shanghai"

    # Development Tools
    enable_query_logging: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from comma-separated string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("storage_base_path", mode="before")
    @classmethod
    def parse_storage_path(cls, v: str | Path) -> Path:
        """Convert string to Path and create directory if needed"""
        path = Path(v) if isinstance(v, str) else v
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        return path

    def validate_required_secrets(self) -> None:
        """Validate that required secrets are configured"""
        errors = []

        if self.python_env == "production":
            if self.demo_mode:
                errors.append("DEMO_MODE=true is forbidden in production")
            if self.model_provider == "fake":
                errors.append("MODEL_PROVIDER=fake is forbidden in production")

            if "dev_password" in str(self.database_url) or "muscle_training_dev" in str(self.database_url):
                errors.append("DATABASE_URL must be a real production DSN (dev default rejected)")

            if len(self.secret_key) < 32:
                errors.append("SECRET_KEY must be at least 32 characters in production")

            if self.storage_backend == "oss":
                if not self.oss_endpoint:
                    errors.append("OSS_ENDPOINT required when STORAGE_BACKEND=oss")
                if not self.oss_access_key_id:
                    errors.append("OSS_ACCESS_KEY_ID required when STORAGE_BACKEND=oss")
                if not self.oss_access_key_secret:
                    errors.append("OSS_ACCESS_KEY_SECRET required when STORAGE_BACKEND=oss")
                if not self.oss_bucket_name:
                    errors.append("OSS_BUCKET_NAME required when STORAGE_BACKEND=oss")

            if self.enable_agent and self.model_provider == "qwen" and not self.dashscope_api_key:
                errors.append("DASHSCOPE_API_KEY required when model provider is qwen")

            if not self.backup_age_recipient:
                errors.append("BACKUP_AGE_RECIPIENT required in production")

        if errors:
            raise ValueError(
                "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    settings = Settings()
    settings.validate_required_secrets()
    return settings
