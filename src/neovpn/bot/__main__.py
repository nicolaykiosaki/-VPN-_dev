"""Run the bot in long-polling mode."""

from __future__ import annotations

import asyncio

from neovpn.bot.app import build_bot, build_dispatcher
from neovpn.bot.container import build_deps
from neovpn.config import get_settings
from neovpn.db.engine import create_engine, create_session_factory
from neovpn.logging import configure_logging, get_logger

log = get_logger(__name__)


async def _run() -> None:
    configure_logging()
    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    # Panel wiring happens at node-registration time (phase 2); in the MVP the
    # bot starts with an empty panel map and populates it dynamically once an
    # admin adds nodes.  Keeping the map injectable makes tests trivial.
    deps = await build_deps(
        settings=settings, session_factory=session_factory, panels={}
    )
    bot = build_bot(deps)
    dp = build_dispatcher(deps)

    log.info("bot.starting", admin_ids=list(settings.bot_admin_ids))
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
