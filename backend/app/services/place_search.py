"""장소 검색 오케스트레이션 — MOCK / 실제 API + 캐시."""

from __future__ import annotations

from app.config import Settings
from app.schemas.place import (
    Place,
    PlaceAutocompleteRequest,
    PlaceAutocompleteResponse,
    PlaceSearchRequest,
    PlaceSearchResponse,
)
from app.services import mock_places
from app.services.cache import cache_key, get_cache
from app.services.places_service import PlacesApiError, PlacesService


async def search_places(
    settings: Settings,
    request: PlaceSearchRequest,
    *,
    strict_empty: bool = False,
) -> PlaceSearchResponse:
    if settings.use_mock_places:
        places = (
            await mock_places.MOCK_search_text_strict(request)
            if strict_empty
            else await mock_places.MOCK_search_text(request)
        )
        return PlaceSearchResponse(places=places, source="MOCK_places", query=request.query)

    key = cache_key(
        "places_search",
        {
            "q": request.query,
            "lang": request.language_code,
            "n": request.max_results,
            "type": request.included_type,
            "min": request.min_rating,
            "lat": request.bias_lat,
            "lng": request.bias_lng,
            "r": request.bias_radius_meters,
            "strict": request.strict_location,
            "rc": request.region_code,
        },
    )
    cache = get_cache()
    cached = await cache.get_json(key)
    if cached and isinstance(cached, dict) and "places" in cached:
        places = [Place.model_validate(p) for p in cached["places"]]
        return PlaceSearchResponse(places=places, source="cache_places", query=request.query)

    async with PlacesService(settings) as service:
        places = await service.search_text(request)

    await cache.set_json(key, {"places": [p.model_dump(mode="json") for p in places]})
    return PlaceSearchResponse(places=places, source="google_places", query=request.query)


async def autocomplete_places(
    settings: Settings, request: PlaceAutocompleteRequest
) -> PlaceAutocompleteResponse:
    if settings.use_mock_places:
        suggestions = await mock_places.MOCK_autocomplete(request)
        return PlaceAutocompleteResponse(
            suggestions=suggestions, source="MOCK_places", input=request.input
        )

    key = cache_key(
        "places_ac",
        {
            "q": request.input,
            "lang": request.language_code,
            "lat": request.bias_lat,
            "lng": request.bias_lng,
            "n": request.max_suggestions,
        },
    )
    cache = get_cache()
    cached = await cache.get_json(key)
    if cached and isinstance(cached, dict) and "suggestions" in cached:
        return PlaceAutocompleteResponse.model_validate({**cached, "source": "cache_places"})

    async with PlacesService(settings) as service:
        suggestions = await service.autocomplete(request)
    payload = {
        "suggestions": [s.model_dump(mode="json") for s in suggestions],
        "input": request.input,
        "source": "google_places",
    }
    await cache.set_json(key, payload)
    return PlaceAutocompleteResponse(
        suggestions=suggestions, source="google_places", input=request.input
    )


async def get_place_by_id(settings: Settings, place_id: str) -> Place:
    if settings.use_mock_places:
        place = await mock_places.MOCK_get_place(place_id)
        if place is None:
            raise PlacesApiError(f"MOCK에서 place_id를 찾을 수 없습니다: {place_id}", status_code=404)
        return place

    key = cache_key("place_detail", {"id": place_id})
    cache = get_cache()
    cached = await cache.get_json(key)
    if cached:
        return Place.model_validate(cached)

    async with PlacesService(settings) as service:
        place = await service.get_place(place_id)
    await cache.set_json(key, place.model_dump(mode="json"))
    return place
