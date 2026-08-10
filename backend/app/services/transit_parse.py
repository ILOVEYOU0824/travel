"""Routes API transitDetails 파싱 — Docs:
https://developers.google.com/maps/documentation/routes/transit-route
https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRoutes
"""

from __future__ import annotations

from typing import Any

from app.schemas.route import TransitLineInfo

# field mask에 포함할 transit 관련 경로
TRANSIT_FIELD_MASK_EXTRA = (
    "routes.legs.steps.travelMode,"
    "routes.legs.steps.transitDetails.transitLine.name,"
    "routes.legs.steps.transitDetails.transitLine.nameShort,"
    "routes.legs.steps.transitDetails.transitLine.agencies.name,"
    "routes.legs.steps.transitDetails.transitLine.vehicle.type,"
    "routes.legs.steps.transitDetails.transitLine.vehicle.name"
)


def _localized_text(value: Any) -> str | None:
    if isinstance(value, dict):
        text = value.get("text")
        return str(text) if text else None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def parse_transit_lines_from_leg(leg: dict[str, Any]) -> list[TransitLineInfo]:
    """한 leg의 steps[]에서 transitLine만 추출. 없으면 빈 목록."""
    out: list[TransitLineInfo] = []
    seen: set[tuple[str | None, str | None, str | None]] = set()
    for step in leg.get("steps") or []:
        if (step.get("travelMode") or "").upper() not in {"", "TRANSIT"}:
            # WALK step 등은 transitDetails 없음
            if not step.get("transitDetails"):
                continue
        details = step.get("transitDetails") or {}
        line = details.get("transitLine") or {}
        if not line:
            continue
        vehicle = line.get("vehicle") or {}
        agencies = [
            a.get("name")
            for a in (line.get("agencies") or [])
            if isinstance(a, dict) and a.get("name")
        ]
        info = TransitLineInfo(
            name=line.get("name"),
            name_short=line.get("nameShort"),
            vehicle_type=vehicle.get("type"),
            vehicle_name=_localized_text(vehicle.get("name")),
            agencies=[str(a) for a in agencies],
        )
        key = (info.name, info.name_short, info.vehicle_type)
        if key in seen:
            continue
        seen.add(key)
        out.append(info)
    return out


def transit_mode_label(lines: list[TransitLineInfo]) -> str | None:
    if not lines:
        return None
    names: list[str] = []
    for line in lines:
        label = (line.name_short or line.name or line.vehicle_name or "").strip()
        if label and label not in names:
            names.append(label)
        if len(names) >= 3:
            break
    if not names:
        return "대중교통"
    return "대중교통 · " + ", ".join(names)
