"""예산 트래커 — Exact 원화 추정 없음."""

from __future__ import annotations

from app.schemas.itinerary import ItineraryDayView, ItineraryItemView, TimeSlot
from app.schemas.place import LatLng, Place, PlaceCategory
from app.services.budget_summary import build_budget_tracker


def test_budget_tracker_alignment() -> None:
    day = ItineraryDayView(
        date="2026-09-10",
        region="오사카",
        items=[
            ItineraryItemView(
                place=Place(
                    place_id="r1",
                    name="식당",
                    location=LatLng(lat=34.7, lng=135.5),
                    category=PlaceCategory.restaurant,
                    price_level=2,
                ),
                order=1,
                time_slot=TimeSlot.lunch,
                ai_description="x",
            ),
            ItineraryItemView(
                place=Place(
                    place_id="r2",
                    name="고급",
                    location=LatLng(lat=34.7, lng=135.5),
                    category=PlaceCategory.restaurant,
                    price_level=4,
                ),
                order=2,
                time_slot=TimeSlot.dinner,
                ai_description="x",
            ),
        ],
    )
    # 1인 총 120만 / 1일 → premium (per_day >= 180k) wait 1 day 1.2M = premium
    out = build_budget_tracker(
        [day],
        travelers=1,
        budget_krw_per_person=1_200_000,
    )
    assert out.priced_places == 2
    assert out.preferred_price_levels
    assert "Exact" in out.note or "가격대" in out.note
