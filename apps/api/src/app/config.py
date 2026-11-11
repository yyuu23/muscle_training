"""
Configuration management using Pydantic Settings
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

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False

    # Security
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    session_expire_days: int = 7
    invite_code_expire_hours: int = 72

    # CORS
    cors_origins: list[str] = Field(default=["http://localhost:5173", "http://localhost:3000"])

    # Database
    database_url: PostgresDsn
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Alibaba Cloud DashScope (百炼)
    dashscope_api_key: str | None = None
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/api/v1"

    # Model Configuration
    default_chat_model: str = "qwen-plus-2025-12-01"
    default_embedding_model: str = "qwen3.7-text-embedding"
    default_asr_model: str = "paraformer-v2"
    embedding_dimension: int = 1024

    # Model Budget (RMB per month)
    model_budget_monthly: float = 100.0
    model_budget_warning_threshold: float = 0.8

    # Storage
    storage_backend: Literal["filesystem", "oss"] = "filesystem"
    storage_base_path: Path = Field(default=Path("./storage"))

    # Alibaba Cloud OSS
    oss_endpoint: str | None = None
    oss_access_key_id: str | None = None
    oss_access_key_secret: str | None = None
    oss_bucket_name: str | None = None
    oss_backup_bucket_name: str | None = None

    # Media Processing
    ffmpeg_path: str = "/usr/bin/ffmpeg"
    ffprobe_path: str = "/usr/bin/ffprobe"
    max_video_size_mb: int = 500
    max_audio_size_mb: int = 100
    max_document_size_mb: int = 10

    # Background Jobs
    worker_poll_interval_seconds: int = 5
    worker_lease_timeout_seconds: int = 300
    worker_max_attempts: int = 3

    # Backup
    backup_schedule: str = "0 3 * * *"  # Cron expression
    backup_retention_daily: int = 7
    backup_retention_weekly: int = 4
    backup_encryption_passphrase: str | None = None

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
    rate_limit_api_requests: int = 100
    rate_limit_api_window_minutes: int = 1

    # Timezone
    default_timezone: str = "Asia/Shanghai"

    # Development Tools
    enable_debug_toolbar: bool = False
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
            if self.secret_key == "changeme_random_secret_key_minimum_32_characters":
                errors.append("SECRET_KEY must be changed in production")

            if self.storage_backend == "oss":
                if not self.oss_endpoint:
                    errors.append("OSS_ENDPOINT required when STORAGE_BACKEND=oss")
                if not self.oss_access_key_id:
                    errors.append("OSS_ACCESS_KEY_ID required when STORAGE_BACKEND=oss")
                if not self.oss_access_key_secret:
                    errors.append("OSS_ACCESS_KEY_SECRET required when STORAGE_BACKEND=oss")
                if not self.oss_bucket_name:
                    errors.append("OSS_BUCKET_NAME required when STORAGE_BACKEND=oss")

            if self.enable_agent and not self.dashscope_api_key:
                errors.append("DASHSCOPE_API_KEY required when ENABLE_AGENT=true")

            if not self.backup_encryption_passphrase:
                errors.append("BACKUP_ENCRYPTION_PASSPHRASE required in production")

        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    settings = Settings()
    settings.validate_required_secrets()
    return settings
