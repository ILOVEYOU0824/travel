"""식사(must_have_food 등)를 첫 슬롯에 고정하지 않고, 당일 동선 위 최적 위치에 끼워 넣는다.

이동시간은 Routes가 나중에 계산. 여기서는 위경도(haversine)만 사용 — LLM 추정 금지.
"""

from __future__ import annotations

from typing import Iterable

from app.schemas.itinerary import LlmItineraryDay, LlmItineraryItem, LlmItineraryResponse, TimeSlot
from app.schemas.place import Place, PlaceCategory
from app.services.flight_windows import FlightWindows, allowed_slots_for_day
from app.services.food_proximity import haversine_m

_MEAL_SLOTS = (TimeSlot.lunch, TimeSlot.dinner)
_SIGHT_SLOTS = (TimeSlot.morning, TimeSlot.afternoon, TimeSlot.evening)


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    return haversine_m(a[0], a[1], b[0], b[1])


def _coords(place: Place) -> tuple[float, float]:
    return (place.location.lat, place.location.lng)


def _path_length(coords: list[tuple[float, float]]) -> float:
    if len(coords) < 2:
        return 0.0
    return sum(_haversine_m(coords[i], coords[i + 1]) for i in range(len(coords) - 1))


def _is_meal_place(
    place: Place,
    *,
    food_place_ids: set[str],
    must_have_food: list[str],
) -> bool:
    if place.place_id in food_place_ids:
        return True
    if place.category in (PlaceCategory.restaurant, PlaceCategory.cafe):
        return True
    blob = place.name.lower()
    return any(q.lower() in blob for q in must_have_food if q.strip())


def _nn_order(place_ids: list[str], places_by_id: dict[str, Place]) -> list[str]:
    if len(place_ids) <= 1:
        return list(place_ids)
    # 별점 높은 곳부터 시작 → 가까운 순으로 이음
    remaining = set(place_ids)
    start = max(
        place_ids,
        key=lambda pid: (places_by_id[pid].rating or 0.0, places_by_id[pid].user_rating_count or 0),
    )
    ordered = [start]
    remaining.remove(start)
    while remaining:
        last = _coords(places_by_id[ordered[-1]])
        nxt = min(remaining, key=lambda pid: _haversine_m(last, _coords(places_by_id[pid])))
        ordered.append(nxt)
        remaining.remove(nxt)
    return ordered


def _best_insert_index(
    route: list[str],
    meal_id: str,
    places_by_id: dict[str, Place],
) -> int:
    """경로 길이 증가가 최소인 삽입 위치(0=맨앞 … len=맨뒤). 맨앞은 패널티."""
    meal_xy = _coords(places_by_id[meal_id])
    if not route:
        return 0

    best_i = 1 if len(route) >= 1 else 0
    best_cost = float("inf")
    base_coords = [_coords(places_by_id[pid]) for pid in route]

    for i in range(len(route) + 1):
        trial = base_coords[:i] + [meal_xy] + base_coords[i:]
        cost = _path_length(trial)
        # 첫 자리(아침 관광 전)에 식사를 두지 않도록 강하게 패널티
        if i == 0:
            cost += 25_000.0
        # 맨 끝(숙소 직전 저녁 식사는 OK, 관광이 있으면 중간 선호)
        if i == len(route) and len(route) >= 2:
            cost += 3_000.0
        if cost < best_cost:
            best_cost = cost
            best_i = i
    return best_i


