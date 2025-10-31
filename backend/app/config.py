"""Application configuration helpers."""
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional


@dataclass(frozen=True)
class Settings:
    """Settings loaded from environment variables."""

    smtp_host: str
    smtp_port: int
    smtp_username: Optional[str]
    smtp_password: Optional[str]
    smtp_use_tls: bool
    smtp_pool_size: int
    smtp_timeout: int
    rate_limit_count: int
    rate_limit_period: int
    default_sender: Optional[str]


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def get_settings() -> Settings:
    """Return the application settings instance."""

    return Settings(
        smtp_host=_get_env("SMTP_HOST", "localhost"),
        smtp_port=int(_get_env("SMTP_PORT", "1025")),
        smtp_username=_get_env("SMTP_USERNAME"),
        smtp_password=_get_env("SMTP_PASSWORD"),
        smtp_use_tls=_get_env("SMTP_USE_TLS", "false").lower() in {"1", "true", "yes", "on"},
        smtp_pool_size=int(_get_env("SMTP_POOL_SIZE", "5")),
        smtp_timeout=int(_get_env("SMTP_TIMEOUT", "30")),
        rate_limit_count=int(_get_env("RATE_LIMIT_COUNT", "30")),
        rate_limit_period=int(_get_env("RATE_LIMIT_PERIOD", "60")),
        default_sender=_get_env("DEFAULT_SENDER"),
    )


settings = get_settings()
