import {
  formatPriceLevel,
  hoursConflictWarning,
  openingHoursForDate,
  timeSlotLabel,
} from '../../lib/format'
import { placeMapsUrl } from '../../lib/mapsLinks'
import { placePhotoUrl } from '../../lib/photos'
import type { ItineraryItem, Place } from '../../types'
import { BookingCtaLink } from './BookingCtaLink'
import { SwapPanel } from './SwapPanel'

export function PlaceCard({
  item,
  dayDate,
  selected,
  isLastDay,
  swapping,
  swapLoading,
  swapMessage,
  swapSuggestions,
  recomputingTravel,
  onSelect,
  onToggleSwap,
  onPickSwap,
}: {
  item: ItineraryItem
  dayDate: string
  selected: boolean
  isLastDay: boolean
  swapping: boolean
  swapLoading: boolean
  swapMessage: string | null
  swapSuggestions: Place[]
  recomputingTravel: boolean
  onSelect: () => void
  onToggleSwap: () => void
  onPickSwap: (p: Place) => void
}) {
  const photo = item.place.photos?.[0]
  const hoursLine = openingHoursForDate(
    item.place.opening_hours?.weekday_descriptions,
    dayDate,
  )
  const hoursWarn = hoursConflictWarning(
    item.place.opening_hours?.weekday_descriptions,
    dayDate,
    item.time_slot,
  )
  const maps = placeMapsUrl(item.place)

  return (
    <div className={`jp-card jp-place-card w-full ${selected ? 'jp-card-active' : ''}`}>
      <img
        src="/generated/ui-card-ornament.png"
        alt=""
        className="jp-card-ornament"
        aria-hidden
      />
      <button type="button" onClick={onSelect} className="w-full text-left">
        {photo ? (
          <div className="relative aspect-[16/9] w-full bg-ink">
            <img
              src={placePhotoUrl(photo.name, 960)}
              alt={item.place.name}
              className="h-full w-full object-cover"
              loading="lazy"
            />
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-ink/50 via-transparent to-transparent" />
            <span className="absolute left-2 top-2 flex h-7 min-w-7 cursor-grab items-center justify-center border border-gold/50 bg-ink/70 px-1.5 font-display text-sm text-fog backdrop-blur-sm active:cursor-grabbing">
              {item.order}
            </span>
            {photo.author_attributions?.length ? (
              <p className="absolute bottom-1 right-1 bg-black/55 px-1.5 py-0.5 text-[10px] text-white/85">
                사진: {photo.author_attributions.slice(0, 2).join(', ')}
              </p>
            ) : null}
          </div>
        ) : (
          <div
            aria-hidden
            className="relative aspect-[16/9] w-full overflow-hidden bg-ink-soft"
          >
            <img
              src="/generated/ink-wash-tile.png"
              alt=""
              className="h-full w-full object-cover opacity-60"
            />
            <span className="absolute left-2 top-2 flex h-7 min-w-7 cursor-grab items-center justify-center border border-gold/50 bg-ink/70 px-1.5 font-display text-sm text-fog active:cursor-grabbing">
              {item.order}
            </span>
          </div>
        )}

        <div className="relative px-4 py-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-medium tracking-wide text-gold">
                {timeSlotLabel(item.time_slot)}
                {item.place.category === 'lodging' ? ' · 숙소' : ''}
                {formatPriceLevel(item.place.price_level)
                  ? ` · ${formatPriceLevel(item.place.price_level)}`
                  : ''}
              </p>
              <h3 className="mt-0.5 font-display text-lg text-fog">
                {maps ? (
                  <a
                    href={maps}
                    target="_blank"
                    rel="noreferrer"
                    className="text-fog underline-offset-2 hover:text-gold hover:underline"
                    title="Google 지도에서 장소·리뷰 보기"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {item.place.name}
                  </a>
                ) : (
                  item.place.name
                )}
              </h3>
              {item.place.formatted_address ? (
                <p className="mt-1 text-xs leading-relaxed text-mist/70">
                  {item.place.formatted_address}
                </p>
              ) : null}
            </div>
            {item.place.rating != null ? (
              <span className="shrink-0 border border-gold/25 bg-ink/40 px-2 py-1 text-sm text-mist">
                ★ {item.place.rating.toFixed(1)}
                {item.place.user_rating_count != null
                  ? ` (${item.place.user_rating_count})`
                  : ''}
              </span>
            ) : null}
          </div>

          <p className="mt-2 text-sm text-mist/85">
            <span className="text-mist/50">추천 이유 · </span>
            {item.ai_description}
          </p>

          {item.place.category === 'lodging' ? (
            <div className="mt-2">
              <p className="text-xs text-ember/90">
                {isLastDay
                  ? '마지막 날 숙소 참고입니다. 당일 밤 묵을지·귀국 전 휴식인지는 일정에 맞춰 확인해 주세요.'
                  : 'Google Places 숙소 참고입니다. 요금·빈방은 Klook에서 확인하세요.'}
              </p>
              {item.booking_cta ? (
                <div className="mt-2">
                  <BookingCtaLink cta={item.booking_cta} />
                </div>
              ) : null}
            </div>
          ) : null}

          {hoursWarn ? (
            <p className="mt-2 border border-ember/35 bg-ember/10 px-2 py-1.5 text-xs text-ember/95">
              영업시간 주의 · {hoursWarn}
            </p>
          ) : null}
          {hoursLine ? (
            <p className="mt-2 text-xs text-mist/55">
              이날 영업시간(참고): {hoursLine}
            </p>
          ) : null}
        </div>
      </button>

      <div className="relative flex flex-wrap gap-2 border-t border-white/10 px-4 py-2.5">
        {maps ? (
          <a
            href={maps}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-gold underline-offset-2 hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            지도·리뷰
          </a>
        ) : null}
        <button
          type="button"
          className="jp-btn jp-btn-ghost px-2.5 py-1 text-xs"
          disabled={swapLoading || recomputingTravel}
          onClick={onToggleSwap}
        >
          {swapping ? '후보 닫기' : '이 장소만 교체'}
        </button>
      </div>

      {swapping ? (
        <SwapPanel
          loading={swapLoading}
          message={swapMessage}
          suggestions={swapSuggestions}
          onPick={onPickSwap}
        />
      ) : null}
    </div>
  )
}
