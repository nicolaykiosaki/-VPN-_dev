"""Inline keyboards for the bot.

Keyboards are deliberately tiny and grid-shaped: 2×N buttons max per row.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from neovpn.core.models import Tariff

# ---- callback data prefixes (kept short on purpose) -----------------------

CB_TRIAL = "trial"
CB_TARIFFS = "tariffs"
CB_KEYS = "keys"
CB_HELP = "help"
CB_REFER = "refer"
CB_TARIFF_PICK = "pick"  # pick:<slug>
CB_PAY_STARS = "pay_s"   # pay_s:<slug>
CB_PAY_CRYPTO = "pay_c"  # pay_c:<slug>
CB_HOME = "home"


def welcome_new_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🎁 Попробовать бесплатно", callback_data=CB_TRIAL)
    b.button(text="💎 Тарифы", callback_data=CB_TARIFFS)
    b.button(text="❓ Что такое VPN", callback_data=CB_HELP)
    b.adjust(1, 1, 1)
    return b.as_markup()


def main_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔑 Мои ключи", callback_data=CB_KEYS)
    b.button(text="💎 Продлить", callback_data=CB_TARIFFS)
    b.button(text="👥 Друзья", callback_data=CB_REFER)
    b.button(text="❓ Помощь", callback_data=CB_HELP)
    b.adjust(2, 2)
    return b.as_markup()


def tariffs_kb(tariffs: list[Tariff]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t in tariffs:
        b.button(
            text=_tariff_label(t),
            callback_data=f"{CB_TARIFF_PICK}:{t.slug}",
        )
    b.button(text="⬅️ Назад", callback_data=CB_HOME)
    b.adjust(1)
    return b.as_markup()


def payment_methods_kb(tariff_slug: str, *, stars: bool, crypto: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if stars:
        b.button(text="⭐ Telegram Stars", callback_data=f"{CB_PAY_STARS}:{tariff_slug}")
    if crypto:
        b.button(text="₮ USDT / TON / BTC", callback_data=f"{CB_PAY_CRYPTO}:{tariff_slug}")
    b.button(text="⬅️ Назад", callback_data=CB_TARIFFS)
    b.adjust(1)
    return b.as_markup()


def pay_url_kb(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Перейти к оплате", url=url)],
            [InlineKeyboardButton(text="🏠 В меню", callback_data=CB_HOME)],
        ]
    )


def home_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🏠 В меню", callback_data=CB_HOME)]]
    )


def _tariff_label(t: Tariff) -> str:
    rub = f"{t.price_rub:.0f}₽" if t.price_rub else ""
    stars = f"{t.price_stars}⭐" if t.price_stars else ""
    usdt = f"{t.price_usdt}$" if t.price_usdt else ""
    tail = " / ".join(x for x in [rub, stars, usdt] if x)
    return f"{t.name} · {tail}" if tail else t.name
