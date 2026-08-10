"""Routes API 스키마 — 이동시간/거리는 API 응답만. LLM 추정 금지.

Docs:
https://developers.google.com/maps/documentation/routes/compute_route_matrix
https://developers.google.com/maps/documentation/routes/compute-route-over
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class TravelMode(str, Enum):
    # https://developers.google.com/maps/documentation/routes/reference/rest/v2/RouteTravelMode
    walk = "WALK"
    transit = "TRANSIT"
    drive = "DRIVE"
    bicycle = "BICYCLE"
    two_wheeler = "TWO_WHEELER"


class Waypoint(BaseModel):
    """origin/destination — lat/lng 또는 place_id 중 하나 필수."""

    lat: float | None = None
    lng: float | None = None
    place_id: str | None = None

    @model_validator(mode="after")
    def require_coords_or_place(self) -> Waypoint:
        has_coords = self.lat is not None and self.lng is not None
        if not has_coords and not self.place_id:
            raise ValueError("lat/lng 또는 place_id 중 하나는 필요합니다.")
        return self


class RouteComputeRequest(BaseModel):
    origin: Waypoint
    destination: Waypoint
    travel_mode: TravelMode = TravelMode.walk
    language_code: str = "ko"


class BookingCta(BaseModel):
    """예약 CTA — URL은 Klook 검색(+선택적 어필리에이트 래핑). 가격/좌석 정보 없음."""

    provider: str = "klook"
    label: str
    url: str
    hint: str
    product_hint: str | None = None  # airport_rail | shinkansen | rail
    search_query: str | None = None
    # Routes API에서 읽은 노선명 (있을 때만)
    source_line_name: str | None = None


class TransitLineInfo(BaseModel):
    """Routes API legs.steps.transitDetails.transitLine 요약. LLM 생성 금지."""

    name: str | None = None
    name_short: str | None = None
    vehicle_type: str | None = None  # TransitVehicleType enum 문자열
    vehicle_name: str | None = None
    agencies: list[str] = Field(default_factory=list)


class RouteLeg(BaseModel):
    distance_meters: int | None = None
    duration_seconds: int | None = None
    static_duration_seconds: int | None = None
    # Routes API routes.polyline.encodedPolyline — 지도 경로 표시용
    encoded_polyline: str | None = None
    travel_mode: TravelMode | None = None
    # 예: "도보", "대중교통 · 하루카" — API 모드/노선 기반
    mode_label: str | None = None
    # Google Maps 길찾기 딥링크 (사용자가 상세 환승 확인용)
    google_maps_dir_uri: str | None = None
    # TRANSIT 구간의 탑승 노선 (Routes steps.transitDetails)
    transit_lines: list[TransitLineInfo] = Field(default_factory=list)
    booking_cta: BookingCta | None = None


class RouteComputeResponse(BaseModel):
    distance_meters: int | None = None
    duration_seconds: int | None = None
    static_duration_seconds: int | None = None
    encoded_polyline: str | None = None
    travel_mode: TravelMode
    source: str  # "google_routes" | "MOCK_routes"
    legs: list[RouteLeg] = Field(default_factory=list)


class RouteMatrixRequest(BaseModel):
    origins: list[Waypoint] = Field(..., min_length=1, max_length=25)
    destinations: list[Waypoint] = Field(..., min_length=1, max_length=25)
    travel_mode: TravelMode = TravelMode.walk
    language_code: str = "ko"


class RouteMatrixElement(BaseModel):
    origin_index: int
    destination_index: int
    distance_meters: int | None = None
    duration_seconds: int | None = None
    static_duration_seconds: int | None = None
    condition: str | None = None  # ROUTE_EXISTS | ROUTE_NOT_FOUND


class RouteMatrixResponse(BaseModel):
    elements: list[RouteMatrixElement]
    travel_mode: TravelMode
    source: str


def parse_duration_seconds(value: str | None) -> int | None:
    """Routes API duration: '160s' → 160. 추정값 생성 금지."""
    if not value or not isinstance(value, str):
        return None
    if value.endswith("s") and value[:-1].isdigit():
        return int(value[:-1])
    # 소수 초 등
    if value.endswith("s"):
        try:
            return int(float(value[:-1]))
        except ValueError:
            return None
    return None
