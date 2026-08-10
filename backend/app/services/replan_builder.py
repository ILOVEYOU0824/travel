"""자연어 리플랜: intent → Places 검색 → LLM 재배치 → 검증 → Routes."""

from __future__ import annotations

from typing import Any

from app.config import Settings
from app.schemas.place import Place
from app.schemas.replan import IntentType, ReplanRequest, ReplanResponse, TravelIntent
from app.services import mock_claude
from app.services.arrange_meal_placement import arrange_meal_placement
from app.services.candidate_brief import place_to_brief
from app.services.claude_service import ClaudeApiError, ClaudeService
from app.services.food_proximity import swap_distant_meals
from app.services.hydrate_itinerary import hydrate_itinerary
from app.services.kkday_links import kkday_esim_cta
from app.services.query_resolve import resolve_must_have_query
from app.services.region_bias import centroid_of_places, resolve_region_center
from app.services.strip_last_day_lodging import strip_lodging_on_last_day
from app.services.validate_itinerary import validate_itinerary_response


def _current_as_llm_dicts(request: ReplanRequest) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for day in request.current_itinerary:
        out.append(
            {
                "date": day.date,
                "items": [
                    {
                        "place_id": it.place.place_id,
                        "order": it.order,
                        "time_slot": it.time_slot.value,
                        "ai_description": it.ai_description,
                        "place": {
                            "place_id": it.place.place_id,
                            "name": it.place.name,
                            "category": it.place.category.value,
                            "lat": it.place.location.lat,
                            "lng": it.place.location.lng,
                        },
                    }
                    for it in day.items
                ],
            }
        )
    return out


def _places_from_current(request: ReplanRequest) -> dict[str, Place]:
    by_id: dict[str, Place] = {}
    for day in request.current_itinerary:
        for it in day.items:
            by_id[it.place.place_id] = it.place
    return by_id


