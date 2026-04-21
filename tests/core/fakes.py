"""In-memory fakes for the repository/UoW protocols.

These let us test domain use-cases without spinning up a real database.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from neovpn.core.models import (
    Node,
    NodeStatus,
    Payment,
    PaymentProvider,
    PaymentStatus,
    Subscription,
    Tariff,
    TariffKind,
    User,
    VpnKey,
    VpnProtocol,
)


class _Store:
    def __init__(self) -> None:
        self.users: dict[UUID, User] = {}
        self.tariffs: dict[UUID, Tariff] = {}
        self.subscriptions: dict[UUID, Subscription] = {}
        self.nodes: dict[UUID, Node] = {}
        self.keys: dict[UUID, VpnKey] = {}
        self.payments: dict[UUID, Payment] = {}


class FakeUserRepo:
    def __init__(self, store: _Store) -> None:
        self._s = store

    async def get_by_tg_id(self, tg_id: int) -> User | None:
        return next((u for u in self._s.users.values() if u.tg_id == tg_id), None)

    async def get(self, user_id: UUID) -> User | None:
        return self._s.users.get(user_id)

    async def upsert_from_tg(
        self,
        *,
        tg_id: int,
        username: str | None,
        first_name: str | None,
        language_code: str | None,
        referrer_id: UUID | None = None,
    ) -> User:
        existing = await self.get_by_tg_id(tg_id)
        if existing is None:
            user = User(
                tg_id=tg_id,
                username=username,
                first_name=first_name,
                language_code=language_code,
                referrer_id=referrer_id,
            )
            self._s.users[user.id] = user
            return user
        updated = existing.model_copy(
            update={
                "username": username,
                "first_name": first_name,
                "language_code": language_code,
                "referrer_id": existing.referrer_id or referrer_id,
            }
        )
        self._s.users[updated.id] = updated
        return updated

    async def has_trial(self, user_id: UUID) -> bool:
        trial_tariffs = {t.id for t in self._s.tariffs.values() if t.kind is TariffKind.TRIAL}
        return any(
            s.user_id == user_id and s.tariff_id in trial_tariffs
            for s in self._s.subscriptions.values()
        )


class FakeTariffRepo:
    def __init__(self, store: _Store) -> None:
        self._s = store

    async def get(self, tariff_id: UUID) -> Tariff | None:
        return self._s.tariffs.get(tariff_id)

    async def get_by_slug(self, slug: str) -> Tariff | None:
        return next((t for t in self._s.tariffs.values() if t.slug == slug), None)

    async def list_public(self) -> list[Tariff]:
        return [t for t in self._s.tariffs.values() if t.is_public and t.kind is TariffKind.PAID]

    async def get_trial(self) -> Tariff | None:
        return next((t for t in self._s.tariffs.values() if t.kind is TariffKind.TRIAL), None)


class FakeSubscriptionRepo:
    def __init__(self, store: _Store) -> None:
        self._s = store

    async def create(self, subscription: Subscription) -> Subscription:
        self._s.subscriptions[subscription.id] = subscription
        return subscription

    async def get(self, subscription_id: UUID) -> Subscription | None:
        return self._s.subscriptions.get(subscription_id)

    async def list_for_user(self, user_id: UUID) -> list[Subscription]:
        return [s for s in self._s.subscriptions.values() if s.user_id == user_id]

    async def active_for_user(self, user_id: UUID, at: datetime) -> list[Subscription]:
        return [
            s
            for s in self._s.subscriptions.values()
            if s.user_id == user_id and s.is_active_at(at)
        ]

    async def extend(self, subscription_id: UUID, new_valid_until: datetime) -> Subscription:
        sub = self._s.subscriptions[subscription_id]
        updated = sub.model_copy(update={"valid_until": new_valid_until})
        self._s.subscriptions[subscription_id] = updated
        return updated


class FakeNodeRepo:
    def __init__(self, store: _Store) -> None:
        self._s = store

    async def list_available(self) -> list[Node]:
        return [n for n in self._s.nodes.values() if n.status is NodeStatus.ONLINE]

    async def get(self, node_id: UUID) -> Node | None:
        return self._s.nodes.get(node_id)


class FakeKeyRepo:
    def __init__(self, store: _Store) -> None:
        self._s = store

    async def create(self, key: VpnKey) -> VpnKey:
        self._s.keys[key.id] = key
        return key

    async def list_for_subscription(self, subscription_id: UUID) -> list[VpnKey]:
        return [k for k in self._s.keys.values() if k.subscription_id == subscription_id]


class FakePaymentRepo:
    def __init__(self, store: _Store) -> None:
        self._s = store

    async def create(self, payment: Payment) -> Payment:
        self._s.payments[payment.id] = payment
        return payment

    async def get_by_external_id(
        self, provider: PaymentProvider, external_id: str
    ) -> Payment | None:
        return next(
            (
                p
                for p in self._s.payments.values()
                if p.provider is provider and p.external_id == external_id
            ),
            None,
        )

    async def set_external_id(self, payment_id: UUID, external_id: str) -> Payment:
        p = self._s.payments[payment_id]
        updated = p.model_copy(update={"external_id": external_id})
        self._s.payments[payment_id] = updated
        return updated

    async def mark(
        self,
        payment_id: UUID,
        *,
        status: PaymentStatus,
        paid_at: datetime | None = None,
    ) -> Payment:
        p = self._s.payments[payment_id]
        updated = p.model_copy(update={"status": status, "paid_at": paid_at})
        self._s.payments[payment_id] = updated
        return updated


class FakeUnitOfWork:
    """Satisfies the :class:`neovpn.core.protocols.UnitOfWork` protocol."""

    def __init__(self) -> None:
        self._store = _Store()
        self.users = FakeUserRepo(self._store)
        self.tariffs = FakeTariffRepo(self._store)
        self.subscriptions = FakeSubscriptionRepo(self._store)
        self.nodes = FakeNodeRepo(self._store)
        self.keys = FakeKeyRepo(self._store)
        self.payments = FakePaymentRepo(self._store)
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        tb: object,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    # Helpers for tests
    def seed(
        self,
        *,
        users: list[User] | None = None,
        tariffs: list[Tariff] | None = None,
        nodes: list[Node] | None = None,
    ) -> None:
        for u in users or []:
            self._store.users[u.id] = u
        for t in tariffs or []:
            self._store.tariffs[t.id] = t
        for n in nodes or []:
            self._store.nodes[n.id] = n


class FakePanel:
    """Minimal ``PanelClient`` that records calls."""

    def __init__(self) -> None:
        self.created: list[tuple[str, VpnProtocol, int | None, int]] = []
        self.revoked: list[str] = []
        self.next_id = 1

    async def health(self) -> bool:
        return True

    async def create_key(
        self,
        *,
        remark: str,
        protocol: VpnProtocol,
        traffic_gb: int | None,
        duration_days: int,
    ) -> tuple[str, str]:
        external_id = f"ext-{self.next_id}"
        self.next_id += 1
        self.created.append((remark, protocol, traffic_gb, duration_days))
        return external_id, f"vless://{external_id}@example.com:443"

    async def revoke_key(self, external_key_id: str) -> None:
        self.revoked.append(external_key_id)

    async def traffic_used(self, external_key_id: str) -> int:
        return 0


__all__ = ["FakePanel", "FakeUnitOfWork"]
