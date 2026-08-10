from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.services.klook_links import affiliate_status
from app.services.rail_cta import AIRPORT_OPTIONS

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/airports")
async def list_arrival_airports() -> list[dict[str, str]]:
    """도착 공항 선택 옵션 — Places 검색어만 (좌표 하드코딩 없음)."""
    return AIRPORT_OPTIONS


@router.get("/affiliate")
async def get_affiliate_status(settings: Settings = Depends(get_settings)) -> dict[str, str | bool]:
    """Klook CTA가 Travelpayouts로 래핑되는지 여부 (키·마커 노출 없음)."""
    return affiliate_status(settings)
