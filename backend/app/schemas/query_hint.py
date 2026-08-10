"""필수 검색어 오타·미매칭 힌트 — Places Autocomplete/검색 결과만."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlaceSuggestion(BaseModel):
    place_id: str
    name: str
    formatted_address: str | None = None


class SearchHint(BaseModel):
    kind: str = Field(description="food | sight | query")
    query: str
    region: str
    # matched | autocorrected | not_found
    status: str
    message: str
    suggestions: list[PlaceSuggestion] = Field(default_factory=list)
