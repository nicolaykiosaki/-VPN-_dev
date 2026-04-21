"""Invariant tests for domain models."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from neovpn.core.models import (
    Money,
    Subscription,
    SubscriptionStatus,
    Tariff,
    TariffKind,
)


def test_money_normalises_currency() -> None:
    m = Money(amount=Decimal("5"), currency="usdt")
    assert m.currency == "USDT"


def test_money_rejects_negative() -> None:
    with pytest.raises(ValidationError):
        Money(amount=Decimal("-1"), currency="USDT")


def test_tariff_rejects_zero_duration() -> None:
    with pytest.raises(ValidationError):
        Tariff(
            slug="bad",
            name="bad",
            duration_days=0,
            devices=1,
        )


def test_subscription_is_active_within_window() -> None:
    now = datetime.now(UTC)
    sub = Subscription(
        user_id=uuid4(),
        tariff_id=uuid4(),
        status=SubscriptionStatus.ACTIVE,
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=1),
    )
    assert sub.is_active_at(now)


def test_subscription_is_not_active_after_expiry() -> None:
    now = datetime.now(UTC)
    sub = Subscription(
        user_id=uuid4(),
        tariff_id=uuid4(),
        status=SubscriptionStatus.ACTIVE,
        valid_from=now - timedelta(days=10),
        valid_until=now - timedelta(days=1),
    )
    assert not sub.is_active_at(now)


def test_tariff_kind_defaults_to_paid() -> None:
    t = Tariff(slug="m1", name="1 month", duration_days=30)
    assert t.kind is TariffKind.PAID
    assert t.is_public is True
