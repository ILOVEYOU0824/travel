"""Supabase JWT 검증 단위 테스트."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from app.config import Settings
from app.services.auth_user import decode_supabase_user


def _token(secret: str, *, sub: str = "user-123", aud: str = "authenticated") -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": sub,
            "aud": aud,
            "role": "authenticated",
            "iat": now,
            "exp": now + timedelta(hours=1),
            "email": "t@example.com",
        },
        secret,
        algorithm="HS256",
    )


def test_decode_supabase_user_ok() -> None:
    secret = "test-jwt-secret"
    settings = Settings(supabase_jwt_secret=secret)
    user = decode_supabase_user(settings, _token(secret))
    assert user.id == "user-123"
    assert user.email == "t@example.com"


def test_decode_supabase_user_bad_secret() -> None:
    settings = Settings(supabase_jwt_secret="right")
    with pytest.raises(HTTPException) as exc:
        decode_supabase_user(settings, _token("wrong"))
    assert exc.value.status_code == 401
