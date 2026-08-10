"""귀국일 숙소 제거 단위 테스트."""

from app.schemas.itinerary import LlmItineraryDay, LlmItineraryItem, LlmItineraryResponse, TimeSlot
from app.schemas.place import LatLng, Place, PlaceCategory
from app.services.strip_last_day_lodging import strip_lodging_on_last_day


def test_strip_lodging_only_on_last_day() -> None:
    places = {
        "hotel": Place(
            place_id="hotel",
            name="호텔",
            location=LatLng(lat=34.6, lng=135.5),
            category=PlaceCategory.lodging,
        ),
        "sight": Place(
            place_id="sight",
            name="관광",
            location=LatLng(lat=34.61, lng=135.51),
            category=PlaceCategory.attraction,
        ),
    }
    raw = LlmItineraryResponse(
        days=[
            LlmItineraryDay(
                date="2026-09-10",
                items=[
                    LlmItineraryItem(
                        place_id="sight", order=1, time_slot=TimeSlot.morning, reason="a"
                    ),
                    LlmItineraryItem(
                        place_id="hotel", order=2, time_slot=TimeSlot.evening, reason="b"
                    ),
                ],
            ),
            LlmItineraryDay(
                date="2026-09-11",
                items=[
                    LlmItineraryItem(
                        place_id="sight", order=1, time_slot=TimeSlot.morning, reason="c"
                    ),
                    LlmItineraryItem(
                        place_id="hotel", order=2, time_slot=TimeSlot.evening, reason="d"
                    ),
                ],
            ),
        ]
    )
    cleaned = strip_lodging_on_last_day(raw, places, ["2026-09-10", "2026-09-11"])
    assert [i.place_id for i in cleaned.days[0].items] == ["sight", "hotel"]
    assert [i.place_id for i in cleaned.days[1].items] == ["sight"]
