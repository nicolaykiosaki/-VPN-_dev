"""SQLAlchemy ORM models.

Column names intentionally mirror the Pydantic domain models in
:mod:`neovpn.core.models` to keep mapping straightforward.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> UUID:
    return uuid4()


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )


class UserRow(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    referrer_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    subscriptions: Mapped[list[SubscriptionRow]] = relationship(
        back_populates="user", foreign_keys="SubscriptionRow.user_id"
    )


class TariffRow(Base, TimestampMixin):
    __tablename__ = "tariffs"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False, default="paid")
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    traffic_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    devices: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    price_rub: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    price_stars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price_usdt: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SubscriptionRow(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tariff_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tariffs.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    user: Mapped[UserRow] = relationship(back_populates="subscriptions", foreign_keys=[user_id])
    keys: Mapped[list[VpnKeyRow]] = relationship(
        back_populates="subscription", cascade="all, delete-orphan"
    )


class NodeRow(Base, TimestampMixin):
    __tablename__ = "nodes"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    region: Mapped[str] = mapped_column(String(40), nullable=False)
    panel_type: Mapped[str] = mapped_column(String(20), nullable=False, default="marzban")
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="online")
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class VpnKeyRow(Base, TimestampMixin):
    __tablename__ = "vpn_keys"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    subscription_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("nodes.id"), nullable=False
    )
    protocol: Mapped[str] = mapped_column(String(40), nullable=False)
    remark: Mapped[str] = mapped_column(String(128), nullable=False)
    config_url: Mapped[str] = mapped_column(Text, nullable=False)
    traffic_used_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    subscription: Mapped[SubscriptionRow] = relationship(back_populates="keys")


class PaymentRow(Base, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("provider", "external_id", name="uq_payments_provider_external_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tariff_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tariffs.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
