"""Pure application use-cases.

Each function orchestrates repositories and external ports to fulfil a single
business operation. They take protocols as dependencies so they can be tested
with in-memory fakes (see ``tests/core``).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from neovpn.core.errors import (
    AlreadyHasTrialError,
    NoAvailableNodeError,
    PaymentAlreadyProcessedError,
    SubscriptionExpiredError,
    TariffNotFoundError,
    UserNotFoundError,
)
from neovpn.core.models import (
    Money,
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
from neovpn.core.protocols import PanelClient, UnitOfWork


def _now() -> datetime:
    return datetime.now(UTC)


async def register_user_from_tg(
    uow: UnitOfWork,
    *,
    tg_id: int,
    username: str | None,
    first_name: str | None,
    language_code: str | None,
    referrer_tg_id: int | None = None,
) -> User:
    """Create (or refresh) a user based on Telegram profile data."""
    referrer_id: UUID | None = None
    if referrer_tg_id is not None and referrer_tg_id != tg_id:
        referrer = await uow.users.get_by_tg_id(referrer_tg_id)
        if referrer is not None:
            referrer_id = referrer.id
    user = await uow.users.upsert_from_tg(
        tg_id=tg_id,
        username=username,
        first_name=first_name,
        language_code=language_code,
        referrer_id=referrer_id,
    )
    await uow.commit()
    return user


async def start_trial(
    uow: UnitOfWork,
    panels: dict[UUID, PanelClient],
    *,
    user_id: UUID,
    protocol: VpnProtocol = VpnProtocol.VLESS_REALITY,
) -> tuple[Subscription, VpnKey]:
    """Give the user a trial subscription and issue the first VPN key.

    Raises :class:`AlreadyHasTrialError` if the user already consumed one.
    """
    user = await uow.users.get(user_id)
    if user is None:
        raise UserNotFoundError(str(user_id))

    if await uow.users.has_trial(user_id):
        raise AlreadyHasTrialError(str(user_id))

    tariff = await uow.tariffs.get_trial()
    if tariff is None or tariff.kind is not TariffKind.TRIAL:
        raise TariffNotFoundError("trial")

    now = _now()
    subscription = Subscription(
        user_id=user_id,
        tariff_id=tariff.id,
        status=SubscriptionStatus.ACTIVE,
        valid_from=now,
        valid_until=now + timedelta(days=tariff.duration_days),
    )
    subscription = await uow.subscriptions.create(subscription)

    key = await _issue_key_internal(
        uow=uow,
        panels=panels,
        subscription=subscription,
        tariff=tariff,
        protocol=protocol,
        user=user,
    )
    await uow.commit()
    return subscription, key


async def purchase_subscription(
    uow: UnitOfWork,
    *,
    user_id: UUID,
    tariff_slug: str,
    provider: PaymentProvider,
) -> Payment:
    """Create a pending payment for the requested tariff."""
    user = await uow.users.get(user_id)
    if user is None:
        raise UserNotFoundError(str(user_id))

    tariff = await uow.tariffs.get_by_slug(tariff_slug)
    if tariff is None or tariff.kind is not TariffKind.PAID:
        raise TariffNotFoundError(tariff_slug)

    amount = _amount_for(provider=provider, tariff=tariff)
    payment = Payment(
        user_id=user_id,
        tariff_id=tariff.id,
        provider=provider,
        status=PaymentStatus.PENDING,
        amount=amount,
    )
    payment = await uow.payments.create(payment)
    await uow.commit()
    return payment


async def confirm_payment(
    uow: UnitOfWork,
    panels: dict[UUID, PanelClient],
    *,
    provider: PaymentProvider,
    external_id: str,
    protocol: VpnProtocol = VpnProtocol.VLESS_REALITY,
) -> tuple[Payment, Subscription, VpnKey]:
    """Finalise a successful payment and provision access."""
    payment = await uow.payments.get_by_external_id(provider, external_id)
    if payment is None:
        raise PaymentAlreadyProcessedError(f"unknown external_id={external_id}")
    if payment.status is PaymentStatus.PAID:
        raise PaymentAlreadyProcessedError(f"already paid: {external_id}")

    tariff = await uow.tariffs.get(payment.tariff_id)
    if tariff is None:
        raise TariffNotFoundError(str(payment.tariff_id))
    user = await uow.users.get(payment.user_id)
    if user is None:
        raise UserNotFoundError(str(payment.user_id))

    now = _now()
    existing = await uow.subscriptions.active_for_user(user.id, now)
    same_tariff = next((s for s in existing if s.tariff_id == tariff.id), None)
    if same_tariff is None:
        subscription = await uow.subscriptions.create(
            Subscription(
                user_id=user.id,
                tariff_id=tariff.id,
                status=SubscriptionStatus.ACTIVE,
                valid_from=now,
                valid_until=now + timedelta(days=tariff.duration_days),
            )
        )
    else:
        subscription = await uow.subscriptions.extend(
            same_tariff.id,
            same_tariff.valid_until + timedelta(days=tariff.duration_days),
        )

    key = await _issue_key_internal(
        uow=uow,
        panels=panels,
        subscription=subscription,
        tariff=tariff,
        protocol=protocol,
        user=user,
    )
    payment = await uow.payments.mark(
        payment.id, status=PaymentStatus.PAID, paid_at=now
    )
    await uow.commit()
    return payment, subscription, key


async def issue_additional_key(
    uow: UnitOfWork,
    panels: dict[UUID, PanelClient],
    *,
    subscription_id: UUID,
    protocol: VpnProtocol,
) -> VpnKey:
    """Add another device key to an existing subscription."""
    now = _now()
    subscription = await uow.subscriptions.get(subscription_id)
    if subscription is None or not subscription.is_active_at(now):
        raise SubscriptionExpiredError(str(subscription_id))

    tariff = await uow.tariffs.get(subscription.tariff_id)
    if tariff is None:
        raise TariffNotFoundError(str(subscription.tariff_id))
    user = await uow.users.get(subscription.user_id)
    if user is None:
        raise UserNotFoundError(str(subscription.user_id))

    key = await _issue_key_internal(
        uow=uow,
        panels=panels,
        subscription=subscription,
        tariff=tariff,
        protocol=protocol,
        user=user,
    )
    await uow.commit()
    return key


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _amount_for(*, provider: PaymentProvider, tariff: Tariff) -> Money:
    if provider is PaymentProvider.TELEGRAM_STARS:
        return Money(amount=tariff.price_stars, currency="STARS")
    if provider is PaymentProvider.CRYPTOBOT:
        return Money(amount=tariff.price_usdt, currency="USDT")
    raise ValueError(f"unsupported provider: {provider}")


async def _issue_key_internal(
    *,
    uow: UnitOfWork,
    panels: dict[UUID, PanelClient],
    subscription: Subscription,
    tariff: Tariff,
    protocol: VpnProtocol,
    user: User,
) -> VpnKey:
    nodes = await uow.nodes.list_available()
    if not nodes:
        raise NoAvailableNodeError()
    node = nodes[0]
    panel = panels.get(node.id)
    if panel is None:
        raise NoAvailableNodeError(f"no panel client for node {node.slug}")

    remark = f"neovpn:{user.tg_id}:{subscription.id.hex[:8]}"
    external_id, config_url = await panel.create_key(
        remark=remark,
        protocol=protocol,
        traffic_gb=tariff.traffic_gb,
        duration_days=tariff.duration_days,
    )
    key = VpnKey(
        subscription_id=subscription.id,
        node_id=node.id,
        protocol=protocol,
        remark=remark,
        config_url=config_url,
        status=VpnKeyStatus.ACTIVE,
    )
    # Attach the panel-side id to the remark — simple, no extra field in the MVP.
    key = key.model_copy(update={"remark": f"{remark}#{external_id}"})
    return await uow.keys.create(key)
