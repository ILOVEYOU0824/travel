"""기존 일정 place_id는 유지하고 Routes 이동수단만 다시 계산."""

from __future__ import annotations

from app.config import Settings
from app.schemas.itinerary import ItineraryDayView, LlmItineraryDay, LlmItineraryItem, LlmItineraryResponse
from app.schemas.place import Place
from app.services.hydrate_itinerary import hydrate_itinerary


def _days_to_llm(days: list[ItineraryDayView]) -> LlmItineraryResponse:
    out_days: list[LlmItineraryDay] = []
    for day in days:
        items = [
            LlmItineraryItem(
                place_id=it.place.place_id,
                order=it.order,
                time_slot=it.time_slot,
                reason=it.ai_description,
            )
            for it in day.items
        ]
        out_days.append(LlmItineraryDay(date=day.date, items=items))
    return LlmItineraryResponse(days=out_days)


def _places_from_days(days: list[ItineraryDayView]) -> dict[str, Place]:
    by_id: dict[str, Place] = {}
    for day in days:
        for it in day.items:
            p = it.place.model_copy(update={"ai_description": None})
            by_id[p.place_id] = p
        arr = day.arrival_from_airport
        if arr and arr.airport:
            by_id[arr.airport.place_id] = arr.airport
        dep = day.departure_to_airport
        if dep and dep.airport:
            by_id[dep.airport.place_id] = dep.airport
    return by_id


async def recompute_travel_times(
    settings: Settings,
    *,
    days: list[ItineraryDayView],
    travel_mode: str,
    language_code: str = "ko",
    arrival_airport_query: str | None = None,
    return_departure_jst: str | None = None,
) -> list[ItineraryDayView]:
    if not days:
        return []
    places = _places_from_days(days)
    cleaned = _days_to_llm(days)
    arrival_q = arrival_airport_query
    return_jst = return_departure_jst
    if not arrival_q and days[0].arrival_from_airport:
        arrival_q = days[0].arrival_from_airport.airport_query
    if not return_jst and days[-1].departure_to_airport:
        return_jst = days[-1].departure_to_airport.return_departure_jst

    return await hydrate_itinerary(
        settings,
        cleaned,
        places,
        include_travel_times=True,
        travel_mode=travel_mode,
        language_code=language_code,
        day_regions={d.date: (d.region or "") for d in days},
        arrival_airport_query=arrival_q,
        return_departure_jst=return_jst,
    )
