import type { AirportArrival, AirportDeparture } from '../../types'
import { BookingCtaLink } from './BookingCtaLink'
import { TravelLegBlock } from './TravelLegBlock'

export function AirportArrivalBlock({ arrival }: { arrival: AirportArrival }) {
  return (
    <li className="jp-airport-card relative overflow-hidden px-4 py-3">
      <img
        src="/generated/loading-shinkansen-night.png"
        alt=""
        className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-[0.14]"
      />
      <div className="relative">
        <p className="text-xs font-medium tracking-[0.14em] text-gold">공항 도착 → 시내</p>
        <h3 className="mt-0.5 font-display text-base text-fog">
          {arrival.airport?.name ?? arrival.airport_query}
        </h3>
        {arrival.airport?.formatted_address ? (
          <p className="mt-1 text-xs text-mist/65">{arrival.airport.formatted_address}</p>
        ) : (
          <p className="mt-1 text-xs text-mist/45">
            공항 상세는 Google에서 확인 · 아래 버튼으로 교통편을 검색하세요
          </p>
        )}
        <TravelLegBlock leg={arrival.travel_to_first} showBookingCta={false} />
        <div className="mt-2 flex flex-col gap-3">
          {arrival.travel_to_first?.booking_cta ? (
            <BookingCtaLink cta={arrival.travel_to_first.booking_cta} />
          ) : arrival.booking_cta ? (
            <BookingCtaLink cta={arrival.booking_cta} />
          ) : null}
          {arrival.connectivity_cta ? (
            <BookingCtaLink cta={arrival.connectivity_cta} />
          ) : null}
        </div>
        {arrival.airport?.google_maps_uri ? (
          <a
            href={arrival.airport.google_maps_uri}
            target="_blank"
            rel="noreferrer"
            className="mt-2 inline-block text-xs text-gold underline-offset-2 hover:underline"
          >
            Google 지도에서 공항 보기
          </a>
        ) : null}
      </div>
    </li>
  )
}

export function AirportDepartureBlock({ departure }: { departure: AirportDeparture }) {
  return (
    <li className="jp-airport-card relative overflow-hidden px-4 py-3">
      <img
        src="/generated/loading-shinkansen-night.png"
        alt=""
        className="pointer-events-none absolute inset-0 h-full w-full scale-x-[-1] object-cover opacity-[0.14]"
      />
      <div className="relative">
        <p className="text-xs font-medium tracking-[0.14em] text-gold">시내 → 공항 · 귀국</p>
        <h3 className="mt-0.5 font-display text-base text-fog">
          {departure.airport?.name ?? departure.airport_query}
        </h3>
        {departure.buffer_note ? (
          <p className="mt-1 text-xs leading-relaxed text-ember/90">{departure.buffer_note}</p>
        ) : departure.return_departure_jst ? (
          <p className="mt-1 text-xs text-ember/90">
            귀국편 {departure.return_departure_jst} (JST) 출발 · 공항 도착·체크인 여유를 두고
            이동하세요
          </p>
        ) : (
          <p className="mt-1 text-xs text-mist/55">
            귀국 비행 시간에 맞춰 여유 있게 공항으로 이동하세요
          </p>
        )}
        {departure.arrive_airport_by_jst || departure.leave_city_by_jst ? (
          <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
            {departure.leave_city_by_jst ? (
              <span className="border border-gold/35 bg-ink/50 px-2 py-1 text-gold">
                시내 출발 권장 {departure.leave_city_by_jst}
              </span>
            ) : null}
            {departure.arrive_airport_by_jst ? (
              <span className="border border-ember/40 bg-ink/50 px-2 py-1 text-ember/90">
                공항 도착 권장 {departure.arrive_airport_by_jst}
              </span>
            ) : null}
          </div>
        ) : null}
        {departure.airport?.formatted_address ? (
          <p className="mt-1 text-xs text-mist/65">{departure.airport.formatted_address}</p>
        ) : null}
        <TravelLegBlock leg={departure.travel_from_last} showBookingCta={false} />
        <div className="mt-2 flex flex-col gap-3">
          {departure.travel_from_last?.booking_cta ? (
            <BookingCtaLink cta={departure.travel_from_last.booking_cta} />
          ) : departure.booking_cta ? (
            <BookingCtaLink cta={departure.booking_cta} />
          ) : null}
        </div>
        {departure.airport?.google_maps_uri ? (
          <a
            href={departure.airport.google_maps_uri}
            target="_blank"
            rel="noreferrer"
            className="mt-2 inline-block text-xs text-gold underline-offset-2 hover:underline"
          >
            Google 지도에서 공항 보기
          </a>
        ) : null}
      </div>
    </li>
  )
}
