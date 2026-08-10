from fastapi import APIRouter, HTTPException

from app.api.schemas import (
    LodgingResponse,
    PlaceResponse,
    TripPlanRequest,
    TripPlanResponse,
)
from app.config import Settings
from app.lodging.search import LodgingSearch
from app.models import TripRequest
from app.places.search import PlaceSearch
from app.services.ai_client import AiClient
from app.services.planner import TripPlanner

router = APIRouter(prefix="/api/trips", tags=["trips"])


@router.post("/plan", response_model=TripPlanResponse)
def create_trip_plan(payload: TripPlanRequest) -> TripPlanResponse:
    if payload.end_date <= payload.start_date:
        raise HTTPException(status_code=400, detail="종료일은 시작일보다 뒤여야 합니다.")

    settings = Settings.from_env()
    request = TripRequest(
        destination=payload.destination,
        start_date=payload.start_date,
        end_date=payload.end_date,
        people=payload.people,
        budget=payload.budget,
    )

    lodgings = LodgingSearch.default(settings).search(request)
    attractions = PlaceSearch.default(settings).attractions(request)
    plan = TripPlanner(AiClient(settings)).create_plan(request, lodgings, attractions)

    return TripPlanResponse(
        destination=request.destination,
        nights=request.nights,
        plan=plan.content,
        lodgings=[LodgingResponse.from_model(item) for item in lodgings],
        attractions=[PlaceResponse.from_model(item) for item in attractions],
    )
