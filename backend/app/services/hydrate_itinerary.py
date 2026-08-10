"""일정 Place 수화 + Routes 이동시간/수단 부착 (생성/리플랜 공용)."""

from __future__ import annotations

import asyncio

from app.config import Settings
from app.schemas.itinerary import (
    AirportArrivalView,
    AirportDepartureView,
    ItineraryDayView,
    ItineraryItemView,
    LlmItineraryResponse,
)
from app.schemas.place import Place, PlaceSearchRequest
from app.schemas.route import BookingCta, RouteLeg, Waypoint
from app.services.place_search import search_places
from app.services.lodging_cta import lodging_booking_cta
from app.services.rail_cta import (
    airport_booking_cta_fallback,
    booking_cta_for_leg,
    resolve_airport_rule,
)
from app.services.kkday_links import kkday_esim_cta
from app.services.flight_windows import (
    DEFAULT_AIRPORT_CHECKIN_BUFFER_MINUTES,
    arrive_airport_by_jst,
    leave_city_by_jst,
    parse_hhmm,
)
from app.services.travel_choice import choose_best_leg


def _attach_cta(leg: RouteLeg, cta: BookingCta | None) -> RouteLeg:
    if cta is None:
        return leg
    return leg.model_copy(update={"booking_cta": cta})


async def _find_airport_place(
    settings: Settings,
    airport_query: str,
    *,
    language_code: str,
) -> Place | None:
    result = await search_places(
        settings,
        PlaceSearchRequest(
            query=airport_query,
            language_code=language_code,
            max_results=5,
            included_type="airport",
        ),
    )
    if result.places:
        return result.places[0]
    result = await search_places(
        settings,
        PlaceSearchRequest(
            query=airport_query,
            language_code=language_code,
            max_results=5,
        ),
    )
    for p in result.places:
        types = " ".join(p.types).lower()
        name = (p.name or "").lower()
        if "airport" in types or "공항" in name or "airport" in name:
            return p
    return None


async def _airport_leg_and_cta(
    settings: Settings,
    *,
    region: str | None,
    airport: Place | None,
    city_place: Place | None,
    to_airport: bool,
    include_travel_times: bool,
    travel_mode: str,
    language_code: str,
) -> tuple[RouteLeg | None, BookingCta | None]:
    """공항↔시내 Routes + CTA. to_airport=True면 시내→공항."""
    travel: RouteLeg | None = None
    if include_travel_times and airport is not None and city_place is not None:
        preferred = travel_mode if travel_mode.upper() != "AUTO" else "TRANSIT"
        if to_airport:
            origin = Waypoint(lat=city_place.location.lat, lng=city_place.location.lng)
            dest = Waypoint(lat=airport.location.lat, lng=airport.location.lng)
        else:
            origin = Waypoint(lat=airport.location.lat, lng=airport.location.lng)
            dest = Waypoint(lat=city_place.location.lat, lng=city_place.location.lng)
        travel = await choose_best_leg(
            settings,
            origin=origin,
            destination=dest,
            language_code=language_code,
            preferred_mode=preferred,
        )
        cta = booking_cta_for_leg(settings, travel)
        if cta is None:
            cta = airport_booking_cta_fallback(
                settings, region, transit_lines=travel.transit_lines
            )
        travel = _attach_cta(travel, cta)

    if travel is None:
        top = airport_booking_cta_fallback(settings, region)
    elif travel.booking_cta is None:
        top = airport_booking_cta_fallback(
            settings, region, transit_lines=travel.transit_lines
        )
    else:
        top = travel.booking_cta
    return travel, top


async def _build_arrival(
    settings: Settings,
    *,
    first_region: str | None,
    first_place: Place | None,
    include_travel_times: bool,
    travel_mode: str,
    language_code: str,
    arrival_airport_query: str | None = None,
) -> AirportArrivalView | None:
    rule = resolve_airport_rule(
        first_region, arrival_airport_query=arrival_airport_query
    )
    if not rule:
        return None

    airport = await _find_airport_place(
        settings, rule.airport_query, language_code=language_code
    )
    travel, booking = await _airport_leg_and_cta(
        settings,
        region=first_region,
        airport=airport,
        city_place=first_place,
        to_airport=False,
        include_travel_times=include_travel_times,
        travel_mode=travel_mode,
        language_code=language_code,
    )
    return AirportArrivalView(
        airport_query=rule.airport_query,
        airport=airport,
        travel_to_first=travel,
        booking_cta=booking,
        connectivity_cta=kkday_esim_cta(settings, region=first_region),
    )


