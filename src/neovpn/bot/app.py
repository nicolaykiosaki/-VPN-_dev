"""Bot application factory."""

from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis as AsyncRedis

from neovpn.bot.container import BotDeps
from neovpn.bot.handlers import build_root_router
from neovpn.bot.middleware import DepsMiddleware


def build_bot(deps: BotDeps) -> Bot:
    return Bot(
        token=deps.settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def build_dispatcher(deps: BotDeps) -> Dispatcher:
    storage: BaseStorage
    if deps.settings.redis_url:
        redis = AsyncRedis.from_url(deps.settings.redis_url)
        storage = RedisStorage(redis=redis)
    else:
        storage = MemoryStorage()  # pragma: no cover — tests only
    dp = Dispatcher(storage=storage)
    dp.update.outer_middleware(DepsMiddleware(deps))
    dp.include_router(build_root_router())
    return dp
