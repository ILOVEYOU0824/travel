from app.lodging.providers.base import LodgingProvider
from app.models import Lodging, TripRequest


class MockLodgingProvider(LodgingProvider):
    def search(self, request: TripRequest) -> list[Lodging]:
        destination = request.destination.strip()
        return [
            Lodging(
                provider="mock",
                name=f"{destination} 시티 호텔",
                area=f"{destination} 중심가",
                price_per_night=110000,
                rating=4.4,
                url="https://example.com/hotel-city",
            ),
            Lodging(
                provider="mock",
                name=f"{destination} 감성 게스트하우스",
                area=f"{destination} 역 근처",
                price_per_night=65000,
                rating=4.2,
                url="https://example.com/guesthouse",
            ),
            Lodging(
                provider="mock",
                name=f"{destination} 오션/뷰 스테이",
                area=f"{destination} 전망 좋은 지역",
                price_per_night=145000,
                rating=4.7,
                url="https://example.com/view-stay",
            ),
        ]
