"""공유 링크 OG 미리보기 — 크롤러용 HTML, 브라우저는 SPA로 리다이렉트."""

from __future__ import annotations

import html
import re

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import Settings, get_settings
from app.services import trip_store

router = APIRouter(tags=["share"])

_BOT_RE = re.compile(
    r"bot|crawl|spider|slurp|facebookexternalhit|Facebot|Twitterbot|"
    r"LinkedInBot|Slackbot|TelegramBot|WhatsApp|Discordbot|Kakao|"
    r"Line/|Embedly|Quora Link Preview|Showyoubot|outbrain|pinterest|"
    r"redditbot|Applebot|bingpreview|Google-InspectionTool",
    re.I,
)

_DEFAULT_OG_IMAGE = "/generated/hero-alley-dusk.png"


def _is_bot(user_agent: str) -> bool:
    return bool(user_agent and _BOT_RE.search(user_agent))


def _trip_blurb(record: dict) -> tuple[str, str]:
    title = str(record.get("title") or "JapanTrip 일정").strip() or "JapanTrip 일정"
    itinerary = record.get("itinerary") or []
    regions: list[str] = []
    for day in itinerary:
        r = (day.get("region") or "").strip()
        if r and r not in regions:
            regions.append(r)
    n = len(itinerary)
    region_bit = " · ".join(regions[:4]) if regions else "일본"
    desc = f"{region_bit} {n}일 일정 · Google 지도 데이터 기준 실제 장소만"
    if n:
        first = itinerary[0].get("date")
        last = itinerary[-1].get("date")
        if first and last:
            desc = f"{first} ~ {last} · {desc}"
    return title, desc


def _og_html(
    *,
    title: str,
    description: str,
    page_url: str,
    image_url: str,
    redirect_url: str,
) -> str:
    t = html.escape(title)
    d = html.escape(description)
    u = html.escape(page_url)
    img = html.escape(image_url)
    redir = html.escape(redirect_url)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <title>{t}</title>
  <meta name="description" content="{d}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="JapanTrip" />
  <meta property="og:title" content="{t}" />
  <meta property="og:description" content="{d}" />
  <meta property="og:url" content="{u}" />
  <meta property="og:image" content="{img}" />
  <meta property="og:locale" content="ko_KR" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{t}" />
  <meta name="twitter:description" content="{d}" />
  <meta name="twitter:image" content="{img}" />
  <meta http-equiv="refresh" content="0;url={redir}" />
  <link rel="canonical" href="{redir}" />
</head>
<body>
  <p><a href="{redir}">{t}</a> — {d}</p>
</body>
</html>
"""


@router.get("/share/{trip_id}", response_model=None)
async def share_trip_preview(
    trip_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    record = await trip_store.aload_public_trip(settings, trip_id)
    if record is None:
        return HTMLResponse(
            "<!DOCTYPE html><html><body><p>일정을 찾을 수 없거나 만료되었습니다.</p></body></html>",
            status_code=404,
        )

    title, desc = _trip_blurb(record)
    fe = (settings.public_frontend_url or "http://localhost:5173").rstrip("/")
    # 공유 URL은 현재 요청 호스트 우선 (Vite 프록시·배포 모두)
    base = str(request.base_url).rstrip("/")
    page_url = f"{base}/share/{trip_id}"
    redirect_url = f"{fe}/?trip={trip_id}"
    image_url = f"{fe}{_DEFAULT_OG_IMAGE}"

    ua = request.headers.get("user-agent") or ""
    if _is_bot(ua):
        return HTMLResponse(
            _og_html(
                title=title,
                description=desc,
                page_url=page_url,
                image_url=image_url,
                redirect_url=redirect_url,
            )
        )
    return RedirectResponse(url=redirect_url, status_code=302)
