"""Wiring for the bot's dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from neovpn.config import Settings
from neovpn.core.protocols import PanelClient
from neovpn.panels.marzban import MarzbanClient
from neovpn.payments.cryptobot import CryptoBotAdapter
from neovpn.payments.stars import TelegramStarsAdapter


@dataclass(slots=True)
class BotDeps:
    """Everything handlers need at runtime."""

    settings: Settings
    session_factory: async_sessionmaker[AsyncSession]
    panels: dict[UUID, PanelClient]
    stars: TelegramStarsAdapter
    cryptobot: CryptoBotAdapter | None


async def build_deps(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    panels: dict[UUID, PanelClient],
) -> BotDeps:
    cryptobot: CryptoBotAdapter | None = None
    if settings.cryptobot_token is not None:
        cryptobot = CryptoBotAdapter(
            api_token=settings.cryptobot_token.get_secret_value(),
            webhook_secret=(
                settings.cryptobot_webhook_secret.get_secret_value()
                if settings.cryptobot_webhook_secret
                else None
            ),
        )
    return BotDeps(
        settings=settings,
        session_factory=session_factory,
        panels=panels,
        stars=TelegramStarsAdapter(),
        cryptobot=cryptobot,
    )


def build_marzban_from_settings(settings: Settings) -> MarzbanClient | None:
    if (
        settings.marzban_url is None
        or settings.marzban_username is None
        or settings.marzban_password is None
    ):
        return None
    return MarzbanClient(
        base_url=str(settings.marzban_url),
        username=settings.marzban_username,
        password=settings.marzban_password.get_secret_value(),
    )
