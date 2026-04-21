"""Public API schemas (request/response DTOs)."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class TariffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    duration_days: int
    traffic_gb: int | None
    devices: int
    price_rub: Decimal
    price_stars: int
    price_usdt: Decimal


class HealthOut(BaseModel):
    status: str = "ok"
    version: str


class CryptoBotWebhook(BaseModel):
    """Partial shape of a CryptoBot webhook payload (what we consume)."""

    update_type: str
    payload: dict[str, object]
