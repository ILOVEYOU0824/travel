"""비행 시간표 → 일정 창 테스트."""

from __future__ import annotations

from app.services.flight_windows import (
    allowed_slots_for_day,
    estimate_flight_minutes,
    resolve_flight_windows,
)


def test_osaka_flight_duration() -> None:
    assert estimate_flight_minutes("오사카") == 120


def test_outbound_departure_estimates_arrival() -> None:
    # 10:00 한국 출발 + 120분 → 12:00 도착 → +90분 → lunch
    fw = resolve_flight_windows(
        outbound_departure_kst="10:00",
        return_departure_jst="11:00",
        first_region="오사카",
    )
    assert fw.arrival_time_jst == "12:00"
    assert fw.estimated_flight_minutes == 120
    assert fw.first_day_earliest_slot == "afternoon"
    assert fw.last_day_latest_slot == "morning"


def test_tokyo_longer_flight() -> None:
    fw = resolve_flight_windows(
        outbound_departure_kst="09:00",
        return_departure_jst="20:00",
        first_region="도쿄",
    )
    assert fw.arrival_time_jst == "11:30"
    assert fw.estimated_flight_minutes == 150


def test_allowed_slots() -> None:
    dates = ["2026-09-10", "2026-09-11", "2026-09-12"]
    fw = resolve_flight_windows(
        outbound_departure_kst="14:00",
        return_departure_jst="10:00",
        first_region="오사카",
    )
    first = allowed_slots_for_day(date=dates[0], dates=dates, windows=fw)
    assert "morning" not in first
