"""귀국일(마지막 날) 숙소 제거 — LLM이 넣어도 서버에서 강제 제외."""

from __future__ import annotations

from app.schemas.itinerary import LlmItineraryDay, LlmItineraryResponse
from app.schemas.place import Place, PlaceCategory


def strip_lodging_on_last_day(
    response: LlmItineraryResponse,
    places_by_id: dict[str, Place],
    dates: list[str],
) -> LlmItineraryResponse:
    if not dates:
        return response
    last = dates[-1]
    cleaned_days: list[LlmItineraryDay] = []
    for day in response.days:
        items = list(day.items)
        if day.date == last:
            items = [
                it
                for it in items
                if places_by_id.get(it.place_id) is None
                or places_by_id[it.place_id].category != PlaceCategory.lodging
            ]
            for i, it in enumerate(items, start=1):
                it.order = i
        cleaned_days.append(LlmItineraryDay(date=day.date, items=items))
    return LlmItineraryResponse(days=cleaned_days)
