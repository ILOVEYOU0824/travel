"""여행 보조 정보: 날씨(Open-Meteo) + 관련 뉴스/축제 기사(Google News RSS).

LLM이 날씨·축제를 지어내지 않음. 출처 URL을 그대로 전달.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote_plus

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger("japantrip")

OPEN_METEO_GEO = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
# Docs: https://open-meteo.com/en/docs
# Google News RSS (공개 피드, 기사 원문은 링크)
NEWS_RSS = "https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"


class WeatherDay(BaseModel):
    date: str
    weather_code: int | None = None
    label_ko: str
    temp_max_c: float | None = None
    temp_min_c: float | None = None
    precipitation_probability_max: int | None = None


class NewsItem(BaseModel):
    title: str
    url: str
    source: str | None = None
    published_at: str | None = None
    kind: str = Field(description="festival | weather | travel")


class TripContextResponse(BaseModel):
    region: str
    resolved_name: str | None = None
    lat: float | None = None
    lng: float | None = None
    weather: list[WeatherDay] = Field(default_factory=list)
    weather_source: str = "Open-Meteo"
    news: list[NewsItem] = Field(default_factory=list)
    news_source: str = "Google News RSS"
    note: str = (
        "날씨는 Open-Meteo 예보, 축제·기사는 Google News 검색 결과입니다. "
        "일정 장소와 별도이며, 방문 전 공식 출처를 확인해 주세요."
    )


_WMO_KO: dict[int, str] = {
    0: "맑음",
    1: "대체로 맑음",
    2: "부분 구름",
    3: "흐림",
    45: "안개",
    48: "착빙 안개",
    51: "약한 이슬비",
    53: "이슬비",
    55: "강한 이슬비",
    61: "약한 비",
    63: "비",
    65: "강한 비",
    71: "약한 눈",
    73: "눈",
    75: "강한 눈",
    80: "소나기",
    81: "소나기",
    82: "강한 소나기",
    95: "뇌우",
    96: "우박 뇌우",
    99: "강한 우박 뇌우",
}


def _wmo_label(code: int | None) -> str:
    if code is None:
        return "정보 없음"
    return _WMO_KO.get(code, f"코드 {code}")


async def _geocode(client: httpx.AsyncClient, region: str) -> dict[str, Any] | None:
    r = await client.get(
        OPEN_METEO_GEO,
        params={"name": region, "count": 5, "language": "ko", "format": "json"},
    )
    r.raise_for_status()
    results = r.json().get("results") or []
    if not results:
        # 일본 지역 보강
        r2 = await client.get(
            OPEN_METEO_GEO,
            params={"name": f"{region} Japan", "count": 5, "language": "en", "format": "json"},
        )
        r2.raise_for_status()
        results = r2.json().get("results") or []
    if not results:
        return None
    # 일본 우선
    for item in results:
        if (item.get("country_code") or "").upper() == "JP":
            return item
    return results[0]


async def _forecast(
    client: httpx.AsyncClient,
    *,
    lat: float,
    lng: float,
    start: date,
    end: date,
) -> tuple[list[WeatherDay], str | None]:
    """단기 예보(약 16일). 여행이 더 뒤면 다가오는 예보를 참고용으로 반환."""
    today = date.today()
    horizon = today + timedelta(days=15)
    beyond = start > horizon
    if beyond:
        start_d = today
        end_d = today + timedelta(days=6)
        hint = (
            "여행 날짜가 Open-Meteo 단기 예보 범위(약 16일) 밖이라 "
            "다가오는 주 예보를 참고용으로 표시합니다."
        )
    else:
        start_d = max(start, today)
        end_d = min(end, horizon)
        if end_d < start_d:
            end_d = start_d
        hint = None
    r = await client.get(
        OPEN_METEO_FORECAST,
        params={
            "latitude": lat,
            "longitude": lng,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "Asia/Tokyo",
            "start_date": start_d.isoformat(),
            "end_date": end_d.isoformat(),
        },
    )
    r.raise_for_status()
    daily = r.json().get("daily") or {}
    dates = daily.get("time") or []
    out: list[WeatherDay] = []
    for i, d in enumerate(dates):
        codes = daily.get("weather_code") or []
        tmaxs = daily.get("temperature_2m_max") or []
        tmins = daily.get("temperature_2m_min") or []
        pops = daily.get("precipitation_probability_max") or []
        code = codes[i] if i < len(codes) else None
        tmax = tmaxs[i] if i < len(tmaxs) else None
        tmin = tmins[i] if i < len(tmins) else None
        pop = pops[i] if i < len(pops) else None
        out.append(
            WeatherDay(
                date=d,
                weather_code=code,
                label_ko=_wmo_label(code),
                temp_max_c=tmax,
                temp_min_c=tmin,
                precipitation_probability_max=pop,
            )
        )
    return out, hint


def _parse_rss(xml_text: str, *, kind: str, limit: int = 5) -> list[NewsItem]:
    items: list[NewsItem] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        source = None
        src_el = item.find("source")
        if src_el is not None and src_el.text:
            source = src_el.text.strip()
        pub = item.findtext("pubDate")
        published = None
        if pub:
            try:
                published = parsedate_to_datetime(pub).isoformat()
            except (TypeError, ValueError, IndexError):
                published = pub
        items.append(
            NewsItem(title=title, url=link, source=source, published_at=published, kind=kind)
        )
        if len(items) >= limit:
            break
    return items


async def _news(
    client: httpx.AsyncClient, region: str, *, year: int
) -> list[NewsItem]:
    queries = [
        (f"{region} 축제 OR 마츠리 {year}", "festival"),
        (f"{region} 이벤트 행사 {year}", "festival"),
        (f"{region} 날씨 여행", "weather"),
        (f"{region} 여행 소식", "travel"),
    ]
    seen: set[str] = set()
    out: list[NewsItem] = []
    for q, kind in queries:
        url = NEWS_RSS.format(q=quote_plus(q))
        try:
            r = await client.get(url)
            r.raise_for_status()
            for item in _parse_rss(r.text, kind=kind, limit=4):
                if item.url in seen:
                    continue
                seen.add(item.url)
                out.append(item)
        except Exception as exc:  # noqa: BLE001
            logger.info("News RSS 실패 (%s): %s", q, exc)
    # festival 우선
    out.sort(key=lambda x: 0 if x.kind == "festival" else 1)
    return out[:12]


async def fetch_trip_context(
    *,
    region: str,
    start_date: date,
    end_date: date,
) -> TripContextResponse:
    region = region.strip()
    if not region:
        return TripContextResponse(region=region, note="지역이 비어 있습니다.")

    note = (
        "날씨는 Open-Meteo 예보, 축제·기사는 Google News 검색 결과입니다. "
        "일정 장소와 별도이며, 방문 전 공식 출처를 확인해 주세요."
    )
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        geo = await _geocode(client, region)
        weather: list[WeatherDay] = []
        resolved = None
        lat = lng = None
        if geo:
            resolved = geo.get("name")
            lat = float(geo["latitude"])
            lng = float(geo["longitude"])
            try:
                weather, weather_hint = await _forecast(
                    client, lat=lat, lng=lng, start=start_date, end=end_date
                )
                if weather_hint:
                    note = f"{note} {weather_hint}"
            except Exception as exc:  # noqa: BLE001
                logger.info("Open-Meteo 예보 실패: %s", exc)
        news = await _news(client, region, year=start_date.year)

    return TripContextResponse(
        region=region,
        resolved_name=resolved,
        lat=lat,
        lng=lng,
        weather=weather,
        news=news,
        note=note,
    )
