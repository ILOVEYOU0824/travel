function minutesParts(seconds: number): string {
  const m = Math.round(seconds / 60)
  if (m < 60) return `약 ${m}분`
  const h = Math.floor(m / 60)
  const rem = m % 60
  return rem ? `약 ${h}시간 ${rem}분` : `약 ${h}시간`
}

export function formatDuration(
  seconds: number | null | undefined,
  modeLabel = '도보',
): string {
  if (seconds == null) return '—'
  return `${modeLabel} ${minutesParts(seconds)}`
}

/** 모드 없이 소요시간만 (일차 요약용) */
export function formatDurationShort(seconds: number | null | undefined): string {
  if (seconds == null || seconds <= 0) return ''
  return minutesParts(seconds)
}

export function travelModeLabel(leg: {
  mode_label?: string | null
  travel_mode?: string | null
}): string {
  if (leg.mode_label) return leg.mode_label
  if (leg.travel_mode === 'TRANSIT') return '대중교통'
  if (leg.travel_mode === 'DRIVE') return '자동차'
  if (leg.travel_mode === 'BICYCLE') return '자전거'
  return '도보'
}

export function formatPriceLevel(level: number | null | undefined): string {
  if (level == null || level < 1) return ''
  const n = Math.min(4, Math.max(1, Math.round(level)))
  return '₩'.repeat(n)
}

export function budgetTierLabel(tier: string | null | undefined): string {
  if (tier === 'budget') return '저예산'
  if (tier === 'premium') return '여유'
  if (tier === 'standard') return '보통'
  return tier ?? ''
}

export function formatDistance(meters: number | null | undefined): string {
  if (meters == null) return ''
  if (meters < 1000) return `${meters}m`
  return `${(meters / 1000).toFixed(1)}km`
}

export function formatDateLabel(iso: string): string {
  const d = new Date(`${iso}T12:00:00`)
  return d.toLocaleDateString('ko-KR', {
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  })
}

const SLOT_LABEL: Record<string, string> = {
  morning: '오전',
  lunch: '점심',
  afternoon: '오후',
  dinner: '저녁',
  evening: '밤',
}

export function timeSlotLabel(slot: string): string {
  return SLOT_LABEL[slot] ?? slot
}