async def _build_departure(
    settings: Settings,
    *,
    last_region: str | None,
    last_place: Place | None,
    include_travel_times: bool,
    travel_mode: str,
    language_code: str,
    arrival_airport_query: str | None = None,
    return_departure_jst: str | None = None,
) -> AirportDepartureView | None:
    """귀국편 기준 시내→공항. 공항 쿼리는 도착 공항 선택값 우선(왕복 동일 공항)."""
    rule = resolve_airport_rule(
        last_region, arrival_airport_query=arrival_airport_query
    )
    if not rule:
        return None

    airport = await _find_airport_place(
        settings, rule.airport_query, language_code=language_code
    )
    travel, booking = await _airport_leg_and_cta(
        settings,
        region=last_region,
        airport=airport,
        city_place=last_place,
        to_airport=True,
        include_travel_times=include_travel_times,
        travel_mode=travel_mode,
        language_code=language_code,
    )

    arrive_by = None
    leave_by = None
    buffer_note = None
    checkin = DEFAULT_AIRPORT_CHECKIN_BUFFER_MINUTES
    parsed = parse_hhmm(return_departure_jst)
    if parsed:
        arrive_by = arrive_airport_by_jst(*parsed, checkin)
        travel_sec = travel.duration_seconds if travel else None
        leave_by = leave_city_by_jst(
            *parsed,
            checkin_buffer=checkin,
            travel_seconds=travel_sec,
        )
        travel_part = (
            f"이동 약 {int(round(travel_sec / 60))}분(Routes)"
            if travel_sec
            else "이동시간은 경로 확인 후 여유를 더 두세요"
        )
        buffer_note = (
            f"귀국편 {return_departure_jst} (JST) · 체크인 여유 {checkin}분 → "
            f"공항 {arrive_by}까지 도착 권장 · 시내 출발 권장 {leave_by} ({travel_part})"
        )

    return AirportDepartureView(
        airport_query=rule.airport_query,
        airport=airport,
        travel_from_last=travel,
        booking_cta=booking,
        return_departure_jst=return_departure_jst,
        arrive_airport_by_jst=arrive_by,
        leave_city_by_jst=leave_by,
        checkin_buffer_minutes=checkin if parsed else None,
        buffer_note=buffer_note,
    )


def _checkout_date(dates: list[str], day_date: str) -> str | None:
    try:
        idx = dates.index(day_date)
    except ValueError:
        return None
    if idx + 1 < len(dates):
        return dates[idx + 1]
    from datetime import date, timedelta

    try:
        return (date.fromisoformat(day_date) + timedelta(days=1)).isoformat()
    except ValueError:
        return None


