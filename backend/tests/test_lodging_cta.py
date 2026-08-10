from urllib.parse import parse_qs, urlparse

from app.config import Settings
from app.schemas.place import LatLng, Place, PlaceCategory
from app.services.lodging_cta import lodging_booking_cta, lodging_search_query


def _hotel(name: str = "Test Hotel Osaka") -> Place:
    return Place(
        place_id="pid_hotel_1",
        name=name,
        location=LatLng(lat=34.7, lng=135.5),
        category=PlaceCategory.lodging,
        types=["lodging", "hotel"],
    )


def test_lodging_query_includes_name_and_region() -> None:
    q = lodging_search_query(_hotel("Cross Hotel"), "오사카")
    assert "Cross Hotel" in q
    assert "오사카" in q
    assert "호텔" in q


def test_lodging_query_excludes_dates() -> None:
    """날짜는 query 문자열이 아니라 URL date_range 로 간다."""
    q = lodging_search_query(_hotel("Cross Hotel"), "오사카")
    assert "2026" not in q


def test_lodging_cta_uses_date_range_param() -> None:
    settings = Settings()
    cta = lodging_booking_cta(
        settings,
        _hotel("센타라 그랜드 호텔 오사카"),
        region="오사카",
        check_in="2026-08-29",
        check_out="2026-08-30",
    )
    assert cta is not None
    assert cta.product_hint == "lodging"
    assert "호텔" in (cta.search_query or "")
    assert "2026-08-29" not in (cta.search_query or "")
    assert "2026-08-29" in (cta.hint or "")

    parsed = urlparse(cta.url)
    assert parsed.path.endswith("/ko/search/result/")
    qs = parse_qs(parsed.query)
    assert qs.get("query", [""])[0] == "센타라 그랜드 호텔 오사카 호텔"
    assert qs.get("date_range", [""])[0] == "2026-08-29"
    assert qs.get("search_scope", [""])[0] == "main_search"
    assert "search_landing" not in qs


def test_lodging_cta_only_for_lodging() -> None:
    settings = Settings()
    sight = _hotel().model_copy(update={"category": PlaceCategory.attraction})
    assert lodging_booking_cta(settings, sight, region="오사카") is None
