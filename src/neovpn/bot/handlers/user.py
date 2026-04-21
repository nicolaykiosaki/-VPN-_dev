"""Friendly user-facing flows: /start, trial, keys, tariffs browsing, help."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from neovpn.bot import keyboards, texts
from neovpn.bot.container import BotDeps
from neovpn.core.errors import (
    AlreadyHasTrialError,
    NoAvailableNodeError,
    TariffNotFoundError,
    UserNotFoundError,
)
from neovpn.core.models import VpnProtocol
from neovpn.core.use_cases import register_user_from_tg, start_trial
from neovpn.db import SqlAlchemyUnitOfWork
from neovpn.logging import get_logger

router = Router(name="user")
log = get_logger(__name__)


# ---------------------------------------------------------------------------
# /start  (with optional deep-link for referrals: /start r123456)
# ---------------------------------------------------------------------------

@router.message(CommandStart(deep_link=True))
async def start_with_deeplink(message: Message, deps: BotDeps) -> None:
    if message.from_user is None:
        return
    ref_tg_id: int | None = None
    payload = message.text.split(maxsplit=1)[1] if message.text and " " in message.text else ""
    if payload.startswith("r") and payload[1:].isdigit():
        ref_tg_id = int(payload[1:])
    await _do_start(message, deps, referrer_tg_id=ref_tg_id)


@router.message(CommandStart())
async def start_plain(message: Message, deps: BotDeps) -> None:
    await _do_start(message, deps, referrer_tg_id=None)


async def _do_start(message: Message, deps: BotDeps, *, referrer_tg_id: int | None) -> None:
    if message.from_user is None:
        return
    tg = message.from_user
    async with SqlAlchemyUnitOfWork(deps.session_factory) as uow:
        existing = await uow.users.get_by_tg_id(tg.id)
        user = await register_user_from_tg(
            uow,
            tg_id=tg.id,
            username=tg.username,
            first_name=tg.first_name,
            language_code=tg.language_code,
            referrer_tg_id=referrer_tg_id,
        )
    if existing is None:
        await message.answer(
            texts.welcome_new(user.first_name),
            reply_markup=keyboards.welcome_new_kb(),
        )
    else:
        await message.answer(
            texts.welcome_back(user.first_name),
            reply_markup=keyboards.main_menu_kb(),
        )


# ---------------------------------------------------------------------------
# Trial
# ---------------------------------------------------------------------------

@router.callback_query(F.data == keyboards.CB_TRIAL)
async def on_trial(call: CallbackQuery, deps: BotDeps) -> None:
    if call.from_user is None or call.message is None:
        return
    await call.answer()
    async with SqlAlchemyUnitOfWork(deps.session_factory) as uow:
        user = await uow.users.get_by_tg_id(call.from_user.id)
        if user is None:
            await call.message.answer(texts.error_generic())
            return
        try:
            subscription, key = await start_trial(
                uow,
                panels=deps.panels,
                user_id=user.id,
                protocol=VpnProtocol.VLESS_REALITY,
            )
        except AlreadyHasTrialError:
            await call.message.answer(texts.trial_already_taken())
            return
        except (NoAvailableNodeError, TariffNotFoundError, UserNotFoundError) as exc:
            log.warning("trial.failed", reason=str(exc))
            await call.message.answer(texts.error_generic())
            return
        tariff = await uow.tariffs.get(subscription.tariff_id)

    await call.message.answer(
        texts.trial_given(days=tariff.duration_days if tariff else 3),
        reply_markup=keyboards.main_menu_kb(),
    )
    await call.message.answer(
        texts.key_card(key, tariff=tariff),
        disable_web_page_preview=True,
    )


# ---------------------------------------------------------------------------
# Keys list
# ---------------------------------------------------------------------------

@router.callback_query(F.data == keyboards.CB_KEYS)
async def on_keys(call: CallbackQuery, deps: BotDeps) -> None:
    if call.from_user is None or call.message is None:
        return
    await call.answer()
    async with SqlAlchemyUnitOfWork(deps.session_factory) as uow:
        user = await uow.users.get_by_tg_id(call.from_user.id)
        if user is None:
            await call.message.answer(texts.error_generic())
            return
        subscriptions = await uow.subscriptions.list_for_user(user.id)
        if not subscriptions:
            await call.message.answer(
                "У тебя пока нет активных ключей. Жми <b>Попробовать бесплатно</b> 🎁",
                reply_markup=keyboards.welcome_new_kb(),
            )
            return
        for sub in subscriptions:
            tariff = await uow.tariffs.get(sub.tariff_id)
            keys = await uow.keys.list_for_subscription(sub.id)
            for key in keys:
                await call.message.answer(
                    texts.key_card(key, tariff=tariff),
                    disable_web_page_preview=True,
                )


# ---------------------------------------------------------------------------
# Help / tariffs / refer placeholders
# ---------------------------------------------------------------------------

@router.callback_query(F.data == keyboards.CB_HELP)
async def on_help(call: CallbackQuery) -> None:
    await call.answer()
    if call.message is None:
        return
    await call.message.answer(
        "🌐 VPN шифрует интернет-трафик и меняет твой «адрес» на адрес сервера. "
        "Сайты начнут открываться без блокировок, а провайдер не увидит содержимое запросов.\n\n"
        "Подключение — 1 минута: скан QR-кода в приложении V2rayTun/Hiddify.",
        reply_markup=keyboards.home_kb(),
    )


@router.callback_query(F.data == keyboards.CB_REFER)
async def on_refer(call: CallbackQuery, deps: BotDeps) -> None:
    if call.from_user is None or call.message is None:
        return
    await call.answer()
    link = f"https://t.me/{deps.settings.bot_username}?start=r{call.from_user.id}"
    await call.message.answer(
        "👥 <b>Зови друзей</b>\n\n"
        f"Твоя ссылка: {link}\n\n"
        "Когда друг оплатит тариф — тебе автоматически продлится подписка.",
        reply_markup=keyboards.home_kb(),
    )


@router.callback_query(F.data == keyboards.CB_HOME)
async def on_home(call: CallbackQuery) -> None:
    await call.answer()
    if call.message is None:
        return
    await call.message.answer(
        texts.welcome_back(call.from_user.first_name if call.from_user else None),
        reply_markup=keyboards.main_menu_kb(),
    )
