from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.config import Settings, get_settings
from app.schemas.place import (
    Place,
    PlaceAutocompleteRequest,
    PlaceAutocompleteResponse,
    PlaceSearchRequest,
    PlaceSearchResponse,
)
from app.services.place_search import autocomplete_places, get_place_by_id, search_places
from app.services.places_service import PlacesApiError, PlacesService

router = APIRouter(prefix="/places", tags=["places"])


@router.get("/search", response_model=PlaceSearchResponse)
async def search(
    query: str = Query(..., min_length=1, description="예: 오사카 라멘"),
    language_code: str = "ko",
    max_results: int = Query(20, ge=1, le=20),
    bias_lat: float | None = None,
    bias_lng: float | None = None,
    included_type: str | None = None,
    min_rating: float | None = Query(None, ge=0, le=5),
    settings: Settings = Depends(get_settings),
) -> PlaceSearchResponse:
    """후보 장소 수집 — LLM 미개입. Places API 또는 MOCK_만."""
    request = PlaceSearchRequest(
        query=query,
        language_code=language_code,
        max_results=max_results,
        bias_lat=bias_lat,
        bias_lng=bias_lng,
        included_type=included_type,
        min_rating=min_rating,
    )
    try:
        return await search_places(settings, request)
    except PlacesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc


@router.get("/autocomplete", response_model=PlaceAutocompleteResponse)
async def autocomplete(
    input: str = Query(..., min_length=1, max_length=120, description="예: 아키하바라"),
    language_code: str = "ko",
    bias_lat: float | None = None,
    bias_lng: float | None = None,
    max_suggestions: int = Query(5, ge=1, le=10),
    settings: Settings = Depends(get_settings),
) -> PlaceAutocompleteResponse:
    """Places Autocomplete — 오타·부분 입력 후보. LLM 미개입."""
    request = PlaceAutocompleteRequest(
        input=input,
        language_code=language_code,
        bias_lat=bias_lat,
        bias_lng=bias_lng,
        max_suggestions=max_suggestions,
    )
    try:
        return await autocomplete_places(settings, request)
    except PlacesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc


@router.get("/photo")
async def place_photo(
    name: str = Query(..., min_length=10, description="places/{id}/photos/{ref}"),
    max_width_px: int = Query(800, ge=1, le=4800),
    max_height_px: int | None = Query(None, ge=1, le=4800),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Place Photos (New) 프록시 — API 키는 서버에만 둠."""
    if settings.use_mock_places or name.startswith("places/ChIJMOCK_"):
        # 1x1 투명 PNG
        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
            b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return Response(content=png, media_type="image/png")
    try:
        async with PlacesService(settings) as service:
            content, content_type = await service.get_photo_media(
                name,
                max_width_px=max_width_px,
                max_height_px=max_height_px,
            )
        return Response(
            content=content,
            media_type=content_type.split(";")[0].strip() or "image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except PlacesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc


@router.get("/{place_id}", response_model=Place)
async def place_details(
    place_id: str,
    settings: Settings = Depends(get_settings),
) -> Place:
    """place_id 재검증 — LLM이 준 id를 실제 데이터로 덮어쓸 때 사용."""
    try:
        return await get_place_by_id(settings, place_id)
    except PlacesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc
