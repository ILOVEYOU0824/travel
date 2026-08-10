import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth_kakao import router as auth_kakao_router
from app.api.itinerary import router as itinerary_router
from app.api.meta import router as meta_router
from app.api.places import router as places_router
from app.api.routes import router as routes_router
from app.api.share import router as share_router
from app.api.trip_context import router as trip_context_router
from app.api.trips import router as trips_router
from app.config import get_settings
from app.errors import register_exception_handlers
from app.services.cache import get_cache
from app.services import trip_store
from app.startup_checks import assert_production_safe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    assert_production_safe(settings)
    await get_cache().init(settings)
    removed = trip_store.purge_expired(settings)
    if removed:
        logging.getLogger("japantrip").info("만료 일정 %s건 삭제", removed)
    yield
    await get_cache().close()


app = FastAPI(
    title="JapanTrip AI",
    description=(
        "일본 여행 일정 AI 플래너 API. "
        "장소 데이터는 Google Places API만 사용하며 LLM은 선택/정렬만 담당합니다."
    ),
    version="0.3.0",
    lifespan=lifespan,
)

register_exception_handlers(app)

def _cors_origins() -> list[str]:
    raw = get_settings().cors_origins.strip()
    if not raw:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    return [o.strip() for o in raw.split(",") if o.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(share_router)
app.include_router(auth_kakao_router, prefix="/api/v1")
app.include_router(places_router, prefix="/api/v1")
app.include_router(routes_router, prefix="/api/v1")
app.include_router(itinerary_router, prefix="/api/v1")
app.include_router(trips_router, prefix="/api/v1")
app.include_router(meta_router, prefix="/api/v1")
app.include_router(trip_context_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str | bool]:
    settings = get_settings()
    cache = get_cache()
    return {
        "status": "ok",
        "cache": cache.backend_name,
        "app_env": settings.app_env,
        "mock_places": settings.use_mock_places,
        "mock_routes": settings.use_mock_routes,
        "mock_llm": settings.use_mock_llm,
    }
