"""Klook 검색 URL 생성 + (선택) Travelpayouts 래핑.

상품·가격·시간표를 만들지 않는다. 공개 검색 URL만 조립한다.
어필리에이트 래핑은 env 템플릿/marker만 사용 (형식 추측 최소화).

검색 결과 URL 형태(실측):
https://www.klook.com/ko/search/result/?query=...&search_scope=main_search&date_range=YYYY-MM-DD
날짜는 query 문자열이 아니라 date_range 로 분리해야 호텔 필터가 적용된다.
"""

from __future__ import annotations

from urllib.parse import quote, urlencode

from app.config import Settings

KLOOK_SEARCH_RESULT_BASE = "https://www.klook.com/ko/search/result/"
# 하위 호환 — 예전 /ko/search/ 경로를 보던 테스트·호출용
KLOOK_SEARCH_BASE = KLOOK_SEARCH_RESULT_BASE
# Travelpayouts 링크 생성기에서 흔히 쓰는 래핑 형태.
# Docs/도구: Destination URL을 u= 파라미터로 넣는 deep link
_DEFAULT_TP_TEMPLATE = "https://tp.media/r?marker={marker}&u={url}"


def klook_search_url(query: str, *, date_range: str | None = None) -> str:
    q = query.strip()
    if not q:
        q = "Japan train"
    params: dict[str, str] = {
        "query": q,
        "search_scope": "main_search",
    }
    dr = (date_range or "").strip()
    if dr:
        params["date_range"] = dr
    return f"{KLOOK_SEARCH_RESULT_BASE}?{urlencode(params)}"


def affiliate_status(settings: Settings) -> dict[str, str | bool]:
    template = (settings.travelpayouts_klook_url_template or "").strip()
    marker = (settings.travelpayouts_marker or "").strip()
    home = (settings.klook_affiliate_home_url or "").strip()
    kkday_home = (settings.kkday_affiliate_home_url or "").strip()
    wrapping = bool((template and "{url}" in template) or marker)
    return {
        "search_wrapping": wrapping,
        "has_home_link": bool(home),
        "has_kkday_link": bool(kkday_home),
        "mode": (
            "template"
            if template and "{url}" in template
            else "marker"
            if marker
            else "plain_klook"
        ),
    }


def wrap_affiliate_url(settings: Settings, destination_url: str) -> str:
    """우선순위: 명시 템플릿 → marker 기본 템플릿 → Klook URL 그대로.

    홈 숏링크(klook.tpk.lu/…)는 검색 deep link가 아니므로 검색 URL에 덮어쓰지 않음.
    """
    template = (settings.travelpayouts_klook_url_template or "").strip()
    if template and "{url}" in template:
        return template.replace("{url}", quote(destination_url, safe=""))

    marker = (settings.travelpayouts_marker or "").strip()
    if marker:
        return (
            _DEFAULT_TP_TEMPLATE.replace("{marker}", quote(marker, safe=""))
            .replace("{url}", quote(destination_url, safe=""))
        )

    if destination_url.startswith("https://www.klook.com"):
        return destination_url

    home = (settings.klook_affiliate_home_url or "").strip()
    return home or destination_url


def booking_url(
    settings: Settings,
    search_query: str,
    *,
    date_range: str | None = None,
) -> str:
    return wrap_affiliate_url(
        settings,
        klook_search_url(search_query, date_range=date_range),
    )
