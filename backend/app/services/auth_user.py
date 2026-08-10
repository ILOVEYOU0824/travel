"""Supabase JWT(Bearer) → user id. 없으면 비로그인.

ECC(ES256) 등 비대칭 키: JWKS로 검증.
Legacy HS256: SUPABASE_JWT_SECRET으로 검증.
Docs: https://supabase.com/docs/guides/auth/jwts
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, Request
from jwt import PyJWKClient

from app.config import Settings, get_settings

logger = logging.getLogger("japantrip")


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str | None = None


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


@lru_cache(maxsize=8)
def _jwks_client(supabase_url: str) -> PyJWKClient:
    base = supabase_url.rstrip("/")
    return PyJWKClient(f"{base}/auth/v1/.well-known/jwks.json", cache_keys=True)


def _user_from_payload(payload: dict) -> AuthUser:
    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise HTTPException(status_code=401, detail="토큰에 사용자 정보가 없습니다.")
    email = payload.get("email")
    return AuthUser(id=sub, email=email if isinstance(email, str) else None)


def decode_supabase_user(settings: Settings, token: str) -> AuthUser:
    """JWKS(ES256 등) 우선, 실패 시 Legacy HS256 secret."""
    errors: list[str] = []

    if settings.supabase_url.strip():
        try:
            client = _jwks_client(settings.supabase_url.strip())
            signing_key = client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256", "EdDSA"],
                audience="authenticated",
            )
            return _user_from_payload(payload)
        except Exception as exc:  # noqa: BLE001 — 다음 방식으로 폴백
            errors.append(f"jwks:{exc}")

    secret = settings.supabase_jwt_secret.strip()
    if secret:
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
            return _user_from_payload(payload)
        except jwt.PyJWTError as exc:
            errors.append(f"hs256:{exc}")
            raise HTTPException(status_code=401, detail="유효하지 않은 로그인 세션입니다.") from exc

    logger.warning("JWT 검증 실패: %s", "; ".join(errors) if errors else "no verifier")
    raise HTTPException(
        status_code=503,
        detail="로그인 검증 설정이 필요합니다. SUPABASE_URL 또는 SUPABASE_JWT_SECRET을 확인하세요.",
    )


async def optional_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> AuthUser | None:
    """Authorization 없으면 None. 잘못된 토큰이면 401."""
    token = _extract_bearer(request)
    if not token:
        return None
    if not settings.supabase_url.strip() and not settings.supabase_jwt_secret.strip():
        logger.warning("Bearer 있음 but Supabase 검증 설정 없음")
        raise HTTPException(status_code=503, detail="로그인 서버 설정이 필요합니다.")
    return decode_supabase_user(settings, token)


async def require_user(
    user: AuthUser | None = Depends(optional_user),
) -> AuthUser:
    if user is None:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    return user
