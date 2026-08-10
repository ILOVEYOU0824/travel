"""당일 순서 변경 단위 테스트."""

from __future__ import annotations

from app.schemas.itinerary import ItineraryDayView, ItineraryItemView, TimeSlot
from app.schemas.place import LatLng, Place, PlaceCategory
from app.services.edit_day import reorder_day_items


def _place(pid: str, cat: PlaceCategory = PlaceCategory.attraction) -> Place:
    return Place(
        place_id=pid,
        name=pid,
        location=LatLng(lat=34.7, lng=135.5),
        category=cat,
    )


def _item(pid: str, order: int, slot: TimeSlot, cat: PlaceCategory = PlaceCategory.attraction) -> ItineraryItemView:
    return ItineraryItemView(
        place=_place(pid, cat),
        order=order,
        time_slot=slot,
        ai_description="x",
        travel_from_previous=None,
    )


def test_reorder_day_items() -> None:
    days = [
        ItineraryDayView(
            date="2026-09-10",
            region="오사카",
            items=[
                _item("a", 1, TimeSlot.morning),
                _item("b", 2, TimeSlot.lunch),
                _item("c", 3, TimeSlot.afternoon),
            ],
        )
    ]
    out = reorder_day_items(
        days, day_date="2026-09-10", ordered_place_ids=["c", "a", "b"]
    )
    ids = [it.place.place_id for it in out[0].items]
    assert ids == ["c", "a", "b"]
    assert [it.order for it in out[0].items] == [1, 2, 3]
