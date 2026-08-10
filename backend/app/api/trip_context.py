"""날씨·축제/뉴스 보조 정보 (일정 타임라인과 분리)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.services.trip_context import TripContextResponse, fetch_trip_context

router = APIRouter(prefix="/trip-context", tags=["trip-context"])


@router.get("", response_model=TripContextResponse)
async def get_trip_context(
    region: str = Query(..., min_length=1, max_length=80),
    start_date: date = Query(...),
    end_date: date = Query(...),
) -> TripContextResponse:
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date가 start_date보다 앞입니다.")
    try:
        return await fetch_trip_context(
            region=region, start_date=start_date, end_date=end_date
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"보조 정보 조회 실패: {exc}") from exc
