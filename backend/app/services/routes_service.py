"""Google Routes API — Compute Routes / Compute Route Matrix.

Docs:
- Compute Routes: https://developers.google.com/maps/documentation/routes/compute-route-over
- Route Matrix: https://developers.google.com/maps/documentation/routes/compute_route_matrix
- REST: https://developers.google.com/maps/documentation/routes/reference/rest
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import Settings
from app.schemas.route import (
    RouteComputeRequest,
    RouteComputeResponse,
    RouteLeg,
    RouteMatrixElement,
    RouteMatrixRequest,
    RouteMatrixResponse,
    TravelMode,
    Waypoint,
    parse_duration_seconds,
)
from app.services.transit_parse import TRANSIT_FIELD_MASK_EXTRA, parse_transit_lines_from_leg

COMPUTE_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
COMPUTE_MATRIX_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"

ROUTES_FIELD_MASK_BASE = ",".join(
    [
        "routes.duration",
        "routes.staticDuration",
        "routes.distanceMeters",
        "routes.polyline.encodedPolyline",
        "routes.legs.duration",
        "routes.legs.staticDuration",
        "routes.legs.distanceMeters",
        "routes.legs.polyline.encodedPolyline",
    ]
)

MATRIX_FIELD_MASK = ",".join(
    [
        "originIndex",
        "destinationIndex",
        "duration",
        "staticDuration",
        "distanceMeters",
        "status",
        "condition",
    ]
)


class RoutesApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _waypoint_payload(wp: Waypoint) -> dict[str, Any]:
    # https://developers.google.com/maps/documentation/routes/reference/rest/v2/Waypoint
    if wp.place_id:
        return {"placeId": wp.place_id}
    return {
        "location": {
            "latLng": {
                "latitude": wp.lat,
                "longitude": wp.lng,
            }
        }
    }


class RoutesService:
    """실제 Routes API 호출. MOCK은 mock_routes.py에만."""

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> RoutesService:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    def _require_key(self) -> str:
        key = self._settings.google_maps_api_key
        if not key:
            raise RoutesApiError(
                "GOOGLE_MAPS_API_KEY가 없습니다. .env를 설정하거나 USE_MOCK_ROUTES=true를 사용하세요."
            )
        return key

    def _body_travel(self, mode: TravelMode, language_code: str) -> dict[str, Any]:
        body: dict[str, Any] = {
            "travelMode": mode.value,
            "languageCode": language_code,
        }
        # TRAFFIC_AWARE는 DRIVE/TWO_WHEELER만. WALK/TRANSIT에는 넣지 않음.
        if mode in (TravelMode.drive, TravelMode.two_wheeler):
            body["routingPreference"] = "TRAFFIC_AWARE"
        # TRANSIT은 departureTime 또는 arrivalTime 필수
        if mode == TravelMode.transit:
            body["departureTime"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return body

    def _routes_field_mask(self, mode: TravelMode) -> str:
        if mode == TravelMode.transit:
            return f"{ROUTES_FIELD_MASK_BASE},{TRANSIT_FIELD_MASK_EXTRA}"
        return ROUTES_FIELD_MASK_BASE

    async def compute_route(self, request: RouteComputeRequest) -> RouteComputeResponse:
        assert self._client is not None
        api_key = self._require_key()
        body = {
            "origin": _waypoint_payload(request.origin),
            "destination": _waypoint_payload(request.destination),
            **self._body_travel(request.travel_mode, request.language_code),
        }
        try:
            response = await self._client.post(
                COMPUTE_ROUTES_URL,
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": self._routes_field_mask(request.travel_mode),
                },
                json=body,
            )
        except httpx.HTTPError as exc:
            raise RoutesApiError(
                f"Compute Routes 네트워크 오류: {exc}",
                status_code=502,
            ) from exc
        if response.status_code >= 400:
            raise RoutesApiError(
                f"Compute Routes 실패: {response.status_code} {response.text}",
                status_code=response.status_code,
            )
        payload = response.json()
        routes = payload.get("routes") or []
        if not routes:
            raise RoutesApiError("경로를 찾을 수 없습니다.", status_code=404)

        route = routes[0]
        legs: list[RouteLeg] = []
        for leg in route.get("legs") or []:
            transit_lines = (
                parse_transit_lines_from_leg(leg)
                if request.travel_mode == TravelMode.transit
                else []
            )
            legs.append(
                RouteLeg(
                    distance_meters=leg.get("distanceMeters"),
                    duration_seconds=parse_duration_seconds(leg.get("duration")),
                    static_duration_seconds=parse_duration_seconds(leg.get("staticDuration")),
                    encoded_polyline=(leg.get("polyline") or {}).get("encodedPolyline"),
                    transit_lines=transit_lines,
                )
            )
        polyline = (route.get("polyline") or {}).get("encodedPolyline")
        # leg에 polyline이 없으면 전체 경로 polyline을 첫 leg에 부여 (지도 표시용)
        if polyline and legs and not legs[0].encoded_polyline:
            legs[0] = legs[0].model_copy(update={"encoded_polyline": polyline})
        return RouteComputeResponse(
            distance_meters=route.get("distanceMeters"),
            duration_seconds=parse_duration_seconds(route.get("duration")),
            static_duration_seconds=parse_duration_seconds(route.get("staticDuration")),
            encoded_polyline=polyline,
            travel_mode=request.travel_mode,
            source="google_routes",
            legs=legs,
        )

    async def compute_matrix(self, request: RouteMatrixRequest) -> RouteMatrixResponse:
        assert self._client is not None
        api_key = self._require_key()
        body = {
            "origins": [{"waypoint": _waypoint_payload(o)} for o in request.origins],
            "destinations": [{"waypoint": _waypoint_payload(d)} for d in request.destinations],
            **self._body_travel(request.travel_mode, request.language_code),
        }
        try:
            response = await self._client.post(
                COMPUTE_MATRIX_URL,
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": MATRIX_FIELD_MASK,
                },
                json=body,
            )
        except httpx.HTTPError as exc:
            raise RoutesApiError(
                f"Compute Route Matrix 네트워크 오류: {exc}",
                status_code=502,
            ) from exc
        if response.status_code >= 400:
            raise RoutesApiError(
                f"Compute Route Matrix 실패: {response.status_code} {response.text}",
                status_code=response.status_code,
            )
        raw_list = response.json()
        if not isinstance(raw_list, list):
            raise RoutesApiError("Route Matrix 응답 형식이 배열이 아닙니다.")

        elements: list[RouteMatrixElement] = []
        for item in raw_list:
            elements.append(
                RouteMatrixElement(
                    origin_index=item.get("originIndex", 0),
                    destination_index=item.get("destinationIndex", 0),
                    distance_meters=item.get("distanceMeters"),
                    duration_seconds=parse_duration_seconds(item.get("duration")),
                    static_duration_seconds=parse_duration_seconds(item.get("staticDuration")),
                    condition=item.get("condition"),
                )
            )
        return RouteMatrixResponse(
            elements=elements,
            travel_mode=request.travel_mode,
            source="google_routes",
        )
