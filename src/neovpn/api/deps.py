"""FastAPI dependency-injection wiring."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from neovpn.config import Settings, get_settings
from neovpn.db import SqlAlchemyUnitOfWork


def get_settings_dep() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


async def get_uow(request: Request) -> AsyncIterator[SqlAlchemyUnitOfWork]:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with SqlAlchemyUnitOfWork(factory) as uow:
        yield uow


UowDep = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]
