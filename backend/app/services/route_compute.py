"""경로 계산 오케스트레이션 — MOCK / 실제 Routes API + 캐시."""

from __future__ import annotations

from app.config import Settings
from app.schemas.route import (
    RouteComputeRequest,
    RouteComputeResponse,
    RouteMatrixRequest,
    RouteMatrixResponse,
)
from app.services import mock_routes
from app.services.cache import cache_key, get_cache
from app.services.routes_service import RoutesService


def _wp(w) -> dict:
    return {"lat": w.lat, "lng": w.lng, "place_id": w.place_id}


async def compute_route(settings: Settings, request: RouteComputeRequest) -> RouteComputeResponse:
    if settings.use_mock_routes:
        return await mock_routes.MOCK_compute_route(request)

    key = cache_key(
        "route",
        {
            "o": _wp(request.origin),
            "d": _wp(request.destination),
            "mode": request.travel_mode.value,
            "lang": request.language_code,
        },
    )
    cache = get_cache()
    cached = await cache.get_json(key)
    if cached:
        data = dict(cached)
        data["source"] = "cache_routes"
        return RouteComputeResponse.model_validate(data)

    async with RoutesService(settings) as service:
        result = await service.compute_route(request)
    await cache.set_json(
        key,
        result.model_dump(mode="json"),
        ttl=settings.cache_ttl_routes_seconds,
    )
    return result


async def compute_matrix(settings: Settings, request: RouteMatrixRequest) -> RouteMatrixResponse:
    if settings.use_mock_routes:
        return await mock_routes.MOCK_compute_matrix(request)

    key = cache_key(
        "matrix",
        {
            "o": [_wp(o) for o in request.origins],
            "d": [_wp(d) for d in request.destinations],
            "mode": request.travel_mode.value,
            "lang": request.language_code,
        },
    )
    cache = get_cache()
    cached = await cache.get_json(key)
    if cached:
        data = dict(cached)
        data["source"] = "cache_routes"
        return RouteMatrixResponse.model_validate(data)

    async with RoutesService(settings) as service:
        result = await service.compute_matrix(request)
    await cache.set_json(
        key,
        result.model_dump(mode="json"),
        ttl=settings.cache_ttl_routes_seconds,
    )
    return result
