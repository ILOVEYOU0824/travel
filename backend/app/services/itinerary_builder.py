"""일정 생성 파이프라인: Places 수집 → LLM 선택 → 검증 → Place 수화 → (선택) Routes."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import timedelta

from app.config import Settings
from app.schemas.itinerary import (
    DayRegion,
    ItineraryGenerateRequest,
    ItineraryGenerateResponse,
)
from app.schemas.place import Place, PlaceSearchRequest
from app.services import mock_claude
from app.services.arrange_meal_placement import arrange_meal_placement
from app.services.budget_tier import BudgetPlan, resolve_budget_plan
from app.services.candidate_brief import place_to_brief
from app.services.claude_service import ClaudeApiError, ClaudeService
from app.services.flight_windows import resolve_flight_windows
from app.services.food_proximity import prune_food_candidates, swap_distant_meals
from app.services.hydrate_itinerary import hydrate_itinerary
from app.services.kkday_links import kkday_esim_cta
from app.schemas.query_hint import SearchHint
from app.services.place_search import search_places
from app.services.query_resolve import resolve_must_have_query
from app.services.region_bias import resolve_region_center
from app.services.strip_last_day_lodging import strip_lodging_on_last_day
from app.services.validate_itinerary import validate_itinerary_response

_PLACES_CONCURRENCY = 6
_REGION_SEARCH_RADIUS_M = 35000.0


def _date_range(start, end) -> list[str]:
    days = []
    cur = start
    while cur <= end:
        days.append(cur.isoformat())
        cur += timedelta(days=1)
    return days


def resolve_day_regions(request: ItineraryGenerateRequest, dates: list[str]) -> list[DayRegion]:
    """날짜별 지역 맵. day_regions 우선, 없으면 region 폴백."""
    by_date = {d.date: d.region.strip() for d in request.day_regions if d.region.strip()}
    fallback = (request.region or "").strip()
    resolved: list[DayRegion] = []
    for d in dates:
        region = by_date.get(d) or fallback
        if not region:
            raise ClaudeApiError(f"{d}의 지역이 비어 있습니다.", status_code=400)
        resolved.append(DayRegion(date=d, region=region))
    return resolved


def merge_must_haves(request: ItineraryGenerateRequest) -> tuple[list[str], list[str], list[str]]:
    food = [q.strip() for q in request.must_have_food if q.strip()]
    sights = [q.strip() for q in request.must_have_sights if q.strip()]
    legacy = [q.strip() for q in request.must_have_queries if q.strip()]
    all_queries = list(dict.fromkeys([*food, *sights, *legacy]))
    return food, sights, all_queries


def _region_scoped_query(region: str, keyword: str) -> str:
    """메인 화면 지역으로 검색어를 한정. Japan 힌트로 한국 동명 체인 억제."""
    r = region.strip()
    k = keyword.strip()
    if not k:
        return f"{r} Japan".strip()
    if r and r in k:
        if "japan" not in k.lower() and "일본" not in k:
            return f"{k} Japan"
        return k
    base = f"{r} {k}".strip()
    if "japan" not in base.lower() and "일본" not in base:
        return f"{base} Japan"
    return base


def _merge_place(
    by_id: dict[str, Place],
    region_tag: dict[str, str],
    food_tags: dict[str, list[str]],
    p: Place,
    region: str,
    food_query: str | None,
) -> None:
    if not p.place_id:
        return
    if p.place_id not in by_id:
        by_id[p.place_id] = p
        region_tag[p.place_id] = region
    if food_query:
        tags = food_tags.setdefault(p.place_id, [])
        if food_query not in tags:
            tags.append(food_query)


async def _search_into(
    settings: Settings,
    by_id: dict[str, Place],
    region_tag: dict[str, str],
    food_tags: dict[str, list[str]],
    *,
    query: str,
    region: str,
    language_code: str,
    max_results: int,
    food_query: str | None = None,
    bias_lat: float | None = None,
    bias_lng: float | None = None,
    included_type: str | None = None,
    min_rating: float | None = None,
    lock: asyncio.Lock | None = None,
) -> None:
    result = await search_places(
        settings,
        PlaceSearchRequest(
            query=query,
            language_code=language_code,
            max_results=max_results,
            region_code="JP",
            bias_lat=bias_lat,
            bias_lng=bias_lng,
            bias_radius_meters=_REGION_SEARCH_RADIUS_M,
            strict_location=bias_lat is not None and bias_lng is not None,
            included_type=included_type,
            min_rating=min_rating,
        ),
    )

    def _apply() -> None:
        for p in result.places:
            _merge_place(by_id, region_tag, food_tags, p, region, food_query)

    if lock:
        async with lock:
            _apply()
    else:
        _apply()


def _lodging_queries(region: str, budget: BudgetPlan) -> list[str]:
    terms = list(dict.fromkeys([*budget.lodging_search_terms, "숙소"]))
    return [_region_scoped_query(region, t) for t in terms]


async def _collect_candidates(
    settings: Settings,
    request: ItineraryGenerateRequest,
    day_regions: list[DayRegion],
    food: list[str],
    sights: list[str],
    legacy: list[str],
    budget: BudgetPlan,
) -> tuple[dict[str, Place], dict[str, str], dict[str, list[str]], list[SearchHint]]:
    """지역별 Places 검색(병렬) + 필수어는 Autocomplete 폴백. LLM 미개입."""
    by_id: dict[str, Place] = {}
    region_tag: dict[str, str] = {}
    food_tags: dict[str, list[str]] = {}
    hints: list[SearchHint] = []
    unique_regions = list(dict.fromkeys(d.region for d in day_regions))
    lock = asyncio.Lock()
    sem = asyncio.Semaphore(_PLACES_CONCURRENCY)

    async def _run(**kwargs: object) -> None:
        async with sem:
            await _search_into(
                settings,
                by_id,
                region_tag,
                food_tags,
                lock=lock,
                **kwargs,  # type: ignore[arg-type]
            )

    async def _resolve_must(
        *,
        keyword: str,
        region: str,
        kind: str,
        food_query: str | None,
        bias_lat: float | None,
        bias_lng: float | None,
    ) -> None:
        async with sem:
            places, hint = await resolve_must_have_query(
                settings,
                keyword=keyword,
                region=region,
                kind=kind,
                language_code=request.language_code,
                max_results=request.max_candidates_per_query,
                bias_lat=bias_lat,
                bias_lng=bias_lng,
            )
            async with lock:
                if hint.status != "matched":
                    hints.append(hint)
                for p in places:
                    _merge_place(by_id, region_tag, food_tags, p, region, food_query)

    tasks: list[asyncio.Task[None]] = []
    for region in unique_regions:
        center = resolve_region_center(region)
        bias_lat = center[0] if center else None
        bias_lng = center[1] if center else None

        base_queries = [
            _region_scoped_query(region, "관광지"),
            _region_scoped_query(region, "맛집"),
            _region_scoped_query(region, "카페"),
        ]
        if request.include_lodging:
            base_queries.extend(_lodging_queries(region, budget))

        for q in base_queries:
            tasks.append(
                asyncio.create_task(
                    _run(
                        query=q,
                        region=region,
                        language_code=request.language_code,
                        max_results=request.max_candidates_per_query,
                        bias_lat=bias_lat,
                        bias_lng=bias_lng,
                    )
                )
            )
        if request.include_lodging:
            tasks.append(
                asyncio.create_task(
                    _run(
                        query=_region_scoped_query(region, "lodging hotel"),
                        region=region,
                        language_code=request.language_code,
                        max_results=request.max_candidates_per_query,
                        bias_lat=bias_lat,
                        bias_lng=bias_lng,
                        included_type="lodging",
                        min_rating=3.5,
                    )
                )
            )
        for fq in food:
            tasks.append(
                asyncio.create_task(
                    _resolve_must(
                        keyword=fq,
                        region=region,
                        kind="food",
                        food_query=fq,
                        bias_lat=bias_lat,
                        bias_lng=bias_lng,
                    )
                )
            )
        for sq in sights:
            tasks.append(
                asyncio.create_task(
                    _resolve_must(
                        keyword=sq,
                        region=region,
                        kind="sight",
                        food_query=None,
                        bias_lat=bias_lat,
                        bias_lng=bias_lng,
                    )
                )
            )
        for lq in legacy:
            tasks.append(
                asyncio.create_task(
                    _resolve_must(
                        keyword=lq,
                        region=region,
                        kind="query",
                        food_query=None,
                        bias_lat=bias_lat,
                        bias_lng=bias_lng,
                    )
                )
            )

    if tasks:
        await asyncio.gather(*tasks)
    return by_id, region_tag, food_tags, hints


async def generate_itinerary(
    settings: Settings,
    request: ItineraryGenerateRequest,
) -> ItineraryGenerateResponse:
    if request.end_date < request.start_date:
        raise ClaudeApiError("end_date가 start_date보다 앞입니다.", status_code=400)

    dates = _date_range(request.start_date, request.end_date)
    day_regions = resolve_day_regions(request, dates)
    food, sights, _all_must = merge_must_haves(request)
    legacy = [q.strip() for q in request.must_have_queries if q.strip()]
    budget = resolve_budget_plan(
        travelers=request.travelers,
        day_count=len(dates),
        budget_krw_per_person=request.budget_krw_per_person,
        budget_krw_total=request.budget_krw_total,
    )
    flights = resolve_flight_windows(
        outbound_departure_kst=request.outbound_departure_kst,
        return_departure_jst=request.return_departure_jst or request.departure_time_jst,
        first_region=day_regions[0].region if day_regions else None,
        arrival_time_jst=request.arrival_time_jst,
    )
    places_by_id, region_tag, food_tags, search_hints = await _collect_candidates(
        settings, request, day_regions, food, sights, legacy, budget
    )
    candidates = [
        place_to_brief(
            p,
            region_tag.get(p.place_id),
            must_food_queries=food_tags.get(p.place_id),
        )
        for p in places_by_id.values()
    ]
    if food:
        candidates = prune_food_candidates(candidates)
    day_region_payload = [d.model_dump() for d in day_regions]

    if settings.use_mock_llm:
        llm_raw = await mock_claude.MOCK_generate_itinerary(
            candidates=candidates,
            dates=dates,
            day_regions=day_region_payload,
            must_have_food=food,
            must_have_sights=sights,
            include_lodging=request.include_lodging,
            preferred_price_levels=list(budget.preferred_price_levels),
            flight_windows=flights,
        )
        llm_source = "MOCK_claude"
    else:
        service = ClaudeService(settings)
        llm_raw = service.generate_itinerary(
            candidates=candidates,
            dates=dates,
            day_regions=day_region_payload,
            must_have_food=food,
            must_have_sights=sights,
            include_lodging=request.include_lodging,
            budget_tier=budget.tier,
            preferred_price_levels=list(budget.preferred_price_levels),
            flight_windows=asdict(flights),
        )
        llm_source = "claude"

    validation = validate_itinerary_response(
        llm_raw,
        set(places_by_id.keys()),
        expected_dates=set(dates),
    )
    if not validation.ok:
        raise ClaudeApiError(
            "일정 검증 실패: " + "; ".join(validation.errors),
            status_code=422,
        )

    cleaned = strip_lodging_on_last_day(validation.cleaned, places_by_id, dates)
    cleaned = swap_distant_meals(
        cleaned,
        places_by_id,
        food_place_ids=set(food_tags.keys()),
        must_have_food=food,
    )
    cleaned = arrange_meal_placement(
        cleaned,
        places_by_id,
        must_have_food=food,
        food_place_ids=food_tags.keys(),
        dates=dates,
        flight_windows=flights,
    )

    day_views = await hydrate_itinerary(
        settings,
        cleaned,
        places_by_id,
        include_travel_times=request.include_travel_times,
        travel_mode=request.travel_mode,
        language_code=request.language_code,
        day_regions={d.date: d.region for d in day_regions},
        arrival_airport_query=request.arrival_airport_query,
        return_departure_jst=flights.return_departure_jst,
    )

    prep = []
    esim = kkday_esim_cta(
        settings, region=day_regions[0].region if day_regions else None
    )
    if esim:
        prep.append(esim)

    return ItineraryGenerateResponse(
        days=day_views,
        candidates_count=len(places_by_id),
        llm_source=llm_source,
        validation={
            "removed_place_ids": validation.removed_place_ids,
            "removed_items_count": validation.removed_items_count,
            "errors": validation.errors,
        },
        budget_tier=budget.tier,
        budget_krw_per_person=budget.budget_krw_per_person,
        budget_per_person_per_day_krw=budget.per_person_per_day_krw,
        budget_note=budget.note,
        travelers=budget.travelers,
        budget_krw_total=budget.budget_krw_total,
        arrival_time_jst=flights.arrival_time_jst,
        departure_time_jst=flights.return_departure_jst,
        outbound_departure_kst=flights.outbound_departure_kst,
        return_departure_jst=flights.return_departure_jst,
        flight_note=f"{flights.first_day_note} / {flights.last_day_note}",
        estimated_flight_minutes=flights.estimated_flight_minutes,
        prep_ctas=prep,
        search_hints=search_hints,
    )
