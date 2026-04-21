"""Health probe endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from neovpn import __version__
from neovpn.api.schemas import HealthOut

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    return HealthOut(version=__version__)
