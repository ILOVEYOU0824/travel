import type { StoreApi } from 'zustand'
import {
  generateItinerary,
  loadTrip,
  replanItinerary,
  saveTrip,
  updateTrip,
} from '../api/itinerary'
import { getAccessToken } from '../lib/supabase'
import type { ItineraryResponse } from '../types'
import type { PlannerState } from './plannerTypes'

const LOCAL_TRIPS_KEY = 'japantrip_saved_ids'

/** 배포 시 API(Render) /share 로 보내 봇 OG·브라우저 리다이렉트 처리. 로컬은 Vite 프록시. */
function tripShareUrl(tripId: string): string {
  const api = (import.meta.env.VITE_API_BASE_URL as string | undefined)
    ?.trim()
    .replace(/\/$/, '')
  if (api) return `${api}/share/${tripId}`
  return `${window.location.origin}/share/${tripId}`
}

function rememberTripId(id: string) {
  try {
    const raw = localStorage.getItem(LOCAL_TRIPS_KEY)
    const list: string[] = raw ? (JSON.parse(raw) as string[]) : []
    const next = [id, ...list.filter((x) => x !== id)].slice(0, 10)
    localStorage.setItem(LOCAL_TRIPS_KEY, JSON.stringify(next))
  } catch {
    /* ignore */
  }
}

type Set = StoreApi<PlannerState>['setState']
type Get = StoreApi<PlannerState>['getState']

