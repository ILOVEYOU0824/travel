"""일정 예산 트래커 — Exact 원화 추정 금지. Google price_level·티어만."""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field

from app.schemas.itinerary import ItineraryDayView
from app.services.budget_tier import BudgetPlan, resolve_budget_plan

_PRICE_LABEL = {1: "₩", 2: "₩₩", 3: "₩₩₩", 4: "₩₩₩₩"}


class DayBudgetRow(BaseModel):
    date: str
    region: str | None = None
    restaurants: int = 0
    cafes: int = 0
    lodging: int = 0
    attractions: int = 0
    price_levels: list[int] = Field(default_factory=list)
    in_tier_count: int = 0
    priced_count: int = 0
    note: str | None = None


class BudgetTrackerResponse(BaseModel):
    tier: str
    tier_label: str
    preferred_price_levels: list[int]
    preferred_label: str
    budget_krw_per_person: int | None = None
    budget_krw_total: int | None = None
    per_person_per_day_krw: int | None = None
    days: list[DayBudgetRow]
    total_restaurants: int
    total_lodging: int
    priced_places: int
    in_tier_places: int
    alignment_pct: int | None = None
    note: str


def _tier_label(tier: str) -> str:
    return {"budget": "저예산", "standard": "보통", "premium": "여유"}.get(tier, tier)


def build_budget_tracker(
    days: list[ItineraryDayView],
    *,
    travelers: int = 1,
    budget_krw_per_person: int | None = None,
    budget_krw_total: int | None = None,
    budget_tier: str | None = None,
) -> BudgetTrackerResponse:
    plan = resolve_budget_plan(
        travelers=travelers,
        day_count=max(1, len(days)),
        budget_krw_per_person=budget_krw_per_person,
        budget_krw_total=budget_krw_total,
    )
    # 응답에 이미 tier가 있으면 표시 일치 (재계산과 다를 수 있어도 plan 우선)
    tier = budget_tier or plan.tier
    preferred = set(plan.preferred_price_levels)

    rows: list[DayBudgetRow] = []
    total_rest = total_lodge = priced = in_tier = 0

    for day in days:
        c = Counter()
        levels: list[int] = []
        day_in = day_priced = 0
        for it in day.items:
            cat = it.place.category
            c[cat] += 1
            pl = it.place.price_level
            if pl is not None:
                levels.append(pl)
                day_priced += 1
                priced += 1
                if pl in preferred:
                    day_in += 1
                    in_tier += 1
        rest = c.get("restaurant", 0)
        cafe = c.get("cafe", 0)
        lodge = c.get("lodging", 0)
        attr = c.get("attraction", 0) + c.get("other", 0)
        total_rest += rest + cafe
        total_lodge += lodge
        note = None
        if day_priced and day_in < day_priced:
            note = "가격대가 예산 티어보다 높은/낮은 곳이 있어요 (Google 가격대 기준)"
        rows.append(
            DayBudgetRow(
                date=day.date,
                region=day.region,
                restaurants=rest,
                cafes=cafe,
                lodging=lodge,
                attractions=attr,
                price_levels=levels,
                in_tier_count=day_in,
                priced_count=day_priced,
                note=note,
            )
        )

    alignment = int(round(100 * in_tier / priced)) if priced else None
    pref_label = "·".join(_PRICE_LABEL[i] for i in sorted(preferred) if i in _PRICE_LABEL)

    return BudgetTrackerResponse(
        tier=tier,
        tier_label=_tier_label(tier),
        preferred_price_levels=list(plan.preferred_price_levels),
        preferred_label=pref_label,
        budget_krw_per_person=plan.budget_krw_per_person,
        budget_krw_total=plan.budget_krw_total,
        per_person_per_day_krw=plan.per_person_per_day_krw,
        days=rows,
        total_restaurants=total_rest,
        total_lodging=total_lodge,
        priced_places=priced,
        in_tier_places=in_tier,
        alignment_pct=alignment,
        note=(
            f"{_tier_label(tier)} 티어 권장 가격대 {pref_label}. "
            "₩ 표시는 Google Places 가격대이며 Exact 원화 요금이 아닙니다. "
            "예약·결제는 Klook 등에서 확인하세요."
        ),
    )
