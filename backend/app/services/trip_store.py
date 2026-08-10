"""일정 저장 — Supabase(설정 시) 또는 UUID JSON 파일 폴백."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.config import Settings
from app.services import trip_store_supabase


def _trips_dir(settings: Settings) -> Path:
    path = Path(settings.trips_data_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_id(trip_id: str) -> bool:
    return bool(trip_id) and "/" not in trip_id and "\\" not in trip_id and ".." not in trip_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _expires_at(settings: Settings, created: datetime | None = None) -> str | None:
    days = int(settings.trips_ttl_days or 0)
    if days <= 0:
        return None
    base = created or _now()
    return (base + timedelta(days=days)).isoformat()


def _is_expired(record: dict[str, Any]) -> bool:
    exp = _parse_iso(record.get("expires_at"))
    if exp is None:
        return False
    return _now() >= exp


def save_trip(
    settings: Settings,
    payload: dict[str, Any],
    *,
    owner_id: str | None = None,
) -> dict[str, Any]:
    trip_id = str(uuid.uuid4())
    now = _now().isoformat()
    record = {
        "id": trip_id,
        "owner_id": owner_id,
        "created_at": now,
        "updated_at": now,
        "expires_at": _expires_at(settings),
        "title": payload.get("title") or "내 일본 여행",
        "itinerary": payload["itinerary"],
        "meta": payload.get("meta") or {},
        "is_public": True,
    }
    path = _trips_dir(settings) / f"{trip_id}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def update_trip(
    settings: Settings,
    trip_id: str,
    *,
    title: str | None = None,
    itinerary: list[Any] | None = None,
    meta: dict[str, Any] | None = None,
    owner_id: str | None = None,
) -> dict[str, Any] | None:
    record = load_trip(settings, trip_id, include_expired=False)
    if record is None:
        return None
    if record.get("owner_id") and owner_id != record.get("owner_id"):
        return None
    if title is not None:
        record["title"] = title.strip() or record.get("title") or "내 일본 여행"
    if itinerary is not None:
        record["itinerary"] = itinerary
    if meta is not None:
        record["meta"] = meta
    if owner_id and not record.get("owner_id"):
        record["owner_id"] = owner_id
    record["updated_at"] = _now().isoformat()
    # 만료는 생성 기준 유지 (없으면 갱신 시점에서 재설정)
    if not record.get("expires_at"):
        created = _parse_iso(record.get("created_at"))
        record["expires_at"] = _expires_at(settings, created)
    path = _trips_dir(settings) / f"{trip_id}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def load_trip(
    settings: Settings,
    trip_id: str,
    *,
    include_expired: bool = False,
) -> dict[str, Any] | None:
    if not _safe_id(trip_id):
        return None
    path = _trips_dir(settings) / f"{trip_id}.json"
    if not path.is_file():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not include_expired and _is_expired(record):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    return record


def delete_trip(
    settings: Settings,
    trip_id: str,
    *,
    owner_id: str | None = None,
) -> bool:
    if not _safe_id(trip_id):
        return False
    record = load_trip(settings, trip_id, include_expired=True)
    if record is None:
        return False
    if record.get("owner_id") and record.get("owner_id") != owner_id:
        return False
    path = _trips_dir(settings) / f"{trip_id}.json"
    if not path.is_file():
        return False
    path.unlink()
    return True


def list_recent_trips(
    settings: Settings,
    limit: int = 20,
    *,
    owner_id: str | None = None,
) -> list[dict[str, Any]]:
    files = sorted(
        _trips_dir(settings).glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    out: list[dict[str, Any]] = []
    for path in files:
        if len(out) >= limit:
            break
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if _is_expired(data):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            continue
        if owner_id is not None and data.get("owner_id") != owner_id:
            continue
        out.append(
            {
                "id": data.get("id"),
                "title": data.get("title"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "expires_at": data.get("expires_at"),
            }
        )
    return out


def purge_expired(settings: Settings) -> int:
    removed = 0
    for path in _trips_dir(settings).glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if _is_expired(data):
            try:
                path.unlink(missing_ok=True)
                removed += 1
            except OSError:
                pass
    return removed


# --- async facade (Supabase 또는 파일) ---


async def asave_trip(
    settings: Settings,
    payload: dict[str, Any],
    *,
    owner_id: str | None = None,
) -> dict[str, Any]:
    if settings.use_supabase_trips:
        return await trip_store_supabase.save_trip(settings, payload, owner_id=owner_id)
    return save_trip(settings, payload, owner_id=owner_id)


async def aupdate_trip(
    settings: Settings,
    trip_id: str,
    *,
    title: str | None = None,
    itinerary: list[Any] | None = None,
    meta: dict[str, Any] | None = None,
    owner_id: str | None = None,
) -> dict[str, Any] | None:
    if settings.use_supabase_trips:
        return await trip_store_supabase.update_trip(
            settings,
            trip_id,
            title=title,
            itinerary=itinerary,
            meta=meta,
            owner_id=owner_id,
        )
    return update_trip(
        settings,
        trip_id,
        title=title,
        itinerary=itinerary,
        meta=meta,
        owner_id=owner_id,
    )


async def aload_trip(
    settings: Settings,
    trip_id: str,
    *,
    include_expired: bool = False,
) -> dict[str, Any] | None:
    if settings.use_supabase_trips:
        return await trip_store_supabase.load_trip(
            settings, trip_id, include_expired=include_expired
        )
    return load_trip(settings, trip_id, include_expired=include_expired)


async def aload_public_trip(settings: Settings, trip_id: str) -> dict[str, Any] | None:
    if settings.use_supabase_trips:
        return await trip_store_supabase.load_public_trip(settings, trip_id)
    record = load_trip(settings, trip_id)
    if record is None:
        return None
    if record.get("is_public") is False:
        return None
    return record


async def adelete_trip(
    settings: Settings,
    trip_id: str,
    *,
    owner_id: str | None = None,
) -> bool:
    if settings.use_supabase_trips:
        return await trip_store_supabase.delete_trip(settings, trip_id, owner_id=owner_id)
    return delete_trip(settings, trip_id, owner_id=owner_id)


async def alist_recent_trips(
    settings: Settings,
    *,
    owner_id: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    if settings.use_supabase_trips:
        return await trip_store_supabase.list_recent_trips(
            settings, owner_id=owner_id, limit=limit
        )
    # 파일 폴백: 로그인 시 본인 것만, 아니면 최근 전체(기존 동작)
    if owner_id:
        return list_recent_trips(settings, limit, owner_id=owner_id)
    return list_recent_trips(settings, limit)
