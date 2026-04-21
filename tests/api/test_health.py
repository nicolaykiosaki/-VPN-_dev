"""Smoke test for the FastAPI app."""

from __future__ import annotations

import httpx
import pytest

from neovpn.api.app import create_app


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
