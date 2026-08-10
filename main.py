from argparse import ArgumentParser

from app.config import Settings
from app.lodging.search import LodgingSearch
from app.models import TripRequest
from app.places.search import PlaceSearch
from app.services.ai_client import AiClient
from app.services.planner import TripPlanner
from app.utils.dates import parse_trip_dates


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="AI travel planner")
    parser.add_argument("--destination", required=True, help="여행 지역")
    parser.add_argument("--start-date", required=True, help="시작일: YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="종료일: YYYY-MM-DD")
    parser.add_argument("--people", type=int, default=2, help="인원 수")
    parser.add_argument("--budget", type=int, default=500000, help="총 예산")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    start_date, end_date = parse_trip_dates(args.start_date, args.end_date)

    request = TripRequest(
        destination=args.destination,
        start_date=start_date,
        end_date=end_date,
        people=args.people,
        budget=args.budget,
    )

    settings = Settings.from_env()
    lodging_search = LodgingSearch.default(settings)
    place_search = PlaceSearch.default(settings)
    planner = TripPlanner(AiClient(settings))

    lodgings = lodging_search.search(request)
    attractions = place_search.attractions(request)
    plan = planner.create_plan(request, lodgings, attractions)

    print(plan.content)


if __name__ == "__main__":
    main()
