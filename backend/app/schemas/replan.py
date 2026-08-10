"""자연어 리플랜 intent / 요청 스키마."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.itinerary import ItineraryDayView, ItineraryGenerateResponse


class IntentType(str, Enum):
    add_food = "add_food"
    add_sight = "add_sight"
    remove_item = "remove_item"
    change_order = "change_order"
    change_date = "change_date"
    unclear = "unclear"


class TravelIntent(BaseModel):
    intent_type: IntentType
    category_query: str | None = None
    must_have: bool = False
    target_day: str | None = None
    raw_text: str


INTENT_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent_type": {
            "type": "string",
            "enum": [
                "add_food",
                "add_sight",
                "remove_item",
                "change_order",
                "change_date",
                "unclear",
            ],
        },
        "category_query": {"type": ["string", "null"]},
        "must_have": {"type": "boolean"},
        "target_day": {"type": ["string", "null"]},
        "raw_text": {"type": "string"},
    },
    "required": ["intent_type", "category_query", "must_have", "target_day", "raw_text"],
    "additionalProperties": False,
}


class ReplanRequest(BaseModel):
    region: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1, description="자연어 요청")
    current_itinerary: list[ItineraryDayView]
    language_code: str = "ko"
    include_travel_times: bool = True
    travel_mode: str = Field(
        default="AUTO",
        description="AUTO면 도보/대중교통 비교, 또는 WALK|TRANSIT|DRIVE",
    )
    max_new_candidates: int = Field(default=15, ge=5, le=20)


class ReplanResponse(ItineraryGenerateResponse):
    intent: TravelIntent
    message: str | None = None
    unchanged: bool = False
