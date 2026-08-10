"""식사 동선 배치 — 첫 슬롯 고정 방지."""

from __future__ import annotations

from app.schemas.itinerary import LlmItineraryDay, LlmItineraryItem, LlmItineraryResponse, TimeSlot
from app.schemas.place import LatLng, Place, PlaceCategory
from app.services.arrange_meal_placement import arrange_meal_placement


def _place(
    pid: str,
    *,
    name: str,
    category: PlaceCategory,
    lat: float,
    lng: float,
    rating: float = 4.5,
) -> Place:
    return Place(
        place_id=pid,
        name=name,
        formatted_address=None,
        location=LatLng(lat=lat, lng=lng),
        rating=rating,
        user_rating_count=100,
        types=[category.value],
        primary_type=category.value,
        category=category,
        google_maps_uri=None,
        opening_hours=None,
        photos=[],
    )


def test_ramen_not_forced_first_morning() -> None:
    """관광 2곳 + 라멘이 morning 첫 순서여도 → 동선 중간·lunch/dinner로."""
    places = {
        "sight_west": _place(
            "sight_west",
            name="서쪽 명소",
            category=PlaceCategory.attraction,
            lat=34.70,
            lng=135.48,
        ),
        "sight_east": _place(
            "sight_east",
            name="동쪽 명소",
            category=PlaceCategory.attraction,
            lat=34.70,
            lng=135.52,
        ),
        "ramen_mid": _place(
            "ramen_mid",
            name="중간 라멘",
            category=PlaceCategory.restaurant,
            lat=34.70,
            lng=135.50,
            rating=4.8,
        ),
    }
    raw = LlmItineraryResponse(
        days=[
            LlmItineraryDay(
                date="2026-09-10",
                items=[
                    LlmItineraryItem(
                        place_id="ramen_mid",
                        order=1,
                        time_slot=TimeSlot.morning,
                        reason="잘못된 첫 배치",
                    ),
                    LlmItineraryItem(
                        place_id="sight_west",
                        order=2,
                        time_slot=TimeSlot.lunch,
                        reason="관광",
                    ),
                    LlmItineraryItem(
                        place_id="sight_east",
                        order=3,
                        time_slot=TimeSlot.afternoon,
                        reason="관광",
                    ),
                ],
            )
        ]
    )
    out = arrange_meal_placement(
        raw,
        places,
        must_have_food=["라멘"],
        food_place_ids={"ramen_mid"},
        dates=["2026-09-10"],
    )
    day = out.days[0]
    assert day.items[0].place_id != "ramen_mid"
    ramen = next(i for i in day.items if i.place_id == "ramen_mid")
    assert ramen.time_slot in (TimeSlot.lunch, TimeSlot.dinner)
    # 동선상 두 명소 사이(중간)에 오는 것이 이상적
    ids = [i.place_id for i in day.items]
    assert ids.index("ramen_mid") not in (0, len(ids) - 1) or len(ids) == 2


def test_meal_only_day_gets_lunch_slot() -> None:
    places = {
        "r1": _place(
            "r1",
            name="라멘",
            category=PlaceCategory.restaurant,
            lat=34.7,
            lng=135.5,
        ),
    }
    raw = LlmItineraryResponse(
        days=[
            LlmItineraryDay(
                date="2026-09-10",
                items=[
                    LlmItineraryItem(
                        place_id="r1",
                        order=1,
                        time_slot=TimeSlot.morning,
                        reason="x",
                    )
                ],
            )
        ]
    )
    out = arrange_meal_placement(
        raw,
        places,
        must_have_food=["라멘"],
        food_place_ids={"r1"},
        dates=["2026-09-10"],
    )
    assert out.days[0].items[0].time_slot in (TimeSlot.lunch, TimeSlot.dinner)
