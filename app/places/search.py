from app.config import Settings
from app.models import Place, TripRequest
from app.places.google_places import GooglePlacesClient


class PlaceSearch:
    def __init__(self, google_places: GooglePlacesClient) -> None:
        self.google_places = google_places

    @classmethod
    def default(cls, settings: Settings) -> "PlaceSearch":
        return cls(google_places=GooglePlacesClient(settings))

    def attractions(self, request: TripRequest) -> list[Place]:
        return sorted(
            self.google_places.search_attractions(request),
            key=lambda item: -item.rating,
        )
