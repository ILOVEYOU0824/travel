"""GOOGLE_MAPS_API_KEY로 Places Text Search 1회 프로브. 키 값은 출력하지 않음."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
import os

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


async def main() -> int:
    key = (os.getenv("GOOGLE_MAPS_API_KEY") or "").strip()
    if not key:
        print("FAIL: GOOGLE_MAPS_API_KEY empty")
        return 1
    print(f"KEY: len={len(key)} start={key[:7]} end={key[-4:]}")

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": "places.id,places.displayName",
    }
    body = {
        "textQuery": "大阪城",
        "languageCode": "ko",
        "maxResultCount": 1,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(url, headers=headers, json=body)
    print(f"HTTP: {res.status_code}")
    if res.status_code >= 400:
        # 키 전체는 찍지 않고 에러 메시지만
        text = res.text
        if key in text:
            text = text.replace(key, "***")
        print(text[:800])
        return 2
    data = res.json()
    places = data.get("places") or []
    print(f"OK: places={len(places)}")
    if places:
        name = (places[0].get("displayName") or {}).get("text")
        print(f"sample: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
