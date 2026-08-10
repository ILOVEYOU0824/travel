"""Supabase PostgREST (service_role). trips CRUD 전용."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings


class SupabaseRestError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _base(settings: Settings) -> str:
    return settings.supabase_url.rstrip("/") + "/rest/v1"


def _headers(settings: Settings, *, prefer: str | None = None) -> dict[str, str]:
    key = settings.supabase_service_role_key
    h = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


async def rest_select(
    settings: Settings,
    table: str,
    *,
    params: dict[str, str],
) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.get(
            f"{_base(settings)}/{table}",
            headers=_headers(settings),
            params=params,
        )
    if res.status_code >= 400:
        raise SupabaseRestError(
            f"Supabase select 실패: {res.status_code} {res.text}",
            status_code=res.status_code,
        )
    data = res.json()
    if not isinstance(data, list):
        raise SupabaseRestError("Supabase select 응답이 배열이 아닙니다.")
    return data


async def rest_insert(
    settings: Settings,
    table: str,
    row: dict[str, Any],
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(
            f"{_base(settings)}/{table}",
            headers=_headers(settings, prefer="return=representation"),
            json=row,
        )
    if res.status_code >= 400:
        raise SupabaseRestError(
            f"Supabase insert 실패: {res.status_code} {res.text}",
            status_code=res.status_code,
        )
    data = res.json()
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    raise SupabaseRestError("Supabase insert 응답 형식 오류")


async def rest_patch(
    settings: Settings,
    table: str,
    *,
    match: dict[str, str],
    patch: dict[str, Any],
) -> dict[str, Any] | None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.patch(
            f"{_base(settings)}/{table}",
            headers=_headers(settings, prefer="return=representation"),
            params=match,
            json=patch,
        )
    if res.status_code >= 400:
        raise SupabaseRestError(
            f"Supabase patch 실패: {res.status_code} {res.text}",
            status_code=res.status_code,
        )
    data = res.json()
    if isinstance(data, list):
        return data[0] if data else None
    return None


async def rest_delete(
    settings: Settings,
    table: str,
    *,
    match: dict[str, str],
) -> bool:
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.delete(
            f"{_base(settings)}/{table}",
            headers=_headers(settings),
            params=match,
        )
    if res.status_code >= 400:
        raise SupabaseRestError(
            f"Supabase delete 실패: {res.status_code} {res.text}",
            status_code=res.status_code,
        )
    return True
