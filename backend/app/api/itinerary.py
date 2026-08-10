from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.services.auth_user import AuthUser, require_user
from app.schemas.budget_rain import BudgetTrackerRequest, RainAdviceRequest
from app.schemas.edit_day import (
    ApplySwapRequest,
    ApplySwapResponse,
    OptimizeDayRequest,
    OptimizeDayResponse,
    ReorderDayRequest,
    ReorderDayResponse,
    SwapSuggestionsRequest,
    SwapSuggestionsResponse,
)
from app.schemas.itinerary import ItineraryGenerateRequest, ItineraryGenerateResponse
from app.schemas.recompute import RecomputeTravelRequest, RecomputeTravelResponse
from app.schemas.replan import ReplanRequest, ReplanResponse
from app.services.budget_summary import BudgetTrackerResponse, build_budget_tracker
from app.services.claude_service import ClaudeApiError
from app.services.edit_day import (
    apply_swap_and_recompute,
    optimize_and_recompute,
    reorder_and_recompute,
    suggest_swaps,
)
from app.services.itinerary_builder import generate_itinerary
from app.services.places_service import PlacesApiError
from app.services.rain_alternatives import RainAdviceResponse, build_rain_advice
from app.services.recompute_travel import recompute_travel_times
from app.services.replan_builder import replan_itinerary
from app.services.routes_service import RoutesApiError

router = APIRouter(prefix="/itinerary", tags=["itinerary"])


@router.post("/generate", response_model=ItineraryGenerateResponse)
async def post_generate_itinerary(
    body: ItineraryGenerateRequest,
    settings: Settings = Depends(get_settings),
    _user: AuthUser = Depends(require_user),
) -> ItineraryGenerateResponse:
    """Places 후보 수집 → Claude 선택 → place_id 검증 → (선택) Routes 이동시간. 로그인 필수."""
    try:
        return await generate_itinerary(settings, body)
    except ClaudeApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc
    except PlacesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc
    except RoutesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/replan", response_model=ReplanResponse)
async def post_replan_itinerary(
    body: ReplanRequest,
    settings: Settings = Depends(get_settings),
    _user: AuthUser = Depends(require_user),
) -> ReplanResponse:
    """자연어 → intent → Places 재검색 → 재배치 → 검증 → Routes 재계산. 로그인 필수."""
    try:
        return await replan_itinerary(settings, body)
    except ClaudeApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc
    except PlacesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc
    except RoutesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/recompute-travel", response_model=RecomputeTravelResponse)
async def post_recompute_travel(
    body: RecomputeTravelRequest,
    settings: Settings = Depends(get_settings),
) -> RecomputeTravelResponse:
    """장소는 유지하고 WALK/TRANSIT 등 이동수단만 Routes로 다시 계산."""
    mode = (body.travel_mode or "AUTO").upper()
    if mode not in {"AUTO", "WALK", "TRANSIT", "DRIVE", "BICYCLE"}:
        raise HTTPException(status_code=400, detail="지원하지 않는 travel_mode입니다.")
    try:
        days = await recompute_travel_times(
            settings,
            days=body.current_itinerary,
            travel_mode=mode,
            language_code=body.language_code,
            arrival_airport_query=body.arrival_airport_query,
            return_departure_jst=body.return_departure_jst,
        )
        label = {
            "WALK": "도보",
            "TRANSIT": "대중교통",
            "DRIVE": "자동차",
            "AUTO": "자동",
        }.get(mode, mode)
        return RecomputeTravelResponse(
            days=days,
            travel_mode=mode,
            message=f"{label} 기준으로 이동 경로를 다시 계산했습니다.",
        )
    except RoutesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"경로 재계산 실패: {exc}") from exc


@router.post("/reorder-day", response_model=ReorderDayResponse)
async def post_reorder_day(
    body: ReorderDayRequest,
    settings: Settings = Depends(get_settings),
) -> ReorderDayResponse:
    """당일 장소 순서만 바꾸고 Routes 재계산."""
    try:
        days = await reorder_and_recompute(
            settings,
            days=body.current_itinerary,
            day_date=body.day_date,
            ordered_place_ids=body.ordered_place_ids,
            travel_mode=body.travel_mode,
            language_code=body.language_code,
            arrival_airport_query=body.arrival_airport_query,
            return_departure_jst=body.return_departure_jst,
        )
        return ReorderDayResponse(days=days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RoutesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc
    except PlacesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc


@router.post("/optimize-day", response_model=OptimizeDayResponse)
async def post_optimize_day(
    body: OptimizeDayRequest,
    settings: Settings = Depends(get_settings),
) -> OptimizeDayResponse:
    """당일 장소 집합 고정 · haversine 동선 최적화 후 Routes 재계산."""
    try:
        days = await optimize_and_recompute(
            settings,
            days=body.current_itinerary,
            day_date=body.day_date,
            travel_mode=body.travel_mode,
            language_code=body.language_code,
            arrival_airport_query=body.arrival_airport_query,
            return_departure_jst=body.return_departure_jst,
        )
        return OptimizeDayResponse(days=days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RoutesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc
    except PlacesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc


@router.post("/swap-suggestions", response_model=SwapSuggestionsResponse)
async def post_swap_suggestions(
    body: SwapSuggestionsRequest,
    settings: Settings = Depends(get_settings),
) -> SwapSuggestionsResponse:
    """선택 장소와 같은 종류·근처 Places 후보(최대 3)."""
    try:
        pid, cat, suggestions, message = await suggest_swaps(
            settings,
            days=body.current_itinerary,
            day_date=body.day_date,
            place_id=body.place_id,
            language_code=body.language_code,
            max_suggestions=body.max_suggestions,
        )
        return SwapSuggestionsResponse(
            place_id=pid,
            category=cat,
            suggestions=suggestions,
            message=message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PlacesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc


@router.post("/apply-swap", response_model=ApplySwapResponse)
async def post_apply_swap(
    body: ApplySwapRequest,
    settings: Settings = Depends(get_settings),
) -> ApplySwapResponse:
    """장소를 교체하고 Routes 재계산."""
    try:
        days = await apply_swap_and_recompute(
            settings,
            days=body.current_itinerary,
            day_date=body.day_date,
            old_place_id=body.old_place_id,
            new_place=body.new_place,
            travel_mode=body.travel_mode,
            language_code=body.language_code,
            arrival_airport_query=body.arrival_airport_query,
            return_departure_jst=body.return_departure_jst,
        )
        return ApplySwapResponse(days=days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RoutesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc
    except PlacesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc


@router.post("/budget-tracker", response_model=BudgetTrackerResponse)
async def post_budget_tracker(body: BudgetTrackerRequest) -> BudgetTrackerResponse:
    """일정 가격대·티어 정렬 요약 (Exact 원화 추정 없음)."""
    return build_budget_tracker(
        body.current_itinerary,
        travelers=body.travelers,
        budget_krw_per_person=body.budget_krw_per_person,
        budget_krw_total=body.budget_krw_total,
        budget_tier=body.budget_tier,
    )


@router.post("/rain-advice", response_model=RainAdviceResponse)
async def post_rain_advice(
    body: RainAdviceRequest,
    settings: Settings = Depends(get_settings),
) -> RainAdviceResponse:
    """강수 높은 날의 야외→실내 Places 대안."""
    try:
        return await build_rain_advice(
            settings,
            days=body.current_itinerary,
            start_date=body.start_date,
            end_date=body.end_date,
            language_code=body.language_code,
            precip_threshold=body.precip_threshold,
        )
    except PlacesApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"우천 대안 조회 실패: {exc}") from exc
