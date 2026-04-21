"""Unit-of-Work implementation backed by an :class:`AsyncSession`."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from neovpn.core.protocols import (
    NodeRepository,
    PaymentRepository,
    SubscriptionRepository,
    TariffRepository,
    UserRepository,
    VpnKeyRepository,
)
from neovpn.db.repositories import (
    SqlAlchemyNodeRepository,
    SqlAlchemyPaymentRepository,
    SqlAlchemySubscriptionRepository,
    SqlAlchemyTariffRepository,
    SqlAlchemyUserRepository,
    SqlAlchemyVpnKeyRepository,
)


class SqlAlchemyUnitOfWork:
    """Aggregates all repositories over a single session.

    Usage::

        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            user = await uow.users.get_by_tg_id(123)
            await uow.commit()
    """

    users: UserRepository
    tariffs: TariffRepository
    subscriptions: SubscriptionRepository
    nodes: NodeRepository
    keys: VpnKeyRepository
    payments: PaymentRepository

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        session = self._session
        self.users = SqlAlchemyUserRepository(session)
        self.tariffs = SqlAlchemyTariffRepository(session)
        self.subscriptions = SqlAlchemySubscriptionRepository(session)
        self.nodes = SqlAlchemyNodeRepository(session)
        self.keys = SqlAlchemyVpnKeyRepository(session)
        self.payments = SqlAlchemyPaymentRepository(session)
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        tb: object,
    ) -> None:
        assert self._session is not None
        try:
            if exc is None:
                await self._session.commit()
            else:
                await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        assert self._session is not None
        await self._session.commit()

    async def rollback(self) -> None:
        assert self._session is not None
        await self._session.rollback()

    @property
    def session(self) -> AsyncSession:
        """Return the underlying session. Prefer repositories when possible."""
        assert self._session is not None, "UnitOfWork used outside of 'async with'"
        return self._session
