"""Pydantic domain models.

These models are the single source of truth for the shape of business data.
They are used both by the database layer (mapped 1:1 to SQLAlchemy rows) and
by the application layer (bot, API, worker).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

class Money(BaseModel):
    """Immutable monetary amount in a single currency.

    Currencies are represented as uppercase ISO codes (e.g. ``RUB``, ``USD``)
    or special markers (``STARS`` for Telegram Stars, ``USDT`` for crypto).
    """

    model_config = ConfigDict(frozen=True)

    amount: Decimal = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=8)

    @field_validator("currency")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.upper()

    def __str__(self) -> str:
        return f"{self.amount:f} {self.currency}"


def _now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TariffKind(StrEnum):
    TRIAL = "trial"
    PAID = "paid"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class VpnProtocol(StrEnum):
    VLESS_REALITY = "vless_reality"
    VLESS_WS_TLS = "vless_ws_tls"
    SHADOWSOCKS = "shadowsocks"
    TROJAN = "trojan"


class VpnKeyStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class NodeStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"


class PaymentProvider(StrEnum):
    TELEGRAM_STARS = "telegram_stars"
    CRYPTOBOT = "cryptobot"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


# ---------------------------------------------------------------------------
# Aggregates
# ---------------------------------------------------------------------------

class _Entity(BaseModel):
    """Base for all entities. Gives every aggregate a stable identity."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class User(_Entity):
    """Telegram user that interacts with the bot or the website."""

    tg_id: int = Field(..., description="Telegram numeric ID")
    username: str | None = None
    first_name: str | None = None
    language_code: str | None = None
    referrer_id: UUID | None = None
    is_banned: bool = False
    email: str | None = None  # optional, used for the web cabinet


class Tariff(_Entity):
    """Subscription plan the user can purchase."""

    slug: str = Field(..., min_length=2, max_length=40)
    name: str
    kind: TariffKind = TariffKind.PAID
    duration_days: int = Field(..., ge=1, le=3650)
    traffic_gb: int | None = Field(
        default=None,
        ge=1,
        description="Monthly traffic cap in GiB; ``None`` means unlimited.",
    )
    devices: int = Field(default=3, ge=1, le=10)
    price_rub: Decimal = Field(default=Decimal("0"), ge=0)
    price_stars: int = Field(default=0, ge=0)
    price_usdt: Decimal = Field(default=Decimal("0"), ge=0)
    is_public: bool = True


class Subscription(_Entity):
    """A paid (or trial) slot that entitles a user to VPN keys."""

    user_id: UUID
    tariff_id: UUID
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    valid_from: datetime = Field(default_factory=_now)
    valid_until: datetime

    def is_active_at(self, moment: datetime) -> bool:
        return (
            self.status is SubscriptionStatus.ACTIVE
            and self.valid_from <= moment <= self.valid_until
        )


class Node(_Entity):
    """A single VPN server we manage."""

    slug: str = Field(..., min_length=2, max_length=40)
    region: str
    panel_type: str = "marzban"
    host: str
    status: NodeStatus = NodeStatus.ONLINE
    is_public: bool = True


class VpnKey(_Entity):
    """An issued connection credential bound to a subscription and node."""

    subscription_id: UUID
    node_id: UUID
    protocol: VpnProtocol
    remark: str
    config_url: str = Field(
        ...,
        description="Subscription or config URL the client imports (e.g. vless://…).",
    )
    traffic_used_bytes: int = Field(default=0, ge=0)
    status: VpnKeyStatus = VpnKeyStatus.ACTIVE


class Payment(_Entity):
    """A payment attempt (successful or not)."""

    user_id: UUID
    tariff_id: UUID
    provider: PaymentProvider
    status: PaymentStatus = PaymentStatus.PENDING
    amount: Money
    external_id: str | None = None
    paid_at: datetime | None = None
