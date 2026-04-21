"""All user-facing strings live here.

Keeping copy isolated makes localisation trivial and prevents markup drift.
"""

from __future__ import annotations

from neovpn.core.models import Tariff, VpnKey


def welcome_new(first_name: str | None) -> str:
    name = first_name or "друг"
    return (
        f"👋 Привет, {name}!\n\n"
        "Это бот NeoVPN. Жми <b>«Попробовать бесплатно»</b> — получишь "
        "личный ключ за 10 секунд.\n\n"
        "Без настроек и мануалов — просто скан QR-кода."
    )


def welcome_back(first_name: str | None) -> str:
    name = first_name or "друг"
    return f"С возвращением, {name} 👋\nЧто делаем?"


def trial_given(days: int) -> str:
    return (
        f"✨ <b>Готово!</b> Твой пробный ключ на {days} дня активен.\n\n"
        "Скан QR-кода — и ты в интернете без ограничений.\n"
        "Дальше — выбери, какая ОС у тебя."
    )


def trial_already_taken() -> str:
    return (
        "Ты уже использовал пробный период 😊\n"
        "Оформи подписку — получишь ключ сразу же."
    )


def key_card(key: VpnKey, tariff: Tariff | None = None) -> str:
    title = tariff.name if tariff else "Активный ключ"
    traffic_line = (
        f"\n📊 Трафик: {tariff.traffic_gb} ГБ" if tariff and tariff.traffic_gb else ""
    )
    return (
        f"🔑 <b>{title}</b>{traffic_line}\n\n"
        f"<code>{key.config_url}</code>\n\n"
        "Нажми «Как подключиться» — покажу пошагово."
    )


def tariffs_header() -> str:
    return "💎 <b>Тарифы</b>\n\nВыбери срок — а способ оплаты спросим на следующем шаге."


def no_tariffs() -> str:
    return "Тарифы пока не настроены. Напиши админу — он включит быстро 🙂"


def choose_payment() -> str:
    return "Как удобнее оплатить?"


def payment_link(url: str) -> str:
    return f"Ссылка на оплату: {url}\nПосле подтверждения ключ придёт прямо сюда."


def payment_success() -> str:
    return "💚 Оплата получена! Держи новый ключ ⬇️"


def error_generic() -> str:
    return "🙈 Что-то пошло не так. Попробуй ещё раз через минуту."
