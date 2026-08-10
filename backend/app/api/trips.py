from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.schemas.trip import TripRecord, TripSaveRequest, TripSummary, TripUpdateRequest
from app.services.auth_user import AuthUser, optional_user
from app.services import trip_store
from app.services.supabase_rest import SupabaseRestError

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("", response_model=list[TripSummary])
async def list_trips(
    settings: Settings = Depends(get_settings),
    user: AuthUser | None = Depends(optional_user),
) -> list[TripSummary]:
    """로그인한 경우 내 일정. Supabase 모드 비로그인이면 빈 목록."""
    try:
        rows = await trip_store.alist_recent_trips(
            settings,
            owner_id=user.id if user else None,
        )
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [TripSummary.model_validate(t) for t in rows]


@router.post("", response_model=TripRecord)
async def create_trip(
    body: TripSaveRequest,
    settings: Settings = Depends(get_settings),
    user: AuthUser | None = Depends(optional_user),
) -> TripRecord:
    """일정 저장. 로그인 시 owner_id 귀속. 비로그인도 공개 링크 저장 가능."""
    if not body.itinerary:
        raise HTTPException(status_code=400, detail="빈 일정은 저장할 수 없습니다.")
    try:
        record = await trip_store.asave_trip(
            settings,
            {
                "title": body.title,
                "itinerary": [d.model_dump(mode="json") for d in body.itinerary],
                "meta": body.meta,
            },
            owner_id=user.id if user else None,
        )
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return TripRecord.model_validate(record)


@router.patch("/{trip_id}", response_model=TripRecord)
async def patch_trip(
    trip_id: str,
    body: TripUpdateRequest,
    settings: Settings = Depends(get_settings),
    user: AuthUser | None = Depends(optional_user),
) -> TripRecord:
    if body.title is None and body.itinerary is None and body.meta is None:
        raise HTTPException(status_code=400, detail="변경할 내용이 없습니다.")
    itinerary = (
        [d.model_dump(mode="json") for d in body.itinerary]
        if body.itinerary is not None
        else None
    )
    try:
        record = await trip_store.aupdate_trip(
            settings,
            trip_id,
            title=body.title,
            itinerary=itinerary,
            meta=body.meta,
            owner_id=user.id if user else None,
        )
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if record is None:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없거나 수정 권한이 없습니다.")
    return TripRecord.model_validate(record)


@router.delete("/{trip_id}")
async def remove_trip(
    trip_id: str,
    settings: Settings = Depends(get_settings),
    user: AuthUser | None = Depends(optional_user),
) -> dict[str, bool]:
    try:
        ok = await trip_store.adelete_trip(
            settings,
            trip_id,
            owner_id=user.id if user else None,
        )
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없거나 삭제 권한이 없습니다.")
    return {"ok": True}


@router.get("/{trip_id}", response_model=TripRecord)
async def get_trip(
    trip_id: str,
    settings: Settings = Depends(get_settings),
    user: AuthUser | None = Depends(optional_user),
) -> TripRecord:
    """공개 일정 또는 본인 소유 일정."""
    try:
        record = await trip_store.aload_trip(settings, trip_id)
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if record is None:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없거나 만료되었습니다.")
    if record.get("is_public") is False:
        if not user or user.id != record.get("owner_id"):
            raise HTTPException(status_code=404, detail="일정을 찾을 수 없거나 만료되었습니다.")
    return TripRecord.model_validate(record)
