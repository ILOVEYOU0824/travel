"""구간별 도보 vs 대중교통 비교 — Routes API만 사용, LLM 추정 금지.

경로 실패 시 다른 수단으로 폴백하고, 전부 실패해도 일정 생성은 막지 않는다.
"""

from __future__ import annotations

import asyncio
import logging

from app.config import Settings
from app.schemas.route import RouteComputeRequest, RouteComputeResponse, RouteLeg, TravelMode, Waypoint
from app.services.route_compute import compute_route
from app.services.routes_service import RoutesApiError
from app.services.transit_parse import transit_mode_label

logger = logging.getLogger("japantrip")

# 이보다 짧으면 도보 우선 (API 결과 기준)
WALK_OK_SECONDS = 20 * 60
WALK_OK_METERS = 1500


def _mode_label(mode: TravelMode, leg: RouteLeg | None = None) -> str:
    if mode == TravelMode.walk:
        return "도보"
    if mode == TravelMode.transit:
        if leg and leg.transit_lines:
            detail = transit_mode_label(leg.transit_lines)
            if detail:
                return detail
        return "대중교통"
    if mode == TravelMode.drive:
        return "자동차"
    if mode == TravelMode.bicycle:
        return "자전거"
    return mode.value


def _maps_dir_uri(origin: Waypoint, destination: Waypoint, mode: TravelMode) -> str | None:
    if origin.lat is None or origin.lng is None or destination.lat is None or destination.lng is None:
        return None
    travel = {
        TravelMode.walk: "walking",
        TravelMode.transit: "transit",
        TravelMode.drive: "driving",
        TravelMode.bicycle: "bicycling",
    }.get(mode, "walking")
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={origin.lat},{origin.lng}"
        f"&destination={destination.lat},{destination.lng}"
        f"&travelmode={travel}&hl=ko"
    )


def route_to_leg(route: RouteComputeResponse, origin: Waypoint, destination: Waypoint) -> RouteLeg:
    travel = route.legs[0] if route.legs else None
    polyline = route.encoded_polyline
    if travel and travel.encoded_polyline:
        polyline = travel.encoded_polyline
    elif travel is None:
        travel = RouteLeg(
            distance_meters=route.distance_meters,
            duration_seconds=route.duration_seconds,
            static_duration_seconds=route.static_duration_seconds,
        )
    transit_lines = list(travel.transit_lines) if travel else []
    draft = RouteLeg(
        distance_meters=travel.distance_meters if travel else route.distance_meters,
        duration_seconds=travel.duration_seconds if travel else route.duration_seconds,
        static_duration_seconds=(
            travel.static_duration_seconds if travel else route.static_duration_seconds
        ),
        encoded_polyline=polyline,
        travel_mode=route.travel_mode,
        transit_lines=transit_lines,
        google_maps_dir_uri=_maps_dir_uri(origin, destination, route.travel_mode),
    )
    return draft.model_copy(
        update={"mode_label": _mode_label(route.travel_mode, draft)},
    )


def _fallback_leg(origin: Waypoint, destination: Waypoint, mode: TravelMode = TravelMode.transit) -> RouteLeg:
    """API가 경로를 못 줄 때 — 시간 추정 없이 구글맵 링크만."""
    return RouteLeg(
        distance_meters=None,
        duration_seconds=None,
        static_duration_seconds=None,
        travel_mode=mode,
        mode_label="경로 확인 필요",
        google_maps_dir_uri=_maps_dir_uri(origin, destination, mode),
    )


async def _try_route(
    settings: Settings,
    *,
    origin: Waypoint,
    destination: Waypoint,
    mode: TravelMode,
    language_code: str,
) -> RouteComputeResponse | None:
    try:
        return await compute_route(
            settings,
            RouteComputeRequest(
                origin=origin,
                destination=destination,
                travel_mode=mode,
                language_code=language_code,
            ),
        )
    except RoutesApiError as exc:
        logger.info("Routes %s 실패: %s", mode.value, exc)
        return None
    except Exception as exc:
        # 네트워크(ConnectError 등)도 일정 생성 전체를 죽이지 않음
        logger.warning("Routes %s 예외 폴백: %s", mode.value, exc)
        return None


async def choose_best_leg(
    settings: Settings,
    *,
    origin: Waypoint,
    destination: Waypoint,
    language_code: str = "ko",
    preferred_mode: str | None = None,
) -> RouteLeg:
    """preferred_mode가 AUTO/비어 있으면 도보·대중교통을 비교해 선택.

    강제 모드 실패 시 다른 수단으로 폴백. 전부 실패해도 예외 대신 링크-only leg.
    """
    force = (preferred_mode or "AUTO").upper()

    if force in {"WALK", "TRANSIT", "DRIVE", "BICYCLE", "TWO_WHEELER"}:
        primary = TravelMode(force)
        # 1차만 우선 시도(속도). 실패 시 보조 1회만.
        backup = {
            TravelMode.transit: TravelMode.drive,
            TravelMode.walk: TravelMode.transit,
            TravelMode.drive: TravelMode.transit,
            TravelMode.bicycle: TravelMode.walk,
            TravelMode.two_wheeler: TravelMode.drive,
        }.get(primary)
        for mode in (primary, backup):
            if mode is None:
                continue
            route = await _try_route(
                settings,
                origin=origin,
                destination=destination,
                mode=mode,
                language_code=language_code,
            )
            if route is not None:
                return route_to_leg(route, origin, destination)
        return _fallback_leg(origin, destination, primary)

    # walk+transit 병렬 — 짧은 도보면 즉시 채택, 아니면 대중교통.
    walk, transit = await asyncio.gather(
        _try_route(
            settings,
            origin=origin,
            destination=destination,
            mode=TravelMode.walk,
            language_code=language_code,
        ),
        _try_route(
            settings,
            origin=origin,
            destination=destination,
            mode=TravelMode.transit,
            language_code=language_code,
        ),
    )

    if walk is not None:
        walk_sec = walk.duration_seconds if walk.duration_seconds is not None else 10**9
        walk_m = walk.distance_meters if walk.distance_meters is not None else 10**9
        if walk_sec <= WALK_OK_SECONDS and walk_m <= WALK_OK_METERS:
            return route_to_leg(walk, origin, destination)

    if transit is not None:
        return route_to_leg(transit, origin, destination)
    if walk is not None:
        return route_to_leg(walk, origin, destination)

    drive = await _try_route(
        settings,
        origin=origin,
        destination=destination,
        mode=TravelMode.drive,
        language_code=language_code,
    )
    if drive is not None:
        return route_to_leg(drive, origin, destination)
    return _fallback_leg(origin, destination)
