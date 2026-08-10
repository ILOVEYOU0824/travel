"""리플랜 intent MOCK / 검증 테스트."""

from __future__ import annotations

import pytest

from app.schemas.itinerary import CandidatePlaceBrief
from app.schemas.replan import IntentType
from app.services import mock_claude


@pytest.mark.asyncio
async def test_MOCK_parse_intent_add_food() -> None:
    intent = await mock_claude.MOCK_parse_intent(
        prompt="라멘 꼭 먹고 싶어",
        available_dates=["2026-09-10"],
    )
    assert intent.intent_type == IntentType.add_food
    assert intent.must_have is True


@pytest.mark.asyncio
async def test_MOCK_parse_intent_unclear() -> None:
    intent = await mock_claude.MOCK_parse_intent(
        prompt="오늘 날씨 어때?",
        available_dates=["2026-09-10"],
    )
    assert intent.intent_type == IntentType.unclear


@pytest.mark.asyncio
async def test_MOCK_replan_adds_only_candidate_id() -> None:
    candidates = [
        CandidatePlaceBrief(
            place_id="keep",
            name="기존",
            category="attraction",
            lat=34.6,
            lng=135.5,
        ),
        CandidatePlaceBrief(
            place_id="new_ramen",
            name="새 라멘",
            category="restaurant",
            lat=34.61,
            lng=135.51,
        ),
    ]
    intent = await mock_claude.MOCK_parse_intent(
        prompt="라멘 먹고 싶어",
        available_dates=["2026-09-10"],
    )
    result = await mock_claude.MOCK_replan_itinerary(
        current_days=[
            {
                "date": "2026-09-10",
                "items": [
                    {
                        "place_id": "keep",
                        "order": 1,
                        "time_slot": "morning",
                        "ai_description": "유지",
                        "place": {"place_id": "keep", "name": "기존"},
                    }
                ],
            }
        ],
        candidates=candidates,
        intent=intent,
        dates=["2026-09-10"],
        region="오사카",
    )
    ids = {i.place_id for d in result.days for i in d.items}
    assert ids <= {"keep", "new_ramen"}
    assert "new_ramen" in ids
