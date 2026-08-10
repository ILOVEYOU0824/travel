"""Routes API 단위 테스트 — 픽스처 + respx (키 없이 실행)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from app.config import Settings
from app.schemas.route import (
    RouteComputeRequest,
    RouteMatrixRequest,
    TravelMode,
    Waypoint,
    parse_duration_seconds,
)
from app.services.route_compute import compute_matrix, compute_route
from app.services.routes_service import COMPUTE_MATRIX_URL, COMPUTE_ROUTES_URL, RoutesService

FIXTURE_ROUTE = Path(__file__).parent / "fixtures" / "routes_compute_osaka.json"
FIXTURE_MATRIX = Path(__file__).parent / "fixtures" / "routes_matrix_osaka.json"


def test_parse_duration_seconds() -> None:
    assert parse_duration_seconds("160s") == 160
    assert parse_duration_seconds("0s") == 0
    assert parse_duration_seconds(None) is None
    assert parse_duration_seconds("abc") is None


@pytest.mark.asyncio
async def test_MOCK_compute_route() -> None:
    settings = Settings(use_mock_routes=True)
    result = await compute_route(
        settings,
        RouteComputeRequest(
            origin=Waypoint(lat=34.6687, lng=135.5013),
            destination=Waypoint(lat=34.6873, lng=135.5259),
            travel_mode=TravelMode.walk,
        ),
    )
    assert result.source == "MOCK_routes"
    assert result.duration_seconds == 2400
    assert result.distance_meters == 3200


@pytest.mark.asyncio
async def test_MOCK_compute_matrix() -> None:
    settings = Settings(use_mock_routes=True)
    result = await compute_matrix(
        settings,
        RouteMatrixRequest(
            origins=[Waypoint(lat=34.66, lng=135.50)],
            destinations=[Waypoint(lat=34.66, lng=135.50), Waypoint(lat=34.68, lng=135.52)],
            travel_mode=TravelMode.walk,
        ),
    )
    assert result.source == "MOCK_routes"
    assert len(result.elements) == 4
    assert result.elements[1].duration_seconds == 2400


@pytest.mark.asyncio
@respx.mock
async def test_routes_service_compute_route_parses_api() -> None:
    fixture = json.loads(FIXTURE_ROUTE.read_text(encoding="utf-8"))
    respx.post(COMPUTE_ROUTES_URL).mock(return_value=httpx.Response(200, json=fixture))
    settings = Settings(use_mock_routes=False, google_maps_api_key="test-key")
    async with RoutesService(settings) as service:
        result = await service.compute_route(
            RouteComputeRequest(
                origin=Waypoint(place_id="ChIJ_origin"),
                destination=Waypoint(place_id="ChIJ_dest"),
                travel_mode=TravelMode.walk,
            )
        )
    assert result.source == "google_routes"
    assert result.duration_seconds == 2400
    assert result.encoded_polyline.startswith("MOCK_")
    assert "WALK" in respx.calls[0].request.content.decode()


@pytest.mark.asyncio
@respx.mock
async def test_routes_service_matrix_parses_api() -> None:
    fixture = json.loads(FIXTURE_MATRIX.read_text(encoding="utf-8"))
    respx.post(COMPUTE_MATRIX_URL).mock(return_value=httpx.Response(200, json=fixture))
    settings = Settings(google_maps_api_key="test-key")
    async with RoutesService(settings) as service:
        result = await service.compute_matrix(
            RouteMatrixRequest(
                origins=[Waypoint(lat=34.66, lng=135.50)],
                destinations=[Waypoint(lat=34.68, lng=135.52)],
                travel_mode=TravelMode.transit,
            )
        )
    assert result.source == "google_routes"
    assert result.elements[0].condition == "ROUTE_EXISTS"
    assert "TRANSIT" in respx.calls[0].request.content.decode()
