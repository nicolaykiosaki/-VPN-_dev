"""Domain-level exceptions."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all expected business errors."""


class UserNotFoundError(DomainError):
    """Raised when a Telegram user cannot be resolved."""


class TariffNotFoundError(DomainError):
    """Raised when the requested tariff does not exist."""


class NoAvailableNodeError(DomainError):
    """Raised when no healthy node is available to host a new key."""


class AlreadyHasTrialError(DomainError):
    """Raised when the user already consumed their trial subscription."""


class PaymentAlreadyProcessedError(DomainError):
    """Raised when a payment webhook is delivered more than once."""


class SubscriptionExpiredError(DomainError):
    """Raised when trying to issue a key for an expired subscription."""
