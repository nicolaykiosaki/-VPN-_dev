"""Adapter for the Marzban REST API.

Marzban (https://github.com/Gozargah/Marzban) exposes an OAuth2 password flow
for admin authentication and a JSON API for managing users and their inbounds.

Only the endpoints needed for the MVP are implemented here:

* obtain/refresh admin JWT;
* create a user with a subscription URL;
* fetch traffic usage;
* revoke a user.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from neovpn.core.models import VpnProtocol
from neovpn.panels.errors import PanelApiError, PanelAuthError, PanelError

_DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
_TOKEN_SKEW_SECONDS = 60


class MarzbanClient:
    """Thin async client for a single Marzban instance."""

    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        inbounds: dict[VpnProtocol, list[str]] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._inbounds: dict[VpnProtocol, list[str]] = inbounds or {
            VpnProtocol.VLESS_REALITY: ["VLESS TCP REALITY"],
            VpnProtocol.VLESS_WS_TLS: ["VLESS WS TLS"],
            VpnProtocol.SHADOWSOCKS: ["Shadowsocks TCP"],
            VpnProtocol.TROJAN: ["Trojan TCP TLS"],
        }
        self._client = client or httpx.AsyncClient(
            base_url=self._base_url, timeout=_DEFAULT_TIMEOUT
        )
        self._owns_client = client is None
        self._token: str | None = None
        self._token_expires_at: datetime | None = None

    # -- public API ---------------------------------------------------------

    async def health(self) -> bool:
        """Return ``True`` if the panel responds to an authenticated request."""
        try:
            await self._get("/api/system")
        except PanelError:  # pragma: no cover - defensive
            return False
        return True

    async def create_key(
        self,
        *,
        remark: str,
        protocol: VpnProtocol,
        traffic_gb: int | None,
        duration_days: int,
    ) -> tuple[str, str]:
        """Create a Marzban user and return ``(username, subscription_url)``."""
        username = _username_from_remark(remark)
        inbounds = self._inbounds.get(protocol)
        if not inbounds:
            raise PanelApiError(f"no inbound configured for {protocol}")

        expire_ts = int(
            (datetime.now(UTC) + timedelta(days=duration_days)).timestamp()
        )
        data_limit = 0 if traffic_gb is None else int(traffic_gb) * 1024**3
        protocol_key = _marzban_protocol(protocol)

        body: dict[str, Any] = {
            "username": username,
            "proxies": {protocol_key: {}},
            "inbounds": {protocol_key: inbounds},
            "expire": expire_ts,
            "data_limit": data_limit,
            "status": "active",
            "note": remark,
        }
        payload = await self._post("/api/user", body)
        sub_url = payload.get("subscription_url")
        if not isinstance(sub_url, str) or not sub_url:
            raise PanelApiError("marzban response missing subscription_url")
        return username, sub_url

    async def revoke_key(self, external_key_id: str) -> None:
        await self._delete(f"/api/user/{external_key_id}")

    async def traffic_used(self, external_key_id: str) -> int:
        payload = await self._get(f"/api/user/{external_key_id}")
        used = payload.get("used_traffic", 0)
        if not isinstance(used, int):
            raise PanelApiError("marzban response missing used_traffic")
        return used

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> MarzbanClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    # -- internals ----------------------------------------------------------

    async def _ensure_token(self) -> str:
        now = datetime.now(UTC)
        if (
            self._token is not None
            and self._token_expires_at is not None
            and self._token_expires_at - timedelta(seconds=_TOKEN_SKEW_SECONDS) > now
        ):
            return self._token

        response = await self._client.post(
            "/api/admin/token",
            data={"username": self._username, "password": self._password},
        )
        if response.status_code != 200:
            raise PanelAuthError(
                f"marzban auth failed: {response.status_code} {response.text}"
            )
        data = response.json()
        token = data.get("access_token")
        if not isinstance(token, str):
            raise PanelAuthError("marzban auth response missing access_token")
        self._token = token
        # Marzban does not return explicit TTL; assume 24h minus skew.
        self._token_expires_at = now + timedelta(hours=24)
        return token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        token = await self._ensure_token()
        response = await self._client.request(
            method,
            path,
            json=json,
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 401:
            # Token expired mid-flight → refresh once and retry.
            self._token = None
            token = await self._ensure_token()
            response = await self._client.request(
                method,
                path,
                json=json,
                headers={"Authorization": f"Bearer {token}"},
            )
        if response.status_code >= 400:
            raise PanelApiError(
                f"marzban {method} {path} failed: {response.status_code} {response.text}"
            )
        if not response.content:
            return {}
        data = response.json()
        if not isinstance(data, dict):
            raise PanelApiError("marzban returned non-object payload")
        return data

    async def _get(self, path: str) -> dict[str, Any]:
        return await self._request("GET", path)

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", path, json=body)

    async def _delete(self, path: str) -> dict[str, Any]:
        return await self._request("DELETE", path)


def _marzban_protocol(protocol: VpnProtocol) -> str:
    match protocol:
        case VpnProtocol.VLESS_REALITY | VpnProtocol.VLESS_WS_TLS:
            return "vless"
        case VpnProtocol.SHADOWSOCKS:
            return "shadowsocks"
        case VpnProtocol.TROJAN:
            return "trojan"


def _username_from_remark(remark: str) -> str:
    # Marzban usernames must be URL-safe and unique. Take the remark, strip
    # punctuation, append 6 random hex chars for uniqueness.
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in remark)[:20]
    return f"{safe}_{secrets.token_hex(3)}"


__all__ = ["MarzbanClient", "PanelError"]
