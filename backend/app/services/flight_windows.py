"""출국·귀국 비행 시간표 → 첫날/마지막날 일정 창.

사용자는 티켓의 출발 시각만 입력한다.
- 출국: 한국 출발 → 지역별 표준 비행시간으로 일본 도착 추정
- 귀국: 일본 출발 → 공항 여유를 빼 마지막날 일정 종료
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_SLOTS = ("morning", "lunch", "afternoon", "dinner", "evening")

_FLIGHT_MINUTES: list[tuple[tuple[str, ...], int]] = [
    (("후쿠오카", "하카타", "기타큐슈", "사가", "나가사키"), 95),
    (("오사카", "간사이", "고베", "나라", "와카야마", "교토"), 120),
    (("나고야", "중부", "아이치", "기후"), 120),
    (("도쿄", "나리타", "하네다", "요코하마", "가마쿠라", "지바", "사이타마"), 150),
    (("삿포로", "홋카이도", "신치토세", "하코다테"), 160),
    (("오키나와", "나하", "이시가키", "미야코"), 165),
    (("히로시마", "오카야마", "마쓰야마", "다카마쓰"), 110),
]


def parse_hhmm(value: str | None) -> tuple[int, int] | None:
    if not value or not isinstance(value, str):
        return None
    m = _TIME_RE.match(value.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _minutes(hh: int, mm: int) -> int:
    return hh * 60 + mm


def _fmt(total_min: int) -> str:
    total_min %= 24 * 60
    if total_min < 0:
        total_min += 24 * 60
    return f"{total_min // 60:02d}:{total_min % 60:02d}"


def estimate_flight_minutes(region: str | None) -> int:
    text = region or ""
    for keys, mins in _FLIGHT_MINUTES:
        if any(k in text for k in keys):
            return mins
    return 130


@dataclass(frozen=True)
class FlightWindows:
    outbound_departure_kst: str | None
    return_departure_jst: str | None
    arrival_time_jst: str | None
    estimated_flight_minutes: int | None
    first_day_earliest_slot: str
    last_day_latest_slot: str
    first_day_note: str
    last_day_note: str
    airport_buffer_minutes: int = 180


def _arrival_to_slot(hh: int, mm: int) -> tuple[str, str]:
    t = _minutes(hh, mm) + 90
    if t < _minutes(10, 0):
        return "morning", "도착 후 오전부터 가벼운 일정 가능"
    if t < _minutes(12, 30):
        return "lunch", "도착 후 점심·오후부터 일정 권장"
    if t < _minutes(15, 30):
        return "afternoon", "도착이 늦어 오후부터 일정 권장"
    if t < _minutes(18, 30):
        return "dinner", "저녁 식사·야경 위주의 짧은 일정 권장"
    return "evening", "밤 늦은 도착 — 첫날은 숙소·근처만 권장"


# 국제선 체크인·보안 여유(분). 이동시간은 Routes로 따로 빼서 leave_city_by 계산.
DEFAULT_AIRPORT_CHECKIN_BUFFER_MINUTES = 120
# 슬롯 계획용: 체크인+시내 이동 대략치 (정확한 이동은 hydrate에서 Routes로 보정)
DEFAULT_CITY_TO_AIRPORT_PLAN_BUFFER_MINUTES = 180


def arrive_airport_by_jst(return_hh: int, return_mm: int, checkin_buffer: int) -> str:
    return _fmt(_minutes(return_hh, return_mm) - checkin_buffer)


def leave_city_by_jst(
    return_hh: int,
    return_mm: int,
    *,
    checkin_buffer: int,
    travel_seconds: int | None,
) -> str:
    arrive_by = _minutes(return_hh, return_mm) - checkin_buffer
    travel_min = int(round((travel_seconds or 0) / 60)) if travel_seconds else 45
    return _fmt(arrive_by - max(travel_min, 15))


def _departure_to_slot(hh: int, mm: int, buffer: int = DEFAULT_CITY_TO_AIRPORT_PLAN_BUFFER_MINUTES) -> tuple[str, str]:
    leave_by = _minutes(hh, mm) - buffer
    arrive_by = arrive_airport_by_jst(hh, mm, DEFAULT_AIRPORT_CHECKIN_BUFFER_MINUTES)
    flight = f"{hh:02d}:{mm:02d}"
    if leave_by < _minutes(8, 0):
        return (
            "morning",
            f"이른 귀국편 {flight} — 공항 {arrive_by}까지 도착 권장, 관광 최소화",
        )
    if leave_by < _minutes(11, 0):
        return (
            "morning",
            f"귀국 {flight} · 공항 {arrive_by}까지 도착 권장 — 아침만 짧게",
        )
    if leave_by < _minutes(14, 0):
        return (
            "lunch",
            f"귀국 {flight} · 공항 {arrive_by}까지 도착 권장 — 점심 전후까지",
        )
    if leave_by < _minutes(17, 0):
        return (
            "afternoon",
            f"귀국 {flight} · 공항 {arrive_by}까지 도착 권장 — 오후 초반까지",
        )
    return (
        "dinner",
        f"귀국 {flight} · 공항 {arrive_by}까지 도착 권장 — 저녁 전후까지(여유 이동)",
    )


def resolve_flight_windows(
    *,
    outbound_departure_kst: str | None = None,
    return_departure_jst: str | None = None,
    first_region: str | None = None,
    arrival_time_jst: str | None = None,
    departure_time_jst: str | None = None,
) -> FlightWindows:
    out = parse_hhmm(outbound_departure_kst)
    ret = parse_hhmm(return_departure_jst or departure_time_jst)
    flight_mins = estimate_flight_minutes(first_region)

    arr = parse_hhmm(arrival_time_jst) if not out else None
    if out:
        arr_str = _fmt(_minutes(*out) + flight_mins)
        arr_parsed = parse_hhmm(arr_str)
        assert arr_parsed is not None
        first_slot, first_base = _arrival_to_slot(*arr_parsed)
        out_str = f"{out[0]:02d}:{out[1]:02d}"
        first_note = (
            f"출국 {out_str} 출발 → 일본 도착 약 {arr_str} 추정"
            f"(비행 약 {flight_mins}분 · 표준치). {first_base}"
        )
        est = flight_mins
    elif arr:
        arr_str = f"{arr[0]:02d}:{arr[1]:02d}"
        first_slot, first_note = _arrival_to_slot(*arr)
        out_str = None
        est = None
    else:
        arr_str = None
        first_slot, first_note = "morning", "출국 출발 미지정 — 첫날 오전부터 구성"
        out_str = None
        est = None

    if ret:
        last_slot, last_note = _departure_to_slot(*ret)
        ret_str = f"{ret[0]:02d}:{ret[1]:02d}"
    else:
        last_slot, last_note = "evening", "귀국편 출발 미지정 — 마지막 날 저녁까지 구성 가능"
        ret_str = None

    return FlightWindows(
        outbound_departure_kst=out_str,
        return_departure_jst=ret_str,
        arrival_time_jst=arr_str,
        estimated_flight_minutes=est,
        first_day_earliest_slot=first_slot,
        last_day_latest_slot=last_slot,
        first_day_note=first_note,
        last_day_note=last_note,
        airport_buffer_minutes=DEFAULT_CITY_TO_AIRPORT_PLAN_BUFFER_MINUTES,
    )


def slot_index(slot: str) -> int:
    try:
        return _SLOTS.index(slot)
    except ValueError:
        return 0


def allowed_slots_for_day(
    *,
    date: str,
    dates: list[str],
    windows: FlightWindows,
) -> list[str]:
    if not dates:
        return list(_SLOTS)
    if date == dates[0]:
        return list(_SLOTS[slot_index(windows.first_day_earliest_slot) :])
    if date == dates[-1]:
        return list(_SLOTS[: slot_index(windows.last_day_latest_slot) + 1])
    return list(_SLOTS)
