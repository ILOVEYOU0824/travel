import { create } from 'zustand'
import type { DayRegion } from '../types'
import { createEditDayActions } from './editDayActions'
import { createPlannerActions } from './plannerActions'
import type { PlannerState } from './plannerTypes'

export type { PlannerState } from './plannerTypes'

function enumerateDates(start: string, end: string): string[] {
  const out: string[] = []
  const cur = new Date(`${start}T12:00:00`)
  const last = new Date(`${end}T12:00:00`)
  while (cur <= last) {
    out.push(cur.toISOString().slice(0, 10))
    cur.setDate(cur.getDate() + 1)
  }
  return out
}

function syncDayRegions(
  start: string,
  end: string,
  prev: DayRegion[],
  fallback = '오사카',
): DayRegion[] {
  const dates = enumerateDates(start, end)
  const map = new Map(prev.map((d) => [d.date, d.region]))
  let last = prev[0]?.region || fallback
  return dates.map((date) => {
    const region = map.get(date) || last
    last = region
    return { date, region }
  })
}

const initialStart = '2026-09-10'
const initialEnd = '2026-09-12'

export const usePlannerStore = create<PlannerState>((set, get) => ({
  startDate: initialStart,
  endDate: initialEnd,
  dayRegions: syncDayRegions(initialStart, initialEnd, [
    { date: '2026-09-10', region: '오사카' },
    { date: '2026-09-11', region: '교토' },
    { date: '2026-09-12', region: '교토' },
  ]),
  foodDraft: '',
  sightDraft: '',
  mustHaveFood: ['라멘'],
  mustHaveSights: [],
  includeLodging: true,
  includeTravelTimes: true,
  travelers: 1,
  budgetKrwPerPerson: 1_200_000,
  outboundDepartureKst: '10:00',
  returnDepartureJst: '11:00',
  arrivalAirportQuery: '',
  travelMode: 'AUTO',
  recomputingTravel: false,
  swapForPlaceId: null,
  swapSuggestions: [],
  swapMessage: null,
  swapLoading: false,
  loading: false,
  loadingStep: null,
  replanning: false,
  saving: false,
  error: null,
  replanMessage: null,
  saveMessage: null,
  replanPrompt: '',
  result: null,
  tripId: null,
  tripTitle: '내 일본 여행',
  shareUrl: null,
  selectedDayIndex: 0,
  selectedPlaceId: null,

  setField: (key, value) => set({ [key]: value } as Partial<PlannerState>),

  setDateRange: (start, end) => {
    set({ startDate: start, endDate: end, dayRegions: syncDayRegions(start, end, get().dayRegions) })
  },

  setDayRegion: (date, region) => {
    set({
      dayRegions: get().dayRegions.map((d) => (d.date === date ? { ...d, region } : d)),
    })
  },

  addMustHave: (kind) => {
    const draft = (kind === 'food' ? get().foodDraft : get().sightDraft).trim()
    if (!draft) return
    if (kind === 'food') {
      const list = get().mustHaveFood
      if (list.includes(draft)) {
        set({ foodDraft: '' })
        return
      }
      set({ mustHaveFood: [...list, draft], foodDraft: '' })
    } else {
      const list = get().mustHaveSights
      if (list.includes(draft)) {
        set({ sightDraft: '' })
        return
      }
      set({ mustHaveSights: [...list, draft], sightDraft: '' })
    }
  },

  removeMustHave: (kind, value) => {
    if (kind === 'food') set({ mustHaveFood: get().mustHaveFood.filter((v) => v !== value) })
    else set({ mustHaveSights: get().mustHaveSights.filter((v) => v !== value) })
  },

  ...createPlannerActions(set, get),
  ...createEditDayActions(set, get),

  reset: () => {
    window.history.replaceState({}, '', window.location.pathname)
    set({
      result: null,
      error: null,
      replanMessage: null,
      saveMessage: null,
      replanPrompt: '',
      selectedDayIndex: 0,
      selectedPlaceId: null,
      tripId: null,
      shareUrl: null,
      loadingStep: null,
      swapForPlaceId: null,
      swapSuggestions: [],
      swapMessage: null,
      swapLoading: false,
    })
  },
}))
