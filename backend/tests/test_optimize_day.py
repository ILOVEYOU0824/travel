"""장소 고정 동선 최적화 — place_id 집합 불변, 숙소 마지막."""

from app.schemas.itinerary import ItineraryDayView, ItineraryItemView, TimeSlot
from app.schemas.place import LatLng, Place, PlaceCategory
from app.services.edit_day import optimize_day_order


def _place(pid: str, cat: PlaceCategory, lat: float, lng: float, rating: float = 4.0) -> Place:
    return Place(
        place_id=pid,
        name=pid,
        formatted_address=None,
        location=LatLng(lat=lat, lng=lng),
        rating=rating,
        user_rating_count=10,
        types=[],
        primary_type=None,
        category=cat,
        google_maps_uri=None,
        opening_hours=None,
        photos=[],
        price_level=None,
        ai_description=None,
    )


def _item(place: Place, order: int, slot: TimeSlot) -> ItineraryItemView:
    return ItineraryItemView(
        place=place,
        order=order,
        time_slot=slot,
        ai_description="t",
        travel_from_previous=None,
    )


def test_optimize_keeps_ids_and_lodging_last() -> None:
    a = _place("a", PlaceCategory.attraction, 34.70, 135.50, 4.5)
    b = _place("b", PlaceCategory.attraction, 34.69, 135.51, 4.0)
    c = _place("c", PlaceCategory.restaurant, 34.695, 135.505, 4.2)
    h = _place("h", PlaceCategory.lodging, 34.68, 135.49, 4.0)
    day = ItineraryDayView(
        date="2026-09-10",
        region="오사카",
        items=[
            _item(h, 1, TimeSlot.evening),
            _item(b, 2, TimeSlot.morning),
            _item(c, 3, TimeSlot.lunch),
            _item(a, 4, TimeSlot.afternoon),
        ],
    )
    ordered = optimize_day_order([day], day_date="2026-09-10")
    assert set(ordered) == {"a", "b", "c", "h"}
    assert ordered[-1] == "h"
    assert "c" in ordered[:-1]
