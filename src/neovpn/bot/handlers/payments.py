"""Payment flows: browse tariffs → pick method → Stars/Crypto invoice."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    SuccessfulPayment,
)

from neovpn.bot import keyboards, texts
from neovpn.bot.container import BotDeps
from neovpn.core.errors import (
    PaymentAlreadyProcessedError,
    TariffNotFoundError,
    UserNotFoundError,
)
from neovpn.core.models import PaymentProvider, VpnProtocol
from neovpn.core.use_cases import confirm_payment, purchase_subscription
from neovpn.db import SqlAlchemyUnitOfWork
from neovpn.logging import get_logger

router = Router(name="payments")
log = get_logger(__name__)


@router.callback_query(F.data == keyboards.CB_TARIFFS)
async def on_tariffs(call: CallbackQuery, deps: BotDeps) -> None:
    if call.message is None:
        return
    await call.answer()
    async with SqlAlchemyUnitOfWork(deps.session_factory) as uow:
        tariffs = await uow.tariffs.list_public()
    if not tariffs:
        await call.message.answer(texts.no_tariffs(), reply_markup=keyboards.home_kb())
        return
    await call.message.answer(texts.tariffs_header(), reply_markup=keyboards.tariffs_kb(tariffs))


@router.callback_query(F.data.startswith(f"{keyboards.CB_TARIFF_PICK}:"))
async def on_pick_tariff(call: CallbackQuery, deps: BotDeps) -> None:
    if call.message is None or call.data is None:
        return
    await call.answer()
    slug = call.data.split(":", 1)[1]
    kb = keyboards.payment_methods_kb(
        slug,
        stars=deps.settings.stars_enabled,
        crypto=deps.cryptobot is not None,
    )
    await call.message.answer(texts.choose_payment(), reply_markup=kb)


# ---------------------------------------------------------------------------
# Telegram Stars
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith(f"{keyboards.CB_PAY_STARS}:"))
async def on_pay_stars(call: CallbackQuery, deps: BotDeps) -> None:
    if call.from_user is None or call.message is None or call.data is None:
        return
    await call.answer()
    slug = call.data.split(":", 1)[1]
    try:
        async with SqlAlchemyUnitOfWork(deps.session_factory) as uow:
            user = await uow.users.get_by_tg_id(call.from_user.id)
            if user is None:
                await call.message.answer(texts.error_generic())
                return
            payment = await purchase_subscription(
                uow,
                user_id=user.id,
                tariff_slug=slug,
                provider=PaymentProvider.TELEGRAM_STARS,
            )
            tariff = await uow.tariffs.get(payment.tariff_id)
            if tariff is None:
                await call.message.answer(texts.error_generic())
                return
            external_id, _ = await deps.stars.create_invoice(
                user=user, tariff=tariff, amount=payment.amount
            )
    except TariffNotFoundError:
        await call.message.answer("Тариф не найден.", reply_markup=keyboards.home_kb())
        return

    async with SqlAlchemyUnitOfWork(deps.session_factory) as uow:
        await uow.payments.set_external_id(payment.id, external_id)

    invoice = deps.stars.invoice_payload(
        tariff=tariff, amount=payment.amount, external_id=external_id
    )
    prices_raw = invoice["prices"]
    assert isinstance(prices_raw, list)
    await call.message.answer_invoice(
        title=str(invoice["title"]),
        description=str(invoice["description"]),
        payload=str(invoice["payload"]),
        currency=str(invoice["currency"]),
        prices=[LabeledPrice(**p) for p in prices_raw],
        provider_token="",  # Telegram Stars => empty provider token
    )


@router.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery) -> None:
    # Stars payments don't carry a meaningful validation step; we always accept.
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message, deps: BotDeps) -> None:
    if message.successful_payment is None or message.from_user is None:
        return
    sp: SuccessfulPayment = message.successful_payment
    external_id = sp.invoice_payload
    async with SqlAlchemyUnitOfWork(deps.session_factory) as uow:
        try:
            _, _, key = await confirm_payment(
                uow,
                panels=deps.panels,
                provider=PaymentProvider.TELEGRAM_STARS,
                external_id=external_id,
                protocol=VpnProtocol.VLESS_REALITY,
            )
        except PaymentAlreadyProcessedError:
            return
        except (TariffNotFoundError, UserNotFoundError) as exc:
            log.warning("stars.confirm_failed", reason=str(exc))
            await message.answer(texts.error_generic())
            return
        tariff = await uow.tariffs.get(key.subscription_id)

    await message.answer(texts.payment_success())
    await message.answer(texts.key_card(key, tariff=tariff), disable_web_page_preview=True)


# ---------------------------------------------------------------------------
# CryptoBot
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith(f"{keyboards.CB_PAY_CRYPTO}:"))
async def on_pay_crypto(call: CallbackQuery, deps: BotDeps) -> None:
    if (
        call.from_user is None
        or call.message is None
        or call.data is None
        or deps.cryptobot is None
    ):
        if call.message is not None:
            await call.message.answer(
                "Крипто-оплата пока не настроена.", reply_markup=keyboards.home_kb()
            )
        return
    await call.answer()
    slug = call.data.split(":", 1)[1]
    try:
        async with SqlAlchemyUnitOfWork(deps.session_factory) as uow:
            user = await uow.users.get_by_tg_id(call.from_user.id)
            if user is None:
                await call.message.answer(texts.error_generic())
                return
            payment = await purchase_subscription(
                uow,
                user_id=user.id,
                tariff_slug=slug,
                provider=PaymentProvider.CRYPTOBOT,
            )
            tariff = await uow.tariffs.get(payment.tariff_id)
    except TariffNotFoundError:
        await call.message.answer("Тариф не найден.", reply_markup=keyboards.home_kb())
        return

    assert tariff is not None
    external_id, pay_url = await deps.cryptobot.create_invoice(
        user=user,
        tariff=tariff,
        amount=payment.amount,
        return_url=f"https://t.me/{deps.settings.bot_username}",
    )
    async with SqlAlchemyUnitOfWork(deps.session_factory) as uow:
        await uow.payments.set_external_id(payment.id, external_id)

    await call.message.answer(
        texts.payment_link(pay_url),
        reply_markup=keyboards.pay_url_kb(pay_url),
    )
