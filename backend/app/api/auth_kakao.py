"""카카오 OIDC 코드 → id_token 교환 (account_email 없이 로그인).

Supabase signInWithOAuth는 account_email을 강제해 개인 앱에서 KOE205가 남.
프론트는 authorize(scope=openid+profile)만 하고, secret은 서버에서만 사용.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"


class KakaoExchangeRequest(BaseModel):
    code: str = Field(..., min_length=1)
    redirect_uri: str = Field(..., min_length=1)


class KakaoExchangeResponse(BaseModel):
    id_token: str
    access_token: str | None = None


@router.post("/kakao/exchange", response_model=KakaoExchangeResponse)
async def exchange_kakao_code(
    body: KakaoExchangeRequest,
    settings: Settings = Depends(get_settings),
) -> KakaoExchangeResponse:
    client_id = settings.kakao_rest_api_key.strip()
    client_secret = settings.kakao_client_secret.strip()
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail="KAKAO_REST_API_KEY / KAKAO_CLIENT_SECRET을 backend/.env에 설정하세요.",
        )

    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": body.redirect_uri,
        "code": body.code,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.post(
            KAKAO_TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        )
    if res.status_code >= 400:
        raise HTTPException(
            status_code=400,
            detail=f"카카오 토큰 교환 실패: {res.text}",
        )
    payload = res.json()
    id_token = payload.get("id_token")
    if not id_token or not isinstance(id_token, str):
        raise HTTPException(
            status_code=400,
            detail=(
                "id_token이 없습니다. 카카오 로그인에서 OpenID Connect를 ON으로 두고 "
                "authorize scope에 openid가 포함되는지 확인하세요."
            ),
        )
    access = payload.get("access_token")
    return KakaoExchangeResponse(
        id_token=id_token,
        access_token=access if isinstance(access, str) else None,
    )
