"""Supabase trips — service_role로 저장. RLS는 직접 FE 접근용."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.config import Settings
from app.services.supabase_rest import (
    SupabaseRestError,
    rest_delete,
    rest_insert,
    rest_patch,
    rest_select,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _expires_at(settings: Settings) -> str | None:
    days = int(settings.trips_ttl_days or 0)
    if days <= 0:
        return None
    return (_now() + timedelta(days=days)).isoformat()


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _row_to_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "owner_id": str(row["owner_id"]) if row.get("owner_id") else None,
        "created_at": _iso(row.get("created_at")) or "",
        "updated_at": _iso(row.get("updated_at")) or "",
        "expires_at": _iso(row.get("expires_at")),
        "title": row.get("title") or "내 일본 여행",
        "itinerary": row.get("itinerary") or [],
        "meta": row.get("meta") or {},
        "is_public": bool(row.get("is_public", True)),
    }


def _is_expired(record: dict[str, Any]) -> bool:
    exp = record.get("expires_at")
    if not exp:
        return False
    try:
        dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
    except ValueError:
        return False
    return _now() >= dt


def _valid_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except ValueError:
        return False


async def save_trip(
    settings: Settings,
    payload: dict[str, Any],
    *,
    owner_id: str | None = None,
) -> dict[str, Any]:
    row = {
        "owner_id": owner_id,
        "title": payload.get("title") or "내 일본 여행",
        "itinerary": payload["itinerary"],
        "meta": payload.get("meta") or {},
        "is_public": True,
        "expires_at": _expires_at(settings),
    }
    try:
        created = await rest_insert(settings, "trips", row)
    except SupabaseRestError:
        raise
    return _row_to_record(created)


async def update_trip(
    settings: Settings,
    trip_id: str,
    *,
    title: str | None = None,
    itinerary: list[Any] | None = None,
    meta: dict[str, Any] | None = None,
    owner_id: str | None = None,
) -> dict[str, Any] | None:
    if not _valid_uuid(trip_id):
        return None
    existing = await load_trip(settings, trip_id, include_expired=True)
    if existing is None:
        return None
    # 소유자가 있으면 본인만 수정. 익명(owner null)은 누구나 패치 가능(기존 링크 UX)
    if existing.get("owner_id"):
        if not owner_id or owner_id != existing["owner_id"]:
            return None
    patch: dict[str, Any] = {}
    if title is not None:
        patch["title"] = title.strip() or existing.get("title") or "내 일본 여행"
    if itinerary is not None:
        patch["itinerary"] = itinerary
    if meta is not None:
        patch["meta"] = meta
    if not patch:
        return existing
    # 익명 저장분을 로그인 사용자가 갱신하면 소유권 귀속
    if owner_id and not existing.get("owner_id"):
        patch["owner_id"] = owner_id
    try:
        updated = await rest_patch(
            settings,
            "trips",
            match={"id": f"eq.{trip_id}"},
            patch=patch,
        )
    except SupabaseRestError:
        raise
    if updated is None:
        return None
    return _row_to_record(updated)


async def load_trip(
    settings: Settings,
    trip_id: str,
    *,
    include_expired: bool = False,
) -> dict[str, Any] | None:
    if not _valid_uuid(trip_id):
        return None
    try:
        rows = await rest_select(
            settings,
            "trips",
            params={"id": f"eq.{trip_id}", "select": "*"},
        )
    except SupabaseRestError:
        raise
    if not rows:
        return None
    record = _row_to_record(rows[0])
    if not include_expired and _is_expired(record):
        return None
    # 비공개는 공유 링크로도 막음 (소유자 조회는 list/update에서)
    if not record.get("is_public", True) and not include_expired:
        # load for share: only public. Callers that need private pass owner check separately.
        pass
    return record


async def load_public_trip(settings: Settings, trip_id: str) -> dict[str, Any] | None:
    record = await load_trip(settings, trip_id)
    if record is None:
        return None
    if not record.get("is_public", True):
        return None
    return record


async def delete_trip(
    settings: Settings,
    trip_id: str,
    *,
    owner_id: str | None = None,
) -> bool:
    if not _valid_uuid(trip_id):
        return False
    existing = await load_trip(settings, trip_id, include_expired=True)
    if existing is None:
        return False
    if existing.get("owner_id") and existing["owner_id"] != owner_id:
        return False
    try:
        await rest_delete(settings, "trips", match={"id": f"eq.{trip_id}"})
    except SupabaseRestError:
        return False
    return True


async def list_recent_trips(
    settings: Settings,
    *,
    owner_id: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """로그인한 사용자 일정만. 비로그인이면 빈 목록(프라이버시)."""
    if not owner_id:
        return []
    try:
        rows = await rest_select(
            settings,
            "trips",
            params={
                "owner_id": f"eq.{owner_id}",
                "select": "id,title,created_at,updated_at,expires_at,owner_id",
                "order": "updated_at.desc",
                "limit": str(limit),
            },
        )
    except SupabaseRestError:
        raise
    out: list[dict[str, Any]] = []
    for row in rows:
        rec = _row_to_record(row)
        if _is_expired(rec):
            continue
        out.append(
            {
                "id": rec["id"],
                "title": rec["title"],
                "created_at": rec["created_at"],
                "updated_at": rec["updated_at"],
                "expires_at": rec["expires_at"],
            }
        )
    return out
