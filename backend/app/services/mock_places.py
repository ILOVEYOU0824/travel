"""MOCK_ 개발용 장소 데이터 — 배포 경로(places_service)와 분리.

실제 Google 응답 구조(픽스처)를 흉내 내며, 임의로 "유명한 라멘집"을
지어내지 않는다. 픽스처 파일의 place_id/좌표만 사용한다.
"""

from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path

from app.schemas.place import (
    Place,
    PlaceAutocompleteRequest,
    PlaceAutocompleteSuggestion,
    PlaceSearchRequest,
    place_from_google_payload,
)

_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "places_search_text_osaka.json"
)


def _load_fixture_places() -> list[Place]:
    raw = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    places: list[Place] = []
    for item in raw.get("places") or []:
        places.append(place_from_google_payload(item))
    return places


def _filter_fixture(query: str) -> list[Place]:
    all_places = _load_fixture_places()
    q = query.lower()
    tokens = [t for t in q.replace("japan", "").split() if len(t) >= 2]
    return [
        p
        for p in all_places
        if q in p.name.lower()
        or any(q in t.lower() for t in p.types)
        or (p.formatted_address and q in p.formatted_address.lower())
        or any(token in p.name.lower() or token in " ".join(p.types) for token in tokens)
    ]


async def MOCK_search_text(request: PlaceSearchRequest) -> list[Place]:
    """쿼리 키워드로 픽스처를 단순 필터. Google을 대체하지 않는 개발용."""
    filtered = _filter_fixture(request.query)
    # 일반 탐색(관광지/맛집)은 폴백 허용. 필수어 오타 테스트는 resolve 쪽에서 엄격히 판정.
    result = filtered if filtered else _load_fixture_places()
    return result[: request.max_results]


async def MOCK_search_text_strict(request: PlaceSearchRequest) -> list[Place]:
    """매칭 없으면 빈 목록 — 오타 시 Autocomplete 폴백 유도."""
    return _filter_fixture(request.query)[: request.max_results]


async def MOCK_autocomplete(
    request: PlaceAutocompleteRequest,
) -> list[PlaceAutocompleteSuggestion]:
    """픽스처 이름과 유사도 높은 후보만. 없는 장소 이름은 만들지 않음."""
    q = request.input.strip().lower()
    if len(q) < 2:
        return []
    scored: list[tuple[float, Place]] = []
    for p in _load_fixture_places():
        name = (p.name or "").lower()
        ratio = SequenceMatcher(None, q, name).ratio()
        if q in name:
            ratio = max(ratio, 0.85)
        # 짧은 오타: 공통 글자 비율
        if len(q) >= 3:
            common = sum(1 for ch in set(q) if ch in name) / max(len(set(q)), 1)
            ratio = max(ratio, common * 0.7)
        if ratio >= 0.45:
            scored.append((ratio, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    out: list[PlaceAutocompleteSuggestion] = []
    for _, p in scored[: request.max_suggestions]:
        out.append(
            PlaceAutocompleteSuggestion(
                place_id=p.place_id,
                primary_text=p.name,
                secondary_text=p.formatted_address,
            )
        )
    return out


async def MOCK_get_place(place_id: str) -> Place | None:
    for p in _load_fixture_places():
        if p.place_id == place_id:
            return p
    return None
