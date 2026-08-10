"""숙소 Klook CTA — Places 숙소명 + 일정 날짜로 검색 URL만. 가격·재고 생성 금지."""

from __future__ import annotations

from datetime import date, timedelta

from app.config import Settings
from app.schemas.place import Place, PlaceCategory
from app.schemas.route import BookingCta
from app.services.klook_links import booking_url


def lodging_search_query(
    place: Place,
    region: str | None = None,
) -> str:
    """검색어만. 날짜는 query에 넣지 않는다(Klook date_range 파라미터로 분리)."""
    name = (place.name or "").strip()
    region_s = (region or "").strip()
    parts: list[str] = []
    if name:
        parts.append(name)
    if region_s and region_s not in name:
        parts.append(region_s)
    parts.append("호텔")
    return " ".join(parts) if parts else "일본 호텔"


def _next_day(iso: str) -> str:
    try:
        d = date.fromisoformat(iso)
        return (d + timedelta(days=1)).isoformat()
    except ValueError:
        return iso


def lodging_booking_cta(
    settings: Settings,
    place: Place,
    *,
    region: str | None = None,
    check_in: str | None = None,
    check_out: str | None = None,
) -> BookingCta | None:
    if place.category != PlaceCategory.lodging:
        return None
    cin = check_in
    cout = check_out or (_next_day(check_in) if check_in else None)
    q = lodging_search_query(place, region)
    display = (place.name or "숙소").strip()
    date_hint = ""
    if cin and cout:
        date_hint = f" 일정상 숙박 참고일: {cin} → {cout}."
    return BookingCta(
        provider="klook",
        label="Klook에서 숙소 검색·예약",
        url=booking_url(settings, q, date_range=cin),
        hint=(
            f"Google Places의 «{display}» 참고입니다.{date_hint} "
            "요금·빈방은 Klook에서 검색해 확인하세요. 동일 숙소가 없을 수 있습니다."
        ),
        product_hint="lodging",
        search_query=q,
        source_line_name=display,
    )
