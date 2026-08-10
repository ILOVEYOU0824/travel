"""철도·공항특급 예약 CTA.

우선순위:
1) Routes API transit_lines (차량 타입·노선명) — 정확
2) 공항 도착 + API 노선 없음일 때만 지역 폴백 (Places 공항 검색용 쿼리)
LLM이 교통수단/티켓을 만들지 않음.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.schemas.route import BookingCta, RouteLeg, TransitLineInfo
from app.services.klook_links import booking_url

# Docs: TransitVehicleType
# https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRoutes
_BOOKABLE_VEHICLE_TYPES = frozenset(
    {
        "HIGH_SPEED_TRAIN",
        "LONG_DISTANCE_TRAIN",
        "COMMUTER_TRAIN",
        "HEAVY_RAIL",
        "RAIL",
    }
)

# 노선명에 있으면 예약 CTA (API name / nameShort 기준, 소문자 비교)
_AIRPORT_EXPRESS_TOKENS = (
    "haruka",
    "はるか",
    "하루카",
    "narita express",
    "n'ex",
    "nex",
    "成田エクスプレス",
    "나리타 익스프레스",
    "keisei skyliner",
    "skyliner",
    "スカイライナー",
    "limousine",
    "airport express",
    "공항",
)

# (지역 키워드, Places 공항 검색어) — CTA 검색어가 아니라 공항 Place 조회용
_AIRPORT_PLACE_QUERIES: list[tuple[tuple[str, ...], str]] = [
    (("오사카", "교토", "고베", "나라", "와카야마", "간사이"), "간사이 국제공항"),
    (("도쿄", "요코하마", "가마쿠라", "지바", "사이타마", "나리타"), "나리타 국제공항"),
    (("하네다",), "하네다 공항"),
    (("나고야", "중부", "아이치"), "중부 국제공항"),
    (("후쿠오카", "하카타", "기타큐슈"), "후쿠오카 공항"),
    (("삿포로", "홋카이도", "신치토세"), "신치토세 공항"),
    (("오키나와", "나하"), "나하 공항"),
]

# FE 선택용 — Places Text 검색어로만 사용 (좌표 하드코딩 금지)
AIRPORT_OPTIONS: list[dict[str, str]] = [
    {"id": "auto", "label": "지역 기준 자동", "query": ""},
    {"id": "kix", "label": "간사이 국제공항 (KIX)", "query": "간사이 국제공항"},
    {"id": "nrt", "label": "나리타 국제공항 (NRT)", "query": "나리타 국제공항"},
    {"id": "hnd", "label": "하네다 공항 (HND)", "query": "하네다 공항"},
    {"id": "ngo", "label": "중부 국제공항 (NGO)", "query": "중부 국제공항"},
    {"id": "fuk", "label": "후쿠오카 공항 (FUK)", "query": "후쿠오카 공항"},
    {"id": "cts", "label": "신치토세 공항 (CTS)", "query": "신치토세 공항"},
    {"id": "oka", "label": "나하 공항 (OKA)", "query": "나하 공항"},
]


@dataclass(frozen=True)
class AirportRailRule:
    airport_query: str


def resolve_airport_rule(
    region: str | None,
    *,
    arrival_airport_query: str | None = None,
) -> AirportRailRule | None:
    manual = (arrival_airport_query or "").strip()
    if manual:
        return AirportRailRule(airport_query=manual)
    text = region or ""
    for keys, airport_q in _AIRPORT_PLACE_QUERIES:
        if any(k in text for k in keys):
            return AirportRailRule(airport_query=airport_q)
    return None


def _line_text(line: TransitLineInfo) -> str:
    parts = [line.name or "", line.name_short or "", line.vehicle_name or ""]
    return " ".join(parts).strip()


def _is_airport_express(line: TransitLineInfo) -> bool:
    blob = _line_text(line).lower()
    return any(tok in blob for tok in _AIRPORT_EXPRESS_TOKENS)


def _is_bookable_rail(line: TransitLineInfo) -> bool:
    vtype = (line.vehicle_type or "").upper()
    if vtype in _BOOKABLE_VEHICLE_TYPES:
        return True
    # 타입이 비어도 공항특급 토큰이면 예약 유도
    return _is_airport_express(line)


def _pick_bookable_line(lines: list[TransitLineInfo]) -> TransitLineInfo | None:
    # 고속철 → 장거리 → 공항특급 → 기타 예약 가능 순
    priority = (
        "HIGH_SPEED_TRAIN",
        "LONG_DISTANCE_TRAIN",
        "COMMUTER_TRAIN",
        "HEAVY_RAIL",
        "RAIL",
    )
    by_type = {((ln.vehicle_type or "").upper()): ln for ln in lines if _is_bookable_rail(ln)}
    for t in priority:
        if t in by_type:
            return by_type[t]
    for ln in lines:
        if _is_airport_express(ln):
            return ln
    for ln in lines:
        if _is_bookable_rail(ln):
            return ln
    return None


def booking_cta_from_transit(
    settings: Settings,
    lines: list[TransitLineInfo],
) -> BookingCta | None:
    """Routes API 노선이 예약 대상 철도일 때만 CTA. 지하철·버스만이면 None."""
    line = _pick_bookable_line(lines)
    if line is None:
        return None

    display = (line.name or line.name_short or line.vehicle_name or "열차").strip()
    vtype = (line.vehicle_type or "").upper()
    query = display

    if vtype == "HIGH_SPEED_TRAIN" or "shinkansen" in display.lower() or "新幹線" in display:
        product = "shinkansen"
        label = f"Klook에서 {display} 티켓 보기"
        hint = (
            f"Google 경로에 고속철({display})이 포함되어 있습니다. "
            "좌석·시간은 Klook에서 확인하세요."
        )
        if "신칸센" not in query and "shinkansen" not in query.lower():
            query = f"신칸센 {display}"
    elif _is_airport_express(line):
        product = "airport_rail"
        label = f"Klook에서 {display} 티켓 보기"
        hint = (
            f"Google 경로에 공항 연결 노선({display})이 포함되어 있습니다. "
            "티켓은 Klook에서 검색·예약하세요."
        )
    else:
        product = "rail"
        label = f"Klook에서 {display} 관련 티켓 보기"
        hint = (
            f"Google 경로에 철도({display})가 포함되어 있습니다. "
            "사전 예약이 필요하면 Klook에서 확인하세요."
        )

    return BookingCta(
        provider="klook",
        label=label,
        url=booking_url(settings, query),
        hint=hint,
        product_hint=product,
        search_query=query,
        source_line_name=display,
    )


def booking_cta_for_leg(
    settings: Settings,
    leg: RouteLeg | None,
    *,
    from_region: str | None = None,
    to_region: str | None = None,
    allow_region_fallback: bool = False,
) -> BookingCta | None:
    """레그 CTA: transit_lines 우선. 폴백은 명시적으로 허용할 때만."""
    if leg and leg.transit_lines:
        cta = booking_cta_from_transit(settings, leg.transit_lines)
        if cta:
            return cta
    if not allow_region_fallback:
        return None
    # API가 노선을 안 준 장거리 TRANSIT + 지역 변경만 약한 폴백
    if not leg or (leg.travel_mode and leg.travel_mode.value != "TRANSIT"):
        return None
    fr = (from_region or "").strip()
    to = (to_region or "").strip()
    if fr and to and fr != to and (leg.distance_meters or 0) >= 80_000:
        q = f"신칸센 {fr} {to}"
        return BookingCta(
            provider="klook",
            label=f"Klook에서 {fr}↔{to} 열차 검색",
            url=booking_url(settings, q),
            hint=(
                "Google이 장거리 대중교통 경로를 반환했으나 노선 상세가 없습니다. "
                "열차 티켓은 Klook에서 검색해 확인하세요."
            ),
            product_hint="shinkansen",
            search_query=q,
        )
    return None


def airport_booking_cta_fallback(
    settings: Settings,
    region: str | None,
    *,
    transit_lines: list[TransitLineInfo] | None = None,
) -> BookingCta | None:
    """공항→시내: API 노선 있으면 그것만. 없을 때만 지역 폴백 검색."""
    if transit_lines:
        cta = booking_cta_from_transit(settings, transit_lines)
        if cta:
            return cta
    rule = resolve_airport_rule(region)
    if not rule:
        return None
    # 폴백 검색어는 공항명 기반 (임의 상품 ID 없음)
    q = f"{rule.airport_query} 교통"
    return BookingCta(
        provider="klook",
        label="Klook에서 공항↔시내 교통 검색",
        url=booking_url(settings, q),
        hint=(
            "Google 환승 상세를 아직 못 읽었거나 노선이 비어 있습니다. "
            f"{rule.airport_query} 교통편을 Klook에서 검색하세요."
        ),
        product_hint="airport_rail",
        search_query=q,
    )


# 하위 호환 이름
def airport_booking_cta(settings: Settings, region: str | None) -> BookingCta | None:
    return airport_booking_cta_fallback(settings, region)
