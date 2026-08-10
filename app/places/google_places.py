import json
from urllib.parse import quote_plus, urlencode
from urllib.request import urlopen

from app.config import Settings
from app.models import Lodging, Place, TripRequest


class GooglePlacesClient:
    base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def search_lodgings(self, request: TripRequest) -> list[Lodging]:
        if not self.settings.google_places_api_key:
            return []

        results = self._text_search(f"hotels in {request.destination}")
        lodgings = [self._to_lodging(item) for item in results]
        return [item for item in lodgings if item is not None]

    def search_attractions(self, request: TripRequest) -> list[Place]:
        if not self.settings.google_places_api_key:
            return []

        results = self._text_search(f"tourist attractions in {request.destination}")
        places = [self._to_place(item) for item in results]
        return [item for item in places if item is not None]

    def _text_search(self, query: str) -> list[dict]:
        params = urlencode(
            {
                "query": query,
                "language": "ko",
                "key": self.settings.google_places_api_key,
            }
        )
        url = f"{self.base_url}?{params}"

        try:
            with urlopen(url, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        if data.get("status") not in {"OK", "ZERO_RESULTS"}:
            return []

        return data.get("results", [])[: self.settings.places_limit]

    def _to_lodging(self, item: dict) -> Lodging | None:
        name = item.get("name")
        if not name:
            return None

        price_level = int(item.get("price_level", 2))
        price_per_night = self._estimate_price(price_level)
        location = item.get("geometry", {}).get("location", {})
        return Lodging(
            provider="google_places",
            name=name,
            area=item.get("formatted_address", ""),
            price_per_night=price_per_night,
            rating=float(item.get("rating", 0)),
            url=self._maps_url(name, item.get("place_id", "")),
            lat=location.get("lat"),
            lng=location.get("lng"),
        )

    def _to_place(self, item: dict) -> Place | None:
        name = item.get("name")
        if not name:
            return None

        location = item.get("geometry", {}).get("location", {})
        return Place(
            provider="google_places",
            name=name,
            area=item.get("formatted_address", ""),
            rating=float(item.get("rating", 0)),
            url=self._maps_url(name, item.get("place_id", "")),
            lat=location.get("lat"),
            lng=location.get("lng"),
        )

    def _maps_url(self, name: str, place_id: str) -> str:
        query = quote_plus(name)
        if place_id:
            return f"https://www.google.com/maps/search/?api=1&query={query}&query_place_id={place_id}"
        return f"https://www.google.com/maps/search/?api=1&query={query}"

    def _estimate_price(self, price_level: int) -> int:
        prices = {
            0: 70000,
            1: 100000,
            2: 150000,
            3: 230000,
            4: 350000,
        }
        return prices.get(price_level, 150000)
