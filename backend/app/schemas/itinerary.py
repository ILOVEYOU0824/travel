"""일정 생성 LLM 입·출력 스키마. 장소 상세는 Place에서만 온다."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.place import Place
from app.schemas.query_hint import SearchHint
from app.schemas.route import BookingCta, RouteLeg


class TimeSlot(str, Enum):
    morning = "morning"
    lunch = "lunch"
    afternoon = "afternoon"
    dinner = "dinner"
    evening = "evening"


class LlmItineraryItem(BaseModel):
    """LLM이 반환하는 선택 결과 — place_id + 배치만. 좌표/주소 없음."""

    place_id: str
    order: int = Field(..., ge=1)
    time_slot: TimeSlot
    reason: str = Field(..., description="AI 추천 이유 (사실 정보와 분리)")


class LlmItineraryDay(BaseModel):
    date: str  # YYYY-MM-DD
    items: list[LlmItineraryItem] = Field(default_factory=list)


class LlmItineraryResponse(BaseModel):
    days: list[LlmItineraryDay]


# Structured Output용 JSON Schema (additionalProperties: false 필수)
ITINERARY_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "days": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "place_id": {"type": "string"},
                                "order": {"type": "integer"},
                                "time_slot": {
                                    "type": "string",
                                    "enum": ["morning", "lunch", "afternoon", "dinner", "evening"],
                                },
                                "reason": {"type": "string"},
                            },
                            "required": ["place_id", "order", "time_slot", "reason"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["date", "items"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["days"],
    "additionalProperties": False,
}


class CandidatePlaceBrief(BaseModel):
    """LLM에 넘기는 후보 — 선택용 최소 필드만 (환각 방지)."""

    place_id: str
    name: str
    category: str
    rating: float | None = None
    lat: float
    lng: float
    region: str | None = None
    price_level: int | None = None
    # Places 검색어(음식 must_have)와 매칭된 경우 — LLM이 첫 슬롯 고정하지 않도록 힌트
    must_food_queries: list[str] = Field(default_factory=list)


class DayRegion(BaseModel):
    date: str  # YYYY-MM-DD
    region: str = Field(..., min_length=1)


class ItineraryGenerateRequest(BaseModel):
    start_date: date
    end_date: date
    # 하위 호환: day_regions가 없을 때 전 일정에 적용
    region: str | None = Field(default=None, examples=["오사카"])
    day_regions: list[DayRegion] = Field(
        default_factory=list,
        description="날짜별 지역. 예: 1일 오사카, 2일 교토",
    )
    must_have_food: list[str] = Field(
        default_factory=list,
        description="필수 음식 검색어 예: ['라멘', '오코노미야키']",
    )
    must_have_sights: list[str] = Field(
        default_factory=list,
        description="필수 관광지 검색어 예: ['후시미이나리', '오사카성']",
    )
    # 하위 호환 (음식+관광 합친 목록)
    must_have_queries: list[str] = Field(default_factory=list)
    include_lodging: bool = Field(
        default=True,
        description="Places lodging 후보를 모아 하루 일정에 숙소 1곳 추천",
    )
    travelers: int = Field(default=1, ge=1, le=20, description="여행 인원")
    budget_krw_per_person: int | None = Field(
        default=1_200_000,
        ge=100_000,
        le=20_000_000,
        description="1인당 총 여행경비(원). 여행 전체 기준이며 1일 단가가 아님",
    )
    # 하위 호환: 일행 총액. per_person이 없을 때만 사용
    budget_krw_total: int | None = Field(
        default=None,
        ge=100_000,
        le=50_000_000,
        description="일행 총 예산(원). budget_krw_per_person 없을 때 호환용",
    )
    language_code: str = "ko"
    max_candidates_per_query: int = Field(default=12, ge=5, le=20)
    include_travel_times: bool = True
    travel_mode: str = Field(
        default="AUTO",
        description="AUTO면 도보/대중교통 비교, 또는 WALK|TRANSIT|DRIVE",
    )
    # 출국: 한국 출발 시각 / 귀국: 일본 출발 시각 (티켓 시간표)
    outbound_departure_kst: str | None = Field(
        default="10:00",
        description="출국편 한국 출발 시각(KST) HH:MM — 일본 도착은 서버가 추정",
        pattern=r"^([01]\d|2[0-3]):([0-5]\d)$",
    )
    return_departure_jst: str | None = Field(
        default="11:00",
        description="귀국편 일본 출발 시각(JST) HH:MM",
        pattern=r"^([01]\d|2[0-3]):([0-5]\d)$",
    )
    # 하위 호환
    arrival_time_jst: str | None = Field(default=None, description="deprecated")
    departure_time_jst: str | None = Field(default=None, description="deprecated → return_departure_jst")
    # Places 검색용 공항명. 비우면 첫날 지역으로 자동
    arrival_airport_query: str | None = Field(
        default=None,
        description="도착 공항 Places 검색어 예: 간사이 국제공항 / 나리타 국제공항",
        max_length=80,
    )



class ItineraryItemView(BaseModel):
    """프론트 표시용 — place는 Places API 원본, reason만 AI."""

    place: Place
    order: int
    time_slot: TimeSlot
    ai_description: str
    travel_from_previous: RouteLeg | None = None
    booking_cta: BookingCta | None = None


class AirportArrivalView(BaseModel):
    """첫날 공항→첫 장소. 공항 Place는 Places 검색 결과만(없으면 None)."""

    airport_query: str
    airport: Place | None = None
    travel_to_first: RouteLeg | None = None
    booking_cta: BookingCta | None = None
    # eSIM 등 — KKday 제휴 검색/홈 (요금·상품 미생성)
    connectivity_cta: BookingCta | None = None


class AirportDepartureView(BaseModel):
    """마지막날 마지막 장소→공항. 공항 Place는 Places 검색 결과만(없으면 None)."""

    airport_query: str
    airport: Place | None = None
    travel_from_last: RouteLeg | None = None
    booking_cta: BookingCta | None = None
    return_departure_jst: str | None = None
    # 귀국 버퍼 — 비행시각에서 체크인 여유·Routes 이동시간을 뺀 권장 시각(추정 금지, 계산만)
    arrive_airport_by_jst: str | None = None
    leave_city_by_jst: str | None = None
    checkin_buffer_minutes: int | None = None
    buffer_note: str | None = None


class ItineraryDayView(BaseModel):
    date: str
    region: str | None = None
    items: list[ItineraryItemView]
    arrival_from_airport: AirportArrivalView | None = None
    departure_to_airport: AirportDepartureView | None = None


class ItineraryGenerateResponse(BaseModel):
    days: list[ItineraryDayView]
    candidates_count: int
    llm_source: str  # "claude" | "MOCK_claude"
    validation: dict[str, Any]
    budget_tier: str | None = None
    budget_krw_per_person: int | None = None
    budget_per_person_per_day_krw: int | None = None
    budget_note: str | None = None
    travelers: int | None = None
    budget_krw_total: int | None = None
    arrival_time_jst: str | None = None
    departure_time_jst: str | None = None
    outbound_departure_kst: str | None = None
    return_departure_jst: str | None = None
    flight_note: str | None = None
    estimated_flight_minutes: int | None = None
    # 여행 준비 CTA (eSIM 등) — 일정 장소와 분리
    prep_ctas: list[BookingCta] = Field(default_factory=list)
    # 필수 검색어 오타·미매칭 안내 (Places Autocomplete 기반)
    search_hints: list[SearchHint] = Field(default_factory=list)
