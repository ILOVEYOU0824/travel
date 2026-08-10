import type { DayRegion, ItineraryResponse, Place, TravelModePref } from '../types'

export interface PlannerState {
  startDate: string
  endDate: string
  dayRegions: DayRegion[]
  foodDraft: string
  sightDraft: string
  mustHaveFood: string[]
  mustHaveSights: string[]
  includeLodging: boolean
  includeTravelTimes: boolean
  travelers: number
  budgetKrwPerPerson: number
  outboundDepartureKst: string
  returnDepartureJst: string
  arrivalAirportQuery: string
  travelMode: TravelModePref
  recomputingTravel: boolean
  loading: boolean
  loadingStep: string | null
  replanning: boolean
  saving: boolean
  error: string | null
  replanMessage: string | null
  saveMessage: string | null
  replanPrompt: string
  result: ItineraryResponse | null
  tripId: string | null
  tripTitle: string
  shareUrl: string | null
  selectedDayIndex: number
  selectedPlaceId: string | null
  swapForPlaceId: string | null
  swapSuggestions: Place[]
  swapMessage: string | null
  swapLoading: boolean
  setField: <K extends keyof PlannerState>(key: K, value: PlannerState[K]) => void
  setDateRange: (start: string, end: string) => void
  setDayRegion: (date: string, region: string) => void
  addMustHave: (kind: 'food' | 'sight') => void
  removeMustHave: (kind: 'food' | 'sight', value: string) => void
  generate: () => Promise<void>
  replan: () => Promise<void>
  setTravelModeAndRecompute: (mode: TravelModePref) => Promise<void>
  reorderSelectedDay: (orderedPlaceIds: string[]) => Promise<void>
  optimizeSelectedDay: () => Promise<void>
  loadSwapSuggestions: (placeId: string) => Promise<void>
  applyPlaceSwap: (newPlace: Place) => Promise<void>
  clearSwapSuggestions: () => void
  save: () => Promise<void>
  openTrip: (tripId: string) => Promise<void>
  reset: () => void
}
