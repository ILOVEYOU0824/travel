"""드래그 순서 변경·동카테고리 근처 장소 교체·동선 최적화. Places/Routes만 사용."""

from __future__ import annotations

from app.config import Settings
from app.schemas.itinerary import ItineraryDayView, ItineraryItemView, TimeSlot
from app.schemas.place import Place, PlaceCategory, PlaceSearchRequest
from app.services.arrange_meal_placement import _best_insert_index, _nn_order
from app.services.food_proximity import haversine_m
from app.services.place_search import search_places
from app.services.recompute_travel import recompute_travel_times

_CATEGORY_QUERY: dict[str, tuple[str, str | None]] = {
    # (검색어 접미사, included_type)
    PlaceCategory.restaurant.value: ("맛집", "restaurant"),
    PlaceCategory.cafe.value: ("카페", "cafe"),
    PlaceCategory.lodging.value: ("호텔", "lodging"),
    PlaceCategory.attraction.value: ("관광지", "tourist_attraction"),
    PlaceCategory.other.value: ("명소", None),
}


def _find_day(days: list[ItineraryDayView], day_date: str) -> ItineraryDayView:
    for d in days:
        if d.date == day_date:
            return d
    raise ValueError(f"{day_date} 일정을 찾을 수 없습니다.")


def reorder_day_items(
    days: list[ItineraryDayView],
    *,
    day_date: str,
    ordered_place_ids: list[str],
) -> list[ItineraryDayView]:
    day = _find_day(days, day_date)
    by_id = {it.place.place_id: it for it in day.items}
    if set(ordered_place_ids) != set(by_id.keys()):
        raise ValueError("순서 목록이 당일 장소와 일치하지 않습니다.")

    slots = [it.time_slot for it in day.items]
    new_items: list[ItineraryItemView] = []
    for i, pid in enumerate(ordered_place_ids):
        old = by_id[pid]
        # 슬롯은 위치 순서를 따르도록 재배치( lodging evening 유지)
        if old.place.category == PlaceCategory.lodging:
            slot = TimeSlot.evening
        else:
            slot = slots[i] if i < len(slots) else old.time_slot
            if slot == TimeSlot.evening and old.place.category != PlaceCategory.lodging:
                # evening이 숙소용이면 afternoon로
                slot = TimeSlot.afternoon if TimeSlot.afternoon in slots else old.time_slot
        new_items.append(
            old.model_copy(
                update={
                    "order": i + 1,
                    "time_slot": slot,
                    "travel_from_previous": None,
                }
            )
        )

    # 숙소는 맨 뒤로
    lodging = [it for it in new_items if it.place.category == PlaceCategory.lodging]
    non = [it for it in new_items if it.place.category != PlaceCategory.lodging]
    fixed = non + lodging
    for i, it in enumerate(fixed, start=1):
        fixed[i - 1] = it.model_copy(update={"order": i})

    out: list[ItineraryDayView] = []
    for d in days:
        if d.date != day_date:
            out.append(d)
        else:
            out.append(d.model_copy(update={"items": fixed}))
    return out


async def reorder_and_recompute(
    settings: Settings,
    *,
    days: list[ItineraryDayView],
    day_date: str,
    ordered_place_ids: list[str],
    travel_mode: str,
    language_code: str,
    arrival_airport_query: str | None,
    return_departure_jst: str | None,
) -> list[ItineraryDayView]:
    reordered = reorder_day_items(
        days, day_date=day_date, ordered_place_ids=ordered_place_ids
    )
    return await recompute_travel_times(
        settings,
        days=reordered,
        travel_mode=travel_mode,
        language_code=language_code,
        arrival_airport_query=arrival_airport_query,
        return_departure_jst=return_departure_jst,
    )


def _path_len_m(ids: list[str], places: dict[str, Place]) -> float:
    if len(ids) < 2:
        return 0.0
    total = 0.0
    for i in range(len(ids) - 1):
        a, b = places[ids[i]], places[ids[i + 1]]
        total += haversine_m(a.location.lat, a.location.lng, b.location.lat, b.location.lng)
    return total


def _two_opt(ids: list[str], places: dict[str, Place]) -> list[str]:
    """짧은 2-opt. 좌표(haversine)만 — Routes/LLM 미사용."""
    if len(ids) < 4:
        return list(ids)
    best = list(ids)
    best_len = _path_len_m(best, places)
    improved = True
    guard = 0
    while improved and guard < 40:
        improved = False
        guard += 1
        for i in range(1, len(best) - 2):
            for k in range(i + 1, len(best)):
                if k - i == 1:
                    continue
                trial = best[:i] + best[i:k][::-1] + best[k:]
                length = _path_len_m(trial, places)
                if length + 1.0 < best_len:
                    best = trial
                    best_len = length
                    improved = True
                    break
            if improved:
                break
    return best


