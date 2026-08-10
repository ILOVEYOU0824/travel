"""Places 스키마·서비스 단위 테스트 — API 키 없이 픽스처로 실행."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from app.config import Settings
from app.schemas.place import PlaceCategory, PlaceSearchRequest, place_from_google_payload
from app.services import mock_places
from app.services.place_search import search_places
from app.services.places_service import SEARCH_TEXT_URL, PlacesService

FIXTURE = Path(__file__).parent / "fixtures" / "places_search_text_osaka.json"


def test_place_from_google_payload_maps_fields_1to1() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))["places"][0]
    place = place_from_google_payload(raw)

    assert place.place_id == "ChIJMOCK_osaka_castle_fixture_001"
    assert place.name == "MOCK_오사카성"
    assert place.formatted_address == raw["formattedAddress"]
    assert place.location.lat == raw["location"]["latitude"]
    assert place.location.lng == raw["location"]["longitude"]
    assert place.rating == raw["rating"]
    assert place.user_rating_count == raw["userRatingCount"]
    assert place.types == raw["types"]
    assert place.category == PlaceCategory.attraction
    assert place.ai_description is None
    assert place.opening_hours is not None
    assert place.opening_hours.weekday_descriptions == raw["regularOpeningHours"]["weekdayDescriptions"]
    assert place.photos[0].name == raw["photos"][0]["name"]


def test_infer_ramen_category() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))["places"][2]
    place = place_from_google_payload(raw)
    assert place.category == PlaceCategory.restaurant


@pytest.mark.asyncio
async def test_MOCK_search_filters_ramen() -> None:
    req = PlaceSearchRequest(query="라멘", max_results=10)
    places = await mock_places.MOCK_search_text(req)
    assert places
    assert all(p.place_id.startswith("ChIJMOCK_") for p in places)
    assert any("라멘" in p.name or "ramen" in p.types for p in places)


@pytest.mark.asyncio
async def test_search_places_uses_MOCK_when_flag_set() -> None:
    settings = Settings(use_mock_places=True, google_maps_api_key="")
    result = await search_places(settings, PlaceSearchRequest(query="오사카", max_results=5))
    assert result.source == "MOCK_places"
    assert 1 <= len(result.places) <= 5
    # 임의 생성 금지: 픽스처 id만
    fixture_ids = {p["id"] for p in json.loads(FIXTURE.read_text(encoding="utf-8"))["places"]}
    assert all(p.place_id in fixture_ids for p in result.places)


@pytest.mark.asyncio
@respx.mock
async def test_places_service_search_text_parses_api_response() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    respx.post(SEARCH_TEXT_URL).mock(return_value=httpx.Response(200, json=fixture))

    settings = Settings(use_mock_places=False, google_maps_api_key="test-key")
    async with PlacesService(settings) as service:
        places = await service.search_text(PlaceSearchRequest(query="Osaka attractions", max_results=5))

    assert len(places) == 5
    assert places[0].place_id == "ChIJMOCK_osaka_castle_fixture_001"
    # FieldMask 헤더 확인
    assert respx.calls[0].request.headers["X-Goog-FieldMask"]
    assert respx.calls[0].request.headers["X-Goog-Api-Key"] == "test-key"


@pytest.mark.asyncio
@respx.mock
async def test_places_service_skips_place_missing_location() -> None:
    bad = {
        "places": [
            {
                "id": "bad",
                "displayName": {"text": "좌표없음", "languageCode": "ko"},
                # location 누락 → 환각으로 채우지 않고 skip
            }
        ]
    }
    respx.post(SEARCH_TEXT_URL).mock(return_value=httpx.Response(200, json=bad))
    settings = Settings(google_maps_api_key="test-key")
    async with PlacesService(settings) as service:
        places = await service.search_text(PlaceSearchRequest(query="x"))
    assert places == []
