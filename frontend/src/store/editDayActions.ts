import type { StoreApi } from 'zustand'
import {
  applySwap,
  fetchSwapSuggestions,
  optimizeDay,
  recomputeTravel,
  reorderDay,
} from '../api/itinerary'
import type { Place, TravelModePref } from '../types'
import type { PlannerState } from './plannerTypes'

type Set = StoreApi<PlannerState>['setState']
type Get = StoreApi<PlannerState>['getState']

export function createEditDayActions(set: Set, get: Get) {
  return {
    setTravelModeAndRecompute: async (mode: TravelModePref) => {
      const { result, arrivalAirportQuery, returnDepartureJst, travelMode, recomputingTravel } =
        get()
      if (!result || recomputingTravel) return
      if (mode === travelMode) return
      set({
        travelMode: mode,
        recomputingTravel: true,
        error: null,
        replanMessage: null,
        loadingStep: '이동 수단에 맞춰 경로를 다시 계산하는 중…',
      })
      try {
        const data = await recomputeTravel({
          current_itinerary: result.days,
          travel_mode: mode,
          arrival_airport_query: arrivalAirportQuery.trim() || null,
          return_departure_jst: returnDepartureJst || null,
        })
        set({
          result: { ...result, days: data.days },
          recomputingTravel: false,
          loadingStep: null,
          replanMessage: data.message,
          shareUrl: null,
        })
      } catch (err) {
        set({
          recomputingTravel: false,
          loadingStep: null,
          error: err instanceof Error ? err.message : '경로 재계산에 실패했습니다.',
        })
      }
    },

    optimizeSelectedDay: async () => {
      const {
        result,
        selectedDayIndex,
        travelMode,
        arrivalAirportQuery,
        returnDepartureJst,
      } = get()
      const day = result?.days[selectedDayIndex]
      if (!result || !day || day.items.length < 2) return
      set({
        recomputingTravel: true,
        error: null,
        replanMessage: null,
        loadingStep: '장소는 그대로 두고 동선만 최적화하는 중…',
      })
      try {
        const data = await optimizeDay({
          current_itinerary: result.days,
          day_date: day.date,
          travel_mode: travelMode,
          arrival_airport_query: arrivalAirportQuery.trim() || null,
          return_departure_jst: returnDepartureJst || null,
        })
        set({
          result: { ...result, days: data.days },
          recomputingTravel: false,
          loadingStep: null,
          replanMessage: data.message,
          shareUrl: null,
          swapForPlaceId: null,
          swapSuggestions: [],
          swapMessage: null,
        })
      } catch (err) {
        set({
          recomputingTravel: false,
          loadingStep: null,
          error: err instanceof Error ? err.message : '동선 최적화에 실패했습니다.',
        })
      }
    },

    reorderSelectedDay: async (orderedPlaceIds: string[]) => {
      const {
        result,
        selectedDayIndex,
        travelMode,
        arrivalAirportQuery,
        returnDepartureJst,
      } = get()
      const day = result?.days[selectedDayIndex]
      if (!result || !day) return
      set({
        recomputingTravel: true,
        error: null,
        replanMessage: null,
        loadingStep: '순서를 바꾸고 경로를 다시 계산하는 중…',
      })
      try {
        const data = await reorderDay({
          current_itinerary: result.days,
          day_date: day.date,
          ordered_place_ids: orderedPlaceIds,
          travel_mode: travelMode,
          arrival_airport_query: arrivalAirportQuery.trim() || null,
          return_departure_jst: returnDepartureJst || null,
        })
        set({
          result: { ...result, days: data.days },
          recomputingTravel: false,
          loadingStep: null,
          replanMessage: data.message,
          shareUrl: null,
          swapForPlaceId: null,
          swapSuggestions: [],
          swapMessage: null,
        })
      } catch (err) {
        set({
          recomputingTravel: false,
          loadingStep: null,
          error: err instanceof Error ? err.message : '순서 변경에 실패했습니다.',
        })
      }
    },

    loadSwapSuggestions: async (placeId: string) => {
      const { result, selectedDayIndex } = get()
      const day = result?.days[selectedDayIndex]
      if (!result || !day) return
      set({
        swapLoading: true,
        swapForPlaceId: placeId,
        swapSuggestions: [],
        swapMessage: null,
        error: null,
        selectedPlaceId: placeId,
      })
      try {
        const data = await fetchSwapSuggestions({
          current_itinerary: result.days,
          day_date: day.date,
          place_id: placeId,
        })
        set({
          swapLoading: false,
          swapSuggestions: data.suggestions,
          swapMessage: data.message,
        })
      } catch (err) {
        set({
          swapLoading: false,
          swapSuggestions: [],
          swapMessage: null,
          error: err instanceof Error ? err.message : '대체 장소를 찾지 못했습니다.',
        })
      }
    },

    applyPlaceSwap: async (newPlace: Place) => {
      const {
        result,
        selectedDayIndex,
        swapForPlaceId,
        travelMode,
        arrivalAirportQuery,
        returnDepartureJst,
      } = get()
      const day = result?.days[selectedDayIndex]
      if (!result || !day || !swapForPlaceId) return
      set({
        recomputingTravel: true,
        swapLoading: true,
        error: null,
        replanMessage: null,
        loadingStep: '장소를 바꾸고 경로를 다시 계산하는 중…',
      })
      try {
        const data = await applySwap({
          current_itinerary: result.days,
          day_date: day.date,
          old_place_id: swapForPlaceId,
          new_place: newPlace,
          travel_mode: travelMode,
          arrival_airport_query: arrivalAirportQuery.trim() || null,
          return_departure_jst: returnDepartureJst || null,
        })
        set({
          result: { ...result, days: data.days },
          recomputingTravel: false,
          swapLoading: false,
          loadingStep: null,
          replanMessage: data.message,
          selectedPlaceId: newPlace.place_id,
          shareUrl: null,
          swapForPlaceId: null,
          swapSuggestions: [],
          swapMessage: null,
        })
      } catch (err) {
        set({
          recomputingTravel: false,
          swapLoading: false,
          loadingStep: null,
          error: err instanceof Error ? err.message : '장소 교체에 실패했습니다.',
        })
      }
    },

    clearSwapSuggestions: () =>
      set({
        swapForPlaceId: null,
        swapSuggestions: [],
        swapMessage: null,
        swapLoading: false,
      }),
  }
}
