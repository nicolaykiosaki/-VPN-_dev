"""Payment-layer errors."""

from __future__ import annotations


class PaymentError(Exception):
    """Base class for payment adapter errors."""


class PaymentApiError(PaymentError):
    """Provider returned an unexpected response."""


class PaymentSignatureError(PaymentError):
    """Webhook signature failed to validate."""
