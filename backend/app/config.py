from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # development | production — production이면 MOCK 금지
    app_env: str = "development"

    google_maps_api_key: str = ""
    anthropic_api_key: str = ""
    agoda_cid: str = ""
    # Klook / Travelpayouts — 상품 URL 추측 금지. 검색 URL + 선택적 래핑만.
    # 템플릿 예: https://tp.media/r?marker=YOUR_MARKER&u={url}
    travelpayouts_klook_url_template: str = ""
    # marker만 있으면 기본 래핑: https://tp.media/r?marker={marker}&u={url}
    travelpayouts_marker: str = ""
    # Tools에서 만든 홈 숏링크 (검색 래핑 없을 때 폴백 CTA)
    klook_affiliate_home_url: str = ""
    # KKday / Travelpayouts — eSIM·투어 등. 예: https://kkday.tpk.lu/I3n5UXqs
    kkday_affiliate_home_url: str = ""
    # 선택: https://tp.media/r?marker=...&u={url}
    travelpayouts_kkday_url_template: str = ""
    use_mock_places: bool = True
    use_mock_routes: bool = True
    use_mock_llm: bool = True

    # 캐시: Redis 없으면 메모리 TTL로 자동 폴백
    cache_enabled: bool = True
    redis_url: str = "redis://127.0.0.1:6379/0"
    cache_ttl_seconds: int = 3600
    # Routes는 교통 상황에 더 민감 — 기본 더 짧게
    cache_ttl_routes_seconds: int = 1800

    # 로그인 없는 일정 저장 경로 (Supabase 미설정 시 폴백)
    trips_data_dir: str = "data/trips"
    # 공유 링크 만료 (일). 0이면 만료 없음
    trips_ttl_days: int = 90
    # OG/리다이렉트용 FE origin (예: http://localhost:5173 / Netlify URL)
    public_frontend_url: str = "http://localhost:5173"
    # CORS 허용 origin — 쉼표 구분. 비우면 localhost만.
    # 예: https://japantrip.netlify.app,http://localhost:5173
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Supabase — URL+service_role+jwt_secret 있으면 trips DB 사용
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # 카카오 OIDC 토큰 교환 (서버 전용 — FE에 secret 넣지 말 것)
    kakao_rest_api_key: str = ""
    kakao_client_secret: str = ""

    @property
    def use_supabase_trips(self) -> bool:
        # JWT는 JWKS(URL) 또는 Legacy secret으로 검증 — secret 필수는 아님
        return bool(
            self.supabase_url.strip() and self.supabase_service_role_key.strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
