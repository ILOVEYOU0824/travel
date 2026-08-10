"""식사 후보를 당일 관광지 반경·평점 기준으로 좁힌다. 좌표는 Places 원본만."""

from __future__ import annotations

import math

from app.schemas.itinerary import CandidatePlaceBrief, LlmItineraryResponse
from app.schemas.place import Place, PlaceCategory

DEFAULT_RADIUS_M = 3500.0
MIN_RATING = 3.8


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def _centroid(points: list[tuple[float, float]]) -> tuple[float, float] | None:
    if not points:
        return None
    return (
        sum(p[0] for p in points) / len(points),
        sum(p[1] for p in points) / len(points),
    )


def prune_food_candidates(
    candidates: list[CandidatePlaceBrief],
    *,
    radius_m: float = DEFAULT_RADIUS_M,
    min_rating: float = MIN_RATING,
) -> list[CandidatePlaceBrief]:
    """must_food 후보 중 관광지 클러스터에서 먼·저평점 식당을 후보 리스트에서 제외.

    해당 음식 쿼리의 유일한 후보면 유지(검색 실패 방지).
    """
    by_region: dict[str, list[CandidatePlaceBrief]] = {}
    for c in candidates:
        key = c.region or "_all"
        by_region.setdefault(key, []).append(c)

    drop: set[str] = set()
    for region, pool in by_region.items():
        sights = [
            c
            for c in pool
            if c.category not in {"restaurant", "cafe", "lodging"}
        ]
        center = _centroid([(c.lat, c.lng) for c in sights]) or _centroid(
            [(c.lat, c.lng) for c in pool if c.category != "lodging"]
        )
        if center is None:
            continue

        food_cands = [c for c in pool if c.must_food_queries or c.category == "restaurant"]
        # 쿼리별로 살아남을 후보 수 추적
        query_pools: dict[str, list[CandidatePlaceBrief]] = {}
        for c in food_cands:
            keys = c.must_food_queries or ["_restaurant"]
            for q in keys:
                query_pools.setdefault(q, []).append(c)

        for c in food_cands:
            dist = haversine_m(center[0], center[1], c.lat, c.lng)
            rating_ok = c.rating is None or c.rating >= min_rating
            near = dist <= radius_m
            if near and rating_ok:
                continue
            # 이 후보가 어떤 must 쿼리의 유일한 생존자면 유지
            sole = False
            for q in c.must_food_queries or []:
                others = [
                    x
                    for x in query_pools.get(q, [])
                    if x.place_id != c.place_id
                    and haversine_m(center[0], center[1], x.lat, x.lng) <= radius_m
                    and (x.rating is None or x.rating >= min_rating)
                ]
                if not others and q in (c.must_food_queries or []):
                    # 근처 대안 없음 → 유지
                    sole = True
                    break
            if not sole and c.must_food_queries:
                drop.add(c.place_id)
            elif not sole and not c.must_food_queries and not near:
                # 일반 맛집 후보는 멀리 있으면 드롭(과다 후보 줄이기)
                if dist > radius_m * 1.4:
                    drop.add(c.place_id)

    if not drop:
        return candidates
    return [c for c in candidates if c.place_id not in drop]


def swap_distant_meals(
    itinerary: LlmItineraryResponse,
    places_by_id: dict[str, Place],
    *,
    food_place_ids: set[str],
    must_have_food: list[str],
    radius_m: float = DEFAULT_RADIUS_M,
    min_rating: float = MIN_RATING,
) -> LlmItineraryResponse:
    """일정에 들어간 식사가 당일 관광지에서 멀면, 반경 안 고평점 food 후보로 교체."""
    if not food_place_ids and not must_have_food:
        return itinerary

    used: set[str] = set()
    for day in itinerary.days:
        for it in day.items:
            used.add(it.place_id)

    new_days = []
    for day in itinerary.days:
        sight_pts = [
            (places_by_id[it.place_id].location.lat, places_by_id[it.place_id].location.lng)
            for it in day.items
            if it.place_id in places_by_id
            and places_by_id[it.place_id].category
            not in (PlaceCategory.restaurant, PlaceCategory.cafe, PlaceCategory.lodging)
        ]
        center = _centroid(sight_pts)
        if center is None:
            new_days.append(day)
            continue

        items = []
        for it in day.items:
            place = places_by_id.get(it.place_id)
            if place is None:
                continue
            is_meal = place.category in (PlaceCategory.restaurant, PlaceCategory.cafe) or (
                it.place_id in food_place_ids
            )
            if not is_meal:
                items.append(it)
                continue
            dist = haversine_m(
                center[0], center[1], place.location.lat, place.location.lng
            )
            rating = place.rating or 0.0
            if dist <= radius_m and rating >= min_rating:
                items.append(it)
                continue

            # 교체 후보
            alts = []
            for pid in food_place_ids:
                if pid in used and pid != it.place_id:
                    continue
                alt = places_by_id.get(pid)
                if alt is None:
                    continue
                if alt.category not in (PlaceCategory.restaurant, PlaceCategory.cafe):
                    continue
                d = haversine_m(center[0], center[1], alt.location.lat, alt.location.lng)
                r = alt.rating or 0.0
                if d <= radius_m and r >= min_rating:
                    alts.append((r, -d, alt))
            if not alts:
                items.append(it)
                continue
            alts.sort(reverse=True)
            best = alts[0][2]
            used.discard(it.place_id)
            used.add(best.place_id)
            items.append(
                it.model_copy(
                    update={
                        "place_id": best.place_id,
                        "reason": (
                            f"{it.reason} · 동선 {int(radius_m)}m 안 고평점 후보로 조정"
                        ),
                    }
                )
            )
        # re-number
        for i, it in enumerate(items, start=1):
            items[i - 1] = it.model_copy(update={"order": i})
        new_days.append(day.model_copy(update={"items": items}))

    return itinerary.model_copy(update={"days": new_days})