export function createPlannerActions(set: Set, get: Get) {
  return {
    generate: async () => {
      const {
        startDate,
        endDate,
        dayRegions,
        mustHaveFood,
        mustHaveSights,
        includeLodging,
        includeTravelTimes,
        travelers,
        budgetKrwPerPerson,
        outboundDepartureKst,
        returnDepartureJst,
        arrivalAirportQuery,
      } = get()
      const token = await getAccessToken()
      if (!token) {
        set({ error: '일정 짜기는 카카오 로그인이 필요합니다.' })
        return
      }
      if (get().replanning) {
        set({ error: '일정 수정이 끝난 뒤 새 일정을 만들어 주세요.' })
        return
      }
      if (dayRegions.some((d) => !d.region.trim())) {
        set({ error: '모든 날짜의 지역을 입력해 주세요.' })
        return
      }
      const steps = [
        'Places에서 지역별 장소·숙소를 모으는 중…',
        '후보 리스트 안에서 하루 동선을 짜는 중…',
        'Google 경로로 이동·환승을 확인하는 중…',
        '공항특급·숙소 Klook 안내를 붙이는 중…',
      ]
      window.history.replaceState({}, '', window.location.pathname)
      set({
        loading: true,
        loadingStep: steps[0],
        error: null,
        replanMessage: null,
        saveMessage: null,
        shareUrl: null,
        tripId: null,
        jobToast: null,
      })
      let stepIdx = 0
      const stepTimer = window.setInterval(() => {
        stepIdx = Math.min(stepIdx + 1, steps.length - 1)
        set({ loadingStep: steps[stepIdx] })
      }, 3500)
      try {
        const result = await generateItinerary({
          start_date: startDate,
          end_date: endDate,
          day_regions: dayRegions.map((d) => ({ date: d.date, region: d.region.trim() })),
          must_have_food: mustHaveFood,
          must_have_sights: mustHaveSights,
          include_lodging: includeLodging,
          include_travel_times: includeTravelTimes,
          travel_mode: get().travelMode,
          travelers,
          budget_krw_per_person: budgetKrwPerPerson,
          outbound_departure_kst: outboundDepartureKst,
          return_departure_jst: returnDepartureJst,
          arrival_airport_query: arrivalAirportQuery.trim() || null,
        })
        window.clearInterval(stepTimer)
        set({
          result,
          loading: false,
          loadingStep: null,
          screen: 'result',
          resultTab: 'itinerary',
          selectedDayIndex: 0,
          selectedPlaceId: result.days[0]?.items[0]?.place.place_id ?? null,
        })
      } catch (err) {
        window.clearInterval(stepTimer)
        set({
          loading: false,
          loadingStep: null,
          error: err instanceof Error ? err.message : '일정 생성에 실패했습니다.',
        })
      }
    },

    replan: async () => {
      const {
        dayRegions,
        result,
        replanPrompt,
        includeTravelTimes,
        selectedDayIndex,
        travelMode,
        tripId,
        tripTitle,
        arrivalAirportQuery,
      } = get()
      if (!result || !replanPrompt.trim() || get().replanning) return
      const token = await getAccessToken()
      if (!token) {
        set({ error: '일정 수정은 카카오 로그인이 필요합니다.' })
        return
      }
      const fallbackRegion =
        dayRegions[selectedDayIndex]?.region || dayRegions[0]?.region || '오사카'
      const seq = get().replanSeq + 1
      set({
        replanning: true,
        replanSeq: seq,
        error: null,
        replanMessage: null,
        saveMessage: null,
        jobToast: null,
      })
      try {
        const data = await replanItinerary({
          region: fallbackRegion.trim(),
          prompt: replanPrompt.trim(),
          current_itinerary: result.days,
          include_travel_times: includeTravelTimes,
          travel_mode: travelMode,
        })
        if (get().replanSeq !== seq) return
        const day = data.days[selectedDayIndex] ?? data.days[0]
        set({
          result: data,
          replanning: false,
          replanMessage: data.message,
          replanPrompt: data.unchanged ? replanPrompt : '',
          selectedPlaceId: day?.items[0]?.place.place_id ?? null,
          shareUrl: null,
          jobToast: {
            kind: 'success',
            title: '일정 수정 완료하였습니다',
            detail: data.unchanged ? data.message : null,
            action: 'open-result',
          },
        })
        if (tripId && !data.unchanged) {
          const meta = {
            candidates_count: data.candidates_count,
            llm_source: data.llm_source,
            day_regions: dayRegions,
            budget_tier: data.budget_tier,
            budget_krw_per_person: data.budget_krw_per_person,
            budget_per_person_per_day_krw: data.budget_per_person_per_day_krw,
            budget_note: data.budget_note,
            travelers: data.travelers,
            budget_krw_total: data.budget_krw_total,
            arrival_airport_query: arrivalAirportQuery || null,
          }
          void updateTrip(tripId, {
            title: tripTitle.trim() || '내 일본 여행',
            itinerary: data.days,
            meta,
          }).catch(() => undefined)
        }
      } catch (err) {
        if (get().replanSeq !== seq) return
        const message = err instanceof Error ? err.message : '일정 재조정에 실패했습니다.'
        set({
          replanning: false,
          error: message,
          jobToast: {
            kind: 'error',
            title: '일정 수정에 실패했습니다',
            detail: message,
            action: null,
          },
        })
      }
    },

    save: async () => {
      const { result, tripTitle, dayRegions, tripId, arrivalAirportQuery } = get()
      if (!result) return
      set({ saving: true, error: null, saveMessage: null })
      const meta = {
        candidates_count: result.candidates_count,
        llm_source: result.llm_source,
        day_regions: dayRegions,
        budget_tier: result.budget_tier,
        budget_krw_per_person: result.budget_krw_per_person,
        budget_per_person_per_day_krw: result.budget_per_person_per_day_krw,
        budget_note: result.budget_note,
        travelers: result.travelers,
        budget_krw_total: result.budget_krw_total,
        arrival_airport_query: arrivalAirportQuery || null,
      }
      const title = tripTitle.trim() || '내 일본 여행'
      try {
        const record = tripId
          ? await updateTrip(tripId, {
              title,
              itinerary: result.days,
              meta,
            })
          : await saveTrip({
              title,
              itinerary: result.days,
              meta,
            })
        rememberTripId(record.id)
        // /share/{id} → 봇은 OG HTML, 브라우저는 FE /?trip= 로 리다이렉트
        const shareUrl = tripShareUrl(record.id)
        window.history.replaceState({}, '', `?trip=${record.id}`)
        set({
          saving: false,
          tripId: record.id,
          shareUrl,
          saveMessage: tripId
            ? '변경이 저장됐어요. 같은 공유 링크가 유지됩니다.'
            : '저장됐어요. 링크를 복사해 두면 카톡·SNS 미리보기가 뜹니다.',
        })
      } catch (err) {
        set({
          saving: false,
          error: err instanceof Error ? err.message : '저장에 실패했습니다.',
        })
      }
    },

    openTrip: async (tripId: string) => {
      if (get().replanning) {
        set({ error: '일정 수정이 끝난 뒤 다른 일정을 열어 주세요.' })
        return
      }
      set({ loading: true, loadingStep: '저장된 일정을 불러오는 중…', error: null, jobToast: null })
      try {
        const record = await loadTrip(tripId)
        const asResult: ItineraryResponse = {
          days: record.itinerary,
          candidates_count: Number(record.meta?.candidates_count ?? 0),
          llm_source: String(record.meta?.llm_source ?? 'saved'),
          validation: { removed_place_ids: [], removed_items_count: 0, errors: [] },
          budget_tier: record.meta?.budget_tier as string | undefined,
          budget_krw_per_person: record.meta?.budget_krw_per_person as number | undefined,
          budget_per_person_per_day_krw: record.meta?.budget_per_person_per_day_krw as
            | number
            | undefined,
          budget_note: record.meta?.budget_note as string | undefined,
          travelers: record.meta?.travelers as number | undefined,
          budget_krw_total: record.meta?.budget_krw_total as number | undefined,
        }
        rememberTripId(record.id)
        const airportQ =
          typeof record.meta?.arrival_airport_query === 'string'
            ? record.meta.arrival_airport_query
            : ''
        document.title = `${record.title} · JapanTrip`
        set({
          result: asResult,
          tripId: record.id,
          tripTitle: record.title,
          arrivalAirportQuery: airportQ,
          shareUrl: tripShareUrl(record.id),
          loading: false,
          loadingStep: null,
          screen: 'result',
          resultTab: 'itinerary',
          selectedDayIndex: 0,
          selectedPlaceId: record.itinerary[0]?.items[0]?.place.place_id ?? null,
        })
      } catch (err) {
        set({
          loading: false,
          loadingStep: null,
          error: err instanceof Error ? err.message : '일정을 불러오지 못했습니다.',
        })
      }
    },
  }
}
