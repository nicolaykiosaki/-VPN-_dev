"""Webhook endpoints for payment providers."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request, status

from neovpn.api.deps import SettingsDep, UowDep
from neovpn.core.errors import PaymentAlreadyProcessedError
from neovpn.core.models import PaymentProvider
from neovpn.core.use_cases import confirm_payment
from neovpn.logging import get_logger
from neovpn.payments.cryptobot import CryptoBotAdapter
from neovpn.payments.errors import PaymentSignatureError

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = get_logger(__name__)


@router.post("/cryptobot", status_code=status.HTTP_200_OK)
async def cryptobot_webhook(
    request: Request,
    uow: UowDep,
    settings: SettingsDep,
    crypto_signature: str = Header(..., alias="crypto-pay-api-signature"),
) -> dict[str, str]:
    if settings.cryptobot_token is None or settings.cryptobot_webhook_secret is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "cryptobot not configured")

    raw = await request.body()
    adapter = CryptoBotAdapter(
        api_token=settings.cryptobot_token.get_secret_value(),
        webhook_secret=settings.cryptobot_webhook_secret.get_secret_value(),
    )
    try:
        payload = adapter.verify_webhook(raw_body=raw, signature=crypto_signature)
    except PaymentSignatureError as exc:
        logger.warning("cryptobot.signature_mismatch", reason=str(exc))
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad signature") from exc

    if payload.get("update_type") != "invoice_paid":
        return {"status": "ignored"}

    invoice = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    invoice_id = invoice.get("invoice_id") if isinstance(invoice, dict) else None
    if invoice_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "missing invoice_id")

    try:
        # The bot layer provisions the key; the API just records payment state.
        # For the MVP we delegate to the same use-case with an empty panel map;
        # the provisioning runs in the bot process, so we treat API-side failure
        # of key creation as a soft error and store paid=True anyway.
        await confirm_payment(
            uow,
            panels={},
            provider=PaymentProvider.CRYPTOBOT,
            external_id=str(invoice_id),
        )
    except PaymentAlreadyProcessedError:
        return {"status": "duplicate"}
    except Exception:  # pragma: no cover — detailed logging only
        logger.exception("cryptobot.webhook_failed", invoice_id=invoice_id)
        raise

    return {"status": "ok"}
