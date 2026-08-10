"""식사 동선 반경 필터."""

from __future__ import annotations

from app.schemas.itinerary import CandidatePlaceBrief
from app.services.food_proximity import prune_food_candidates


def test_prune_drops_far_low_rated_must_food_when_near_alt_exists() -> None:
    candidates = [
        CandidatePlaceBrief(
            place_id="sight",
            name="명소",
            category="attraction",
            rating=4.5,
            lat=34.70,
            lng=135.50,
            region="오사카",
        ),
        CandidatePlaceBrief(
            place_id="near_ramen",
            name="근처 라멘",
            category="restaurant",
            rating=4.6,
            lat=34.701,
            lng=135.501,
            region="오사카",
            must_food_queries=["라멘"],
        ),
        CandidatePlaceBrief(
            place_id="far_ramen",
            name="먼 라멘",
            category="restaurant",
            rating=3.2,
            lat=34.90,
            lng=135.80,
            region="오사카",
            must_food_queries=["라멘"],
        ),
    ]
    out = prune_food_candidates(candidates, radius_m=3500, min_rating=3.8)
    ids = {c.place_id for c in out}
    assert "near_ramen" in ids
    assert "far_ramen" not in ids
    assert "sight" in ids
