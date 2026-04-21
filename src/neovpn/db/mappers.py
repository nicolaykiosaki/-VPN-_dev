"""Bidirectional mapping between ORM rows and domain models."""

from __future__ import annotations

from neovpn.core.models import (
    Money,
    Node,
    NodeStatus,
    Payment,
    PaymentProvider,
    PaymentStatus,
    Subscription,
    SubscriptionStatus,
    Tariff,
    TariffKind,
    User,
    VpnKey,
    VpnKeyStatus,
    VpnProtocol,
)
from neovpn.db.models import (
    NodeRow,
    PaymentRow,
    SubscriptionRow,
    TariffRow,
    UserRow,
    VpnKeyRow,
)


def user_from_row(row: UserRow) -> User:
    return User(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        tg_id=row.tg_id,
        username=row.username,
        first_name=row.first_name,
        language_code=row.language_code,
        referrer_id=row.referrer_id,
        is_banned=row.is_banned,
        email=row.email,
    )


def tariff_from_row(row: TariffRow) -> Tariff:
    return Tariff(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        slug=row.slug,
        name=row.name,
        kind=TariffKind(row.kind),
        duration_days=row.duration_days,
        traffic_gb=row.traffic_gb,
        devices=row.devices,
        price_rub=row.price_rub,
        price_stars=row.price_stars,
        price_usdt=row.price_usdt,
        is_public=row.is_public,
    )


def subscription_from_row(row: SubscriptionRow) -> Subscription:
    return Subscription(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        user_id=row.user_id,
        tariff_id=row.tariff_id,
        status=SubscriptionStatus(row.status),
        valid_from=row.valid_from,
        valid_until=row.valid_until,
    )


def node_from_row(row: NodeRow) -> Node:
    return Node(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        slug=row.slug,
        region=row.region,
        panel_type=row.panel_type,
        host=row.host,
        status=NodeStatus(row.status),
        is_public=row.is_public,
    )


def key_from_row(row: VpnKeyRow) -> VpnKey:
    return VpnKey(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        subscription_id=row.subscription_id,
        node_id=row.node_id,
        protocol=VpnProtocol(row.protocol),
        remark=row.remark,
        config_url=row.config_url,
        traffic_used_bytes=row.traffic_used_bytes,
        status=VpnKeyStatus(row.status),
    )


def payment_from_row(row: PaymentRow) -> Payment:
    return Payment(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        user_id=row.user_id,
        tariff_id=row.tariff_id,
        provider=PaymentProvider(row.provider),
        status=PaymentStatus(row.status),
        amount=Money(amount=row.amount, currency=row.currency),
        external_id=row.external_id,
        paid_at=row.paid_at,
    )
