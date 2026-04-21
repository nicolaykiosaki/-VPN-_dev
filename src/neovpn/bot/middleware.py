"""Aiogram middlewares."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from neovpn.bot.container import BotDeps


class DepsMiddleware(BaseMiddleware):
    """Inject :class:`BotDeps` into every handler."""

    def __init__(self, deps: BotDeps) -> None:
        self._deps = deps

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["deps"] = self._deps
        return await handler(event, data)
