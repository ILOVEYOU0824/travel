import { formatDistance, formatDuration, travelModeLabel } from '../../lib/format'
import type { RouteLeg } from '../../types'
import { BookingCtaLink } from './BookingCtaLink'

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
  return (
    <div className="jp-travel-leg mb-2 flex flex-col gap-1 text-xs text-mist/65">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="font-display tracking-wide text-sea-bright/90">
          ↓ {formatDuration(leg.duration_seconds, travelModeLabel(leg))}
          {leg.distance_meters != null ? ` · ${formatDistance(leg.distance_meters)}` : ''}
        </span>
        {leg.google_maps_dir_uri ? (
          <a
            href={leg.google_maps_dir_uri}
            target="_blank"
            rel="noreferrer"
            className="text-gold underline-offset-2 hover:underline"
          >
            구글맵에서 경로 보기
          </a>
        ) : null}
      </div>
      {showBookingCta && leg.booking_cta ? <BookingCtaLink cta={leg.booking_cta} /> : null}
    </div>
  )
}
