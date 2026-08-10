"""Place → LLM 후보 brief 변환 (생성/리플랜 공용)."""

from __future__ import annotations

from app.schemas.itinerary import CandidatePlaceBrief
from app.schemas.place import Place


def place_to_brief(
    p: Place,
    region: str | None = None,
    *,
    must_food_queries: list[str] | None = None,
) -> CandidatePlaceBrief:
    return CandidatePlaceBrief(
        place_id=p.place_id,
        name=p.name,
        category=p.category.value,
        rating=p.rating,
        lat=p.location.lat,
        lng=p.location.lng,
        region=region,
        price_level=p.price_level,
        must_food_queries=list(must_food_queries or []),
    )
