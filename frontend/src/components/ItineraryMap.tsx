import { APIProvider, Map, Marker, Polyline, useMap } from '@vis.gl/react-google-maps'
import { useEffect, useMemo } from 'react'
import { decodePolyline } from '../lib/polyline'
import type { ItineraryDay } from '../types'
import { usePlannerStore } from '../store/plannerStore'

const MAPS_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined

function collectPoints(day: ItineraryDay): Array<{ lat: number; lng: number }> {
  const pts: Array<{ lat: number; lng: number }> = []
  const arrival = day.arrival_from_airport?.airport?.location
  if (arrival) pts.push({ lat: arrival.lat, lng: arrival.lng })
  for (const it of day.items) {
    pts.push({ lat: it.place.location.lat, lng: it.place.location.lng })
  }
  const departure = day.departure_to_airport?.airport?.location
  if (departure) pts.push({ lat: departure.lat, lng: departure.lng })
  return pts
}

function FitBounds({ day }: { day: ItineraryDay | undefined }) {
  const map = useMap()
  const selectedPlaceId = usePlannerStore((s) => s.selectedPlaceId)

  useEffect(() => {
    if (!map || !day) return

    const fit = () => {
      const points = collectPoints(day)
      if (!points.length) return
      if (points.length === 1) {
        map.setCenter(points[0])
        map.setZoom(14)
        return
      }
      const bounds = new google.maps.LatLngBounds()
      points.forEach((p) => bounds.extend(p))
      // 상단 컨트롤·하단 여유 — 핀이 보이는 영역 중앙에 오도록
      map.fitBounds(bounds, { top: 72, right: 48, bottom: 56, left: 48 })
    }

    fit()
    // 컨테이너 크기 확정 후 재 fit — 지도가 뷰포트보다 길면 핀이 아래로 밀려 보이던 문제 방지
    const t1 = window.setTimeout(fit, 80)
    const t2 = window.setTimeout(fit, 320)
    const ro = new ResizeObserver(() => fit())
    ro.observe(map.getDiv())

    return () => {
      window.clearTimeout(t1)
      window.clearTimeout(t2)
      ro.disconnect()
    }
  }, [map, day])

  useEffect(() => {
    if (!map || !day || !selectedPlaceId) return
    const item = day.items.find((it) => it.place.place_id === selectedPlaceId)
    if (!item) return
    map.panTo({ lat: item.place.location.lat, lng: item.place.location.lng })
  }, [map, day, selectedPlaceId])

  return null
}

function DayRouteLines({ day }: { day: ItineraryDay | undefined }) {
  const segments = useMemo(() => {
    if (!day?.items.length) return []
    const lines: Array<{
      key: string
      path: Array<{ lat: number; lng: number }>
      color: string
    }> = []
    for (let i = 1; i < day.items.length; i++) {
      const curr = day.items[i]
      const prev = day.items[i - 1]
      const travel = curr.travel_from_previous
      const encoded = travel?.encoded_polyline
      let path: Array<{ lat: number; lng: number }>
      if (encoded) {
        path = decodePolyline(encoded)
      } else {
        path = [
          { lat: prev.place.location.lat, lng: prev.place.location.lng },
          { lat: curr.place.location.lat, lng: curr.place.location.lng },
        ]
      }
      if (path.length >= 2) {
        lines.push({
          key: `${prev.place.place_id}-${curr.place.place_id}`,
          path,
          color: travel?.travel_mode === 'TRANSIT' ? '#d97706' : '#2a9b98',
        })
      }
    }
    return lines
  }, [day])

  return (
    <>
      {segments.map((seg) => (
        <Polyline
          key={seg.key}
          path={seg.path}
          strokeColor={seg.color}
          strokeOpacity={0.9}
          strokeWeight={4}
        />
      ))}
    </>
  )
}

export function ItineraryMap({ day }: { day: ItineraryDay | undefined }) {
  const selectedPlaceId = usePlannerStore((s) => s.selectedPlaceId)
  const setField = usePlannerStore((s) => s.setField)

  if (!MAPS_KEY) {
    return (
      <div className="flex h-full min-h-[320px] items-center justify-center bg-ink-soft p-6 text-center text-sm text-mist/70">
        `VITE_GOOGLE_MAPS_API_KEY`를 frontend/.env에 설정하면 지도가 표시됩니다.
      </div>
    )
  }

  const center = day?.items[0]
    ? { lat: day.items[0].place.location.lat, lng: day.items[0].place.location.lng }
    : { lat: 34.6937, lng: 135.5023 }

  return (
    <div className="anim-map h-full min-h-0 overflow-hidden border border-white/10">
      <APIProvider apiKey={MAPS_KEY} language="ko" region="JP">
        <Map
          defaultCenter={center}
          defaultZoom={13}
          gestureHandling="greedy"
          disableDefaultUI={false}
          style={{ width: '100%', height: '100%' }}
          colorScheme="DARK"
        >
          <FitBounds day={day} />
          <DayRouteLines day={day} />
          {day?.items.map((it) => (
            <Marker
              key={`${it.order}-${it.place.place_id}`}
              position={{ lat: it.place.location.lat, lng: it.place.location.lng }}
              title={`${it.order}. ${it.place.name}`}
              label={{
                text: String(it.order),
                color: '#f4f8f9',
                fontWeight: '700',
              }}
              onClick={() => setField('selectedPlaceId', it.place.place_id)}
              opacity={it.place.place_id === selectedPlaceId ? 1 : 0.8}
              zIndex={it.place.place_id === selectedPlaceId ? 10 : 1}
            />
          ))}
        </Map>
      </APIProvider>
    </div>
  )
}