def optimize_day_order(days: list[ItineraryDayView], *, day_date: str) -> list[str]:
    """당일 place_id만 재배치. 숙소 마지막, 식사는 경로 삽입, 관광 NN+2-opt."""
    day = _find_day(days, day_date)
    if len(day.items) <= 1:
        return [it.place.place_id for it in day.items]

    places = {it.place.place_id: it.place for it in day.items}
    lodging: list[str] = []
    meals: list[str] = []
    sights: list[str] = []
    for it in day.items:
        cat = it.place.category
        if cat == PlaceCategory.lodging:
            lodging.append(it.place.place_id)
        elif cat in (PlaceCategory.restaurant, PlaceCategory.cafe):
            meals.append(it.place.place_id)
        else:
            sights.append(it.place.place_id)

    route = _nn_order(sights, places) if sights else []
    route = _two_opt(route, places)
    for mid in meals:
        idx = _best_insert_index(route, mid, places)
        route.insert(idx, mid)
    return route + lodging


async def optimize_and_recompute(
    settings: Settings,
    *,
    days: list[ItineraryDayView],
    day_date: str,
    travel_mode: str,
    language_code: str,
    arrival_airport_query: str | None,
    return_departure_jst: str | None,
) -> list[ItineraryDayView]:
    ordered = optimize_day_order(days, day_date=day_date)
    return await reorder_and_recompute(
        settings,
        days=days,
        day_date=day_date,
        ordered_place_ids=ordered,
        travel_mode=travel_mode,
        language_code=language_code,
        arrival_airport_query=arrival_airport_query,
        return_departure_jst=return_departure_jst,
    )


async def suggest_swaps(
    settings: Settings,
    *,
    days: list[ItineraryDayView],
    day_date: str,
    place_id: str,
    language_code: str = "ko",
    max_suggestions: int = 3,
) -> tuple[str, str, list[Place], str | None]:
    day = _find_day(days, day_date)
    current = next((it for it in day.items if it.place.place_id == place_id), None)
    if current is None:
        raise ValueError("해당 날짜에 그 장소가 없습니다.")

    used = {
        it.place.place_id
        for d in days
        for it in d.items
    }
    cat = current.place.category.value
    suffix, included = _CATEGORY_QUERY.get(cat, ("명소", None))
    region = day.region or ""
    query = f"{region} {suffix}".strip() or suffix

    found = await search_places(
        settings,
        PlaceSearchRequest(
            query=query,
            language_code=language_code,
            max_results=20,
            bias_lat=current.place.location.lat,
            bias_lng=current.place.location.lng,
            bias_radius_meters=2500.0,
            included_type=included,
            min_rating=3.8,
        ),
    )

    scored: list[tuple[float, Place]] = []
    for p in found.places:
        if not p.place_id or p.place_id in used:
            continue
        if cat != PlaceCategory.other.value and p.category.value != cat:
            # lodging/restaurant 등 카테고리 일치 우선
            if cat == PlaceCategory.attraction.value and p.category == PlaceCategory.other:
                pass
            elif p.category.value != cat:
                continue
        dist = haversine_m(
            current.place.location.lat,
            current.place.location.lng,
            p.location.lat,
            p.location.lng,
        )
        if dist > 4000:
            continue
        rating = p.rating or 0.0
        scored.append((rating * 10 - dist / 500.0, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    suggestions = [p for _, p in scored[:max_suggestions]]
    msg = None
    if not suggestions:
        msg = (
            f"근처에서 같은 종류의 대체 장소를 찾지 못했어요. "
            f"(Places · {query})"
        )
    return place_id, cat, suggestions, msg


async def apply_swap_and_recompute(
    settings: Settings,
    *,
    days: list[ItineraryDayView],
    day_date: str,
    old_place_id: str,
    new_place: Place,
    travel_mode: str,
    language_code: str,
    arrival_airport_query: str | None,
    return_departure_jst: str | None,
) -> list[ItineraryDayView]:
    day = _find_day(days, day_date)
    if not any(it.place.place_id == old_place_id for it in day.items):
        raise ValueError("교체할 장소가 당일 일정에 없습니다.")
    if any(
        it.place.place_id == new_place.place_id
        for d in days
        for it in d.items
    ):
        raise ValueError("이미 일정에 있는 장소입니다.")

    new_days: list[ItineraryDayView] = []
    for d in days:
        if d.date != day_date:
            new_days.append(d)
            continue
        items: list[ItineraryItemView] = []
        for it in d.items:
            if it.place.place_id != old_place_id:
                items.append(it)
                continue
            place_view = new_place.model_copy(
                update={
                    "ai_description": (
                        f"같은 종류·근처 후보로 교체 · ★{new_place.rating}"
                        if new_place.rating is not None
                        else "같은 종류·근처 후보로 교체"
                    )
                }
            )
            items.append(
                it.model_copy(
                    update={
                        "place": place_view,
                        "ai_description": place_view.ai_description or it.ai_description,
                        "travel_from_previous": None,
                        "booking_cta": None,
                    }
                )
            )
        new_days.append(d.model_copy(update={"items": items}))

    return await recompute_travel_times(
        settings,
        days=new_days,
        travel_mode=travel_mode,
        language_code=language_code,
        arrival_airport_query=arrival_airport_query,
        return_departure_jst=return_departure_jst,
    )
