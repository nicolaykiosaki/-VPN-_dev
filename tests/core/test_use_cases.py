"""Behavioural tests for the core use-cases."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from neovpn.core.errors import (
    AlreadyHasTrialError,
    NoAvailableNodeError,
    PaymentAlreadyProcessedError,
    TariffNotFoundError,
)
from neovpn.core.models import (
    Node,
    PaymentProvider,
    PaymentStatus,
    Tariff,
    TariffKind,
    VpnProtocol,
)
from neovpn.core.use_cases import (
    confirm_payment,
    purchase_subscription,
    register_user_from_tg,
    start_trial,
)
from tests.core.fakes import FakePanel, FakeUnitOfWork


@pytest.fixture()
def trial_tariff() -> Tariff:
    return Tariff(
        slug="trial-3d",
        name="Пробный",
        kind=TariffKind.TRIAL,
        duration_days=3,
        traffic_gb=10,
        is_public=False,
    )


@pytest.fixture()
def paid_tariff() -> Tariff:
    return Tariff(
        slug="m1",
        name="Месяц",
        kind=TariffKind.PAID,
        duration_days=30,
        traffic_gb=100,
        price_rub=Decimal("199"),
        price_stars=150,
        price_usdt=Decimal("2.49"),
    )


@pytest.fixture()
def node() -> Node:
    return Node(slug="de-1", region="DE", host="de1.example.com")


async def test_register_user_creates_new_user() -> None:
    uow = FakeUnitOfWork()
    user = await register_user_from_tg(
        uow,
        tg_id=42,
        username="alice",
        first_name="Alice",
        language_code="en",
    )
    assert user.tg_id == 42
    assert uow.commits == 1
    again = await register_user_from_tg(
        uow,
        tg_id=42,
        username="alice2",
        first_name="Alice2",
        language_code="en",
    )
    assert again.id == user.id
    assert again.username == "alice2"


async def test_start_trial_issues_key(
    trial_tariff: Tariff, node: Node
) -> None:
    uow = FakeUnitOfWork()
    uow.seed(tariffs=[trial_tariff], nodes=[node])
    user = await register_user_from_tg(
        uow, tg_id=1, username=None, first_name=None, language_code=None
    )
    panel = FakePanel()
    sub, key = await start_trial(
        uow,
        panels={node.id: panel},
        user_id=user.id,
        protocol=VpnProtocol.VLESS_REALITY,
    )
    assert sub.tariff_id == trial_tariff.id
    assert key.subscription_id == sub.id
    assert key.config_url.startswith("vless://")
    assert len(panel.created) == 1


async def test_start_trial_twice_fails(trial_tariff: Tariff, node: Node) -> None:
    uow = FakeUnitOfWork()
    uow.seed(tariffs=[trial_tariff], nodes=[node])
    user = await register_user_from_tg(
        uow, tg_id=1, username=None, first_name=None, language_code=None
    )
    panel = FakePanel()
    await start_trial(uow, panels={node.id: panel}, user_id=user.id)
    with pytest.raises(AlreadyHasTrialError):
        await start_trial(uow, panels={node.id: panel}, user_id=user.id)


async def test_start_trial_without_node_fails(trial_tariff: Tariff) -> None:
    uow = FakeUnitOfWork()
    uow.seed(tariffs=[trial_tariff])
    user = await register_user_from_tg(
        uow, tg_id=1, username=None, first_name=None, language_code=None
    )
    with pytest.raises(NoAvailableNodeError):
        await start_trial(uow, panels={}, user_id=user.id)


async def test_purchase_subscription_creates_pending_payment(
    paid_tariff: Tariff,
) -> None:
    uow = FakeUnitOfWork()
    uow.seed(tariffs=[paid_tariff])
    user = await register_user_from_tg(
        uow, tg_id=1, username=None, first_name=None, language_code=None
    )
    payment = await purchase_subscription(
        uow,
        user_id=user.id,
        tariff_slug=paid_tariff.slug,
        provider=PaymentProvider.TELEGRAM_STARS,
    )
    assert payment.status is PaymentStatus.PENDING
    assert payment.amount.currency == "STARS"
    assert payment.amount.amount == paid_tariff.price_stars


async def test_purchase_unknown_tariff_fails(paid_tariff: Tariff) -> None:
    uow = FakeUnitOfWork()
    uow.seed(tariffs=[paid_tariff])
    user = await register_user_from_tg(
        uow, tg_id=1, username=None, first_name=None, language_code=None
    )
    with pytest.raises(TariffNotFoundError):
        await purchase_subscription(
            uow,
            user_id=user.id,
            tariff_slug="nope",
            provider=PaymentProvider.TELEGRAM_STARS,
        )


async def test_confirm_payment_activates_subscription(
    paid_tariff: Tariff, node: Node
) -> None:
    uow = FakeUnitOfWork()
    uow.seed(tariffs=[paid_tariff], nodes=[node])
    user = await register_user_from_tg(
        uow, tg_id=1, username=None, first_name=None, language_code=None
    )
    panel = FakePanel()
    payment = await purchase_subscription(
        uow,
        user_id=user.id,
        tariff_slug=paid_tariff.slug,
        provider=PaymentProvider.CRYPTOBOT,
    )
    await uow.payments.set_external_id(payment.id, "invoice-123")
    confirmed, sub, key = await confirm_payment(
        uow,
        panels={node.id: panel},
        provider=PaymentProvider.CRYPTOBOT,
        external_id="invoice-123",
    )
    assert confirmed.status is PaymentStatus.PAID
    assert confirmed.paid_at is not None
    assert sub.user_id == user.id
    assert key.subscription_id == sub.id
    now = datetime.now(UTC)
    assert sub.valid_until > now + timedelta(days=paid_tariff.duration_days - 1)


async def test_confirm_payment_is_idempotent(
    paid_tariff: Tariff, node: Node
) -> None:
    uow = FakeUnitOfWork()
    uow.seed(tariffs=[paid_tariff], nodes=[node])
    user = await register_user_from_tg(
        uow, tg_id=1, username=None, first_name=None, language_code=None
    )
    panel = FakePanel()
    payment = await purchase_subscription(
        uow,
        user_id=user.id,
        tariff_slug=paid_tariff.slug,
        provider=PaymentProvider.CRYPTOBOT,
    )
    await uow.payments.set_external_id(payment.id, "invoice-123")
    await confirm_payment(
        uow,
        panels={node.id: panel},
        provider=PaymentProvider.CRYPTOBOT,
        external_id="invoice-123",
    )
    with pytest.raises(PaymentAlreadyProcessedError):
        await confirm_payment(
            uow,
            panels={node.id: panel},
            provider=PaymentProvider.CRYPTOBOT,
            external_id="invoice-123",
        )


async def test_confirm_payment_extends_existing_subscription(
    paid_tariff: Tariff, node: Node
) -> None:
    uow = FakeUnitOfWork()
    uow.seed(tariffs=[paid_tariff], nodes=[node])
    user = await register_user_from_tg(
        uow, tg_id=1, username=None, first_name=None, language_code=None
    )
    panel = FakePanel()
    # First purchase
    p1 = await purchase_subscription(
        uow, user_id=user.id, tariff_slug=paid_tariff.slug,
        provider=PaymentProvider.CRYPTOBOT,
    )
    await uow.payments.set_external_id(p1.id, "inv-1")
    _, sub1, _ = await confirm_payment(
        uow, panels={node.id: panel},
        provider=PaymentProvider.CRYPTOBOT, external_id="inv-1",
    )
    # Second purchase — should extend
    p2 = await purchase_subscription(
        uow, user_id=user.id, tariff_slug=paid_tariff.slug,
        provider=PaymentProvider.CRYPTOBOT,
    )
    await uow.payments.set_external_id(p2.id, "inv-2")
    _, sub2, _ = await confirm_payment(
        uow, panels={node.id: panel},
        provider=PaymentProvider.CRYPTOBOT, external_id="inv-2",
    )
    assert sub2.id == sub1.id
    assert sub2.valid_until > sub1.valid_until
