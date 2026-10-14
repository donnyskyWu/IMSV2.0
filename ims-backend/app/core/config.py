# app/core/config.py - Application configuration (FP-A01-01)
"""
Configuration management with environment-based loading.

Config groups per FP-A01-01:
- db: IMS main database（连接串只从环境变量读取，仓库不写主机或库名）
- football_live: Read-only connection, schema definition file path
- redis: Cache and session storage
- jwt: Secret, access TTL (2h), refresh TTL (7d)
- file: storage_root
- dingtalk: IMS app credentials and mode
- dingtalk_attendance: Separate attendance app (FW-H07)
- train_ai: Training AI client config (FW-H08, managed by B10)
- integrations.<system>.mode: real/mock

Rules:
- Missing required fields -> startup failure with missing field names (not values)
- prod disables OpenAPI docs and debug
- Secrets never output in logs or /health
- dev allows Redis fallback to in-memory; test/e2e/prod require Redis
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """IMS main database configuration."""

    url: str = Field(default="", description="Database connection URL from env")
    pool_size: int = Field(default=10, ge=1, le=100)
    pool_recycle: int = Field(default=3600)
    echo: bool = Field(default=False)

    model_config = SettingsConfigDict(env_prefix="IMS_DB_")


class FootballLiveSettings(BaseSettings):
    """Football live_room read-only connection."""

    url: str = Field(default="", description="Read-only connection URL")
    schema_file: str = Field(
        default="docs/ims-v2-rewrite/modules/B0a-框架/live_room-真实DDL.sql",
        description="Schema definition file path"
    )
    tenant_map: dict[int, int] = Field(
        default={1: 1},
        description="Football tenant ID -> IMS tenant ID mapping"
    )
    enabled: bool = Field(default=True)

    model_config = SettingsConfigDict(env_prefix="IMS_FOOTBALL_LIVE_")


class RedisSettings(BaseSettings):
    """Redis configuration."""

    url: str = Field(default="redis://localhost:6379/0")
    password: Optional[str] = Field(default=None)
    max_connections: int = Field(default=10)

    model_config = SettingsConfigDict(env_prefix="IMS_REDIS_")


class JWTSettings(BaseSettings):
    """JWT token configuration."""

    secret: str = Field(default="", description="JWT signing secret (required)")
    algorithm: str = Field(default="HS256")
    access_token_ttl: int = Field(default=7200, description="Access token TTL in seconds (2h)")
    refresh_token_ttl: int = Field(default=604800, description="Refresh token TTL in seconds (7d)")

    model_config = SettingsConfigDict(env_prefix="IMS_JWT_")


class FileSettings(BaseSettings):
    """File storage configuration."""

    storage_root: str = Field(default="/tmp/ims-files")

    model_config = SettingsConfigDict(env_prefix="IMS_FILE_")


class DingTalkSettings(BaseSettings):
    """DingTalk IMS application configuration."""

    app_key: str = Field(default="")
    app_secret: str = Field(default="")
    agent_id: str = Field(default="")
    mode: str = Field(default="mock", description="real or mock")
    corp_id: str = Field(default="")
    base_url: str = Field(default="https://oapi.dingtalk.com", description="oapi endpoint")
    api_base_url: str = Field(default="https://api.dingtalk.com", description="api endpoint")
    callback_token: str = Field(default="", description="Callback signature token")
    callback_aes_key: str = Field(default="", description="Callback AES key (43 char Base64)")

    model_config = SettingsConfigDict(env_prefix="IMS_DINGTALK_")


class DingTalkAttendanceSettings(BaseSettings):
    """DingTalk Attendance application - separate from IMS app (FW-H07)."""

    enabled: bool = Field(default=False)
    mode: str = Field(default="mock")
    app_key: str = Field(default="")
    app_secret: str = Field(default="")  # Encrypted storage, masked display
    base_url: str = Field(default="https://oapi.dingtalk.com")
    timeout_ms: int = Field(default=10000)

    model_config = SettingsConfigDict(env_prefix="IMS_DINGTALK_ATTENDANCE_")


class TrainAISettings(BaseSettings):
    """Training AI configuration - managed by B10, B0a only provides skeleton (FW-H08)."""

    enabled: bool = Field(default=True)
    mode: str = Field(default="mock")
    base_url: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    model: str = Field(default="qwen3.8-max")
    api_key: str = Field(default="")  # Empty = unconfigured
    timeout_ms: int = Field(default=60000)
    max_questions: int = Field(default=20)

    model_config = SettingsConfigDict(env_prefix="IMS_TRAIN_AI_")


class IntegrationModeSettings(BaseSettings):
    """Integration mode switches."""

    dingtalk: str = Field(default="real")
    dingtalk_attendance: str = Field(default="mock")
    football_web: str = Field(default="mock")
    collector: str = Field(default="real")
    comfyui: str = Field(default="mock")
    content_ai: str = Field(default="real")
    train_ai: str = Field(default="mock")

    model_config = SettingsConfigDict(env_prefix="IMS_INTEGRATION_MODE_")


class SecuritySettings(BaseSettings):
    """Security configuration."""

    field_key: str = Field(default="", description="AES encryption key for fields")
    field_key_versions: dict[str, str] = Field(default={}, description="Historical keys for rotation")
    hash_key: str = Field(default="", description="HMAC key for hashing")

    model_config = SettingsConfigDict(env_prefix="IMS_SECURITY_")


class LockSettings(BaseSettings):
    """Login lock configuration."""

    max_fail_count: int = Field(default=5, description="Max login failures before lock")
    lock_minutes: int = Field(default=15, description="Lock duration in minutes")

    model_config = SettingsConfigDict(env_prefix="IMS_LOCK_")


class APISettings(BaseSettings):
    """API configuration.

    D2: id and *Id are always strings. There is no environment switch
    (IMS_API_ID_AS_STRING is ignored).
    """

    model_config = SettingsConfigDict(env_prefix="IMS_API_", extra="ignore")

    @property
    def id_as_string(self) -> bool:
        """Always True. D2 does not allow turning string ids off."""
        return True


class Settings(BaseSettings):
    """Main application settings."""

    env: str = Field(default="dev", description="Environment: dev/test/e2e/prod")
    app_name: str = Field(default="IMS Backend")
    debug: bool = Field(default=False)

    # Sub-configurations
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    football_live: FootballLiveSettings = Field(default_factory=FootballLiveSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    file: FileSettings = Field(default_factory=FileSettings)
    dingtalk: DingTalkSettings = Field(default_factory=DingTalkSettings)
    dingtalk_attendance: DingTalkAttendanceSettings = Field(default_factory=DingTalkAttendanceSettings)
    train_ai: TrainAISettings = Field(default_factory=TrainAISettings)
    integrations: IntegrationModeSettings = Field(default_factory=IntegrationModeSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    lock: LockSettings = Field(default_factory=LockSettings)
    api: APISettings = Field(default_factory=APISettings)

    model_config = SettingsConfigDict(
        env_prefix="IMS_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        """Validate required settings based on environment."""
        missing = []

        # JWT secret is always required except in test environment
        if not self.jwt.secret and self.env not in ("test",):
            missing.append("jwt.secret")

        # Database URL is required in non-test environments
        # Tests can use SQLite in-memory
        if not self.db.url and self.env not in ("test",):
            missing.append("db.url")

        # prod disables debug and OpenAPI
        if self.env == "prod":
            self.debug = False

        # e2e/prod require Redis (dev can fallback to memory, test uses memory)
        if self.env in ("e2e", "prod") and not self.redis.url:
            missing.append("redis.url")

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        return self

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    @property
    def is_test(self) -> bool:
        return self.env == "test"

    @property
    def docs_enabled(self) -> bool:
        """OpenAPI docs enabled in non-prod."""
        return self.env != "prod"


def load_config_file(env: str) -> dict[str, Any]:
    """Load environment-specific config file."""
    config_paths = [
        Path(f"config/{env}.yaml"),
        Path(f"config/{env}.yml"),
    ]

    for path in config_paths:
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f) or {}

    return {}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    env = os.getenv("IMS_ENV", "dev")

    # Load config file first (lower priority)
    file_config = load_config_file(env)

    # Environment variables override file config
    return Settings(env=env, **file_config)


# Global settings instance
settings = get_settings()
