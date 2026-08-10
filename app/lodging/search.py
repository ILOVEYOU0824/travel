from app.config import Settings
from app.lodging.providers.base import LodgingProvider
from app.lodging.providers.google_places import GooglePlacesLodgingProvider
from app.lodging.providers.mock import MockLodgingProvider
from app.models import Lodging, TripRequest


class LodgingSearch:
    def __init__(self, providers: list[LodgingProvider]) -> None:
        self.providers = providers

    @classmethod
    def default(cls, settings: Settings) -> "LodgingSearch":
        if settings.google_places_api_key:
            return cls(providers=[GooglePlacesLodgingProvider(settings)])
        return cls(providers=[MockLodgingProvider()])

    def search(self, request: TripRequest) -> list[Lodging]:
        results: list[Lodging] = []
        for provider in self.providers:
            results.extend(provider.search(request))

        if not results:
            results = MockLodgingProvider().search(request)

        return sorted(results, key=lambda item: (-item.rating, item.price_per_night))
