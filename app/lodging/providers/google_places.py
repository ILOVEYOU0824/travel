from app.config import Settings
from app.lodging.providers.base import LodgingProvider
from app.models import Lodging, TripRequest
from app.places.google_places import GooglePlacesClient


class GooglePlacesLodgingProvider(LodgingProvider):
    def __init__(self, settings: Settings) -> None:
        self.google_places = GooglePlacesClient(settings)

    def search(self, request: TripRequest) -> list[Lodging]:
        return self.google_places.search_lodgings(request)
