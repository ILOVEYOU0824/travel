"""Place 스키마 — Google Places API (New) 응답 필드와 1:1 매핑.

공식 문서:
https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places
https://developers.google.com/maps/documentation/places/web-service/text-search
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PlaceCategory(str, Enum):
    attraction = "attraction"
    restaurant = "restaurant"
    cafe = "cafe"
    lodging = "lodging"
    other = "other"


# Places types → 내부 카테고리 (API types 원본은 types 필드에 그대로 보존)
_TYPE_TO_CATEGORY: dict[str, PlaceCategory] = {
    "lodging": PlaceCategory.lodging,
    "hotel": PlaceCategory.lodging,
    "cafe": PlaceCategory.cafe,
    "coffee_shop": PlaceCategory.cafe,
    "restaurant": PlaceCategory.restaurant,
    "ramen_restaurant": PlaceCategory.restaurant,
    "sushi_restaurant": PlaceCategory.restaurant,
    "meal_takeaway": PlaceCategory.restaurant,
    "food": PlaceCategory.restaurant,
    "tourist_attraction": PlaceCategory.attraction,
    "museum": PlaceCategory.attraction,
    "park": PlaceCategory.attraction,
    "shrine": PlaceCategory.attraction,
    "place_of_worship": PlaceCategory.attraction,
    "hindu_temple": PlaceCategory.attraction,
}


def infer_category(types: list[str], primary_type: str | None = None) -> PlaceCategory:
    if primary_type and primary_type in _TYPE_TO_CATEGORY:
        return _TYPE_TO_CATEGORY[primary_type]
    for t in types:
        if t in _TYPE_TO_CATEGORY:
            return _TYPE_TO_CATEGORY[t]
    return PlaceCategory.other


class LatLng(BaseModel):
    lat: float
    lng: float


class PlacePhoto(BaseModel):
    """photos[].name — Place Photos (New) media 요청에 사용.

    Docs: https://developers.google.com/maps/documentation/places/web-service/place-photos
    """

    name: str
    width_px: int | None = None
    height_px: int | None = None
    # Google 정책: 가능하면 저작자 attribution 표시
    author_attributions: list[str] = Field(default_factory=list)


class OpeningHoursPeriod(BaseModel):
    """regularOpeningHours.weekdayDescriptions 등 API 원본 문자열 보존."""

    weekday_descriptions: list[str] = Field(default_factory=list)
    open_now: bool | None = None


class Place(BaseModel):
    """프론트 카드에 표시할 사실 필드 = Places API 원본만. AI 문구는 별도(ai_description)."""

    place_id: str
    name: str
    formatted_address: str | None = None
    location: LatLng
    rating: float | None = None
    user_rating_count: int | None = None
    types: list[str] = Field(default_factory=list)
    primary_type: str | None = None
    category: PlaceCategory = PlaceCategory.other
    google_maps_uri: str | None = None
    opening_hours: OpeningHoursPeriod | None = None
    photos: list[PlacePhoto] = Field(default_factory=list)
    # Places priceLevel → 1~4 (없으면 None). Exact 원화 요금 아님.
    price_level: int | None = Field(default=None, ge=1, le=4)
    # LLM 생성 문구 슬롯 — 사실 정보와 분리 (3단계 이후)
    ai_description: str | None = None


# https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places#PriceLevel
_PRICE_LEVEL_MAP: dict[str, int] = {
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
    # 일부 응답/레거시
    "PRICE_LEVEL_FREE": 1,
    "INEXPENSIVE": 1,
    "MODERATE": 2,
    "EXPENSIVE": 3,
    "VERY_EXPENSIVE": 4,
}


def parse_price_level(raw: Any) -> int | None:
    """Places priceLevel enum/문자열 → 1~4. 모르면 None (추정 금지)."""
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw if 1 <= raw <= 4 else None
    if isinstance(raw, str):
        mapped = _PRICE_LEVEL_MAP.get(raw.strip())
        if mapped is not None:
            return mapped
        # "2" 같은 숫자 문자열
        if raw.strip().isdigit():
            n = int(raw.strip())
            return n if 1 <= n <= 4 else None
    return None


class PlaceSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Places textQuery")
    language_code: str = "ko"
    region_code: str = "JP"
    max_results: int = Field(default=20, ge=1, le=20)
    # locationBias circle (선택)
    bias_lat: float | None = None
    bias_lng: float | None = None
    bias_radius_meters: float = 15000.0
    # True면 locationRestriction(하드 바운드) — 여행 지역 밖(예: 한국 체인점) 제외
    # Docs: https://developers.google.com/maps/documentation/places/web-service/text-search
    strict_location: bool = False
    included_type: str | None = None
    min_rating: float | None = Field(default=None, ge=0, le=5)


class PlaceSearchResponse(BaseModel):
    places: list[Place]
    source: str  # "google_places" | "MOCK_places"
    query: str


class PlaceAutocompleteRequest(BaseModel):
    """Places Autocomplete (New).

    Docs: https://developers.google.com/maps/documentation/places/web-service/place-autocomplete
    """

    input: str = Field(..., min_length=1, max_length=120)
    language_code: str = "ko"
    region_code: str = "JP"
    bias_lat: float | None = None
    bias_lng: float | None = None
    bias_radius_meters: float = 35000.0
    max_suggestions: int = Field(default=5, ge=1, le=10)


class PlaceAutocompleteSuggestion(BaseModel):
    place_id: str
    primary_text: str
    secondary_text: str | None = None


class PlaceAutocompleteResponse(BaseModel):
    suggestions: list[PlaceAutocompleteSuggestion]
    source: str
    input: str


def place_from_google_payload(raw: dict[str, Any]) -> Place:
    """Places API (New) Place 객체 → 내부 Place. 임의 필드 채우기 금지."""
    display = raw.get("displayName") or {}
    loc = raw.get("location") or {}
    hours = raw.get("regularOpeningHours") or raw.get("currentOpeningHours")
    opening = None
    if hours:
        opening = OpeningHoursPeriod(
            weekday_descriptions=list(hours.get("weekdayDescriptions") or []),
            open_now=hours.get("openNow"),
        )
    photos: list[PlacePhoto] = []
    for p in raw.get("photos") or []:
        if not p.get("name"):
            continue
        photos.append(
            PlacePhoto(
                name=p["name"],
                width_px=p.get("widthPx"),
                height_px=p.get("heightPx"),
                author_attributions=[
                    a.get("displayName") or a.get("uri") or ""
                    for a in (p.get("authorAttributions") or [])
                    if a.get("displayName") or a.get("uri")
                ],
            )
        )
    types = list(raw.get("types") or [])
    primary = raw.get("primaryType")
    place_id = raw.get("id") or ""
    # name 리소스 "places/{id}" 에서 id 추출 (id 필드 없을 때)
    if not place_id and isinstance(raw.get("name"), str) and raw["name"].startswith("places/"):
        place_id = raw["name"].removeprefix("places/")

    return Place(
        place_id=place_id,
        name=display.get("text") or "",
        formatted_address=raw.get("formattedAddress"),
        location=LatLng(
            lat=float(loc["latitude"]),
            lng=float(loc["longitude"]),
        ),
        rating=raw.get("rating"),
        user_rating_count=raw.get("userRatingCount"),
        types=types,
        primary_type=primary,
        category=infer_category(types, primary),
        google_maps_uri=raw.get("googleMapsUri"),
        opening_hours=opening,
        photos=photos,
        price_level=parse_price_level(raw.get("priceLevel")),
        ai_description=None,
    )
