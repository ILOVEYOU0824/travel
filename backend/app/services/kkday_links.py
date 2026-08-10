"""KKday 공개 URL + Travelpayouts 숏링크/래핑.

상품 ID·요금을 만들지 않는다. 홈 숏링크 또는 공개 검색 URL만 사용.
사용자 Travelpayouts 링크 예: https://kkday.tpk.lu/I3n5UXqs
"""

from __future__ import annotations

from urllib.parse import quote, urlencode

from app.config import Settings
from app.schemas.route import BookingCta

# 공개 검색 — 상품 상세 URL 추측 금지
# KKday 사이트 검색 (ko). 404 등이면 홈 숏링크로 폴백.
KKDAY_SEARCH_BASE = "https://www.kkday.com/ko/search"


def kkday_search_url(query: str) -> str:
    q = query.strip() or "Japan eSIM"
    return f"{KKDAY_SEARCH_BASE}?{urlencode({'keyword': q})}"


def wrap_kkday_url(settings: Settings, destination_url: str) -> str:
    """우선: KKDAY 전용 템플릿 → 홈 숏링크(제휴) → destination 그대로."""
    template = (settings.travelpayouts_kkday_url_template or "").strip()
    if template and "{url}" in template:
        return template.replace("{url}", quote(destination_url, safe=""))

    home = (settings.kkday_affiliate_home_url or "").strip()
    # Travelpayouts Tools 숏링크는 홈/카테고리 진입용 — eSIM 안내용으로 우선 사용
    if home:
        return home

    return destination_url


def kkday_esim_cta(settings: Settings, *, region: str | None = None) -> BookingCta | None:
    home = (settings.kkday_affiliate_home_url or "").strip()
    if not home and not (settings.travelpayouts_kkday_url_template or "").strip():
        return None

    region_bit = (region or "일본").strip() or "일본"
    query = f"{region_bit} eSIM"
    # 숏링크가 있으면 그걸 쓰고, 검색어는 hint에만 (요금·상품 미생성)
    url = wrap_kkday_url(settings, kkday_search_url(query))
    return BookingCta(
        provider="kkday",
        label="KKday에서 일본 eSIM·WiFi 보기",
        url=url,
        hint=(
            "도착 후 바로 쓸 데이터는 KKday에서 eSIM·포켓 WiFi를 검색·예약하세요. "
            "요금·용량은 예약 페이지에서 확인합니다. (제휴 링크)"
        ),
        product_hint="esim",
        search_query=query,
    )
