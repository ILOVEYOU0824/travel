import {
  formatDateLabel,
  formatDistance,
  formatDuration,
  formatPriceLevel,
  openingHoursForDate,
  timeSlotLabel,
  travelModeLabel,
} from './format'
import type { ItineraryResponse } from '../types'

function esc(s: string): string {
  return s
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

function buildPdfHtml(result: ItineraryResponse, title: string): string {
  const heading = title.trim() || 'JapanTrip 일정'
  const daysHtml = result.days
    .map((day) => {
      const arrival = day.arrival_from_airport
      const departure = day.departure_to_airport
      const arrivalHtml = arrival
        ? `<div class="block airport">
            <p class="slot">공항 도착 → 시내</p>
            <h3>${esc(arrival.airport?.name ?? arrival.airport_query)}</h3>
            ${
              arrival.travel_to_first
                ? `<p class="travel">↓ ${esc(
                    formatDuration(
                      arrival.travel_to_first.duration_seconds,
                      travelModeLabel(arrival.travel_to_first),
                    ),
                  )}${
                    arrival.travel_to_first.distance_meters != null
                      ? ` · ${esc(formatDistance(arrival.travel_to_first.distance_meters))}`
                      : ''
                  }</p>`
                : ''
            }
          </div>`
        : ''
      const departureHtml = departure
        ? `<div class="block airport">
            <p class="slot">시내 → 공항 · 귀국</p>
            <h3>${esc(departure.airport?.name ?? departure.airport_query)}</h3>
            ${
              departure.return_departure_jst
                ? `<p class="addr">귀국편 ${esc(departure.return_departure_jst)} (JST)</p>`
                : ''
            }
            ${
              departure.arrive_airport_by_jst
                ? `<p class="addr">공항 도착 권장 ${esc(departure.arrive_airport_by_jst)}</p>`
                : ''
            }
            ${
              departure.leave_city_by_jst
                ? `<p class="addr">시내 출발 권장 ${esc(departure.leave_city_by_jst)}</p>`
                : ''
            }
            ${
              departure.travel_from_last
                ? `<p class="travel">↓ ${esc(
                    formatDuration(
                      departure.travel_from_last.duration_seconds,
                      travelModeLabel(departure.travel_from_last),
                    ),
                  )}${
                    departure.travel_from_last.distance_meters != null
                      ? ` · ${esc(formatDistance(departure.travel_from_last.distance_meters))}`
                      : ''
                  }</p>`
                : ''
            }
          </div>`
        : ''

      const itemsHtml = day.items
        .map((item, idx) => {
          const place = item.place
          const hours = openingHoursForDate(
            place.opening_hours?.weekday_descriptions,
            day.date,
          )
          const price =
            place.price_level != null ? ` · ${formatPriceLevel(place.price_level)}` : ''
          const rating =
            place.rating != null
              ? `★ ${place.rating}${
                  place.user_rating_count != null ? ` (${place.user_rating_count})` : ''
                }`
              : ''
          const nextTravel = day.items[idx + 1]?.travel_from_previous
          return `<div class="block">
            <p class="slot">${esc(timeSlotLabel(item.time_slot))} · ${esc(place.category)}</p>
            <h3>${esc(place.name)}</h3>
            ${place.formatted_address ? `<p class="addr">${esc(place.formatted_address)}</p>` : ''}
            <p class="hours">${esc([rating, price, hours].filter(Boolean).join(' '))}</p>
            ${item.ai_description ? `<p class="ai">${esc(item.ai_description)}</p>` : ''}
            ${
              nextTravel
                ? `<p class="travel">↓ ${esc(
                    formatDuration(nextTravel.duration_seconds, travelModeLabel(nextTravel)),
                  )}${
                    nextTravel.distance_meters != null
                      ? ` · ${esc(formatDistance(nextTravel.distance_meters))}`
                      : ''
                  }</p>`
                : ''
            }
          </div>`
        })
        .join('')

      return `<section class="day">
        <h2>${esc(formatDateLabel(day.date))}${day.region ? ` · ${esc(day.region)}` : ''}</h2>
        ${arrivalHtml}
        ${itemsHtml}
        ${departureHtml}
      </section>`
    })
    .join('')

  return `<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <title>${esc(heading)}</title>
  <style>
    @page { margin: 16mm; }
    body { font-family: "Malgun Gothic", "Apple SD Gothic Neo", sans-serif; color: #1a1a1a; line-height: 1.45; margin: 0; background: #fff; }
    .wrap { max-width: 720px; margin: 0 auto; padding: 12px 8px 32px; }
    header { margin-bottom: 20px; border-bottom: 2px solid #c4a574; padding-bottom: 12px; }
    .brand { font-size: 12px; letter-spacing: 0.2em; color: #8a6a3d; margin: 0 0 6px; }
    h1 { font-size: 22px; margin: 0 0 6px; }
    .meta { font-size: 11px; color: #666; margin: 0; }
    .day { margin: 22px 0; page-break-inside: avoid; }
    .day h2 { font-size: 16px; margin: 0 0 10px; padding-bottom: 6px; border-bottom: 1px solid #ddd; }
    .block { margin: 0 0 12px; padding: 8px 0; border-bottom: 1px dashed #e5e5e5; }
    .block.airport { background: #f7f4ee; padding: 10px 12px; border: 1px solid #e8dfd0; border-bottom: 1px solid #e8dfd0; }
    .slot { font-size: 11px; letter-spacing: 0.06em; color: #8a6a3d; margin: 0 0 4px; font-weight: 600; }
    h3 { font-size: 15px; margin: 0 0 4px; }
    .addr, .hours { font-size: 11px; color: #666; margin: 0 0 4px; }
    .ai { font-size: 12px; margin: 6px 0 0; }
    .travel { font-size: 11px; color: #2f5c56; margin: 4px 0 8px 8px; }
    footer { margin-top: 28px; font-size: 10px; color: #888; border-top: 1px solid #ddd; padding-top: 12px; }
    @media print {
      body { background: #fff; }
      .noprint { display: none !important; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <p class="noprint" style="background:#fff3cd;border:1px solid #c4a574;padding:10px 12px;font-size:13px;margin-bottom:16px;">
      인쇄 대화상자에서 대상 프린터를 «PDF로 저장» / «Microsoft Print to PDF»로 선택하세요.
    </p>
    <header>
      <p class="brand">JapanTrip · 旅</p>
      <h1>${esc(heading)}</h1>
      <p class="meta">장소·주소·평점·영업시간은 Google 지도 데이터 · 방문 전 공식 출처에서 재확인</p>
    </header>
    ${daysHtml}
    <footer>
      JapanTrip AI · 일정 PDF · ${esc(new Date().toLocaleString('ko-KR'))}
    </footer>
  </div>
</body>
</html>`
}

/** 팝업 없이 iframe 인쇄 → PDF 저장. */
export function exportItineraryPdf(result: ItineraryResponse, title: string): Promise<void> {
  const html = buildPdfHtml(result, title)
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)

  return new Promise((resolve, reject) => {
    const prev = document.getElementById('japantrip-pdf-frame')
    if (prev) prev.remove()

    const iframe = document.createElement('iframe')
    iframe.id = 'japantrip-pdf-frame'
    iframe.title = 'PDF 미리보기'
    iframe.setAttribute('aria-hidden', 'true')
    iframe.style.cssText =
      'position:fixed;right:0;bottom:0;width:0;height:0;border:0;opacity:0;pointer-events:none'
    document.body.appendChild(iframe)

    const cleanup = () => {
      URL.revokeObjectURL(url)
      window.setTimeout(() => iframe.remove(), 60_000)
    }

    iframe.onload = () => {
      const win = iframe.contentWindow
      if (!win) {
        cleanup()
        reject(new Error('PDF 미리보기를 열지 못했습니다. 다시 시도해 주세요.'))
        return
      }
      window.setTimeout(() => {
        try {
          win.focus()
          win.print()
          resolve()
        } catch (e) {
          reject(e instanceof Error ? e : new Error('인쇄 대화상자를 열지 못했습니다.'))
        } finally {
          cleanup()
        }
      }, 250)
    }

    iframe.onerror = () => {
      cleanup()
      reject(new Error('PDF 생성에 실패했습니다.'))
    }

    iframe.src = url
  })
}
