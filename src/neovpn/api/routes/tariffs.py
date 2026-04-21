"""Public tariff catalogue."""

from __future__ import annotations

from fastapi import APIRouter

from neovpn.api.deps import UowDep
from neovpn.api.schemas import TariffOut

router = APIRouter(prefix="/tariffs", tags=["tariffs"])


@router.get("", response_model=list[TariffOut])
async def list_tariffs(uow: UowDep) -> list[TariffOut]:
    tariffs = await uow.tariffs.list_public()
    return [TariffOut.model_validate(t) for t in tariffs]
