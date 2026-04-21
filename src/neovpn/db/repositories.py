"""SQLAlchemy repository implementations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from neovpn.core.errors import TariffNotFoundError, UserNotFoundError
from neovpn.core.models import (
    Node,
    Payment,
    PaymentProvider,
    PaymentStatus,
    Subscription,
    Tariff,
    User,
    VpnKey,
)
from neovpn.db import mappers
from neovpn.db.models import (
    NodeRow,
    PaymentRow,
    SubscriptionRow,
    TariffRow,
    UserRow,
    VpnKeyRow,
)


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_by_tg_id(self, tg_id: int) -> User | None:
        row = await self._s.scalar(select(UserRow).where(UserRow.tg_id == tg_id))
        return mappers.user_from_row(row) if row else None

    async def get(self, user_id: UUID) -> User | None:
        row = await self._s.get(UserRow, user_id)
        return mappers.user_from_row(row) if row else None

    async def upsert_from_tg(
        self,
        *,
        tg_id: int,
        username: str | None,
        first_name: str | None,
        language_code: str | None,
        referrer_id: UUID | None = None,
    ) -> User:
        row = await self._s.scalar(select(UserRow).where(UserRow.tg_id == tg_id))
        if row is None:
            row = UserRow(
                tg_id=tg_id,
                username=username,
                first_name=first_name,
                language_code=language_code,
                referrer_id=referrer_id,
            )
            self._s.add(row)
        else:
            row.username = username
            row.first_name = first_name
            row.language_code = language_code
            if row.referrer_id is None and referrer_id is not None:
                row.referrer_id = referrer_id
        await self._s.flush()
        return mappers.user_from_row(row)

    async def has_trial(self, user_id: UUID) -> bool:
        row = await self._s.scalar(
            select(SubscriptionRow)
            .join(TariffRow, TariffRow.id == SubscriptionRow.tariff_id)
            .where(SubscriptionRow.user_id == user_id, TariffRow.kind == "trial")
            .limit(1)
        )
        return row is not None


class SqlAlchemyTariffRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, tariff_id: UUID) -> Tariff | None:
        row = await self._s.get(TariffRow, tariff_id)
        return mappers.tariff_from_row(row) if row else None

    async def get_by_slug(self, slug: str) -> Tariff | None:
        row = await self._s.scalar(select(TariffRow).where(TariffRow.slug == slug))
        return mappers.tariff_from_row(row) if row else None

    async def list_public(self) -> list[Tariff]:
        rows = (
            await self._s.scalars(
                select(TariffRow)
                .where(TariffRow.is_public, TariffRow.kind == "paid")
                .order_by(TariffRow.duration_days)
            )
        ).all()
        return [mappers.tariff_from_row(r) for r in rows]

    async def get_trial(self) -> Tariff | None:
        row = await self._s.scalar(
            select(TariffRow).where(TariffRow.kind == "trial").limit(1)
        )
        return mappers.tariff_from_row(row) if row else None


class SqlAlchemySubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(self, subscription: Subscription) -> Subscription:
        row = SubscriptionRow(
            id=subscription.id,
            user_id=subscription.user_id,
            tariff_id=subscription.tariff_id,
            status=subscription.status.value,
            valid_from=subscription.valid_from,
            valid_until=subscription.valid_until,
        )
        self._s.add(row)
        await self._s.flush()
        return mappers.subscription_from_row(row)

    async def get(self, subscription_id: UUID) -> Subscription | None:
        row = await self._s.get(SubscriptionRow, subscription_id)
        return mappers.subscription_from_row(row) if row else None

    async def list_for_user(self, user_id: UUID) -> list[Subscription]:
        rows = (
            await self._s.scalars(
                select(SubscriptionRow)
                .where(SubscriptionRow.user_id == user_id)
                .order_by(SubscriptionRow.valid_until.desc())
            )
        ).all()
        return [mappers.subscription_from_row(r) for r in rows]

    async def active_for_user(
        self, user_id: UUID, at: datetime
    ) -> list[Subscription]:
        rows = (
            await self._s.scalars(
                select(SubscriptionRow).where(
                    SubscriptionRow.user_id == user_id,
                    SubscriptionRow.status == "active",
                    SubscriptionRow.valid_from <= at,
                    SubscriptionRow.valid_until >= at,
                )
            )
        ).all()
        return [mappers.subscription_from_row(r) for r in rows]

    async def extend(
        self, subscription_id: UUID, new_valid_until: datetime
    ) -> Subscription:
        row = await self._s.get(SubscriptionRow, subscription_id)
        if row is None:
            raise LookupError(f"subscription not found: {subscription_id}")
        row.valid_until = new_valid_until
        row.status = "active"
        await self._s.flush()
        return mappers.subscription_from_row(row)


class SqlAlchemyNodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def list_available(self) -> list[Node]:
        rows = (
            await self._s.scalars(
                select(NodeRow)
                .where(NodeRow.is_public, NodeRow.status == "online")
                .order_by(NodeRow.slug)
            )
        ).all()
        return [mappers.node_from_row(r) for r in rows]

    async def get(self, node_id: UUID) -> Node | None:
        row = await self._s.get(NodeRow, node_id)
        return mappers.node_from_row(row) if row else None


class SqlAlchemyVpnKeyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(self, key: VpnKey) -> VpnKey:
        row = VpnKeyRow(
            id=key.id,
            subscription_id=key.subscription_id,
            node_id=key.node_id,
            protocol=key.protocol.value,
            remark=key.remark,
            config_url=key.config_url,
            traffic_used_bytes=key.traffic_used_bytes,
            status=key.status.value,
        )
        self._s.add(row)
        await self._s.flush()
        return mappers.key_from_row(row)

    async def list_for_subscription(self, subscription_id: UUID) -> list[VpnKey]:
        rows = (
            await self._s.scalars(
                select(VpnKeyRow)
                .where(VpnKeyRow.subscription_id == subscription_id)
                .order_by(VpnKeyRow.created_at)
            )
        ).all()
        return [mappers.key_from_row(r) for r in rows]


class SqlAlchemyPaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(self, payment: Payment) -> Payment:
        row = PaymentRow(
            id=payment.id,
            user_id=payment.user_id,
            tariff_id=payment.tariff_id,
            provider=payment.provider.value,
            status=payment.status.value,
            amount=payment.amount.amount,
            currency=payment.amount.currency,
            external_id=payment.external_id,
            paid_at=payment.paid_at,
        )
        self._s.add(row)
        await self._s.flush()
        return mappers.payment_from_row(row)

    async def get_by_external_id(
        self, provider: PaymentProvider, external_id: str
    ) -> Payment | None:
        row = await self._s.scalar(
            select(PaymentRow).where(
                PaymentRow.provider == provider.value,
                PaymentRow.external_id == external_id,
            )
        )
        return mappers.payment_from_row(row) if row else None

    async def set_external_id(self, payment_id: UUID, external_id: str) -> Payment:
        row = await self._s.get(PaymentRow, payment_id)
        if row is None:
            raise LookupError(f"payment not found: {payment_id}")
        row.external_id = external_id
        await self._s.flush()
        return mappers.payment_from_row(row)

    async def mark(
        self,
        payment_id: UUID,
        *,
        status: PaymentStatus,
        paid_at: datetime | None = None,
    ) -> Payment:
        row = await self._s.get(PaymentRow, payment_id)
        if row is None:
            raise LookupError(f"payment not found: {payment_id}")
        row.status = status.value
        if paid_at is not None:
            row.paid_at = paid_at
        await self._s.flush()
        return mappers.payment_from_row(row)


__all__ = [
    "SqlAlchemyNodeRepository",
    "SqlAlchemyPaymentRepository",
    "SqlAlchemySubscriptionRepository",
    "SqlAlchemyTariffRepository",
    "SqlAlchemyUserRepository",
    "SqlAlchemyVpnKeyRepository",
    "TariffNotFoundError",
    "UserNotFoundError",
]