async def hydrate_itinerary(
    settings: Settings,
    cleaned: LlmItineraryResponse,
    places_by_id: dict[str, Place],
    *,
    include_travel_times: bool,
    travel_mode: str,
    language_code: str = "ko",
    day_regions: dict[str, str] | None = None,
    arrival_airport_query: str | None = None,
    return_departure_jst: str | None = None,
) -> list[ItineraryDayView]:
    """장소는 이미 확정 → 구간 Routes는 좌표만으로 전부 병렬 계산."""
    regions = day_regions or {}
    all_dates = [d.date for d in cleaned.days]
    last_index = len(cleaned.days) - 1

    # (day_i, item_i, origin_region, day_region, origin, dest)
    route_jobs: list[tuple[int, int, str | None, str | None, Waypoint, Waypoint]] = []
    prev_place: Place | None = None
    prev_region: str | None = None
    day_item_meta: list[list[tuple]] = []

    for day_index, day in enumerate(cleaned.days):
        day_region = regions.get(day.date)
        day_prev = prev_place
        day_prev_region = prev_region
        meta: list[tuple] = []
        for item_index, item in enumerate(day.items):
            place = places_by_id[item.place_id]
            origin_place = day_prev if item_index == 0 else prev_place
            origin_region = day_prev_region if item_index == 0 else prev_region
            meta.append((item, place, origin_region, day_region))
            if include_travel_times and origin_place is not None:
                route_jobs.append(
                    (
                        day_index,
                        item_index,
                        origin_region,
                        day_region,
                        Waypoint(
                            lat=origin_place.location.lat,
                            lng=origin_place.location.lng,
                        ),
                        Waypoint(lat=place.location.lat, lng=place.location.lng),
                    )
                )
            prev_place = place
            prev_region = day_region
        day_item_meta.append(meta)

    route_map: dict[tuple[int, int], RouteLeg] = {}
    if route_jobs:
        # 과도한 병렬은 TLS/연결 실패를 늘려 오히려 느려짐 → 상한
        sem = asyncio.Semaphore(6)

        async def _leg(origin: Waypoint, dest: Waypoint) -> RouteLeg:
            async with sem:
                return await choose_best_leg(
                    settings,
                    origin=origin,
                    destination=dest,
                    language_code=language_code,
                    preferred_mode=travel_mode,
                )

        legs = await asyncio.gather(
            *[_leg(origin, dest) for *_, origin, dest in route_jobs]
        )
        for (day_i, item_i, origin_region, day_region, _, _), leg in zip(
            route_jobs, legs, strict=True
        ):
            cta = booking_cta_for_leg(
                settings,
                leg,
                from_region=origin_region,
                to_region=day_region,
                allow_region_fallback=True,
            )
            route_map[(day_i, item_i)] = _attach_cta(leg, cta)

    first_region = regions.get(cleaned.days[0].date) if cleaned.days else None
    first_place = None
    if cleaned.days and cleaned.days[0].items:
        first_place = places_by_id.get(cleaned.days[0].items[0].place_id)
    last_region = regions.get(cleaned.days[-1].date) if cleaned.days else None
    last_place = None
    if cleaned.days and cleaned.days[-1].items:
        last_place = places_by_id.get(cleaned.days[-1].items[-1].place_id)

    async def _no_arrival() -> AirportArrivalView | None:
        return None

    async def _no_departure() -> AirportDepartureView | None:
        return None

    arrival, departure = await asyncio.gather(
        (
            _build_arrival(
                settings,
                first_region=first_region,
                first_place=first_place,
                include_travel_times=include_travel_times,
                travel_mode=travel_mode,
                language_code=language_code,
                arrival_airport_query=arrival_airport_query,
            )
            if cleaned.days and first_place
            else _no_arrival()
        ),
        (
            _build_departure(
                settings,
                last_region=last_region,
                last_place=last_place,
                include_travel_times=include_travel_times,
                travel_mode=travel_mode,
                language_code=language_code,
                arrival_airport_query=arrival_airport_query,
                return_departure_jst=return_departure_jst,
            )
            if cleaned.days and (last_place or arrival_airport_query)
            else _no_departure()
        ),
    )

    day_views: list[ItineraryDayView] = []
    for day_index, day in enumerate(cleaned.days):
        day_region = regions.get(day.date)
        item_views: list[ItineraryItemView] = []
        for item_index, (item, place, _or, _dr) in enumerate(day_item_meta[day_index]):
            place_view = place.model_copy(update={"ai_description": item.reason})
            lodging_cta = lodging_booking_cta(
                settings,
                place,
                region=day_region,
                check_in=day.date,
                check_out=_checkout_date(all_dates, day.date),
            )
            item_views.append(
                ItineraryItemView(
                    place=place_view,
                    order=item.order,
                    time_slot=item.time_slot,
                    ai_description=item.reason,
                    travel_from_previous=route_map.get((day_index, item_index)),
                    booking_cta=lodging_cta,
                )
            )
        day_views.append(
            ItineraryDayView(
                date=day.date,
                region=day_region,
                items=item_views,
                arrival_from_airport=arrival if day_index == 0 else None,
                departure_to_airport=departure if day_index == last_index else None,
            )
        )
    return day_views
