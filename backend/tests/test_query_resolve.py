"""필수 검색어 해석 — Text Search 실패 시 Autocomplete만 사용 (장소 생성 금지)."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.services.mock_places import MOCK_autocomplete
from app.schemas.place import PlaceAutocompleteRequest
from app.services.query_resolve import resolve_must_have_query


@pytest.mark.asyncio
async def test_resolve_matched_food() -> None:
    settings = Settings(use_mock_places=True, google_maps_api_key="")
    places, hint = await resolve_must_have_query(
        settings,
        keyword="라멘",
        region="오사카",
        kind="food",
    )
    assert hint.status == "matched"
    assert places
    assert all(p.place_id.startswith("ChIJMOCK_") for p in places)


@pytest.mark.asyncio
async def test_resolve_typo_uses_autocomplete() -> None:
    settings = Settings(use_mock_places=True, google_maps_api_key="")
    places, hint = await resolve_must_have_query(
        settings,
        keyword="라멘테스또",
        region="오사카",
        kind="food",
    )
    assert hint.status in ("autocorrected", "not_found")
    if hint.status == "autocorrected":
        assert places
        assert hint.suggestions
        assert all(p.place_id.startswith("ChIJMOCK_") for p in places)
        assert "자동완성" in hint.message


@pytest.mark.asyncio
async def test_resolve_unknown_not_found() -> None:
    settings = Settings(use_mock_places=True, google_maps_api_key="")
    places, hint = await resolve_must_have_query(
        settings,
        keyword="zzzznotaplace999",
        region="오사카",
        kind="sight",
    )
    assert places == []
    assert hint.status == "not_found"
    assert hint.suggestions == []
    assert "만들지" in hint.message


@pytest.mark.asyncio
async def test_MOCK_autocomplete_only_fixture_ids() -> None:
    sugg = await MOCK_autocomplete(
        PlaceAutocompleteRequest(input="오사카성", max_suggestions=5)
    )
    assert sugg
    assert all(s.place_id.startswith("ChIJMOCK_") for s in sugg)
