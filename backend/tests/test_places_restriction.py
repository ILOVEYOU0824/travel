"""locationRestriction은 rectangle만 — circle 변환 검증."""

from app.services.places_service import _circle_to_rectangle


def test_circle_to_rectangle_osaka() -> None:
    box = _circle_to_rectangle(34.6937, 135.5023, 35000.0)
    assert "rectangle" in box
    low = box["rectangle"]["low"]
    high = box["rectangle"]["high"]
    assert low["latitude"] < 34.6937 < high["latitude"]
    assert low["longitude"] < 135.5023 < high["longitude"]
    # 한국(서울 ~37.5, 127)은 박스 밖
    assert not (low["latitude"] <= 37.5 <= high["latitude"] and low["longitude"] <= 127.0 <= high["longitude"])
