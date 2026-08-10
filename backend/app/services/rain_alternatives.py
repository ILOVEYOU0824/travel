"""강수 확률 높은 날 — 야외 장소를 실내 Places 후보로 제안. LLM이 장소 생성 금지."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.config import Settings
from app.schemas.itinerary import ItineraryDayView
from app.schemas.place import Place, PlaceCategory, PlaceSearchRequest
from app.services.food_proximity import haversine_m
from app.services.place_search import search_places
from app.services.trip_context import WeatherDay, fetch_trip_context

# Places types / primary — 야외로 간주
_OUTDOOR_HINTS = (
    "park",
    "tourist_attraction",
    "amusement_park",
    "zoo",
    "campground",
    "rv_park",
    "natural_feature",
    "hiking",
    "garden",
    "plaza",
    "shrine",  # 야외 신사 많음 — 실내 대안 제안 대상
    "place_of_worship",
)

_INDOOR_QUERIES = (
    ("실내 관광", "museum"),
    ("쇼핑몰", "shopping_mall"),
    ("아쿠아리움", "aquarium"),
    ("미술관", "art_gallery"),
)


class RainAltSuggestion(BaseModel):
    old_place_id: str
    old_place_name: str
    alternatives: list[Place] = Field(default_factory=list)


class RainDayAdvice(BaseModel):
    date: str
    region: str | None = None
    precipitation_probability_max: int | None = None
    weather_label: str | None = None
    rainy: bool = False
    outdoor_count: int = 0
    suggestions: list[RainAltSuggestion] = Field(default_factory=list)


class RainAdviceResponse(BaseModel):
    rainy_days: list[RainDayAdvice]
    message: str
    source: str = "Open-Meteo + Google Places"


def _is_outdoor(place: Place) -> bool:
    if place.category == PlaceCategory.lodging:
        return False
    if place.category in (PlaceCategory.restaurant, PlaceCategory.cafe):
        return False
    blob = " ".join([place.primary_type or "", *place.types]).lower()
    return any(h in blob for h in _OUTDOOR_HINTS)


def _weather_by_date(weather: list[WeatherDay]) -> dict[str, WeatherDay]:
    return {w.date: w for w in weather}


async def build_rain_advice(
    settings: Settings,
    *,
    days: list[ItineraryDayView],
    start_date: str,
    end_date: str,
    language_code: str = "ko",
    precip_threshold: int = 50,
) -> RainAdviceResponse:
    from datetime import date as date_cls

    if not days:
        return RainAdviceResponse(rainy_days=[], message="일정이 비어 있습니다.")

    # 대표 지역: 첫날
    region = days[0].region or "Japan"
    ctx = await fetch_trip_context(
        region=region,
        start_date=date_cls.fromisoformat(start_date),
        end_date=date_cls.fromisoformat(end_date),
    )
    wmap = _weather_by_date(ctx.weather)

    used = {it.place.place_id for d in days for it in d.items}
    rainy_out: list[RainDayAdvice] = []

    for day in days:
        w = wmap.get(day.date)
        # 여행일이 예보 밖이면 같은 요일 아님 — precip 없으면 스킵
        precip = w.precipitation_probability_max if w else None
        rainy = precip is not None and precip >= precip_threshold
        outdoors = [it for it in day.items if _is_outdoor(it.place)]
        advice = RainDayAdvice(
            date=day.date,
            region=day.region,
            precipitation_probability_max=precip,
            weather_label=w.label_ko if w else None,
            rainy=rainy,
            outdoor_count=len(outdoors),
        )
        if not rainy or not outdoors:
            if rainy:
                rainy_out.append(advice)
            continue

        # 당일 중심 좌표
        lats = [it.place.location.lat for it in day.items]
        lngs = [it.place.location.lng for it in day.items]
        clat = sum(lats) / len(lats)
        clng = sum(lngs) / len(lngs)
        region_q = day.region or region

        pool: list[Place] = []
        for q_suffix, included in _INDOOR_QUERIES:
            found = await search_places(
                settings,
                PlaceSearchRequest(
                    query=f"{region_q} {q_suffix}",
                    language_code=language_code,
                    max_results=8,
                    bias_lat=clat,
                    bias_lng=clng,
                    bias_radius_meters=4000.0,
                    included_type=included,
                    min_rating=3.8,
                ),
            )
            for p in found.places:
                if p.place_id and p.place_id not in used:
                    pool.append(p)

        # 중복 제거
        seen: set[str] = set()
        unique_pool: list[Place] = []
        for p in pool:
            if p.place_id in seen:
                continue
            seen.add(p.place_id)
            unique_pool.append(p)

        for it in outdoors:
            alts = sorted(
                unique_pool,
                key=lambda p: (
                    -(p.rating or 0),
                    haversine_m(
                        it.place.location.lat,
                        it.place.location.lng,
                        p.location.lat,
                        p.location.lng,
                    ),
                ),
            )[:3]
            if alts:
                advice.suggestions.append(
                    RainAltSuggestion(
                        old_place_id=it.place.place_id,
                        old_place_name=it.place.name,
                        alternatives=alts,
                    )
                )
        rainy_out.append(advice)

    if not rainy_out:
        msg = "예보 기준 비 걱정이 큰 날은 없어요. (또는 단기 예보 범위 밖입니다)"
    else:
        n = sum(1 for d in rainy_out if d.rainy)
        msg = (
            f"강수확률 {precip_threshold}% 이상인 날 {n}일 — "
            "야외 장소의 실내 Places 대안을 제안합니다. AI가 장소를 만들지 않습니다."
        )
    return RainAdviceResponse(rainy_days=rainy_out, message=msg)
