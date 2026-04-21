"""Shared pytest fixtures."""

from __future__ import annotations

import os

# Settings require env vars to build.  Tests supply safe defaults here so
# individual test files don't have to duplicate this boilerplate.
os.environ.setdefault("NEOVPN_BOT_TOKEN", "123456:test")
os.environ.setdefault("NEOVPN_JWT_SECRET", "a" * 32)
os.environ.setdefault(
    "NEOVPN_DATABASE_URL", "sqlite+aiosqlite:///:memory:"
)
os.environ.setdefault("NEOVPN_REDIS_URL", "")
