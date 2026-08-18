import type {
  AirportOption,
  GeneratePayload,
  ItineraryDay,
  ItineraryResponse,
  Place,
  PlaceAutocompleteSuggestion,
  TravelModePref,
  TripContext,
  TripSummary,
} from '../types'
import { getAccessToken } from '../lib/supabase'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

async function authHeaders(json = true): Promise<Record<string, string>> {
  const headers: Record<string, string> = {}
  if (json) headers['Content-Type'] = 'application/json'
  const token = await getAccessToken()
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

export interface ReplanResponse extends ItineraryResponse {
  intent: {
    intent_type: string
    category_query: string | null
    must_have: boolean
    target_day: string | null
    raw_text: string
  }
  message: string | null
  unchanged: boolean
}

export interface TripRecord {
  id: string
  title: string
  created_at: string
  updated_at: string
  expires_at?: string | null
  itinerary: ItineraryDay[]
  meta: Record<string, unknown>
}

async function readError(res: Response, fallback: string): Promise<string> {
  try {
    const data = (await res.json()) as { detail?: string | unknown; code?: string }
    if (typeof data.detail === 'string' && data.detail) return data.detail
  } catch {
    /* ignore */
  }
  return fallback
}

export async function generateItinerary(payload: GeneratePayload): Promise<ItineraryResponse> {
  const res = await fetch(`${API_BASE}/api/v1/itinerary/generate`, {
    method: 'POST',
    headers: await authHeaders(),
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await readError(res, `요청 실패 (${res.status})`))
  return (await res.json()) as ItineraryResponse
}

export async function replanItinerary(payload: {
  region: string
  prompt: string
  current_itinerary: ItineraryDay[]
  include_travel_times: boolean
  travel_mode?: TravelModePref
}): Promise<ReplanResponse> {
  const res = await fetch(`${API_BASE}/api/v1/itinerary/replan`, {
    method: 'POST',
    headers: await authHeaders(),
    body: JSON.stringify({ ...payload, travel_mode: payload.travel_mode ?? 'AUTO' }),
  })
  if (!res.ok) throw new Error(await readError(res, `재조정 실패 (${res.status})`))
  return (await res.json()) as ReplanResponse
}

export async function recomputeTravel(payload: {
  current_itinerary: ItineraryDay[]
  travel_mode: TravelModePref
  arrival_airport_query?: string | null
  return_departure_jst?: string | null
}): Promise<{ days: ItineraryDay[]; travel_mode: string; message: string }> {
  const res = await fetch(`${API_BASE}/api/v1/itinerary/recompute-travel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await readError(res, `경로 재계산 실패 (${res.status})`))
  return (await res.json()) as { days: ItineraryDay[]; travel_mode: string; message: string }
}

export async function fetchTripContext(payload: {
  region: string
  start_date: string
  end_date: string
}): Promise<TripContext> {
  const q = new URLSearchParams({
    region: payload.region,
    start_date: payload.start_date,
    end_date: payload.end_date,
  })
  const res = await fetch(`${API_BASE}/api/v1/trip-context?${q}`)
  if (!res.ok) throw new Error(await readError(res, `날씨·소식 조회 실패 (${res.status})`))
  return (await res.json()) as TripContext
}

export async function reorderDay(payload: {
  current_itinerary: ItineraryDay[]
  day_date: string
  ordered_place_ids: string[]
  travel_mode: TravelModePref
  arrival_airport_query?: string | null
  return_departure_jst?: string | null
}): Promise<{ days: ItineraryDay[]; message: string }> {
  const res = await fetch(`${API_BASE}/api/v1/itinerary/reorder-day`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await readError(res, `순서 변경 실패 (${res.status})`))
  return (await res.json()) as { days: ItineraryDay[]; message: string }
}

export async function optimizeDay(payload: {
  current_itinerary: ItineraryDay[]
  day_date: string
  travel_mode: TravelModePref
  arrival_airport_query?: string | null
  return_departure_jst?: string | null
}): Promise<{ days: ItineraryDay[]; message: string }> {
  const res = await fetch(`${API_BASE}/api/v1/itinerary/optimize-day`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await readError(res, `동선 최적화 실패 (${res.status})`))
  return (await res.json()) as { days: ItineraryDay[]; message: string }
}

export async function fetchSwapSuggestions(payload: {
  current_itinerary: ItineraryDay[]
  day_date: string
  place_id: string
}): Promise<{ place_id: string; category: string; suggestions: Place[]; message: string | null }> {
  const res = await fetch(`${API_BASE}/api/v1/itinerary/swap-suggestions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await readError(res, `대체 장소 조회 실패 (${res.status})`))
  return (await res.json()) as {
    place_id: string
    category: string
    suggestions: Place[]
    message: string | null
  }
}

export async function applySwap(payload: {
  current_itinerary: ItineraryDay[]
  day_date: string
  old_place_id: string
  new_place: Place
  travel_mode: TravelModePref
  arrival_airport_query?: string | null
  return_departure_jst?: string | null
}): Promise<{ days: ItineraryDay[]; message: string }> {
  const res = await fetch(`${API_BASE}/api/v1/itinerary/apply-swap`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await readError(res, `장소 교체 실패 (${res.status})`))
  return (await res.json()) as { days: ItineraryDay[]; message: string }
}

export interface BudgetTracker {
  tier: string
  tier_label: string
  preferred_price_levels: number[]
  preferred_label: string
  budget_krw_per_person: number | null
  budget_krw_total: number | null
  per_person_per_day_krw: number | null
  days: Array<{
    date: string
    region: string | null
    restaurants: number
    cafes: number
    lodging: number
    attractions: number
    price_levels: number[]
    in_tier_count: number
    priced_count: number
    note: string | null
  }>
  total_restaurants: number
  total_lodging: number
  priced_places: number
  in_tier_places: number
  alignment_pct: number | null
  note: string
}

export interface RainAdvice {
  rainy_days: Array<{
    date: string
    region: string | null
    precipitation_probability_max: number | null
    weather_label: string | null
    rainy: boolean
    outdoor_count: number
    suggestions: Array<{
      old_place_id: string
      old_place_name: string
      alternatives: Place[]
    }>
  }>
  message: string
  source: string
}

export async function fetchBudgetTracker(payload: {
  current_itinerary: ItineraryDay[]
  travelers: number
  budget_krw_per_person?: number | null
  budget_tier?: string | null
}): Promise<BudgetTracker> {
  const res = await fetch(`${API_BASE}/api/v1/itinerary/budget-tracker`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await readError(res, `예산 요약 실패 (${res.status})`))
  return (await res.json()) as BudgetTracker
}

export async function fetchRainAdvice(payload: {
  current_itinerary: ItineraryDay[]
  start_date: string
  end_date: string
}): Promise<RainAdvice> {
  const res = await fetch(`${API_BASE}/api/v1/itinerary/rain-advice`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await readError(res, `우천 대안 실패 (${res.status})`))
  return (await res.json()) as RainAdvice
}

export async function saveTrip(payload: {
  title: string
  itinerary: ItineraryDay[]
  meta?: Record<string, unknown>
}): Promise<TripRecord> {
  const res = await fetch(`${API_BASE}/api/v1/trips`, {
    method: 'POST',
    headers: await authHeaders(),
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await readError(res, `저장 실패 (${res.status})`))
  return (await res.json()) as TripRecord
}

export async function updateTrip(
  tripId: string,
  payload: {
    title?: string
    itinerary?: ItineraryDay[]
    meta?: Record<string, unknown>
  },
): Promise<TripRecord> {
  const res = await fetch(`${API_BASE}/api/v1/trips/${tripId}`, {
    method: 'PATCH',
    headers: await authHeaders(),
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await readError(res, `수정 실패 (${res.status})`))
  return (await res.json()) as TripRecord
}

export async function deleteTrip(tripId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/trips/${tripId}`, {
    method: 'DELETE',
    headers: await authHeaders(false),
  })
  if (!res.ok) throw new Error(await readError(res, `삭제 실패 (${res.status})`))
}

export async function loadTrip(tripId: string): Promise<TripRecord> {
  const res = await fetch(`${API_BASE}/api/v1/trips/${tripId}`, {
    headers: await authHeaders(false),
  })
  if (!res.ok) throw new Error(await readError(res, `불러오기 실패 (${res.status})`))
  return (await res.json()) as TripRecord
}

export async function listTrips(): Promise<TripSummary[]> {
  const res = await fetch(`${API_BASE}/api/v1/trips`, {
    headers: await authHeaders(false),
  })
  if (!res.ok) throw new Error(await readError(res, `목록 실패 (${res.status})`))
  return (await res.json()) as TripSummary[]
}

export async function fetchAirportOptions(): Promise<AirportOption[]> {
  const res = await fetch(`${API_BASE}/api/v1/meta/airports`)
  if (!res.ok) throw new Error(await readError(res, `공항 목록 실패 (${res.status})`))
  return (await res.json()) as AirportOption[]
}

export async function autocompletePlaces(payload: {
  input: string
  language_code?: string
  bias_lat?: number | null
  bias_lng?: number | null
  max_suggestions?: number
}): Promise<{ suggestions: PlaceAutocompleteSuggestion[]; source: string; input: string }> {
  const q = new URLSearchParams({
    input: payload.input,
    language_code: payload.language_code ?? 'ko',
    max_suggestions: String(payload.max_suggestions ?? 5),
  })
  if (payload.bias_lat != null) q.set('bias_lat', String(payload.bias_lat))
  if (payload.bias_lng != null) q.set('bias_lng', String(payload.bias_lng))
  const res = await fetch(`${API_BASE}/api/v1/places/autocomplete?${q}`)
  if (!res.ok) throw new Error(await readError(res, `자동완성 실패 (${res.status})`))
  return (await res.json()) as {
    suggestions: PlaceAutocompleteSuggestion[]
    source: string
    input: string
  }
}
