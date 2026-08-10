"""공유 링크 OG HTML."""

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.services import trip_store


def test_share_bot_gets_og_html(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TRIPS_DATA_DIR", str(tmp_path / "trips"))
    monkeypatch.setenv("PUBLIC_FRONTEND_URL", "http://localhost:5173")
    monkeypatch.setenv("CACHE_ENABLED", "false")
    monkeypatch.setenv("USE_MOCK_PLACES", "true")
    monkeypatch.setenv("USE_MOCK_ROUTES", "true")
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    get_settings.cache_clear()
    settings = get_settings()

    record = trip_store.save_trip(
        settings,
        {
            "title": "오사카 테스트 여행",
            "itinerary": [
                {"date": "2026-09-10", "region": "오사카", "items": []},
                {"date": "2026-09-11", "region": "교토", "items": []},
            ],
            "meta": {},
        },
    )
    client = TestClient(app)
    res = client.get(
        f"/share/{record['id']}",
        headers={"User-Agent": "facebookexternalhit/1.1"},
    )
    get_settings.cache_clear()
    assert res.status_code == 200
    assert "og:title" in res.text
    assert "오사카 테스트 여행" in res.text
    assert "og:description" in res.text


def test_share_browser_redirects(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TRIPS_DATA_DIR", str(tmp_path / "trips2"))
    monkeypatch.setenv("PUBLIC_FRONTEND_URL", "http://localhost:5173")
    monkeypatch.setenv("CACHE_ENABLED", "false")
    monkeypatch.setenv("USE_MOCK_PLACES", "true")
    monkeypatch.setenv("USE_MOCK_ROUTES", "true")
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    get_settings.cache_clear()
    settings = get_settings()

    record = trip_store.save_trip(
        settings,
        {
            "title": "리다이렉트",
            "itinerary": [{"date": "2026-09-10", "region": "오사카", "items": []}],
            "meta": {},
        },
    )
    client = TestClient(app, follow_redirects=False)
    res = client.get(
        f"/share/{record['id']}",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    get_settings.cache_clear()
    assert res.status_code == 302
    assert f"trip={record['id']}" in res.headers["location"]
