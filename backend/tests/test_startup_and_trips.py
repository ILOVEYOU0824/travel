"""프로덕션 가드·일정 저장 PATCH/DELETE/만료."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.services import trip_store
from app.startup_checks import assert_production_safe


def test_production_blocks_mock() -> None:
    with pytest.raises(RuntimeError, match="MOCK"):
        assert_production_safe(
            Settings(
                app_env="production",
                use_mock_places=True,
                use_mock_routes=False,
                use_mock_llm=False,
                google_maps_api_key="x",
                anthropic_api_key="y",
            )
        )


def test_production_ok_without_mock() -> None:
    assert_production_safe(
        Settings(
            app_env="production",
            use_mock_places=False,
            use_mock_routes=False,
            use_mock_llm=False,
            google_maps_api_key="x",
            anthropic_api_key="y",
        )
    )


def test_trip_update_delete_expiry(tmp_path) -> None:
    settings = Settings(trips_data_dir=str(tmp_path / "trips"), trips_ttl_days=30)
    saved = trip_store.save_trip(
        settings,
        {
            "title": "원본",
            "itinerary": [{"date": "2026-09-10", "region": "오사카", "items": []}],
            "meta": {},
        },
    )
    assert saved.get("expires_at")
    updated = trip_store.update_trip(settings, saved["id"], title="수정됨")
    assert updated is not None
    assert updated["title"] == "수정됨"
    assert trip_store.delete_trip(settings, saved["id"]) is True
    assert trip_store.load_trip(settings, saved["id"]) is None


def test_expired_trip_purged_on_load(tmp_path) -> None:
    settings = Settings(trips_data_dir=str(tmp_path / "trips"), trips_ttl_days=1)
    saved = trip_store.save_trip(
        settings,
        {
            "title": "만료",
            "itinerary": [{"date": "2026-09-10", "region": "오사카", "items": []}],
            "meta": {},
        },
    )
    path = tmp_path / "trips" / f"{saved['id']}.json"
    past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    data["expires_at"] = past
    path.write_text(json.dumps(data), encoding="utf-8")
    assert trip_store.load_trip(settings, saved["id"]) is None


def test_trips_patch_api(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TRIPS_DATA_DIR", str(tmp_path / "trips"))
    monkeypatch.setenv("CACHE_ENABLED", "false")
    monkeypatch.setenv("USE_MOCK_PLACES", "true")
    monkeypatch.setenv("USE_MOCK_ROUTES", "true")
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    monkeypatch.setenv("APP_ENV", "development")
    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    with TestClient(app) as client:
        res = client.post(
            "/api/v1/trips",
            json={
                "title": "오사카",
                "itinerary": [{"date": "2026-09-10", "region": "오사카", "items": []}],
                "meta": {},
            },
        )
        assert res.status_code == 200
        trip_id = res.json()["id"]
        patched = client.patch(f"/api/v1/trips/{trip_id}", json={"title": "교토"})
        assert patched.status_code == 200
        assert patched.json()["title"] == "교토"
        deleted = client.delete(f"/api/v1/trips/{trip_id}")
        assert deleted.status_code == 200
        assert client.get(f"/api/v1/trips/{trip_id}").status_code == 404
        airports = client.get("/api/v1/meta/airports")
        assert airports.status_code == 200
        assert any(a["id"] == "kix" for a in airports.json())

    get_settings.cache_clear()


def test_manual_airport_rule() -> None:
    from app.services.rail_cta import resolve_airport_rule

    rule = resolve_airport_rule("오사카", arrival_airport_query="하네다 공항")
    assert rule is not None
    assert rule.airport_query == "하네다 공항"