async def replan_itinerary(settings: Settings, request: ReplanRequest) -> ReplanResponse:
    if not request.current_itinerary:
        raise ClaudeApiError("현재 일정이 비어 있습니다.", status_code=400)

    dates = [d.date for d in request.current_itinerary]
    places_by_id = _places_from_current(request)

    if settings.use_mock_llm:
        intent = await mock_claude.MOCK_parse_intent(
            prompt=request.prompt,
            available_dates=dates,
        )
        llm_source = "MOCK_claude"
    else:
        service = ClaudeService(settings)
        intent = service.parse_intent(prompt=request.prompt, available_dates=dates)
        llm_source = "claude"

    if intent.intent_type == IntentType.unclear:
        return ReplanResponse(
            days=request.current_itinerary,
            candidates_count=len(places_by_id),
            llm_source=llm_source,
            validation={"removed_place_ids": [], "removed_items_count": 0, "errors": []},
            intent=intent,
            message=(
                "요청을 일정 수정으로 해석하지 못했어요. "
                "아래처럼 구체적으로 적어 주세요.\n"
                "· 음식 추가: 「라멘 추가해줘」 「오코노미야키 먹고 싶어」\n"
                "· 장소 삭제: 「쓰텐카쿠는 빼줘」 「이 카페 삭제」\n"
                "· 순서: 「오전 일정이랑 오후 바꿔줘」"
            ),
            unchanged=True,
        )

    # add_* 는 Places(+Autocomplete)로 새 후보 검색. 없으면 임의 생성 금지.
    new_food_ids: set[str] = set()
    search_hints = []
    if intent.intent_type in (IntentType.add_food, IntentType.add_sight):
        query = (intent.category_query or request.prompt or "").strip()
        target_day = intent.target_day or dates[0]
        day_region = next(
            (d.region for d in request.current_itinerary if d.date == target_day and d.region),
            None,
        )
        search_region = day_region or request.region
        day_places = next(
            (d for d in request.current_itinerary if d.date == target_day),
            None,
        )
        coords = [
            (it.place.location.lat, it.place.location.lng)
            for it in (day_places.items if day_places else [])
            if it.place and it.place.location
        ]
        center = centroid_of_places(coords) or resolve_region_center(search_region)
        kind = "food" if intent.intent_type == IntentType.add_food else "sight"
        found_places, hint = await resolve_must_have_query(
            settings,
            keyword=query,
            region=search_region,
            kind=kind,
            language_code=request.language_code,
            max_results=request.max_new_candidates,
            bias_lat=center[0] if center else None,
            bias_lng=center[1] if center else None,
        )
        if hint.status != "matched":
            search_hints.append(hint)
        if not found_places:
            return ReplanResponse(
                days=request.current_itinerary,
                candidates_count=len(places_by_id),
                llm_source=llm_source,
                validation={"removed_place_ids": [], "removed_items_count": 0, "errors": []},
                intent=intent,
                message=hint.message,
                unchanged=True,
                search_hints=search_hints,
            )
        for p in found_places:
            places_by_id[p.place_id] = p
            if intent.intent_type == IntentType.add_food:
                new_food_ids.add(p.place_id)

    candidates = [place_to_brief(p) for p in places_by_id.values()]
    current_days = _current_as_llm_dicts(request)

    if settings.use_mock_llm:
        llm_raw = await mock_claude.MOCK_replan_itinerary(
            current_days=current_days,
            candidates=candidates,
            intent=intent,
            dates=dates,
            region=request.region,
        )
    else:
        service = ClaudeService(settings)
        llm_raw = service.replan_itinerary(
            current_days=current_days,
            candidates=candidates,
            intent=intent,
            dates=dates,
            region=request.region,
        )

    validation = validate_itinerary_response(
        llm_raw,
        set(places_by_id.keys()),
        expected_dates=set(dates),
    )
    if not validation.ok:
        raise ClaudeApiError(
            "리플랜 검증 실패: " + "; ".join(validation.errors),
            status_code=422,
        )

    cleaned = strip_lodging_on_last_day(validation.cleaned, places_by_id, dates)
    if intent.intent_type == IntentType.add_food or new_food_ids:
        food_q = [intent.category_query or request.prompt]
        cleaned = swap_distant_meals(
            cleaned,
            places_by_id,
            food_place_ids=new_food_ids,
            must_have_food=food_q,
        )
        cleaned = arrange_meal_placement(
            cleaned,
            places_by_id,
            must_have_food=food_q,
            food_place_ids=new_food_ids,
            dates=dates,
        )

    arrival_q = None
    return_jst = None
    if request.current_itinerary:
        arr = request.current_itinerary[0].arrival_from_airport
        if arr and arr.airport_query:
            arrival_q = arr.airport_query
        dep = request.current_itinerary[-1].departure_to_airport
        if dep:
            if not arrival_q and dep.airport_query:
                arrival_q = dep.airport_query
            return_jst = dep.return_departure_jst

    day_views = await hydrate_itinerary(
        settings,
        cleaned,
        places_by_id,
        include_travel_times=request.include_travel_times,
        travel_mode=request.travel_mode,
        language_code=request.language_code,
        day_regions={d.date: (d.region or request.region) for d in request.current_itinerary},
        arrival_airport_query=arrival_q,
        return_departure_jst=return_jst,
    )

    prep = []
    esim = kkday_esim_cta(settings, region=request.region)
    if esim:
        prep.append(esim)

    msg = _success_message(intent)
    if search_hints:
        msg = f"{msg} {search_hints[0].message}"

    return ReplanResponse(
        days=day_views,
        candidates_count=len(places_by_id),
        llm_source=llm_source,
        validation={
            "removed_place_ids": validation.removed_place_ids,
            "removed_items_count": validation.removed_items_count,
            "errors": validation.errors,
        },
        intent=intent,
        message=msg,
        unchanged=False,
        prep_ctas=prep,
        search_hints=search_hints,
    )


def _success_message(intent: TravelIntent) -> str:
    if intent.intent_type == IntentType.add_food:
        return "음식 요청을 반영했어요. 동선 근처·점심/저녁 슬롯에 맞춰 넣었습니다."
    if intent.intent_type == IntentType.add_sight:
        return "관광지 요청을 반영했어요. Google Places에서 찾은 장소만 추가했습니다."
    if intent.intent_type == IntentType.remove_item:
        return "요청하신 장소를 일정에서 빼었어요."
    if intent.intent_type == IntentType.change_order:
        return "일정 순서를 바꿨어요. 이동 경로도 다시 계산했습니다."
    return "일정을 반영했습니다."
