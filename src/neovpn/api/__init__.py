"""FastAPI application exposing tariffs, payments and webhooks."""

from neovpn.api.app import create_app

__all__ = ["create_app"]
