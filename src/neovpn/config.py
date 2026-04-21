"""Centralised application configuration.

Settings are loaded from environment variables prefixed with ``NEOVPN_``.
A local ``.env`` file (see ``.env.example``) is respected in development.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["dev", "test", "prod"]


class Settings(BaseSettings):
    """Top-level settings object.

    The object is immutable once constructed; call :func:`get_settings` to
    retrieve a cached instance.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="NEOVPN_",
        extra="ignore",
        frozen=True,
    )

    environment: Environment = "dev"

    # Telegram bot
    bot_token: SecretStr = Field(..., description="Telegram Bot API token")
    bot_admin_ids: tuple[int, ...] = Field(
        default=(),
        description="Comma-separated Telegram IDs of bot administrators.",
    )
    bot_username: str = "NeoVPN_bot"

    # Public URLs shared with the browser and bot deep-links
    public_web_url: HttpUrl = Field(default=HttpUrl("http://localhost:3000"))
    public_api_url: HttpUrl = Field(default=HttpUrl("http://localhost:8000"))

    # Persistence
    database_url: str = "postgresql+asyncpg://neovpn:neovpn@localhost:5432/neovpn"
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret: SecretStr = Field(..., description="Secret for signing site JWTs")
    jwt_ttl_seconds: int = 7 * 24 * 3600

    # Marzban panel
    marzban_url: HttpUrl | None = None
    marzban_username: str | None = None
    marzban_password: SecretStr | None = None

    # Payments
    stars_enabled: bool = True
    cryptobot_token: SecretStr | None = None
    cryptobot_webhook_secret: SecretStr | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide :class:`Settings` instance."""
    return Settings()
