"""Errors surfaced by panel adapters."""

from __future__ import annotations


class PanelError(Exception):
    """Base class for VPN panel errors."""


class PanelAuthError(PanelError):
    """Authentication with the panel failed."""


class PanelApiError(PanelError):
    """The panel returned an unexpected response."""
