"""MOCK_ Claude — 후보 place_id만 사용. 새 장소 생성 금지."""

from __future__ import annotations

from typing import Any

from app.schemas.itinerary import (
    CandidatePlaceBrief,
    LlmItineraryDay,
    LlmItineraryItem,
    LlmItineraryResponse,
    TimeSlot,
)
from app.schemas.replan import IntentType, TravelIntent
from app.services.flight_windows import FlightWindows, allowed_slots_for_day

_SLOTS = [TimeSlot.morning, TimeSlot.lunch, TimeSlot.afternoon, TimeSlot.dinner, TimeSlot.evening]


def _region_for_date(day_regions: list[dict[str, Any]], date: str) -> str | None:
    for d in day_regions:
        if d.get("date") == date:
            return d.get("region")
    return None


def _dist2(a: CandidatePlaceBrief, b: CandidatePlaceBrief) -> float:
    return (a.lat - b.lat) ** 2 + (a.lng - b.lng) ** 2


def _matches_query(c: CandidatePlaceBrief, q: str) -> bool:
    q_l = q.lower()
    if q_l in f"{c.name} {c.category}".lower():
        return True
    return any(q_l == t.lower() or q_l in t.lower() for t in c.must_food_queries)


async def MOCK_generate_itinerary(
    *,
    candidates: list[CandidatePlaceBrief],
    dates: list[str],
    day_regions: list[dict[str, Any]],
    must_have_food: list[str],
    must_have_sights: list[str],
    include_lodging: bool = True,
    preferred_price_levels: list[int] | None = None,
    flight_windows: FlightWindows | None = None,
) -> LlmItineraryResponse:
    if not candidates:
        return LlmItineraryResponse(days=[LlmItineraryDay(date=d, items=[]) for d in dates])

    preferred = set(preferred_price_levels or [2, 3])
    fw = flight_windows
    used_must: set[str] = set()
    days: list[LlmItineraryDay] = []

    for d in dates:
        region = _region_for_date(day_regions, d)
        pool = [c for c in candidates if not region or c.region is None or c.region == region]
        if not pool:
            pool = list(candidates)
        lodging_pool = [c for c in pool if c.category == "lodging"]
        non_lodging = [c for c in pool if c.category != "lodging"]
        day_slots = (
            [TimeSlot(s) for s in allowed_slots_for_day(date=d, dates=dates, windows=fw)]
            if fw
            else list(_SLOTS)
        )
        if not day_slots:
            days.append(LlmItineraryDay(date=d, items=[]))
            continue
        max_items = min(4, len(day_slots))

        # 1) 관광·기타를 먼저 (식사는 나중에 동선에 삽입)
        sight_pool = [
            c
            for c in non_lodging
            if c.category not in {"restaurant", "cafe"}
        ]
        if not sight_pool:
            sight_pool = list(non_lodging)

        def sight_score(c: CandidatePlaceBrief) -> float:
            s = float(c.rating or 0) * 10
            for q in must_have_sights:
                if _matches_query(c, q):
                    s += 30
            return s

        sights_picked: list[CandidatePlaceBrief] = []
        for q in must_have_sights:
            if q in used_must:
                continue
            for c in sorted(sight_pool, key=sight_score, reverse=True):
                if _matches_query(c, q) and c.place_id not in {x.place_id for x in sights_picked}:
                    sights_picked.append(c)
                    used_must.add(q)
                    break

        for c in sorted(sight_pool, key=sight_score, reverse=True):
            if len(sights_picked) >= max(1, max_items - 1):
                break
            if c.place_id in {x.place_id for x in sights_picked}:
                continue
            sights_picked.append(c)

        # 2) must_have_food — 관광 동선 중심에 가까운 고평점 식당
        meals_picked: list[CandidatePlaceBrief] = []
        meal_pool = [c for c in non_lodging if c.category in {"restaurant", "cafe"} or c.must_food_queries]
        if not meal_pool:
            meal_pool = non_lodging

        def meal_score(c: CandidatePlaceBrief) -> float:
            s = float(c.rating or 0) * 10
            if c.must_food_queries:
                s += 25
            for q in must_have_food:
                if _matches_query(c, q):
                    s += 40
            if c.price_level is not None and c.price_level in preferred:
                s += 8
            if sights_picked:
                avg_lat = sum(x.lat for x in sights_picked) / len(sights_picked)
                avg_lng = sum(x.lng for x in sights_picked) / len(sights_picked)
                s -= ((c.lat - avg_lat) ** 2 + (c.lng - avg_lng) ** 2) * 8000
            return s

        for q in must_have_food:
            if q in used_must:
                continue
            ranked = sorted(meal_pool, key=meal_score, reverse=True)
            for c in ranked:
                if c.place_id in {x.place_id for x in sights_picked + meals_picked}:
                    continue
                if _matches_query(c, q) or c.category in {"restaurant", "cafe"}:
                    meals_picked.append(c)
                    used_must.add(q)
                    break

        # 3) 관광 NN 순서 후, 식사를 중간(또는 끝 직전)에 삽입 — 맨 앞 금지
        ordered: list[CandidatePlaceBrief] = []
        if sights_picked:
            ordered = [sights_picked[0]]
            rest = sights_picked[1:]
            while rest:
                last = ordered[-1]
                rest.sort(key=lambda c: _dist2(last, c))
                ordered.append(rest.pop(0))
        for meal in meals_picked:
            if not ordered:
                ordered.append(meal)
            else:
                insert_at = max(1, len(ordered) // 2)  # 최소 두 번째
                ordered.insert(insert_at, meal)

        for c in non_lodging:
            if len(ordered) >= max_items:
                break
            if c.place_id in {x.place_id for x in ordered}:
                continue
            ordered.append(c)

        meal_ids = {m.place_id for m in meals_picked}
        meal_slots = [s for s in (TimeSlot.lunch, TimeSlot.dinner) if s in day_slots]
        sight_slots = [s for s in (TimeSlot.morning, TimeSlot.afternoon, TimeSlot.evening) if s in day_slots]
        if not meal_slots:
            meal_slots = [s for s in day_slots if s != TimeSlot.evening] or list(day_slots)
        if not sight_slots:
            sight_slots = list(day_slots)

        items: list[LlmItineraryItem] = []
        mi = si = 0
        for c in ordered[:max_items]:
            if c.place_id in meal_ids or c.category in {"restaurant", "cafe"}:
                slot = meal_slots[min(mi, len(meal_slots) - 1)]
                mi += 1
                reason = f"MOCK must_have food · 동선 근처: {c.name}"
            else:
                slot = sight_slots[min(si, len(sight_slots) - 1)]
                si += 1
                reason = f"MOCK_{region or '지역'}: 후보에서 선택"
            items.append(
                LlmItineraryItem(
                    place_id=c.place_id,
                    order=len(items) + 1,
                    time_slot=slot,
                    reason=reason,
                )
            )

        if include_lodging and lodging_pool and d != dates[-1] and TimeSlot.evening in day_slots:

            def lodging_key(c: CandidatePlaceBrief) -> tuple[int, float]:
                in_pref = 1 if c.price_level is not None and c.price_level in preferred else 0
                return (in_pref, c.rating or 0)

            best = max(lodging_pool, key=lodging_key)
            if best.place_id not in {i.place_id for i in items}:
                items.append(
                    LlmItineraryItem(
                        place_id=best.place_id,
                        order=len(items) + 1,
                        time_slot=TimeSlot.evening,
                        reason=(
                            f"MOCK 숙소 추천: 예산 가격대·별점 기준 "
                            f"(price_level={best.price_level}, rating={best.rating})"
                        ),
                    )
                )
        days.append(LlmItineraryDay(date=d, items=items))
    return LlmItineraryResponse(days=days)


async def MOCK_parse_intent(*, prompt: str, available_dates: list[str]) -> TravelIntent:
    text = prompt.lower()
    target = available_dates[0] if available_dates else None
    for d in available_dates:
        if d in prompt:
            target = d
            break

    if any(k in text for k in ("삭제", "빼", "제거", "remove")):
        return TravelIntent(
            intent_type=IntentType.remove_item,
            category_query=prompt,
            must_have=False,
            target_day=target,
            raw_text=prompt,
        )
    if any(k in text for k in ("순서", "바꿔", "order")):
        return TravelIntent(
            intent_type=IntentType.change_order,
            category_query=None,
            must_have=False,
            target_day=target,
            raw_text=prompt,
        )
    if any(k in text for k in ("날짜", "다른 날", "옮기")):
        return TravelIntent(
            intent_type=IntentType.change_date,
            category_query=None,
            must_have=False,
            target_day=target,
            raw_text=prompt,
        )
    if any(k in text for k in ("먹", "라멘", "스시", "식당", "맛집", "카페")):
        return TravelIntent(
            intent_type=IntentType.add_food,
            category_query=prompt,
            must_have=True,
            target_day=target,
            raw_text=prompt,
        )
    if any(k in text for k in ("가", "보고", "관광", "신사", "성", "박물관")):
        return TravelIntent(
            intent_type=IntentType.add_sight,
            category_query=prompt,
            must_have=True,
            target_day=target,
            raw_text=prompt,
        )
    return TravelIntent(
        intent_type=IntentType.unclear,
        category_query=None,
        must_have=False,
        target_day=None,
        raw_text=prompt,
    )


async def MOCK_replan_itinerary(
    *,
    current_days: list[dict[str, Any]],
    candidates: list[CandidatePlaceBrief],
    intent: TravelIntent,
    dates: list[str],
    region: str,
) -> LlmItineraryResponse:
    cand_ids = {c.place_id for c in candidates}
    by_id = {c.place_id: c for c in candidates}
    days_out: list[LlmItineraryDay] = []

    for day in current_days:
        date = day["date"]
        items_in = day.get("items") or []
        items: list[LlmItineraryItem] = []
        for it in items_in:
            pid = it.get("place_id") or (it.get("place") or {}).get("place_id")
            if not pid or pid not in cand_ids:
                continue
            if intent.intent_type == IntentType.remove_item and intent.category_query:
                name = (it.get("place") or {}).get("name") or ""
                if intent.category_query in name or intent.category_query in pid:
                    continue
            items.append(
                LlmItineraryItem(
                    place_id=pid,
                    order=len(items) + 1,
                    time_slot=TimeSlot(it.get("time_slot", "afternoon")),
                    reason=it.get("ai_description") or it.get("reason") or "MOCK 유지",
                )
            )

        if intent.intent_type in (IntentType.add_food, IntentType.add_sight):
            existing = {i.place_id for i in items}
            insert_day = intent.target_day or date
            if date == insert_day:
                # 기존 일정 중심에 가까운 후보
                def near_score(c: CandidatePlaceBrief) -> float:
                    if not items:
                        return float(c.rating or 0)
                    pts = [by_id[i.place_id] for i in items if i.place_id in by_id]
                    if not pts:
                        return float(c.rating or 0)
                    avg_lat = sum(p.lat for p in pts) / len(pts)
                    avg_lng = sum(p.lng for p in pts) / len(pts)
                    return float(c.rating or 0) * 10 - ((c.lat - avg_lat) ** 2 + (c.lng - avg_lng) ** 2) * 8000

                for c in sorted(candidates, key=near_score, reverse=True):
                    if c.place_id not in existing:
                        slot = TimeSlot.lunch if intent.intent_type == IntentType.add_food else TimeSlot.afternoon
                        insert_at = max(1, len(items) // 2) if items else 0
                        items.insert(
                            insert_at,
                            LlmItineraryItem(
                                place_id=c.place_id,
                                order=1,  # 아래에서 재부여
                                time_slot=slot,
                                reason=f"MOCK 리플랜 추가 ({region})",
                            ),
                        )
                        for i, it in enumerate(items, start=1):
                            it.order = i
                        break

        if intent.intent_type == IntentType.change_order and len(items) >= 2:
            items[0], items[1] = items[1], items[0]
            for i, it in enumerate(items, start=1):
                it.order = i

        days_out.append(LlmItineraryDay(date=date, items=items))

    present = {d.date for d in days_out}
    for d in dates:
        if d not in present:
            days_out.append(LlmItineraryDay(date=d, items=[]))
    days_out.sort(key=lambda x: x.date)
    return LlmItineraryResponse(days=days_out)
