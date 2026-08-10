from abc import ABC, abstractmethod

from app.models import Lodging, TripRequest


class LodgingProvider(ABC):
    @abstractmethod
    def search(self, request: TripRequest) -> list[Lodging]:
        """Return lodgings for a trip request."""
