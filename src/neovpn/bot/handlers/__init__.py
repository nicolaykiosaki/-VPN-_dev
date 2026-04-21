"""Bot routers."""

from aiogram import Router

from neovpn.bot.handlers.admin import router as admin_router
from neovpn.bot.handlers.payments import router as payments_router
from neovpn.bot.handlers.user import router as user_router


def build_root_router() -> Router:
    """Return a single parent router aggregating every feature router."""
    root = Router(name="neovpn-root")
    root.include_router(admin_router)
    root.include_router(user_router)
    root.include_router(payments_router)
    return root


__all__ = ["build_root_router"]