const KO_WEEKDAYS = ['일요일', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일']

/** 방문일 요일에 맞는 영업시간 한 줄 (Places weekday_descriptions) */
export function openingHoursForDate(
  descriptions: string[] | null | undefined,
  isoDate: string,
): string | null {
  if (!descriptions?.length) return null
  const day = new Date(`${isoDate}T12:00:00`)
  const label = KO_WEEKDAYS[day.getDay()]
  const hit = descriptions.find((line) => line.includes(label))
  return hit ?? descriptions[0] ?? null
}

/** 슬롯별 방문 추정 구간(분, 0–1440). LLM/임의 시간이 아니라 UI 휴리스틱. */
const SLOT_WINDOW_MIN: Record<string, [number, number]> = {
  morning: [9 * 60, 11 * 60 + 30],
  lunch: [11 * 60 + 30, 14 * 60],
  afternoon: [14 * 60, 17 * 60 + 30],
  dinner: [17 * 60 + 30, 20 * 60 + 30],
  evening: [20 * 60, 22 * 60],
}

const EN_WEEKDAYS = [
  'Sunday',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
]

function _toMinutes(h: number, m: number, pm?: boolean): number {
  let hh = h % 24
  if (pm === true && hh < 12) hh += 12
  if (pm === false && hh === 12) hh = 0
  return hh * 60 + m
}

/** "오전 11:00" / "11:00 AM" / "14:30" → 분. 실패 시 null. */
function parseClockToken(raw: string): number | null {
  const s = raw.trim()
  let m = s.match(/오전\s*(\d{1,2})\s*[:：]\s*(\d{2})/)
  if (m) return _toMinutes(Number(m[1]), Number(m[2]), false)
  m = s.match(/오후\s*(\d{1,2})\s*[:：]\s*(\d{2})/)
  if (m) return _toMinutes(Number(m[1]), Number(m[2]), true)
  m = s.match(/(\d{1,2})\s*[:：]\s*(\d{2})\s*(AM|PM)/i)
  if (m) return _toMinutes(Number(m[1]), Number(m[2]), m[3].toUpperCase() === 'PM')
  m = s.match(/(\d{1,2})\s*[:：]\s*(\d{2})/)
  if (m) {
    const h = Number(m[1])
    if (h > 23) return null
    return _toMinutes(h, Number(m[2]))
  }
  return null
}

function parseOpenClose(line: string): { closed: boolean; open: number | null; close: number | null } {
  if (/휴무|닫음|closed|정기휴무/i.test(line)) {
    return { closed: true, open: null, close: null }
  }
  if (/24\s*시간|open\s*24/i.test(line)) {
    return { closed: false, open: 0, close: 24 * 60 }
  }
  const range = line.match(
    /((?:오전|오후)?\s*\d{1,2}\s*[:：]\s*\d{2}(?:\s*(?:AM|PM))?)\s*[–\-〜~～]\s*((?:오전|오후)?\s*\d{1,2}\s*[:：]\s*\d{2}(?:\s*(?:AM|PM))?)/i,
  )
  if (!range) return { closed: false, open: null, close: null }
  return {
    closed: false,
    open: parseClockToken(range[1]),
    close: parseClockToken(range[2]),
  }
}

function hoursLineForVisit(
  descriptions: string[] | null | undefined,
  isoDate: string,
): string | null {
  if (!descriptions?.length) return null
  const day = new Date(`${isoDate}T12:00:00`)
  const ko = KO_WEEKDAYS[day.getDay()]
  const en = EN_WEEKDAYS[day.getDay()]
  return (
    descriptions.find((line) => line.includes(ko) || line.toLowerCase().includes(en.toLowerCase())) ??
    null
  )
}

/**
 * Places weekday_descriptions vs time_slot 휴리스틱 충돌.
 * 확실할 때만 경고 — 파싱 실패 시 null (환각 방지).
 */
export function hoursConflictWarning(
  descriptions: string[] | null | undefined,
  isoDate: string,
  timeSlot: string,
): string | null {
  const line = hoursLineForVisit(descriptions, isoDate)
  if (!line) return null
  const win = SLOT_WINDOW_MIN[timeSlot]
  if (!win) return null
  const parsed = parseOpenClose(line)
  if (parsed.closed) {
    return '이날 휴무로 보여요 · 방문 전 공식 확인'
  }
  if (parsed.open == null || parsed.close == null) return null
  const [slotStart, slotEnd] = win
  let open = parsed.open
  let close = parsed.close
  if (close <= open) close += 24 * 60 // 자정 넘어 영업
  // 슬롯 구간과 영업 구간이 겹치지 않으면 충돌
  if (slotEnd <= open || slotStart >= close) {
    return '방문 시간대에 문을 열지 않을 수 있어요 · 공식 확인'
  }
  return null
}

export function summarizeDay(day: {
  region?: string | null
  items: Array<{
    place: { category: string }
    travel_from_previous?: { duration_seconds: number | null } | null
  }>
  departure_to_airport?: {
    travel_from_last?: { duration_seconds: number | null } | null
  } | null
}): string {
  const parts: string[] = []
  if (day.region) parts.push(day.region)
  parts.push(`${day.items.length}곳`)
  const travelSec =
    day.items.reduce((sum, it) => sum + (it.travel_from_previous?.duration_seconds ?? 0), 0) +
    (day.departure_to_airport?.travel_from_last?.duration_seconds ?? 0)
  const travel = formatDurationShort(travelSec)
  if (travel) parts.push(`이동 ${travel}`)
  if (day.items.some((it) => it.place.category === 'lodging')) parts.push('숙소 포함')
  if (day.departure_to_airport) parts.push('공항 복귀')
  return parts.join(' · ')
}
