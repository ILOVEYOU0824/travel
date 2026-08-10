from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.schemas.route import (
    RouteComputeRequest,
    RouteComputeResponse,
    RouteMatrixRequest,
    RouteMatrixResponse,
)
from app.services.route_compute import compute_matrix, compute_route
from app.services.routes_service import RoutesApiError

router = APIRouter(prefix="/routes", tags=["routes"])


@router.post("/compute", response_model=RouteComputeResponse)
async def post_compute_route(
    body: RouteComputeRequest,
    settings: Settings = Depends(get_settings),
) -> RouteComputeResponse:
    """A→B 경로/시간 — Routes API Compute Routes. LLM 추정 금지."""
    try:
        return await compute_route(settings, body)
    except RoutesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/matrix", response_model=RouteMatrixResponse)
async def post_route_matrix(
    body: RouteMatrixRequest,
    settings: Settings = Depends(get_settings),
) -> RouteMatrixResponse:
    """다대다 거리·시간 행렬 — Routes API Compute Route Matrix."""
    try:
        return await compute_matrix(settings, body)
    except RoutesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
