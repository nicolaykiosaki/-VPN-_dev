"""Webhook signature validation for CryptoBot."""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from neovpn.payments.cryptobot import CryptoBotAdapter
from neovpn.payments.errors import PaymentSignatureError


def _sign(secret: str, body: bytes) -> str:
    key = hashlib.sha256(secret.encode()).digest()
    return hmac.new(key, body, hashlib.sha256).hexdigest()


def test_valid_signature_returns_payload() -> None:
    adapter = CryptoBotAdapter(api_token="tkn", webhook_secret="s3cret")
    body = json.dumps({"update_type": "invoice_paid"}).encode()
    sig = _sign("s3cret", body)
    assert adapter.verify_webhook(raw_body=body, signature=sig)["update_type"] == "invoice_paid"


def test_bad_signature_raises() -> None:
    adapter = CryptoBotAdapter(api_token="tkn", webhook_secret="s3cret")
    with pytest.raises(PaymentSignatureError):
        adapter.verify_webhook(raw_body=b"{}", signature="deadbeef")


def test_missing_secret_raises() -> None:
    adapter = CryptoBotAdapter(api_token="tkn", webhook_secret=None)
    with pytest.raises(PaymentSignatureError):
        adapter.verify_webhook(raw_body=b"{}", signature="x")
