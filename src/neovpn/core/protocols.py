"""Protocols (ports) the core layer depends on.

Concrete adapters (database, VPN panels, payment providers) live in other
packages and are wired together at application start-up.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from neovpn.core.models import (
    Money,
    Node,
    Payment,
    PaymentProvider,
    PaymentStatus,
    Subscription,
    Tariff,
    User,
    VpnKey,
    VpnProtocol,
)


class UserRepository(Protocol):
    async def get_by_tg_id(self, tg_id: int) -> User | None: ...
    async def get(self, user_id: UUID) -> User | None: ...
    async def upsert_from_tg(
        self,
        *,
        tg_id: int,
        username: str | None,
        first_name: str | None,
        language_code: str | None,
        referrer_id: UUID | None = None,
    ) -> User: ...
    async def has_trial(self, user_id: UUID) -> bool: ...


class TariffRepository(Protocol):
    async def get_by_slug(self, slug: str) -> Tariff | None: ...
    async def get(self, tariff_id: UUID) -> Tariff | None: ...
    async def list_public(self) -> list[Tariff]: ...
    async def get_trial(self) -> Tariff | None: ...


class SubscriptionRepository(Protocol):
    async def create(self, subscription: Subscription) -> Subscription: ...
    async def get(self, subscription_id: UUID) -> Subscription | None: ...
    async def list_for_user(self, user_id: UUID) -> list[Subscription]: ...
    async def active_for_user(self, user_id: UUID, at: datetime) -> list[Subscription]: ...
    async def extend(self, subscription_id: UUID, new_valid_until: datetime) -> Subscription: ...


class NodeRepository(Protocol):
    async def list_available(self) -> list[Node]: ...
    async def get(self, node_id: UUID) -> Node | None: ...


class VpnKeyRepository(Protocol):
    async def create(self, key: VpnKey) -> VpnKey: ...
    async def list_for_subscription(self, subscription_id: UUID) -> list[VpnKey]: ...


class PaymentRepository(Protocol):
    async def create(self, payment: Payment) -> Payment: ...
    async def get_by_external_id(
        self, provider: PaymentProvider, external_id: str
    ) -> Payment | None: ...
    async def set_external_id(self, payment_id: UUID, external_id: str) -> Payment: ...
    async def mark(
        self,
        payment_id: UUID,
        *,
        status: PaymentStatus,
        paid_at: datetime | None = None,
    ) -> Payment: ...


class UnitOfWork(Protocol):
    users: UserRepository
    tariffs: TariffRepository
    subscriptions: SubscriptionRepository
    nodes: NodeRepository
    keys: VpnKeyRepository
    payments: PaymentRepository

    async def __aenter__(self) -> UnitOfWork: ...
    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class VpnKeyRequest(Protocol):
    subscription_id: UUID
    user_id: UUID
    protocol: VpnProtocol
    traffic_gb: int | None
    duration_days: int
    remark: str


class PanelClient(Protocol):
    """Generic VPN panel interface. Implemented per panel (Marzban, Amnezia)."""

    async def health(self) -> bool: ...
    async def create_key(
        self,
        *,
        remark: str,
        protocol: VpnProtocol,
        traffic_gb: int | None,
        duration_days: int,
    ) -> tuple[str, str]:
        """Return ``(external_key_id, config_url)``."""
        ...

    async def revoke_key(self, external_key_id: str) -> None: ...
    async def traffic_used(self, external_key_id: str) -> int: ...


class PaymentAdapter(Protocol):
    """Payment provider adapter."""

    provider: PaymentProvider

    async def create_invoice(
        self,
        *,
        user: User,
        tariff: Tariff,
        amount: Money,
        return_url: str | None,
    ) -> tuple[str, str]:
        """Return ``(external_id, pay_url)``."""
        ...
