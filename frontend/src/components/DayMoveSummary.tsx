import { formatDistance, formatDuration, formatDurationShort, travelModeLabel } from '../lib/format'
import type { ItineraryDay, RouteLeg } from '../types'

type Hop = {
  key: string
  from: string
  to: string
  leg: RouteLeg
}

function hopsForDay(day: ItineraryDay): Hop[] {
  const hops: Hop[] = []
  const arrival = day.arrival_from_airport
  if (arrival?.travel_to_first && day.items[0]) {
    hops.push({
      key: 'arrival',
      from: arrival.airport?.name ?? arrival.airport_query,
      to: day.items[0].place.name,
      leg: arrival.travel_to_first,
    })
  }
  for (let i = 0; i < day.items.length; i++) {
    const it = day.items[i]
    if (!it.travel_from_previous || i === 0) continue
    hops.push({
      key: it.place.place_id,
      from: day.items[i - 1].place.name,
      to: it.place.name,
      leg: it.travel_from_previous,
    })
  }
  const departure = day.departure_to_airport
  if (departure?.travel_from_last && day.items.length) {
    hops.push({
      key: 'departure',
      from: day.items[day.items.length - 1].place.name,
      to: departure.airport?.name ?? departure.airport_query,
      leg: departure.travel_from_last,
    })
  }
  return hops
}

function hopDetail(leg: RouteLeg): string {
  const lines = (leg.transit_lines ?? [])
    .map((l) => (l.name || l.name_short || l.vehicle_name || '').trim())
    .filter(Boolean)
  if (lines.length) return lines.join(' → ')
  return travelModeLabel(leg)
}

/** 하루 이동을 텍스트로 먼저 보여 줌 (지도보다 정보 밀도 높음) */
export function DayMoveSummary({ day }: { day: ItineraryDay }) {
  const hops = hopsForDay(day)
  if (!hops.length) return null

  const totalSec = hops.reduce((s, h) => s + (h.leg.duration_seconds ?? 0), 0)
  const mapsUri = hops.find((h) => h.leg.google_maps_dir_uri)?.leg.google_maps_dir_uri

  return (
    <section className="rounded-sm border border-sea-bright/25 bg-ink/50 px-3 py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-display text-[11px] tracking-[0.22em] text-sea-bright/90">
          移動 · 오늘 이동 요약
        </p>
        <p className="text-xs text-fog/85">
          총 이동 {formatDurationShort(totalSec) || '—'} · {hops.length}구간
        </p>
      </div>
      <ol className="mt-2.5 space-y-2">
        {hops.map((h, i) => (
          <li key={h.key} className="text-sm leading-snug">
            <p className="text-fog">
              <span className="mr-1.5 text-mist/40">{i + 1}.</span>
              {h.from}
              <span className="mx-1.5 text-mist/40">→</span>
              {h.to}
            </p>
            <p className="mt-0.5 pl-5 text-xs text-mist/70">
              {formatDuration(h.leg.duration_seconds, travelModeLabel(h.leg))}
              {h.leg.distance_meters != null
                ? ` · ${formatDistance(h.leg.distance_meters)}`
                : ''}
              {' · '}
              {hopDetail(h.leg)}
            </p>
          </li>
        ))}
      </ol>
      <p className="mt-2.5 text-[11px] leading-relaxed text-mist/45">
        참고용 한 가지 경로입니다. 다른 경로·요금·출발역 변경은 구글맵에서 하세요.
        {mapsUri ? (
          <>
            {' '}
            <a
              href={mapsUri}
              target="_blank"
              rel="noreferrer"
              className="text-gold underline-offset-2 hover:underline"
            >
              구글맵 길찾기
            </a>
          </>
        ) : null}
      </p>
    </section>
  )
}
