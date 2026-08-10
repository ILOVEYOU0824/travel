"""캐시·일정 저장 단위 테스트."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.services.cache import CacheService, cache_key
from app.services import trip_store


@pytest.mark.asyncio
async def test_memory_cache_roundtrip() -> None:
    cache = CacheService()
    await cache.init(Settings(cache_enabled=True, redis_url=""))
    key = cache_key("t", {"a": 1})
    assert await cache.get_json(key) is None
    await cache.set_json(key, {"hello": "world"}, ttl=60)
    assert await cache.get_json(key) == {"hello": "world"}
    assert cache.backend_name == "memory"


def test_trip_store_save_and_load(tmp_path) -> None:
    settings = Settings(trips_data_dir=str(tmp_path / "trips"))
    saved = trip_store.save_trip(
        settings,
        {
            "title": "테스트",
            "itinerary": [{"date": "2026-09-10", "region": "오사카", "items": []}],
            "meta": {"region": "오사카"},
        },
    )
    loaded = trip_store.load_trip(settings, saved["id"])
    assert loaded is not None
    assert loaded["title"] == "테스트"
    assert trip_store.load_trip(settings, "../etc/passwd") is None


def test_trips_api(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TRIPS_DATA_DIR", str(tmp_path / "trips"))
    monkeypatch.setenv("CACHE_ENABLED", "false")
    monkeypatch.setenv("USE_MOCK_PLACES", "true")
    monkeypatch.setenv("USE_MOCK_ROUTES", "true")
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    from app.config import get_settings

    get_settings.cache_clear()

    from app.main import app

    with TestClient(app) as client:
        res = client.post(
            "/api/v1/trips",
            json={
                "title": "오사카 여행",
                "itinerary": [{"date": "2026-09-10", "region": "오사카", "items": []}],
                "meta": {},
            },
        )
        assert res.status_code == 200
        trip_id = res.json()["id"]
        got = client.get(f"/api/v1/trips/{trip_id}")
        assert got.status_code == 200
        assert got.json()["title"] == "오사카 여행"
        listed = client.get("/api/v1/trips")
        assert listed.status_code == 200
        assert any(t["id"] == trip_id for t in listed.json())

    get_settings.cache_clear()
