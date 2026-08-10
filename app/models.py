from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TripRequest:
    destination: str
    start_date: date
    end_date: date
    people: int
    budget: int

    @property
    def nights(self) -> int:
        return (self.end_date - self.start_date).days


@dataclass(frozen=True)
class Lodging:
    provider: str
    name: str
    area: str
    price_per_night: int
    rating: float
    url: str
    lat: float | None = None
    lng: float | None = None

    def compact(self) -> str:
        return (
            f"{self.provider}|{self.name}|{self.area}|"
            f"{self.price_per_night}원/박|평점 {self.rating}|{self.url}"
        )


@dataclass(frozen=True)
class Place:
    provider: str
    name: str
    area: str
    rating: float
    url: str
    lat: float | None = None
    lng: float | None = None

    def compact(self) -> str:
        return f"{self.provider}|{self.name}|{self.area}|평점 {self.rating}|{self.url}"


@dataclass(frozen=True)
class TripPlan:
    content: str
