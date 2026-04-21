"""HTTP-level tests for :class:`MarzbanClient`."""

from __future__ import annotations

import httpx
import pytest

from neovpn.core.models import VpnProtocol
from neovpn.panels.errors import PanelApiError, PanelAuthError
from neovpn.panels.marzban import MarzbanClient


def _mock_transport(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url="https://panel.test", transport=handler)


async def test_token_obtained_and_user_created() -> None:
    calls: list[tuple[str, str]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append((req.method, req.url.path))
        if req.url.path == "/api/admin/token":
            return httpx.Response(200, json={"access_token": "tok"})
        if req.url.path == "/api/user" and req.method == "POST":
            return httpx.Response(
                200,
                json={
                    "username": "u",
                    "subscription_url": "https://panel.test/sub/abc",
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = MarzbanClient(
        base_url="https://panel.test",
        username="admin",
        password="pw",
        client=_mock_transport(transport),
    )
    try:
        ext_id, url = await client.create_key(
            remark="test",
            protocol=VpnProtocol.VLESS_REALITY,
            traffic_gb=10,
            duration_days=30,
        )
    finally:
        await client.close()
    assert url == "https://panel.test/sub/abc"
    assert ext_id.startswith("test_")
    assert ("POST", "/api/admin/token") in calls
    assert ("POST", "/api/user") in calls


async def test_auth_failure_raises() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="bad creds")

    client = MarzbanClient(
        base_url="https://panel.test",
        username="admin",
        password="pw",
        client=_mock_transport(httpx.MockTransport(handler)),
    )
    try:
        with pytest.raises(PanelAuthError):
            await client.create_key(
                remark="x",
                protocol=VpnProtocol.VLESS_REALITY,
                traffic_gb=None,
                duration_days=30,
            )
    finally:
        await client.close()


async def test_missing_subscription_url_raises() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/api/admin/token":
            return httpx.Response(200, json={"access_token": "tok"})
        return httpx.Response(200, json={"username": "u"})

    client = MarzbanClient(
        base_url="https://panel.test",
        username="admin",
        password="pw",
        client=_mock_transport(httpx.MockTransport(handler)),
    )
    try:
        with pytest.raises(PanelApiError):
            await client.create_key(
                remark="x",
                protocol=VpnProtocol.VLESS_REALITY,
                traffic_gb=None,
                duration_days=30,
            )
    finally:
        await client.close()
