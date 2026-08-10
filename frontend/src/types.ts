export type TimeSlot = 'morning' | 'lunch' | 'afternoon' | 'dinner' | 'evening'

export interface LatLng {
  lat: number
  lng: number
}

export interface OpeningHours {
  weekday_descriptions: string[]
  open_now: boolean | null
}

export interface PlacePhoto {
  name: string
  width_px: number | null
  height_px: number | null
  author_attributions: string[]
}

export interface Place {
  place_id: string
  name: string
  formatted_address: string | null
  location: LatLng
  rating: number | null
  user_rating_count: number | null
  types: string[]
  primary_type: string | null
  category: string
  google_maps_uri: string | null
  opening_hours: OpeningHours | null
  photos: PlacePhoto[]
  price_level?: number | null
  ai_description: string | null
}

export interface BookingCta {
  provider: string
  label: string
  url: string
  hint: string
  product_hint?: string | null
  search_query?: string | null
  source_line_name?: string | null
}

export interface TransitLineInfo {
  name?: string | null
  name_short?: string | null
  vehicle_type?: string | null
  vehicle_name?: string | null
  agencies?: string[]
}

export interface RouteLeg {
  distance_meters: number | null
  duration_seconds: number | null
  static_duration_seconds: number | null
  encoded_polyline?: string | null
  travel_mode?: string | null
  mode_label?: string | null
  google_maps_dir_uri?: string | null
  transit_lines?: TransitLineInfo[]
  booking_cta?: BookingCta | null
}

export interface ItineraryItem {
  place: Place
  order: number
  time_slot: TimeSlot
  ai_description: string
  travel_from_previous: RouteLeg | null
  booking_cta?: BookingCta | null
}

export interface AirportArrival {
  airport_query: string
  airport: Place | null
  travel_to_first: RouteLeg | null
  booking_cta: BookingCta | null
  connectivity_cta?: BookingCta | null
}

export interface AirportDeparture {
  airport_query: string
  airport: Place | null
  travel_from_last: RouteLeg | null
  booking_cta: BookingCta | null
  return_departure_jst?: string | null
  arrive_airport_by_jst?: string | null
  leave_city_by_jst?: string | null
  checkin_buffer_minutes?: number | null
  buffer_note?: string | null
}

export type TravelModePref = 'AUTO' | 'WALK' | 'TRANSIT' | 'DRIVE'

export interface WeatherDay {
  date: string
  weather_code: number | null
  label_ko: string
  temp_max_c: number | null
  temp_min_c: number | null
  precipitation_probability_max: number | null
}

export interface NewsItem {
  title: string
  url: string
  source: string | null
  published_at: string | null
  kind: string
}

export interface TripContext {
  region: string
  resolved_name: string | null
  lat: number | null
  lng: number | null
  weather: WeatherDay[]
  weather_source: string
  news: NewsItem[]
  news_source: string
  note: string
}

export interface ItineraryDay {
  date: string
  region?: string | null
  items: ItineraryItem[]
  arrival_from_airport?: AirportArrival | null
  departure_to_airport?: AirportDeparture | null
}

export interface ItineraryResponse {
  days: ItineraryDay[]
  candidates_count: number
  llm_source: string
  validation: {
    removed_place_ids: string[]
    removed_items_count: number
    errors: string[]
  }
  budget_tier?: string | null
  budget_krw_per_person?: number | null
  budget_per_person_per_day_krw?: number | null
  budget_note?: string | null
  travelers?: number | null
  budget_krw_total?: number | null
  arrival_time_jst?: string | null
  departure_time_jst?: string | null
  outbound_departure_kst?: string | null
  return_departure_jst?: string | null
  flight_note?: string | null
  estimated_flight_minutes?: number | null
  prep_ctas?: BookingCta[]
  search_hints?: SearchHint[]
}

export interface PlaceSuggestion {
  place_id: string
  name: string
  formatted_address?: string | null
}

export interface SearchHint {
  kind: string
  query: string
  region: string
  status: string
  message: string
  suggestions: PlaceSuggestion[]
}

export interface PlaceAutocompleteSuggestion {
  place_id: string
  primary_text: string
  secondary_text?: string | null
}

export interface DayRegion {
  date: string
  region: string
}

export interface GeneratePayload {
  start_date: string
  end_date: string
  region?: string
  day_regions: DayRegion[]
  must_have_food: string[]
  must_have_sights: string[]
  include_lodging: boolean
  include_travel_times: boolean
  travel_mode: string
  travelers: number
  budget_krw_per_person: number
  outbound_departure_kst: string
  return_departure_jst: string
  arrival_airport_query?: string | null
}

export interface TripSummary {
  id: string
  title: string
  created_at?: string | null
  updated_at?: string | null
  expires_at?: string | null
}

export interface AirportOption {
  id: string
  label: string
  query: string
}
