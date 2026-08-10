from app.models import Lodging, Place, TripPlan, TripRequest
from app.services.ai_client import AiClient


class TripPlanner:
    def __init__(self, ai_client: AiClient) -> None:
        self.ai_client = ai_client

    def create_plan(
        self,
        request: TripRequest,
        lodgings: list[Lodging],
        attractions: list[Place] | None = None,
    ) -> TripPlan:
        lodging_options = lodgings[: self.ai_client.settings.lodging_limit]
        attraction_options = (attractions or [])[: self.ai_client.settings.places_limit]
        ai_plan = self.ai_client.complete(
            system_prompt=(
                "너는 한국어 여행 플래너다. 답변은 짧고 실용적으로 작성한다. "
                "표현은 간결하게 하고, 숙소/일정/예산/링크만 포함한다."
            ),
            user_prompt=self._build_prompt(request, lodging_options, attraction_options),
        )

        if ai_plan:
            return TripPlan(content=ai_plan)

        return TripPlan(content=self._fallback_plan(request, lodging_options, attraction_options))

    def _build_prompt(
        self,
        request: TripRequest,
        lodgings: list[Lodging],
        attractions: list[Place],
    ) -> str:
        lodging_text = "\n".join(item.compact() for item in lodgings)
        attraction_text = "\n".join(item.compact() for item in attractions)
        return (
            f"여행지:{request.destination}\n"
            f"기간:{request.start_date}~{request.end_date}({request.nights}박)\n"
            f"인원:{request.people}명\n"
            f"총예산:{request.budget}원\n"
            f"숙소후보:\n{lodging_text}\n"
            f"명소후보:\n{attraction_text}\n"
            "요청: 추천 숙소 1개, 날짜별 동선, 예상 비용, 확인 링크를 작성."
        )

    def _fallback_plan(
        self,
        request: TripRequest,
        lodgings: list[Lodging],
        attractions: list[Place],
    ) -> str:
        lodging = lodgings[0] if lodgings else None
        lodging_cost = lodging.price_per_night * request.nights if lodging else 0
        activity_budget = max(request.budget - lodging_cost, 0)
        daily_budget = activity_budget // max(request.nights + 1, 1)

        lodging_line = (
            f"{lodging.name} ({lodging.area}, {lodging.price_per_night:,}원/박)"
            if lodging
            else "숙소 후보 없음"
        )

        place_names = [place.name for place in attractions] or [f"{request.destination} 주요 명소"]
        days = []
        for idx in range(request.nights + 1):
            place = place_names[idx % len(place_names)]
            days.append(f"{idx + 1}일차: {place}, 식사, 휴식 (예상 {daily_budget:,}원)")

        return "\n".join(
            [
                f"{request.destination} {request.nights}박 {request.nights + 1}일 여행안",
                f"추천 숙소: {lodging_line}",
                *days,
                f"예상 숙박비: {lodging_cost:,}원",
                f"남은 활동/식비 예산: {activity_budget:,}원",
            ]
        )
