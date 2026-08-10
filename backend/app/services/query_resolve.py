"""필수 검색어 해석 — Text Search 실패 시 Autocomplete로 Places 후보만 보강.

AI가 장소 이름을 고치지 않는다. Google Autocomplete/Details 응답만 사용.
Docs: https://developers.google.com/maps/documentation/places/web-service/place-autocomplete
"""

from __future__ import annotations

from app.config import Settings
from app.schemas.place import (
    Place,
    PlaceAutocompleteRequest,
    PlaceSearchRequest,
)
from app.schemas.query_hint import PlaceSuggestion, SearchHint
from app.services.place_search import autocomplete_places, get_place_by_id, search_places
from app.services.places_service import PlacesApiError


def _keyword_hits(query: str, place: Place) -> bool:
    """검색어가 결과 이름/주소에 실질적으로 닿는지 — MOCK 폴백 잡음 제거용."""
    raw = query.strip().lower()
    for noise in ("japan", "일본"):
        raw = raw.replace(noise, " ")
    tokens = [t for t in raw.split() if len(t) >= 2]
    if not tokens:
        return False
    blob = f"{place.name or ''} {place.formatted_address or ''}".lower()
    # 가장 긴 토큰이 포함되거나, 토큰 절반 이상 매칭
    longest = max(tokens, key=len)
    if longest in blob:
        return True
    hits = sum(1 for t in tokens if t in blob)
    return hits >= max(1, (len(tokens) + 1) // 2)


async def resolve_must_have_query(
    settings: Settings,
    *,
    keyword: str,
    region: str,
    kind: str,
    language_code: str = "ko",
    max_results: int = 12,
    bias_lat: float | None = None,
    bias_lng: float | None = None,
) -> tuple[list[Place], SearchHint]:
    """필수 음식/관광 검색. 오타면 Autocomplete place_id → Details로 후보 확보."""
    kw = keyword.strip()
    region = region.strip()
    scoped = f"{region} {kw} Japan".strip() if region else f"{kw} Japan"

    text = await search_places(
        settings,
        PlaceSearchRequest(
            query=scoped,
            language_code=language_code,
            max_results=max_results,
            region_code="JP",
            bias_lat=bias_lat,
            bias_lng=bias_lng,
            bias_radius_meters=35000.0,
            strict_location=bias_lat is not None and bias_lng is not None,
        ),
        strict_empty=True,
    )
    hit = [p for p in text.places if p.place_id and _keyword_hits(kw, p)]
    if hit:
        return hit, SearchHint(
            kind=kind,
            query=kw,
            region=region,
            status="matched",
            message=f"‘{kw}’ Places 검색 일치",
            suggestions=[],
        )

    ac = await autocomplete_places(
        settings,
        PlaceAutocompleteRequest(
            input=f"{region} {kw}".strip() if region else kw,
            language_code=language_code,
            region_code="JP",
            bias_lat=bias_lat,
            bias_lng=bias_lng,
            bias_radius_meters=35000.0,
            max_suggestions=5,
        ),
    )

    places: list[Place] = []
    suggestions: list[PlaceSuggestion] = []
    for s in ac.suggestions:
        try:
            place = await get_place_by_id(settings, s.place_id)
        except PlacesApiError:
            continue
        if not place.place_id:
            continue
        places.append(place)
        suggestions.append(
            PlaceSuggestion(
                place_id=place.place_id,
                name=place.name,
                formatted_address=place.formatted_address,
            )
        )

    if places:
        names = " / ".join(p.name for p in places[:3])
        return places, SearchHint(
            kind=kind,
            query=kw,
            region=region,
            status="autocorrected",
            message=(
                f"‘{kw}’로 바로 찾지 못해 Places 자동완성을 썼어요. "
                f"일정에는 「{names}」 후보를 넣었습니다. 다르면 수정해 주세요."
            ),
            suggestions=suggestions,
        )

    return [], SearchHint(
        kind=kind,
        query=kw,
        region=region,
        status="not_found",
        message=(
            f"‘{kw}’를 Places에서 찾지 못했어요. 맞춤법·지역을 확인해 다시 입력하거나 "
            f"자동완성 후보를 골라 주세요. 없는 장소는 AI가 만들지 않습니다."
        ),
        suggestions=[],
    )
