"""예산 티어·priceLevel 파싱 테스트."""

from __future__ import annotations

from app.schemas.place import parse_price_level, place_from_google_payload
from app.services.budget_tier import resolve_budget_plan


def test_parse_price_level_enums() -> None:
    assert parse_price_level("PRICE_LEVEL_INEXPENSIVE") == 1
    assert parse_price_level("PRICE_LEVEL_MODERATE") == 2
    assert parse_price_level("PRICE_LEVEL_EXPENSIVE") == 3
    assert parse_price_level("PRICE_LEVEL_VERY_EXPENSIVE") == 4
    assert parse_price_level(None) is None
    assert parse_price_level("UNKNOWN") is None
    assert parse_price_level(2) == 2
    assert parse_price_level(9) is None


def test_place_from_google_payload_price_level() -> None:
    place = place_from_google_payload(
        {
            "id": "abc",
            "displayName": {"text": "테스트 호텔"},
            "formattedAddress": "Osaka",
            "location": {"latitude": 34.6, "longitude": 135.5},
            "types": ["lodging"],
            "primaryType": "lodging",
            "priceLevel": "PRICE_LEVEL_MODERATE",
        }
    )
    assert place.price_level == 2
    assert place.category.value == "lodging"


def test_budget_tier_from_per_person_total() -> None:
    # 1인 총 210_000 / 3일 = 70_000 → budget
    plan = resolve_budget_plan(travelers=1, day_count=3, budget_krw_per_person=210_000)
    assert plan.tier == "budget"
    assert plan.budget_krw_per_person == 210_000
    assert plan.budget_krw_total == 210_000
    assert plan.per_person_per_day_krw == 70_000
    assert "게스트하우스" in plan.lodging_search_terms


def test_budget_tier_group_total_derived() -> None:
    # 1인 360_000 × 2명 = 720_000, /3일 = 120_000 → standard
    plan = resolve_budget_plan(travelers=2, day_count=3, budget_krw_per_person=360_000)
    assert plan.tier == "standard"
    assert plan.budget_krw_total == 720_000
    assert plan.preferred_price_levels == (2, 3)


def test_budget_tier_premium() -> None:
    plan = resolve_budget_plan(travelers=1, day_count=2, budget_krw_per_person=500_000)
    assert plan.tier == "premium"
    assert plan.preferred_price_levels == (3, 4)


def test_budget_legacy_total_compat() -> None:
    # 구버전: 일행 총액 720_000 / 2인 = 1인 360_000
    plan = resolve_budget_plan(travelers=2, day_count=3, budget_krw_total=720_000)
    assert plan.budget_krw_per_person == 360_000
    assert plan.tier == "standard"


def test_budget_tier_none_defaults_standard() -> None:
    plan = resolve_budget_plan(travelers=1, day_count=3, budget_krw_per_person=None)
    assert plan.tier == "standard"
    assert plan.budget_krw_per_person is None
