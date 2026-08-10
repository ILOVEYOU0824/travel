"""마지막날 공항 복귀 스키마."""

from __future__ import annotations

from app.schemas.itinerary import AirportDepartureView, ItineraryDayView


def test_day_view_accepts_departure_to_airport() -> None:
    day = ItineraryDayView(
        date="2026-09-12",
        region="오사카",
        items=[],
        departure_to_airport=AirportDepartureView(
            airport_query="간사이 국제공항",
            airport=None,
            travel_from_last=None,
            booking_cta=None,
            return_departure_jst="18:30",
        ),
    )
    assert day.departure_to_airport is not None
    assert day.departure_to_airport.return_departure_jst == "18:30"
    assert day.departure_to_airport.airport_query == "간사이 국제공항"
