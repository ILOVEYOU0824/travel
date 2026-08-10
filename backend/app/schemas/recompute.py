"""이동수단만 재계산 요청."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.itinerary import ItineraryDayView


class RecomputeTravelRequest(BaseModel):
    current_itinerary: list[ItineraryDayView]
    travel_mode: str = Field(
        default="TRANSIT",
        description="WALK | TRANSIT | DRIVE | AUTO",
    )
    language_code: str = "ko"
    arrival_airport_query: str | None = None
    return_departure_jst: str | None = None


class RecomputeTravelResponse(BaseModel):
    days: list[ItineraryDayView]
    travel_mode: str
    message: str = "이동 경로를 다시 계산했습니다."
