from datetime import date

from pydantic import BaseModel, Field

from app.models import Lodging, Place


class TripPlanRequest(BaseModel):
    destination: str = Field(min_length=1, examples=["Tokyo"])
    start_date: date
    end_date: date
    people: int = Field(default=2, ge=1, le=20)
    budget: int = Field(default=500000, ge=0)


class LodgingResponse(BaseModel):
    provider: str
    name: str
    area: str
    price_per_night: int
    rating: float
    url: str
    lat: float | None = None
    lng: float | None = None

    @classmethod
    def from_model(cls, lodging: Lodging) -> "LodgingResponse":
        return cls(
            provider=lodging.provider,
            name=lodging.name,
            area=lodging.area,
            price_per_night=lodging.price_per_night,
            rating=lodging.rating,
            url=lodging.url,
            lat=lodging.lat,
            lng=lodging.lng,
        )


class PlaceResponse(BaseModel):
    provider: str
    name: str
    area: str
    rating: float
    url: str
    lat: float | None = None
    lng: float | None = None

    @classmethod
    def from_model(cls, place: Place) -> "PlaceResponse":
        return cls(
            provider=place.provider,
            name=place.name,
            area=place.area,
            rating=place.rating,
            url=place.url,
            lat=place.lat,
            lng=place.lng,
        )


class TripPlanResponse(BaseModel):
    destination: str
    nights: int
    plan: str
    lodgings: list[LodgingResponse]
    attractions: list[PlaceResponse]
