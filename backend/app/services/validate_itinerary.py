"""LLM 일정 응답 검증 — 후보에 없는 place_id는 절대 통과시키지 않는다."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.itinerary import LlmItineraryDay, LlmItineraryResponse


@dataclass
class ValidationResult:
    cleaned: LlmItineraryResponse
    removed_place_ids: list[str] = field(default_factory=list)
    removed_items_count: int = 0
    ok: bool = True
    errors: list[str] = field(default_factory=list)


def validate_itinerary_response(
    response: LlmItineraryResponse,
    candidate_place_ids: set[str],
    *,
    expected_dates: set[str] | None = None,
) -> ValidationResult:
    """후보 리스트에 없는 place_id 제거. 전부 비면 ok=False."""
    removed: list[str] = []
    cleaned_days: list[LlmItineraryDay] = []

    for day in response.days:
        if expected_dates is not None and day.date not in expected_dates:
            # 날짜 조작 시 해당 일 스킵 (환각 날짜 방지)
            continue
        valid_items = []
        for item in day.items:
            if item.place_id in candidate_place_ids:
                valid_items.append(item)
            else:
                removed.append(item.place_id)
        # order 재정렬
        valid_items.sort(key=lambda x: x.order)
        for i, it in enumerate(valid_items, start=1):
            it.order = i
        cleaned_days.append(LlmItineraryDay(date=day.date, items=valid_items))

    # expected_dates가 있으면 빠진 날짜는 빈 일정으로 채움
    if expected_dates is not None:
        present = {d.date for d in cleaned_days}
        for d in sorted(expected_dates):
            if d not in present:
                cleaned_days.append(LlmItineraryDay(date=d, items=[]))
        cleaned_days.sort(key=lambda d: d.date)

    total_items = sum(len(d.items) for d in cleaned_days)
    errors: list[str] = []
    if total_items == 0:
        errors.append("검증 후 유효한 일정이 없습니다.")
    if removed:
        errors.append(f"후보에 없는 place_id {len(removed)}개 제거됨")

    return ValidationResult(
        cleaned=LlmItineraryResponse(days=cleaned_days),
        removed_place_ids=removed,
        removed_items_count=len(removed),
        ok=total_items > 0,
        errors=errors,
    )
