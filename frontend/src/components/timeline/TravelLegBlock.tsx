import { formatDistance, formatDuration, travelModeLabel } from '../../lib/format'
import type { RouteLeg, TransitLineInfo } from '../../types'
import { BookingCtaLink } from './BookingCtaLink'

function lineLabel(line: TransitLineInfo): string {
  const name = (line.name || line.name_short || '').trim()
  const vehicle = (line.vehicle_name || line.vehicle_type || '').trim()
  const agency = line.agencies?.filter(Boolean).join(', ') || ''
  return [name, vehicle, agency].filter(Boolean).join(' · ')
}

export function TravelLegBlock({
  leg,
  emptyHint,
  showBookingCta = true,
}: {
  leg: RouteLeg | null | undefined
  emptyHint?: string
  /** false면 CTA는 부모에서 같은 열로 렌더 (공항 카드 정렬용) */
  showBookingCta?: boolean
}) {
  if (!leg) {
    return emptyHint ? (
      <p className="jp-travel-leg mb-2 text-xs text-mist/40">{emptyHint}</p>
    ) : null
  }

  const lines = (leg.transit_lines ?? []).filter(
    (l) => l.name || l.name_short || l.vehicle_name || l.vehicle_type,
  )
  const mode = travelModeLabel(leg)

  return (
    <div className="jp-travel-leg mb-2 flex flex-col gap-1.5 text-xs text-mist/65">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="font-display tracking-wide text-sea-bright/90">
          ↓ {formatDuration(leg.duration_seconds, mode)}
          {leg.distance_meters != null ? ` · ${formatDistance(leg.distance_meters)}` : ''}
        </span>
        {leg.google_maps_dir_uri ? (
          <a
            href={leg.google_maps_dir_uri}
            target="_blank"
            rel="noreferrer"
            className="text-gold underline-offset-2 hover:underline"
          >
            구글맵 길찾기
          </a>
        ) : null}
      </div>

      {lines.length > 0 ? (
        <div className="rounded-sm border border-sea-bright/20 bg-ink/40 px-2.5 py-2">
          <p className="text-[10px] tracking-wide text-sea-bright/80">이동 상세 · Google Routes</p>
          <ul className="mt-1.5 space-y-1">
            {lines.map((line, i) => (
              <li key={`${lineLabel(line)}-${i}`} className="leading-relaxed text-fog/85">
                <span className="text-mist/45">{i + 1}.</span> {lineLabel(line)}
              </li>
            ))}
          </ul>
          {leg.static_duration_seconds != null &&
          leg.duration_seconds != null &&
          Math.abs(leg.static_duration_seconds - leg.duration_seconds) >= 120 ? (
            <p className="mt-1.5 text-[11px] text-mist/45">
              교통 상황 반영 시간 기준 · 정체 없을 때 약{' '}
              {formatDuration(leg.static_duration_seconds, mode)}
            </p>
          ) : null}
        </div>
      ) : leg.travel_mode === 'TRANSIT' || leg.travel_mode === 'DRIVE' ? (
        <p className="leading-relaxed text-mist/50">
          {mode} 구간입니다. 노선·요금 상세는 「구글맵 길찾기」에서 확인할 수 있어요.
        </p>
      ) : null}

      {showBookingCta && leg.booking_cta ? <BookingCtaLink cta={leg.booking_cta} /> : null}
    </div>
  )
}
