"""Claude API — 일정 선택/배치·intent 파싱만. 장소 생성 금지.

Docs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
"""

from __future__ import annotations

import json
from typing import Any

from anthropic import Anthropic, APIError

from app.config import Settings
from app.schemas.itinerary import (
    ITINERARY_JSON_SCHEMA,
    CandidatePlaceBrief,
    LlmItineraryResponse,
)
from app.schemas.replan import INTENT_JSON_SCHEMA, TravelIntent

DEFAULT_MODEL = "claude-sonnet-4-5"

SYSTEM_PROMPT = """당신은 일본 여행 일정을 구성하는 어시스턴트입니다.

당신에게는 후보 장소 리스트(JSON)가 주어집니다. 이 리스트는 Google Places API에서
실제로 검색된 장소들이며, 각 항목은 place_id, name, category, rating, lat, lng, region,
price_level(1~4 또는 null)을 포함합니다.
category가 lodging인 항목은 숙소입니다.
price_level은 Google Places 가격대이며 Exact 원화 요금이 아닙니다.

규칙:
1. 반드시 주어진 후보 리스트 안에 있는 place_id만 사용하세요. 리스트에 없는
   장소를 새로 만들거나 이름만 바꿔 쓰는 것은 절대 금지입니다.
2. day_regions에 지정된 날짜별 지역을 지키세요. 해당 날짜에는 그 지역(region)과
   맞는 후보를 우선 배정하세요. (예: 1일 오사카, 2일 교토)
3. 하루 관광지·식사·카페를 조합하되, include_lodging이 true이면
   evening 슬롯에 lodging 후보를 1곳 배정하세요.
   단, dates 배열의 마지막 날짜(귀국일)에는 숙소를 절대 넣지 마세요.
4. 숙소·식사(restaurant) 선택 기준(후보 안에서만):
   - preferred_price_levels에 해당하는 price_level을 가능하면 우선
   - price_level이 null인 후보는 제외하지 말고 차선으로 사용
   - 그날 관광지들과 위경도가 가까운 것(동선 한가운데·사이) 우선
   - rating이 높고 user_rating이 충분한 것 우선
   - 예약 링크·Exact 요금을 만들지 마세요. 추천 이유만 reason에 적으세요.
5. 같은 날 장소들은 위경도 기준으로 가까운 것끼리 묶으세요.
   정확한 이동시간은 계산하지 마세요.
6. must_have_food / must_have_sights가 있으면 여행 전체에서 각각 관련 후보를
   최소 1개 이상 포함하세요.
   must_have_food(및 must_food_queries가 있는 restaurant) 배치 규칙:
   - 그날의 첫 장소(order=1)나 morning에 고정하지 마세요.
   - time_slot은 lunch 또는 dinner만 사용하세요.
   - 먼저 관광지(attraction 등)를 배치한 뒤, 그 동선 근처 식사로 끼워 넣으세요.
   - 첫날 아침부터 식사만 시작하는 일정은 금지입니다(비행 제약으로 lunch가
     첫 허용 슬롯인 경우는 lunch 식사를 허용하되, 가능하면 관광 뒤에 두세요).
7. 비행 시간표(flight_windows)를 지키세요.
   - arrival_time_jst_estimated는 출국 출발+표준 비행시간으로 서버가 추정한 값입니다.
     Exact 항공편이 아니므로 분을 더 지어내지 말고, first_day_earliest_slot만 따르세요.
   - 첫날(dates[0]): first_day_earliest_slot 이전 time_slot 금지.
   - 마지막날(dates[-1]): last_day_latest_slot 이후 time_slot 금지. 숙소 금지.
8. 출력은 지정된 JSON 스키마만 따르세요. 스키마 외 텍스트는 포함하지 마세요.
"""

INTENT_SYSTEM_PROMPT = """당신은 여행자의 자연어 요청을 구조화된 intent로 변환하는 파서입니다.
장소를 직접 추천하지 마세요. 오직 요청을 분류하고 구조화하는 역할만 합니다.
모호하거나 여행 일정과 무관하면 intent_type을 unclear로 반환하세요.
"""

REPLAN_SYSTEM_PROMPT = """당신은 기존 일본 여행 일정을 재조정하는 어시스턴트입니다.

입력으로 현재 일정과 후보 장소 리스트가 주어집니다.
후보 리스트의 place_id만 사용할 수 있습니다. 새 장소를 만들어내지 마세요.
이동 시간은 계산하지 마세요. 위경도로 대략 가까운 위치에 배치하세요.
음식을 추가할 때는 lunch/dinner에 두고, 기존 관광 동선 근처 후보를 고르세요.
그날의 맨 앞(order=1)·morning에 식당을 꽂지 마세요.
출력은 지정된 JSON 스키마(days/items)만 따르세요.
"""


class ClaudeApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ClaudeService:
    def __init__(self, settings: Settings) -> None:
        if not settings.anthropic_api_key:
            raise ClaudeApiError("ANTHROPIC_API_KEY가 없습니다.")
        self._client = Anthropic(api_key=settings.anthropic_api_key)
        self._model = DEFAULT_MODEL

    def _parse_json_message(self, message: Any) -> dict[str, Any]:
        text_parts = [b.text for b in message.content if getattr(b, "type", None) == "text"]
        if not text_parts:
            raise ClaudeApiError("Claude 응답에 텍스트가 없습니다.")
        try:
            return json.loads(text_parts[0])
        except json.JSONDecodeError as exc:
            raise ClaudeApiError("Claude 응답 JSON 파싱 실패") from exc

    def _create_structured(
        self,
        *,
        system: str,
        user_payload: dict[str, Any],
        schema: dict[str, Any],
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[
                    {
                        "role": "user",
                        "content": json.dumps(user_payload, ensure_ascii=False),
                    }
                ],
                output_config={
                    "format": {
                        "type": "json_schema",
                        "schema": schema,
                    }
                },
            )
        except APIError as exc:
            raise ClaudeApiError(
                f"Claude API 오류: {exc}",
                status_code=getattr(exc, "status_code", 502),
            ) from exc
        return self._parse_json_message(message)

    def generate_itinerary(
        self,
        *,
        candidates: list[CandidatePlaceBrief],
        dates: list[str],
        day_regions: list[dict[str, Any]],
        must_have_food: list[str],
        must_have_sights: list[str],
        include_lodging: bool = True,
        budget_tier: str = "standard",
        preferred_price_levels: list[int] | None = None,
        flight_windows: dict[str, Any] | None = None,
    ) -> LlmItineraryResponse:
        if not candidates:
            raise ClaudeApiError("후보 장소가 비어 있어 일정을 생성할 수 없습니다.", status_code=400)

        levels = preferred_price_levels or [2, 3]
        fw = flight_windows or {}
        data = self._create_structured(
            system=SYSTEM_PROMPT,
            user_payload={
                "dates": dates,
                "day_regions": day_regions,
                "must_have_food": must_have_food,
                "must_have_sights": must_have_sights,
                "include_lodging": include_lodging,
                "budget_tier": budget_tier,
                "preferred_price_levels": levels,
                "flight_windows": fw,
                "candidates": [c.model_dump() for c in candidates],
                "instruction": (
                    "candidates의 place_id만 사용하고, day_regions의 날짜별 지역에 맞게 배정하세요. "
                    "flight_windows의 첫날 earliest_slot / 마지막날 latest_slot을 지키세요. "
                    "must_have_food는 must_food_queries가 있는 restaurant 중 별점·동선 근접으로 고르고 "
                    "lunch/dinner에만 배정하세요. 첫 일정·morning에 식당을 두지 마세요. "
                    "include_lodging이 true이면 lodging 후보 중 별점·위치·preferred_price_levels 기준으로 "
                    "숙소를 고르세요. restaurant도 가능하면 preferred_price_levels를 우선하세요. "
                    "price_level이 null이면 차선으로 사용하세요. "
                    "단 마지막 날짜(귀국일)에는 숙소를 넣지 마세요. Exact 요금을 지어내지 마세요."
                ),
            },
            schema=ITINERARY_JSON_SCHEMA,
        )
        try:
            return LlmItineraryResponse.model_validate(data)
        except Exception as exc:
            raise ClaudeApiError(f"Claude 응답 스키마 불일치: {exc}") from exc

    def parse_intent(self, *, prompt: str, available_dates: list[str]) -> TravelIntent:
        data = self._create_structured(
            system=INTENT_SYSTEM_PROMPT,
            user_payload={
                "raw_text": prompt,
                "available_dates": available_dates,
                "instruction": "자연어를 intent JSON으로만 변환하세요. 장소 추천 금지.",
            },
            schema=INTENT_JSON_SCHEMA,
            max_tokens=512,
        )
        try:
            return TravelIntent.model_validate(data)
        except Exception as exc:
            raise ClaudeApiError(f"Intent 스키마 불일치: {exc}") from exc

    def replan_itinerary(
        self,
        *,
        current_days: list[dict[str, Any]],
        candidates: list[CandidatePlaceBrief],
        intent: TravelIntent,
        dates: list[str],
        region: str,
    ) -> LlmItineraryResponse:
        if not candidates:
            raise ClaudeApiError("재배치할 후보가 없습니다.", status_code=400)
        data = self._create_structured(
            system=REPLAN_SYSTEM_PROMPT,
            user_payload={
                "region": region,
                "dates": dates,
                "intent": intent.model_dump(),
                "current_itinerary": current_days,
                "candidates": [c.model_dump() for c in candidates],
                "instruction": (
                    "intent에 맞게 current_itinerary를 수정한 전체 일정을 반환하세요. "
                    "candidates의 place_id만 사용하세요. "
                    "add_food면 lunch/dinner·기존 장소 위경도 근처에 삽입하고 맨 앞·morning 금지."
                ),
            },
            schema=ITINERARY_JSON_SCHEMA,
        )
        try:
            return LlmItineraryResponse.model_validate(data)
        except Exception as exc:
            raise ClaudeApiError(f"리플랜 응답 스키마 불일치: {exc}") from exc
