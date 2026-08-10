"""캐시 레이어 — Redis 우선, 연결 실패 시 메모리 TTL 캐시로 폴백."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Any

from app.config import Settings

logger = logging.getLogger(__name__)


class _MemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> str | None:
        async with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            expires, value = item
            if expires < time.time():
                del self._store[key]
                return None
            return value

    async def set(self, key: str, value: str, ttl: int) -> None:
        async with self._lock:
            self._store[key] = (time.time() + ttl, value)


class CacheService:
    def __init__(self) -> None:
        self._memory = _MemoryCache()
        self._redis: Any = None
        self._redis_ok = False
        self._enabled = True
        self._default_ttl = 3600

    async def init(self, settings: Settings) -> None:
        self._enabled = settings.cache_enabled
        self._default_ttl = settings.cache_ttl_seconds
        if not self._enabled:
            logger.info("캐시 비활성화")
            return
        if not settings.redis_url:
            logger.info("REDIS_URL 없음 — 메모리 캐시 사용")
            return
        try:
            import redis.asyncio as redis

            client = redis.from_url(settings.redis_url, decode_responses=True)
            await client.ping()
            self._redis = client
            self._redis_ok = True
            logger.info("Redis 캐시 연결됨")
        except Exception as exc:  # noqa: BLE001 — 캐시 실패는 서비스 중단 사유 아님
            logger.warning("Redis 연결 실패, 메모리 캐시로 폴백: %s", exc)
            self._redis = None
            self._redis_ok = False

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()

    @property
    def backend_name(self) -> str:
        if not self._enabled:
            return "off"
        return "redis" if self._redis_ok else "memory"

    async def get_json(self, key: str) -> Any | None:
        if not self._enabled:
            return None
        raw: str | None = None
        if self._redis_ok and self._redis is not None:
            try:
                raw = await self._redis.get(key)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Redis GET 실패: %s", exc)
                raw = None
        if raw is None:
            raw = await self._memory.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        if not self._enabled:
            return
        ttl = ttl if ttl is not None else self._default_ttl
        raw = json.dumps(value, ensure_ascii=False, default=str)
        await self._memory.set(key, raw, ttl)
        if self._redis_ok and self._redis is not None:
            try:
                await self._redis.set(key, raw, ex=ttl)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Redis SET 실패: %s", exc)


_cache = CacheService()


def get_cache() -> CacheService:
    return _cache


def cache_key(prefix: str, payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]
    return f"japantrip:{prefix}:{digest}"
