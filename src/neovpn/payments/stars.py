"""Telegram Stars payment adapter.

Telegram Stars invoices are created by the bot via ``sendInvoice`` with an
empty ``provider_token`` (Telegram acts as the provider).  The actual network
call lives in the bot layer; this adapter only produces the payload we need
and a deterministic ``external_id``.
"""

from __future__ import annotations

import secrets

from neovpn.core.models import (
    Money,
    PaymentProvider,
    Tariff,
    User,
)


class TelegramStarsAdapter:
    """Builds Stars invoices the bot then sends to Telegram."""

    provider = PaymentProvider.TELEGRAM_STARS

    async def create_invoice(
        self,
        *,
        user: User,
        tariff: Tariff,
        amount: Money,
        return_url: str | None = None,
    ) -> tuple[str, str]:
        """Return ``(external_id, payload)``.

        ``payload`` is the ``invoice_payload`` string the bot passes to
        :func:`aiogram.Bot.send_invoice`.  The web layer does not consume it.
        """
        if amount.currency != "STARS":
            raise ValueError(f"stars adapter requires STARS currency, got {amount.currency}")
        external_id = f"stars_{user.tg_id}_{tariff.slug}_{secrets.token_hex(6)}"
        return external_id, external_id

    def invoice_payload(
        self, *, tariff: Tariff, amount: Money, external_id: str
    ) -> dict[str, object]:
        """Build the kwargs forwarded to ``bot.send_invoice``."""
        return {
            "title": tariff.name,
            "description": _description(tariff),
            "payload": external_id,
            "currency": "XTR",
            "prices": [{"label": tariff.name, "amount": int(amount.amount)}],
        }


def _description(tariff: Tariff) -> str:
    pieces = [f"{tariff.duration_days} дн."]
    if tariff.traffic_gb is not None:
        pieces.append(f"{tariff.traffic_gb} ГБ")
    else:
        pieces.append("без лимита трафика")
    pieces.append(f"{tariff.devices} устройства")
    return " · ".join(pieces)
