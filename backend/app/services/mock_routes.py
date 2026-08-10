"""MOCK_ 경로 데이터 — 배포 경로(routes_service)와 분리.

이동시간/거리를 추정·생성하지 않고, 픽스처에 저장된 API 형태 응답만 반환한다.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.schemas.route import (
    RouteComputeRequest,
    RouteComputeResponse,
    RouteLeg,
    RouteMatrixElement,
    RouteMatrixRequest,
    RouteMatrixResponse,
    TravelMode,
    parse_duration_seconds,
)
from app.services.transit_parse import parse_transit_lines_from_leg

_FIXTURE_ROUTE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "routes_compute_osaka.json"
_FIXTURE_TRANSIT = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "routes_compute_transit_haruka.json"
)
_FIXTURE_MATRIX = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "routes_matrix_osaka.json"
)


async def MOCK_compute_route(request: RouteComputeRequest) -> RouteComputeResponse:
    path = _FIXTURE_TRANSIT if request.travel_mode == TravelMode.transit else _FIXTURE_ROUTE
    raw = json.loads(path.read_text(encoding="utf-8"))
    route = (raw.get("routes") or [None])[0]
    if not route:
        raise ValueError("MOCK route fixture empty")
    legs = [
        RouteLeg(
            distance_meters=leg.get("distanceMeters"),
            duration_seconds=parse_duration_seconds(leg.get("duration")),
            static_duration_seconds=parse_duration_seconds(leg.get("staticDuration")),
            transit_lines=(
                parse_transit_lines_from_leg(leg)
                if request.travel_mode == TravelMode.transit
                else []
            ),
        )
        for leg in route.get("legs") or []
    ]
    return RouteComputeResponse(
        distance_meters=route.get("distanceMeters"),
        duration_seconds=parse_duration_seconds(route.get("duration")),
        static_duration_seconds=parse_duration_seconds(route.get("staticDuration")),
        encoded_polyline=(route.get("polyline") or {}).get("encodedPolyline"),
        travel_mode=request.travel_mode,
        source="MOCK_routes",
        legs=legs,
    )


async def MOCK_compute_matrix(request: RouteMatrixRequest) -> RouteMatrixResponse:
    raw_list = json.loads(_FIXTURE_MATRIX.read_text(encoding="utf-8"))
    elements = [
        RouteMatrixElement(
            origin_index=item.get("originIndex", 0),
            destination_index=item.get("destinationIndex", 0),
            distance_meters=item.get("distanceMeters"),
            duration_seconds=parse_duration_seconds(item.get("duration")),
            static_duration_seconds=parse_duration_seconds(item.get("staticDuration")),
            condition=item.get("condition"),
        )
        for item in raw_list
    ]
    # 요청 크기와 다르면 추정으로 채우지 않고 픽스처 그대로(개발용)
    return RouteMatrixResponse(
        elements=elements,
        travel_mode=request.travel_mode,
        source="MOCK_routes",
    )
