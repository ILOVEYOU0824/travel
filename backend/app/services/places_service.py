"""Google Places API (New) — 실제 호출 전용.

Docs:
- Text Search: https://developers.google.com/maps/documentation/places/web-service/text-search
- Place Details: https://developers.google.com/maps/documentation/places/web-service/place-details
- Field masks: https://developers.google.com/maps/documentation/places/web-service/choose-fields
"""

from __future__ import annotations

import math

import httpx

from app.config import Settings
from app.schemas.place import (
    Place,
    PlaceAutocompleteRequest,
    PlaceAutocompleteSuggestion,
    PlaceSearchRequest,
    place_from_google_payload,
)


def _circle_to_rectangle(lat: float, lng: float, radius_m: float) -> dict:
    """중심+반경 → Text Search locationRestriction용 viewport.

    Docs: locationRestriction은 rectangle만 지원 (circle 불가).
    https://developers.google.com/maps/documentation/places/web-service/text-search
    """
    # 위도 1° ≈ 111.32km, 경도는 위도에 따라 보정
    lat_delta = radius_m / 111_320.0
    cos_lat = math.cos(math.radians(lat))
    lng_delta = radius_m / (111_320.0 * cos_lat) if abs(cos_lat) > 1e-6 else lat_delta
    return {
        "rectangle": {
            "low": {
                "latitude": lat - lat_delta,
                "longitude": lng - lng_delta,
            },
            "high": {
                "latitude": lat + lat_delta,
                "longitude": lng + lng_delta,
            },
        }
    }

SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
AUTOCOMPLETE_URL = "https://places.googleapis.com/v1/places:autocomplete"
PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"

# Docs: field mask optional; placeId + text for typo suggestions
AUTOCOMPLETE_FIELD_MASK = ",".join(
    [
        "suggestions.placePrediction.placeId",
        "suggestions.placePrediction.text",
        "suggestions.placePrediction.structuredFormat",
    ]
)

# Pro SKU 필드 — 필요 최소 집합. 필드 추가 시 과금 등급 확인 후 확장.
FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.rating",
        "places.userRatingCount",
        "places.types",
        "places.primaryType",
        "places.googleMapsUri",
        "places.regularOpeningHours",
        "places.photos",
        "places.priceLevel",
    ]
)

DETAILS_FIELD_MASK = ",".join(
    [
        "id",
        "displayName",
        "formattedAddress",
        "location",
        "rating",
        "userRatingCount",
        "types",
        "primaryType",
        "googleMapsUri",
        "regularOpeningHours",
        "photos",
        "priceLevel",
    ]
)


class PlacesApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class PlacesService:
    """실제 Google Places 호출. MOCK 데이터는 mock_places.py에만 둔다."""

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> PlacesService:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    def _require_key(self) -> str:
        key = self._settings.google_maps_api_key
        if not key:
            raise PlacesApiError(
                "GOOGLE_MAPS_API_KEY가 없습니다. .env를 설정하거나 USE_MOCK_PLACES=true를 사용하세요."
            )
        return key

    async def search_text(self, request: PlaceSearchRequest) -> list[Place]:
        """POST places:searchText — textQuery 기반 검색."""
        assert self._client is not None
        api_key = self._require_key()

        body: dict = {
            "textQuery": request.query,
            "languageCode": request.language_code,
            "regionCode": request.region_code,
            # Docs: pageSize (max 20 for Text Search New)
            "pageSize": request.max_results,
        }
        if request.included_type:
            body["includedType"] = request.included_type
        if request.min_rating is not None:
            body["minRating"] = request.min_rating
        if request.bias_lat is not None and request.bias_lng is not None:
            # Bias: circle OK / Restriction: rectangle only (circle → 400)
            if request.strict_location:
                body["locationRestriction"] = _circle_to_rectangle(
                    request.bias_lat,
                    request.bias_lng,
                    request.bias_radius_meters,
                )
            else:
                body["locationBias"] = {
                    "circle": {
                        "center": {
                            "latitude": request.bias_lat,
                            "longitude": request.bias_lng,
                        },
                        "radius": request.bias_radius_meters,
                    }
                }

        response = await self._client.post(
            SEARCH_TEXT_URL,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": FIELD_MASK,
            },
            json=body,
        )
        if response.status_code >= 400:
            raise PlacesApiError(
                f"Places Text Search 실패: {response.status_code} {response.text}",
                status_code=response.status_code,
            )

        payload = response.json()
        places: list[Place] = []
        for raw in payload.get("places") or []:
            try:
                places.append(place_from_google_payload(raw))
            except (KeyError, TypeError, ValueError):
                # 좌표 등 필수 필드 누락 항목은 버림 (환각으로 채우지 않음)
                continue
        return places

    async def autocomplete(
        self, request: PlaceAutocompleteRequest
    ) -> list[PlaceAutocompleteSuggestion]:
        """POST places:autocomplete — 오타·부분 입력 보정용. 장소 생성 금지."""
        assert self._client is not None
        api_key = self._require_key()
        body: dict = {
            "input": request.input.strip(),
            "languageCode": request.language_code,
            "regionCode": request.region_code,
            "includedRegionCodes": [request.region_code.lower()],
        }
        if request.bias_lat is not None and request.bias_lng is not None:
            # Autocomplete: circle bias OK
            # https://developers.google.com/maps/documentation/places/web-service/place-autocomplete
            body["locationBias"] = {
                "circle": {
                    "center": {
                        "latitude": request.bias_lat,
                        "longitude": request.bias_lng,
                    },
                    "radius": min(request.bias_radius_meters, 50000.0),
                }
            }

        response = await self._client.post(
            AUTOCOMPLETE_URL,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": AUTOCOMPLETE_FIELD_MASK,
            },
            json=body,
        )
        if response.status_code >= 400:
            raise PlacesApiError(
                f"Places Autocomplete 실패: {response.status_code} {response.text}",
                status_code=response.status_code,
            )

        out: list[PlaceAutocompleteSuggestion] = []
        for item in response.json().get("suggestions") or []:
            pred = item.get("placePrediction") or {}
            pid = (pred.get("placeId") or "").strip()
            if not pid:
                continue
            text_obj = pred.get("text") or {}
            primary = (text_obj.get("text") or "").strip()
            structured = pred.get("structuredFormat") or {}
            main = ((structured.get("mainText") or {}).get("text") or "").strip()
            secondary = ((structured.get("secondaryText") or {}).get("text") or "").strip()
            label = main or primary
            if not label:
                continue
            out.append(
                PlaceAutocompleteSuggestion(
                    place_id=pid,
                    primary_text=label,
                    secondary_text=secondary or None,
                )
            )
            if len(out) >= request.max_suggestions:
                break
        return out

    async def get_place(self, place_id: str, language_code: str = "ko") -> Place:
        """GET places/{place_id} — place_id 재검증용."""
        assert self._client is not None
        api_key = self._require_key()
        url = PLACE_DETAILS_URL.format(place_id=place_id)
        response = await self._client.get(
            url,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": DETAILS_FIELD_MASK,
            },
            params={"languageCode": language_code},
        )
        if response.status_code >= 400:
            raise PlacesApiError(
                f"Place Details 실패: {response.status_code} {response.text}",
                status_code=response.status_code,
            )
        return place_from_google_payload(response.json())

    async def get_photo_media(
        self,
        photo_name: str,
        *,
        max_width_px: int = 800,
        max_height_px: int | None = None,
    ) -> tuple[bytes, str]:
        """Place Photos (New) media 바이너리.

        Docs: https://developers.google.com/maps/documentation/places/web-service/place-photos
        photo_name: places/{place_id}/photos/{photo_reference}
        """
        assert self._client is not None
        api_key = self._require_key()
        name = photo_name.strip().lstrip("/")
        if not name.startswith("places/") or "/photos/" not in name:
            raise PlacesApiError("잘못된 사진 리소스 이름입니다.", status_code=400)
        if ".." in name or name.count("/") < 3:
            raise PlacesApiError("잘못된 사진 리소스 이름입니다.", status_code=400)
        # photos.name 뒤에 /media 붙임
        media_path = name if name.endswith("/media") else f"{name}/media"
        params: dict[str, int | str] = {
            "key": api_key,
            "maxWidthPx": max(1, min(max_width_px, 4800)),
        }
        if max_height_px is not None:
            params["maxHeightPx"] = max(1, min(max_height_px, 4800))

        url = f"https://places.googleapis.com/v1/{media_path}"
        response = await self._client.get(url, params=params, follow_redirects=True)
        if response.status_code >= 400:
            raise PlacesApiError(
                f"Place Photo 실패: {response.status_code}",
                status_code=response.status_code,
            )
        content_type = response.headers.get("content-type", "image/jpeg")
        return response.content, content_type
