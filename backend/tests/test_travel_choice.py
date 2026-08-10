"""도보 vs 대중교통 선택 단위 테스트."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.route import RouteComputeResponse, RouteLeg, TravelMode, Waypoint
from app.services.routes_service import RoutesApiError
from app.services.travel_choice import choose_best_leg


def _wp(lat: float, lng: float) -> Waypoint:
    return Waypoint(lat=lat, lng=lng)


def _route(mode: TravelMode, seconds: int, meters: int) -> RouteComputeResponse:
    return RouteComputeResponse(
        distance_meters=meters,
        duration_seconds=seconds,
        static_duration_seconds=seconds,
        encoded_polyline="abc",
        travel_mode=mode,
        source="MOCK_routes",
        legs=[
            RouteLeg(
                distance_meters=meters,
                duration_seconds=seconds,
                static_duration_seconds=seconds,
                encoded_polyline="abc",
            )
        ],
    )


@pytest.mark.asyncio
async def test_short_walk_skips_transit():
    walk = _route(TravelMode.walk, 600, 800)  # 10분, 800m
    transit = _route(TravelMode.transit, 900, 1200)

    async def side_effect(_settings, request):
        if request.travel_mode == TravelMode.walk:
            return walk
        return transit

    with patch(
        "app.services.travel_choice.compute_route",
        new=AsyncMock(side_effect=side_effect),
    ) as mock_compute:
        leg = await choose_best_leg(
            settings=None,  # type: ignore[arg-type]
            origin=_wp(34.7, 135.5),
            destination=_wp(34.71, 135.51),
            preferred_mode="AUTO",
        )
    assert leg.travel_mode == TravelMode.walk
    assert leg.mode_label == "도보"
    # walk+transit 병렬 후 짧은 도보 채택 (drive 추가 호출 없음)
    assert mock_compute.await_count == 2
    assert "walking" in (leg.google_maps_dir_uri or "")


@pytest.mark.asyncio
async def test_long_walk_prefers_faster_transit():
    walk = _route(TravelMode.walk, 2400, 3000)  # 40분
    transit = _route(TravelMode.transit, 900, 3200)  # 15분

    async def side_effect(_settings, request):
        if request.travel_mode == TravelMode.walk:
            return walk
        return transit

    with patch(
        "app.services.travel_choice.compute_route",
        new=AsyncMock(side_effect=side_effect),
    ):
        leg = await choose_best_leg(
            settings=None,  # type: ignore[arg-type]
            origin=_wp(34.7, 135.5),
            destination=_wp(34.75, 135.55),
            preferred_mode="AUTO",
        )
    assert leg.travel_mode == TravelMode.transit
    assert leg.mode_label == "대중교통"
    assert "transit" in (leg.google_maps_dir_uri or "")


@pytest.mark.asyncio
async def test_force_walk_mode():
    walk = _route(TravelMode.walk, 3000, 4000)
    with patch(
        "app.services.travel_choice.compute_route",
        new=AsyncMock(return_value=walk),
    ) as mock_compute:
        leg = await choose_best_leg(
            settings=None,  # type: ignore[arg-type]
            origin=_wp(34.7, 135.5),
            destination=_wp(34.75, 135.55),
            preferred_mode="WALK",
        )
    assert leg.travel_mode == TravelMode.walk
    assert mock_compute.await_count == 1


@pytest.mark.asyncio
async def test_transit_failure_falls_back_without_raising():
    async def side_effect(_settings, request):
        if request.travel_mode == TravelMode.transit:
            raise RoutesApiError("경로를 찾을 수 없습니다.", status_code=404)
        if request.travel_mode == TravelMode.drive:
            return _route(TravelMode.drive, 2400, 40000)
        raise RoutesApiError("no", status_code=404)

    with patch(
        "app.services.travel_choice.compute_route",
        new=AsyncMock(side_effect=side_effect),
    ):
        leg = await choose_best_leg(
            settings=None,  # type: ignore[arg-type]
            origin=_wp(34.43, 135.24),
            destination=_wp(34.70, 135.50),
            preferred_mode="TRANSIT",
        )
    assert leg.travel_mode == TravelMode.drive
    assert leg.duration_seconds == 2400


@pytest.mark.asyncio
async def test_all_modes_fail_returns_maps_link_leg():
    with patch(
        "app.services.travel_choice.compute_route",
        new=AsyncMock(side_effect=RoutesApiError("경로를 찾을 수 없습니다.", status_code=404)),
    ):
        leg = await choose_best_leg(
            settings=None,  # type: ignore[arg-type]
            origin=_wp(34.43, 135.24),
            destination=_wp(34.70, 135.50),
            preferred_mode="TRANSIT",
        )
    assert leg.mode_label == "경로 확인 필요"
    assert leg.duration_seconds is None
    assert "google.com/maps/dir" in (leg.google_maps_dir_uri or "")


@pytest.mark.asyncio
async def test_connect_error_falls_back_without_raising():
    """네트워크 ConnectError가 일정 생성 500으로 전파되지 않아야 함."""
    import httpx

    with patch(
        "app.services.travel_choice.compute_route",
        new=AsyncMock(side_effect=httpx.ConnectError("boom")),
    ):
        leg = await choose_best_leg(
            settings=None,  # type: ignore[arg-type]
            origin=_wp(34.43, 135.24),
            destination=_wp(34.70, 135.50),
            preferred_mode="AUTO",
        )
    assert leg.mode_label == "경로 확인 필요"
    assert leg.duration_seconds is None
