"""일정 검증·MOCK LLM 단위 테스트."""

from __future__ import annotations

import pytest

from app.schemas.itinerary import (
    CandidatePlaceBrief,
    LlmItineraryDay,
    LlmItineraryItem,
    LlmItineraryResponse,
    TimeSlot,
)
from app.services import mock_claude
from app.services.validate_itinerary import validate_itinerary_response


def test_validate_removes_unknown_place_ids() -> None:
    raw = LlmItineraryResponse(
        days=[
            LlmItineraryDay(
                date="2026-09-10",
                items=[
                    LlmItineraryItem(
                        place_id="real_1",
                        order=1,
                        time_slot=TimeSlot.morning,
                        reason="ok",
                    ),
                    LlmItineraryItem(
                        place_id="HALLUCINATED_PLACE",
                        order=2,
                        time_slot=TimeSlot.lunch,
                        reason="fake",
                    ),
                ],
            )
        ]
    )
    result = validate_itinerary_response(raw, {"real_1"}, expected_dates={"2026-09-10"})
    assert result.ok
    assert result.removed_place_ids == ["HALLUCINATED_PLACE"]
    assert len(result.cleaned.days[0].items) == 1
    assert result.cleaned.days[0].items[0].place_id == "real_1"


def test_validate_fails_when_all_removed() -> None:
    raw = LlmItineraryResponse(
        days=[
            LlmItineraryDay(
                date="2026-09-10",
                items=[
                    LlmItineraryItem(
                        place_id="fake",
                        order=1,
                        time_slot=TimeSlot.morning,
                        reason="x",
                    )
                ],
            )
        ]
    )
    result = validate_itinerary_response(raw, {"real_1"}, expected_dates={"2026-09-10"})
    assert not result.ok
    assert result.cleaned.days[0].items == []


@pytest.mark.asyncio
async def test_MOCK_claude_only_uses_candidate_ids() -> None:
    candidates = [
        CandidatePlaceBrief(
            place_id="a",
            name="A",
            category="attraction",
            lat=34.6,
            lng=135.5,
        ),
        CandidatePlaceBrief(
            place_id="b",
            name="라멘집",
            category="restaurant",
            lat=34.61,
            lng=135.51,
        ),
    ]
    result = await mock_claude.MOCK_generate_itinerary(
        candidates=candidates,
        dates=["2026-09-10", "2026-09-11"],
        day_regions=[
            {"date": "2026-09-10", "region": "오사카"},
            {"date": "2026-09-11", "region": "오사카"},
        ],
        must_have_food=["라멘"],
        must_have_sights=[],
    )
    ids = {c.place_id for c in candidates}
    for day in result.days:
        assert day.items
        assert all(i.place_id in ids for i in day.items)
