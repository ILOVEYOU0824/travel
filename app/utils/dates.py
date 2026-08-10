from datetime import date


def parse_trip_dates(start: str, end: str) -> tuple[date, date]:
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)

    if end_date <= start_date:
        raise ValueError("종료일은 시작일보다 뒤여야 합니다.")

    return start_date, end_date
