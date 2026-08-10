"""예산 트래커 · 우천 실내 대안 요청 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.itinerary import ItineraryDayView


class BudgetTrackerRequest(BaseModel):
    current_itinerary: list[ItineraryDayView]
    travelers: int = Field(default=1, ge=1, le=20)
    budget_krw_per_person: int | None = None
    budget_krw_total: int | None = None
    budget_tier: str | None = None


class RainAdviceRequest(BaseModel):
    current_itinerary: list[ItineraryDayView]
    start_date: str
    end_date: str
    language_code: str = "ko"
    precip_threshold: int = Field(default=50, ge=30, le=90)
