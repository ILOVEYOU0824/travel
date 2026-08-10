"""지역 스코프 검색 — 일본 중심점·쿼리 조립."""

from app.services.itinerary_builder import _region_scoped_query
from app.services.region_bias import resolve_region_center


def test_osaka_center() -> None:
    c = resolve_region_center("오사카")
    assert c is not None
    lat, lng = c
    assert 34.0 < lat < 35.5
    assert 135.0 < lng < 136.5


def test_scoped_query_adds_japan() -> None:
    q = _region_scoped_query("오사카", "도우터 커피")
    assert "오사카" in q
    assert "도우터" in q
    assert "Japan" in q


def test_scoped_query_no_double_region() -> None:
    q = _region_scoped_query("오사카", "오사카 도우터 커피")
    assert q.count("오사카") == 1
