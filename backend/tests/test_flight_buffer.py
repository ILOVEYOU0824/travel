"""귀국 공항 도착·시내 출발 권장 시각."""

from __future__ import annotations

from app.services.flight_windows import (
    DEFAULT_AIRPORT_CHECKIN_BUFFER_MINUTES,
    arrive_airport_by_jst,
    leave_city_by_jst,
)


def test_arrive_airport_by_subtracts_checkin() -> None:
    # 18:30 비행, 체크인 120분 → 16:30
    assert arrive_airport_by_jst(18, 30, DEFAULT_AIRPORT_CHECKIN_BUFFER_MINUTES) == "16:30"


def test_leave_city_uses_routes_duration() -> None:
    # 공항 16:30 도착 권장, 이동 40분 → 시내 15:50
    assert (
        leave_city_by_jst(18, 30, checkin_buffer=120, travel_seconds=40 * 60) == "15:50"
    )
