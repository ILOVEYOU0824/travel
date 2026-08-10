"""당일 순서 변경·장소 교체."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.itinerary import ItineraryDayView
from app.schemas.place import Place


class ReorderDayRequest(BaseModel):
    current_itinerary: list[ItineraryDayView]
    day_date: str = Field(..., description="YYYY-MM-DD")
    ordered_place_ids: list[str] = Field(..., min_length=1)
    travel_mode: str = "AUTO"
    language_code: str = "ko"
    arrival_airport_query: str | None = None
    return_departure_jst: str | None = None


class ReorderDayResponse(BaseModel):
    days: list[ItineraryDayView]
    message: str = "순서를 바꾸고 경로를 다시 계산했습니다."


class OptimizeDayRequest(BaseModel):
    current_itinerary: list[ItineraryDayView]
    day_date: str = Field(..., description="YYYY-MM-DD")
    travel_mode: str = "AUTO"
    language_code: str = "ko"
    arrival_airport_query: str | None = None
    return_departure_jst: str | None = None


class OptimizeDayResponse(BaseModel):
    days: list[ItineraryDayView]
    message: str = "장소는 그대로 두고 동선만 최적화한 뒤 경로를 다시 계산했습니다."


class SwapSuggestionsRequest(BaseModel):
    current_itinerary: list[ItineraryDayView]
    day_date: str
    place_id: str
    language_code: str = "ko"
    max_suggestions: int = Field(default=3, ge=1, le=5)


class SwapSuggestionsResponse(BaseModel):
    place_id: str
    category: str
    suggestions: list[Place]
    message: str | None = None


class ApplySwapRequest(BaseModel):
    current_itinerary: list[ItineraryDayView]
    day_date: str
    old_place_id: str
    new_place: Place
    travel_mode: str = "AUTO"
    language_code: str = "ko"
    arrival_airport_query: str | None = None
    return_departure_jst: str | None = None


class ApplySwapResponse(BaseModel):
    days: list[ItineraryDayView]
    message: str = "장소를 바꾸고 경로를 다시 계산했습니다."
