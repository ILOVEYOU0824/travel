from typing import Any

from pydantic import BaseModel, Field

from app.schemas.itinerary import ItineraryDayView


class TripSaveRequest(BaseModel):
    title: str = Field(default="내 일본 여행", max_length=120)
    itinerary: list[ItineraryDayView]
    meta: dict[str, Any] = Field(default_factory=dict)


class TripUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    itinerary: list[ItineraryDayView] | None = None
    meta: dict[str, Any] | None = None


class TripRecord(BaseModel):
    id: str
    created_at: str
    updated_at: str
    expires_at: str | None = None
    title: str
    itinerary: list[ItineraryDayView]
    meta: dict[str, Any] = Field(default_factory=dict)
    owner_id: str | None = None
    is_public: bool = True


class TripSummary(BaseModel):
    id: str
    title: str
    created_at: str | None = None
    updated_at: str | None = None
    expires_at: str | None = None
