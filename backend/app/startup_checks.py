"""앱 기동 시 환경 검증."""

from __future__ import annotations

import logging

from app.config import Settings

logger = logging.getLogger("japantrip")


def assert_production_safe(settings: Settings) -> None:
    """production에서 MOCK 또는 필수 키 누락이면 기동 실패."""
    env = (settings.app_env or "development").strip().lower()
    if env not in {"production", "prod"}:
        if settings.use_mock_places or settings.use_mock_routes or settings.use_mock_llm:
            logger.warning(
                "MOCK 활성 (APP_ENV=%s). 배포 전에는 USE_MOCK_*=false + APP_ENV=production",
                env,
            )
        return

    mocks = []
    if settings.use_mock_places:
        mocks.append("USE_MOCK_PLACES")
    if settings.use_mock_routes:
        mocks.append("USE_MOCK_ROUTES")
    if settings.use_mock_llm:
        mocks.append("USE_MOCK_LLM")
    if mocks:
        raise RuntimeError(
            "production에서 MOCK을 켤 수 없습니다: " + ", ".join(mocks)
        )
    if not settings.google_maps_api_key:
        raise RuntimeError("production에는 GOOGLE_MAPS_API_KEY가 필요합니다.")
    if not settings.anthropic_api_key:
        raise RuntimeError("production에는 ANTHROPIC_API_KEY가 필요합니다.")
    logger.info("production 환경 검증 통과")