def _assign_slots(
    ordered_ids: list[str],
    places_by_id: dict[str, Place],
    meal_ids: set[str],
    allowed: list[TimeSlot],
    *,
    reasons: dict[str, str],
) -> list[LlmItineraryItem]:
    meal_slots = [s for s in _MEAL_SLOTS if s in allowed]
    sight_slots = [s for s in _SIGHT_SLOTS if s in allowed]
    if not meal_slots:
        meal_slots = [s for s in allowed if s != TimeSlot.evening] or list(allowed)
    if not sight_slots:
        sight_slots = list(allowed)

    meal_i = 0
    sight_i = 0
    items: list[LlmItineraryItem] = []
    for pid in ordered_ids:
        place = places_by_id[pid]
        if place.category == PlaceCategory.lodging and TimeSlot.evening in allowed:
            slot = TimeSlot.evening
        elif pid in meal_ids or place.category in (PlaceCategory.restaurant, PlaceCategory.cafe):
            slot = meal_slots[min(meal_i, len(meal_slots) - 1)]
            meal_i += 1
        else:
            slot = sight_slots[min(sight_i, len(sight_slots) - 1)]
            sight_i += 1
        items.append(
            LlmItineraryItem(
                place_id=pid,
                order=len(items) + 1,
                time_slot=slot,
                reason=reasons.get(pid, "동선·식사 시간대에 맞게 재배치"),
            )
        )
    return items


def _arrange_day(
    day: LlmItineraryDay,
    places_by_id: dict[str, Place],
    *,
    food_place_ids: set[str],
    must_have_food: list[str],
    dates: list[str],
    flight_windows: FlightWindows | None,
) -> LlmItineraryDay:
    if not day.items:
        return day

    reasons = {it.place_id: it.reason for it in day.items}
    lodging: list[str] = []
    meals: list[str] = []
    sights: list[str] = []

    for it in day.items:
        place = places_by_id.get(it.place_id)
        if place is None:
            continue
        if place.category == PlaceCategory.lodging:
            lodging.append(it.place_id)
        elif _is_meal_place(place, food_place_ids=food_place_ids, must_have_food=must_have_food):
            meals.append(it.place_id)
        else:
            sights.append(it.place_id)

    # 식사만 있고 관광이 없으면 슬롯만 lunch/dinner로
    route = _nn_order(sights, places_by_id) if sights else []
    # 별점 높은 식사부터 삽입 (must_food 우선)
    def meal_key(pid: str) -> tuple[int, float]:
        p = places_by_id[pid]
        must = 1 if pid in food_place_ids or any(
            q.lower() in p.name.lower() for q in must_have_food
        ) else 0
        return (must, p.rating or 0.0)

    for meal_id in sorted(meals, key=meal_key, reverse=True):
        if meal_id in route:
            continue
        idx = _best_insert_index(route, meal_id, places_by_id)
        route.insert(idx, meal_id)

    # 관광도 식사도 없이 이상한 경우 원본 유지
    if not route and not lodging:
        return day

    ordered = route + [pid for pid in lodging if pid not in route]
    allowed_raw = (
        allowed_slots_for_day(date=day.date, dates=dates, windows=flight_windows)
        if flight_windows
        else [s.value for s in TimeSlot]
    )
    allowed = [TimeSlot(s) for s in allowed_raw]
    meal_set = set(meals)
    items = _assign_slots(ordered, places_by_id, meal_set, allowed, reasons=reasons)
    return LlmItineraryDay(date=day.date, items=items)


def arrange_meal_placement(
    itinerary: LlmItineraryResponse,
    places_by_id: dict[str, Place],
    *,
    must_have_food: Iterable[str] = (),
    food_place_ids: Iterable[str] = (),
    dates: list[str] | None = None,
    flight_windows: FlightWindows | None = None,
) -> LlmItineraryResponse:
    """검증 통과 후 hydrate 전에 호출. place_id는 바꾸지 않고 순서·슬롯만 조정."""
    food_ids = set(food_place_ids)
    foods = [q.strip() for q in must_have_food if q and q.strip()]
    date_list = dates or [d.date for d in itinerary.days]
    days = [
        _arrange_day(
            day,
            places_by_id,
            food_place_ids=food_ids,
            must_have_food=foods,
            dates=date_list,
            flight_windows=flight_windows,
        )
        for day in itinerary.days
    ]
    return LlmItineraryResponse(days=days)
