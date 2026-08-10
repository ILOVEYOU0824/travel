"""예산 → 티어 매핑. Exact 숙박비 추정 금지 — priceLevel 선호 범위만.

입력은「1인당 총 여행경비」(여행 전체). 티어만 day_count로 환산해 판별한다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BudgetPlan:
    tier: str  # budget | standard | premium
    travelers: int
    day_count: int
    # 1인당 총 여행경비 (여행 전체)
    budget_krw_per_person: int | None
    # 일행 전체 = per_person × travelers
    budget_krw_total: int | None
    # 티어 판별용 참고 환산 (표시는 보조)
    per_person_per_day_krw: int | None
    preferred_price_levels: tuple[int, ...]
    note: str
    lodging_search_terms: tuple[str, ...]


_TIER_NOTES = {
    "budget": (
        "저예산 가이드: 1인 총경비 기준으로 숙소·식사 Google 가격대 ₩~₩₩ 위주. "
        "Exact 요금은 예약 사이트에서 확인하세요."
    ),
    "standard": (
        "보통 예산 가이드: 1인 총경비 기준으로 숙소·식사 Google 가격대 ₩₩~₩₩₩ 위주. "
        "Exact 요금은 예약 사이트에서 확인하세요."
    ),
    "premium": (
        "여유 예산 가이드: 1인 총경비 기준으로 숙소·식사 Google 가격대 ₩₩₩~₩₩₩₩ 위주. "
        "Exact 요금은 예약 사이트에서 확인하세요."
    ),
}

_LODGING_TERMS = {
    "budget": ("게스트하우스", "비즈니스호텔", "캡슐호텔"),
    "standard": ("호텔", "비즈니스호텔"),
    "premium": ("호텔", "료칸", "리조트"),
}


def resolve_budget_plan(
    *,
    travelers: int,
    day_count: int,
    budget_krw_per_person: int | None = None,
    budget_krw_total: int | None = None,
) -> BudgetPlan:
    """budget_krw_per_person 우선. 없으면 구버전 total을 인원으로 나눠 호환."""
    travelers = max(1, travelers)
    day_count = max(1, day_count)

    per_person = budget_krw_per_person
    if per_person is None and budget_krw_total is not None and budget_krw_total > 0:
        per_person = budget_krw_total // travelers

    group_total: int | None = None
    if per_person is not None and per_person > 0:
        group_total = per_person * travelers

    per_day: int | None = None
    if per_person is not None and per_person > 0:
        per_day = per_person // day_count

    # 1인당 총경비 ÷ 일수 → 티어 신호 (Exact 견적 아님)
    if per_day is None:
        tier = "standard"
    elif per_day < 80_000:
        tier = "budget"
    elif per_day < 180_000:
        tier = "standard"
    else:
        tier = "premium"

    preferred = {
        "budget": (1, 2),
        "standard": (2, 3),
        "premium": (3, 4),
    }[tier]

    return BudgetPlan(
        tier=tier,
        travelers=travelers,
        day_count=day_count,
        budget_krw_per_person=per_person,
        budget_krw_total=group_total,
        per_person_per_day_krw=per_day,
        preferred_price_levels=preferred,
        note=_TIER_NOTES[tier],
        lodging_search_terms=_LODGING_TERMS[tier],
    )
