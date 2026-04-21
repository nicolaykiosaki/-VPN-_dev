"""CryptoBot (https://help.crypt.bot/crypto-pay-api) payment adapter."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx

from neovpn.core.models import (
    Money,
    PaymentProvider,
    Tariff,
    User,
)
from neovpn.payments.errors import PaymentApiError, PaymentSignatureError

_API_URL = "https://pay.crypt.bot/api"


class CryptoBotAdapter:
    """Creates invoices via CryptoBot and validates webhook signatures."""

    provider = PaymentProvider.CRYPTOBOT

    def __init__(
        self,
        *,
        api_token: str,
        webhook_secret: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token = api_token
        self._webhook_secret = webhook_secret
        self._client = client or httpx.AsyncClient(base_url=_API_URL, timeout=10.0)
        self._owns_client = client is None

    async def create_invoice(
        self,
        *,
        user: User,
        tariff: Tariff,
        amount: Money,
        return_url: str | None,
    ) -> tuple[str, str]:
        if amount.currency not in {"USDT", "TON", "BTC", "ETH"}:
            raise ValueError(f"unsupported crypto currency: {amount.currency}")
        body: dict[str, Any] = {
            "asset": amount.currency,
            "amount": f"{amount.amount:f}",
            "description": f"{tariff.name} · @{user.username or user.tg_id}",
            "hidden_message": "Спасибо! Ключ придёт в бота сразу после подтверждения.",
            "payload": f"{user.id}:{tariff.slug}",
            "allow_comments": False,
        }
        if return_url is not None:
            body["paid_btn_name"] = "openBot"
            body["paid_btn_url"] = return_url
        data = await self._request("POST", "/createInvoice", body)
        invoice = data.get("result", {})
        invoice_id = invoice.get("invoice_id")
        pay_url = invoice.get("pay_url") or invoice.get("bot_invoice_url")
        if not invoice_id or not pay_url:
            raise PaymentApiError(f"unexpected CryptoBot payload: {data}")
        return str(invoice_id), str(pay_url)

    def verify_webhook(self, *, raw_body: bytes, signature: str) -> dict[str, Any]:
        """Validate a webhook signature and return the parsed payload."""
        if not self._webhook_secret:
            raise PaymentSignatureError("webhook secret not configured")
        secret = hashlib.sha256(self._webhook_secret.encode()).digest()
        digest = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(digest, signature):
            raise PaymentSignatureError("signature mismatch")
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as exc:  # pragma: no cover
            raise PaymentApiError("invalid JSON in webhook") from exc
        if not isinstance(payload, dict):
            raise PaymentApiError("webhook payload must be an object")
        return payload

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _request(
        self, method: str, path: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        response = await self._client.request(
            method,
            path,
            json=body,
            headers={"Crypto-Pay-API-Token": self._token},
        )
        if response.status_code >= 400:
            raise PaymentApiError(
                f"cryptobot {method} {path} failed: "
                f"{response.status_code} {response.text}"
            )
        data = response.json()
        if not isinstance(data, dict) or not data.get("ok"):
            raise PaymentApiError(f"cryptobot returned error: {data}")
        return data
