import { useEffect, useMemo, useRef, useState } from 'react'
import { formatDateLabel, hoursConflictWarning, summarizeDay } from '../lib/format'
import type { ItineraryDay } from '../types'
import { usePlannerStore } from '../store/plannerStore'
import {
  AirportArrivalBlock,
  AirportDepartureBlock,
} from './timeline/AirportBlocks'
import { PlaceCard } from './timeline/PlaceCard'
import { TravelLegBlock } from './timeline/TravelLegBlock'

export function DayTimeline({
  days,
  selectedDayIndex,
}: {
  days: ItineraryDay[]
  selectedDayIndex: number
}) {
  const setField = usePlannerStore((s) => s.setField)
  const selectedPlaceId = usePlannerStore((s) => s.selectedPlaceId)
  const reorderSelectedDay = usePlannerStore((s) => s.reorderSelectedDay)
  const optimizeSelectedDay = usePlannerStore((s) => s.optimizeSelectedDay)
  const loadSwapSuggestions = usePlannerStore((s) => s.loadSwapSuggestions)
  const applyPlaceSwap = usePlannerStore((s) => s.applyPlaceSwap)
  const clearSwapSuggestions = usePlannerStore((s) => s.clearSwapSuggestions)
  const swapForPlaceId = usePlannerStore((s) => s.swapForPlaceId)
  const swapSuggestions = usePlannerStore((s) => s.swapSuggestions)
  const swapMessage = usePlannerStore((s) => s.swapMessage)
  const swapLoading = usePlannerStore((s) => s.swapLoading)
  const recomputingTravel = usePlannerStore((s) => s.recomputingTravel)
  const day = days[selectedDayIndex]
  const isLastDay = selectedDayIndex === days.length - 1
  const arrival = day?.arrival_from_airport
  const departure = day?.departure_to_airport
  const dragId = useRef<string | null>(null)
  const [overId, setOverId] = useState<string | null>(null)

  useEffect(() => {
    if (!selectedPlaceId) return
    const el = document.getElementById(`place-${selectedPlaceId}`)
    el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [selectedPlaceId, selectedDayIndex])

  function onDropReorder(targetId: string) {
    const fromId = dragId.current
    dragId.current = null
    setOverId(null)
    if (!day || !fromId || fromId === targetId || recomputingTravel) return
    const ids = day.items.map((it) => it.place.place_id)
    const from = ids.indexOf(fromId)
    const to = ids.indexOf(targetId)
    if (from < 0 || to < 0) return
    const next = [...ids]
    const [moved] = next.splice(from, 1)
    next.splice(to, 0, moved)
    void reorderSelectedDay(next)
  }

  const hoursWarnCount = useMemo(() => {
    if (!day) return 0
    return day.items.filter((it) =>
      hoursConflictWarning(
        it.place.opening_hours?.weekday_descriptions,
        day.date,
        it.time_slot,
      ),
    ).length
  }, [day])

  return (
    <div className="jp-timeline relative flex h-full flex-col gap-3">
      <div className="jp-timeline-hero relative overflow-hidden border border-gold/25">
        <img
          src="/generated/ui-day-header.png"
          alt=""
          className="absolute inset-0 h-full w-full object-cover opacity-55"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-ink via-ink/75 to-ink/40" />
        <div className="relative flex items-center gap-3 px-4 py-3">
          <img src="/generated/seal-tabi.png" alt="" className="h-9 w-9 object-contain opacity-90" />
          <div>
            <p className="font-display text-[10px] tracking-[0.32em] text-gold/85">日程 · 하루 동선</p>
            <p className="font-display text-base tracking-wide text-fog">
              {day ? formatDateLabel(day.date) : '일정'}
              {day?.region ? ` · ${day.region}` : ''}
            </p>
            <p className="mt-0.5 text-[11px] text-mist/50">
              ⋮⋮ 드래그로 순서 변경 · 「이 장소만 교체」로 근처 후보 3곳
            </p>
          </div>
          {day && day.items.length >= 2 ? (
            <button
              type="button"
              className="jp-btn jp-btn-secondary ml-auto shrink-0 text-xs"
              disabled={recomputingTravel}
              onClick={() => void optimizeSelectedDay()}
            >
              {recomputingTravel ? '계산 중…' : '동선 최적화'}
            </button>
          ) : null}
        </div>
      </div>

      <div className="sticky top-0 z-10 -mx-1 flex flex-wrap gap-2 bg-ink-soft/95 px-1 py-2 backdrop-blur-sm">
        {days.map((d, i) => (
          <button
            key={d.date}
            type="button"
            onClick={() => {
              setField('selectedDayIndex', i)
              setField('selectedPlaceId', d.items[0]?.place.place_id ?? null)
            }}
            className={`jp-tab ${i === selectedDayIndex ? 'jp-tab-active' : ''}`}
          >
            {formatDateLabel(d.date)}
            {d.region ? ` · ${d.region}` : ''}
          </button>
        ))}
      </div>

      {day ? (
        <p className="text-xs text-mist/65">
          {summarizeDay(day)}
          {hoursWarnCount > 0 ? (
            <span className="ml-2 text-ember/90">· 영업시간 주의 {hoursWarnCount}곳</span>
          ) : null}
        </p>
      ) : null}

      {!day?.items.length && !arrival && !departure ? (
        <p className="jp-panel text-center text-sm text-mist/70">
          이 날 장소가 없습니다. 위에서 일정을 수정해 장소를 추가해 보세요.
        </p>
      ) : (
        <ul className="flex flex-1 flex-col gap-3 overflow-y-auto pr-1">
          {arrival ? <AirportArrivalBlock arrival={arrival} /> : null}

          {day.items.map((it, idx) => {
            const showFirstLegHint = idx === 0 && !arrival
            const swapping = swapForPlaceId === it.place.place_id
            return (
              <li
                key={`${it.place.place_id}-${it.order}`}
                id={`place-${it.place.place_id}`}
                draggable={!recomputingTravel}
                onDragStart={(e) => {
                  dragId.current = it.place.place_id
                  e.dataTransfer.effectAllowed = 'move'
                  e.dataTransfer.setData('text/plain', it.place.place_id)
                }}
                onDragOver={(e) => {
                  e.preventDefault()
                  setOverId(it.place.place_id)
                }}
                onDragLeave={() => {
                  if (overId === it.place.place_id) setOverId(null)
                }}
                onDrop={(e) => {
                  e.preventDefault()
                  onDropReorder(it.place.place_id)
                }}
                onDragEnd={() => {
                  dragId.current = null
                  setOverId(null)
                }}
                className={overId === it.place.place_id ? 'opacity-90 ring-1 ring-gold/50' : ''}
              >
                <TravelLegBlock
                  leg={it.travel_from_previous}
                  emptyHint={
                    showFirstLegHint ? '첫 장소 · 여기서 하루를 시작합니다' : undefined
                  }
                />
                <PlaceCard
                  item={it}
                  dayDate={day.date}
                  selected={it.place.place_id === selectedPlaceId}
                  isLastDay={isLastDay}
                  swapping={swapping}
                  swapLoading={swapLoading}
                  swapMessage={swapMessage}
                  swapSuggestions={swapSuggestions}
                  recomputingTravel={recomputingTravel}
                  onSelect={() => setField('selectedPlaceId', it.place.place_id)}
                  onToggleSwap={() => {
                    if (swapping) clearSwapSuggestions()
                    else void loadSwapSuggestions(it.place.place_id)
                  }}
                  onPickSwap={(p) => void applyPlaceSwap(p)}
                />
              </li>
            )
          })}

          {departure ? <AirportDepartureBlock departure={departure} /> : null}
        </ul>
      )}

      <p className="text-xs leading-relaxed text-mist/45">
        사진·주소·평점·영업시간·가격대(₩)는 Google 지도 데이터입니다. 열차·숙소 CTA는
        Klook 검색으로 연결되며 좌석·요금·빈방은 예약 페이지에서 확인하세요. 영업시간은
        방문 전 공식 출처에서 재확인해 주세요.
      </p>
    </div>
  )
}
