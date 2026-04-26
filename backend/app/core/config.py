"""
TBAPS Configuration
Application settings and environment variables — unified across local and production.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List, Literal, Optional
import secrets


class Settings(BaseSettings):
    """Application settings — reads from a single .env file in the project root."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "TBAPS"
    APP_ENV: Literal["development", "production", "testing"] = Field(default="production")
    DEBUG: bool = Field(default=False)
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=20, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=40, env="DATABASE_MAX_OVERFLOW")

    # Redis (optional — set REDIS_OPTIONAL=true to allow degraded mode)
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_CACHE_DB: int = Field(default=0)
    REDIS_SESSION_DB: int = Field(default=1)
    REDIS_CELERY_DB: int = Field(default=2)
    REDIS_OPTIONAL: bool = Field(default=True)

    # RabbitMQ (optional)
    RABBITMQ_URL: str = Field(default="amqp://guest:guest@localhost:5672/")

    # JWT
    JWT_SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(64))
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ISSUER: str = Field(default="tbaps")
    JWT_AUDIENCE: str = Field(default="tbaps-api")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # Encryption
    ENCRYPTION_KEY: str = Field(default_factory=lambda: secrets.token_hex(16))

    # CORS — comma-separated list of allowed origins
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    # URLs
    FRONTEND_URL: str = Field(default="http://localhost:5173")
    # SERVER_URL is used by the agent package generator to embed the backend URL
    SERVER_URL: str = Field(default="http://localhost:8000")

    # Google OAuth
    GOOGLE_CLIENT_ID: str = Field(default="")
    GOOGLE_CLIENT_SECRET: str = Field(default="")
    GOOGLE_REDIRECT_URI: str = Field(default="http://localhost:8000/api/v1/integrations/google/callback")

    # Microsoft OAuth
    MICROSOFT_CLIENT_ID: str = Field(default="")
    MICROSOFT_CLIENT_SECRET: str = Field(default="")
    MICROSOFT_TENANT_ID: str = Field(default="common")
    MICROSOFT_REDIRECT_URI: str = Field(default="http://localhost:8000/api/v1/integrations/microsoft/callback")

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    RATE_LIMIT_INTEGRATION_SYNC: int = Field(default=10)

    # Integration Settings
    INTEGRATION_TIMEOUT_SECONDS: int = Field(default=30)
    INTEGRATION_MAX_RETRIES: int = Field(default=3)
    INTEGRATION_RETRY_BACKOFF: int = Field(default=2)

    # Sync Settings
    SYNC_BATCH_SIZE: int = Field(default=100)
    SYNC_LOOKBACK_DAYS: int = Field(default=30)

    # Celery (optional)
    CELERY_BROKER_URL: str = Field(default="amqp://guest:guest@localhost:5672/")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")
    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(default=300)
    CELERY_TASK_TIME_LIMIT: int = Field(default=360)
    CELERY_MAX_RETRIES: int = Field(default=3)

    # Monitoring
    PROMETHEUS_ENABLED: bool = Field(default=False)
    SENTRY_DSN: str = Field(default="")

    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: Literal["json", "text"] = Field(default="json")

    # Traffic Monitoring
    CAPTURE_INTERFACE: str = Field(default="tun0")
    CAPTURE_FILTER: str = Field(default="udp port 53 or tcp port 443")
    BATCH_SIZE: int = Field(default=100)
    FLUSH_INTERVAL: int = Field(default=10)
    AGGREGATION_INTERVAL: int = Field(default=60)

    # Email — NEF Agent Distribution
    EMAIL_PROVIDER: Literal["smtp", "sendgrid"] = Field(default="smtp")
    EMAIL_FROM_ADDRESS: str = Field(default="noreply@tbaps.local")
    EMAIL_FROM_NAME: str = Field(default="TBAPS Admin")
    # SMTP (Gmail, Outlook, etc.)
    SMTP_HOST: str = Field(default="smtp.gmail.com")
    SMTP_PORT: int = Field(default=587)
    SMTP_USERNAME: str = Field(default="")
    SMTP_PASSWORD: str = Field(default="")
    SMTP_USE_TLS: bool = Field(default=True)
    # SendGrid (alternative)
    SENDGRID_API_KEY: str = Field(default="")
    # Rate limit for send-agent endpoint
    AGENT_SEND_RATE_LIMIT: str = Field(default="10/hour")

    # Chat / File Sharing
    CHAT_FILE_MAX_MB:             int    = Field(default=20)
    CHAT_STORAGE_PATH:            str    = Field(default="/storage/chat_files")
    CHAT_FILE_TOKEN_EXPIRY_HOURS: int    = Field(default=24)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string, JSON array string, or list."""
        import json
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            # Handle JSON array format: ["http://...", "http://..."]
            if v.startswith("["):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [o.strip() for o in parsed if o.strip()]
                except (json.JSONDecodeError, ValueError):
                    pass
            # Fallback: comma-separated format
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


# Create settings instance
settings = Settings()
