import { useEffect, useState } from 'react'
import {
  applySwap,
  fetchBudgetTracker,
  fetchRainAdvice,
  fetchTripContext,
  type BudgetTracker,
  type RainAdvice,
} from '../api/itinerary'
import { formatPriceLevel } from '../lib/format'
import type { TripContext } from '../types'
import { usePlannerStore } from '../store/plannerStore'

type Tab = 'weather' | 'news' | 'budget' | 'rain' | null

export function TripInsightsBar() {
  const result = usePlannerStore((s) => s.result)
  const startDate = usePlannerStore((s) => s.startDate)
  const endDate = usePlannerStore((s) => s.endDate)
  const dayRegions = usePlannerStore((s) => s.dayRegions)
  const selectedDayIndex = usePlannerStore((s) => s.selectedDayIndex)
  const travelers = usePlannerStore((s) => s.travelers)
  const budgetKrwPerPerson = usePlannerStore((s) => s.budgetKrwPerPerson)
  const travelMode = usePlannerStore((s) => s.travelMode)
  const arrivalAirportQuery = usePlannerStore((s) => s.arrivalAirportQuery)
  const returnDepartureJst = usePlannerStore((s) => s.returnDepartureJst)
  const setField = usePlannerStore((s) => s.setField)

  const [tab, setTab] = useState<Tab>(null)
  const [ctx, setCtx] = useState<TripContext | null>(null)
  const [budget, setBudget] = useState<BudgetTracker | null>(null)
  const [rain, setRain] = useState<RainAdvice | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const region =
    result?.days[selectedDayIndex]?.region ||
    dayRegions[selectedDayIndex]?.region ||
    dayRegions[0]?.region ||
    ''

  useEffect(() => {
    if (!result || !region.trim()) return
    let cancelled = false
    void fetchTripContext({
      region: region.trim(),
      start_date: startDate,
      end_date: endDate,
    })
      .then((d) => {
        if (!cancelled) setCtx(d)
      })
      .catch(() => {
        if (!cancelled) setCtx(null)
      })
    return () => {
      cancelled = true
    }
  }, [result, region, startDate, endDate])

  useEffect(() => {
    if (!result) return
    let cancelled = false
    void fetchBudgetTracker({
      current_itinerary: result.days,
      travelers,
      budget_krw_per_person: budgetKrwPerPerson,
      budget_tier: result.budget_tier,
    })
      .then((d) => {
        if (!cancelled) setBudget(d)
      })
      .catch(() => {
        if (!cancelled) setBudget(null)
      })
    return () => {
      cancelled = true
    }
  }, [result, travelers, budgetKrwPerPerson])

  useEffect(() => {
    if (!result || tab !== 'rain') return
    let cancelled = false
    setBusy(true)
    void fetchRainAdvice({
      current_itinerary: result.days,
      start_date: startDate,
      end_date: endDate,
    })
      .then((d) => {
        if (!cancelled) {
          setRain(d)
          setError(null)
          setBusy(false)
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : '우천 대안 실패')
          setBusy(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [result, startDate, endDate, tab])

  if (!result) return null

  const todayWeather = ctx?.weather.find((w) => w.date === result.days[selectedDayIndex]?.date)
  const weatherHint = todayWeather
    ? `${todayWeather.label_ko}${
        todayWeather.temp_min_c != null && todayWeather.temp_max_c != null
          ? ` ${Math.round(todayWeather.temp_min_c)}~${Math.round(todayWeather.temp_max_c)}°`
          : ''
      }`
    : null
  const newsCount = ctx?.news.length ?? 0

  function toggle(next: Tab) {
    setTab((cur) => (cur === next ? null : next))
  }

  async function pick(
    dayDate: string,
    oldId: string,
    place: RainAdvice['rainy_days'][0]['suggestions'][0]['alternatives'][0],
  ) {
    if (!result) return
    setBusy(true)
    setField('loadingStep', '실내 대안으로 바꾸고 경로를 다시 계산하는 중…')
    setField('recomputingTravel', true)
    try {
      const out = await applySwap({
        current_itinerary: result.days,
        day_date: dayDate,
        old_place_id: oldId,
        new_place: place,
        travel_mode: travelMode,
        arrival_airport_query: arrivalAirportQuery.trim() || null,
        return_departure_jst: returnDepartureJst || null,
      })
      setField('result', { ...result, days: out.days })
      setField('replanMessage', out.message)
      setField('shareUrl', null)
      setTab(null)
      setRain(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '교체 실패')
    } finally {
      setBusy(false)
      setField('recomputingTravel', false)
      setField('loadingStep', null)
    }
  }

  const rainyWithAlts = rain?.rainy_days.filter((d) => d.rainy && d.suggestions.length) ?? []

  return (
    <section className="border-b border-white/10 px-4 py-2.5 sm:px-6">
      <div className="mx-auto max-w-7xl">
        <div className="flex flex-wrap items-center gap-2">
          <p className="jp-legend shrink-0 text-sm">여행 참고</p>
          {weatherHint ? (
            <span className="text-xs text-mist/60">
              {region} · {weatherHint}
              {newsCount ? ` · 소식 ${newsCount}` : ''}
            </span>
          ) : (
            <span className="text-xs text-mist/45">{region || '지역'} 날씨·소식·예산</span>
          )}
          <div className="ml-auto flex flex-wrap gap-1.5">
            {(
              [
                ['weather', '날씨'],
                ['news', '소식'],
                ['budget', '예산'],
                ['rain', '우천'],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                className={`jp-tab ${tab === id ? 'jp-tab-active' : ''}`}
                onClick={() => toggle(id)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {tab ? (
          <div className="mt-3 border border-white/10 bg-ink/35 px-3 py-3">
            {tab === 'weather' ? (
              ctx?.weather.length ? (
                <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                  {ctx.weather.map((w) => (
                    <li key={w.date} className="text-xs text-mist/85">
                      <p className="text-mist/45">{w.date}</p>
                      <p className="mt-0.5 font-display text-fog">{w.label_ko}</p>
                      <p className="mt-0.5">
                        {w.temp_min_c != null && w.temp_max_c != null
                          ? `${Math.round(w.temp_min_c)}° ~ ${Math.round(w.temp_max_c)}°`
                          : '기온 —'}
                        {w.precipitation_probability_max != null
                          ? ` · 강수 ${w.precipitation_probability_max}%`
                          : ''}
                      </p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-mist/50">날씨 불러오는 중…</p>
              )
            ) : null}

            {tab === 'news' ? (
              ctx?.news.length ? (
                <ul className="flex max-h-48 flex-col gap-2 overflow-y-auto">
                  {ctx.news.map((n) => (
                    <li key={n.url}>
                      <a
                        href={n.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-sm text-fog underline-offset-2 hover:text-gold hover:underline"
                      >
                        {n.kind === 'festival' ? '[축제] ' : n.kind === 'weather' ? '[날씨] ' : ''}
                        {n.title}
                      </a>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-mist/50">관련 소식이 없거나 불러오는 중…</p>
              )
            ) : null}

            {tab === 'budget' ? (
              budget ? (
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className="border border-gold/35 px-2 py-1 text-gold">
                    {budget.tier_label}
                  </span>
                  <span className="border border-white/15 px-2 py-1 text-mist/80">
                    {budget.preferred_label}
                  </span>
                  {budget.alignment_pct != null ? (
                    <span className="border border-sea-bright/40 px-2 py-1 text-sea-bright">
                      일치 {budget.alignment_pct}%
                    </span>
                  ) : null}
                  <span className="border border-white/10 px-2 py-1 text-mist/70">
                    식사 {budget.total_restaurants} · 숙소 {budget.total_lodging}
                  </span>
                  {budget.days.slice(0, 4).map((d) => (
                    <span key={d.date} className="border border-white/10 px-2 py-1 text-mist/65">
                      {d.date.slice(5)}{' '}
                      {d.price_levels.length
                        ? d.price_levels.map((p) => formatPriceLevel(p) || '?').join('')
                        : '—'}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-mist/50">예산 요약 계산 중…</p>
              )
            ) : null}

            {tab === 'rain' ? (
              <div>
                {busy && !rain ? <p className="text-xs text-mist/55">예보·Places 조회 중…</p> : null}
                {error ? <p className="text-xs text-ember">{error}</p> : null}
                {rain ? <p className="text-xs text-mist/65">{rain.message}</p> : null}
                {rainyWithAlts.length === 0 && rain && !busy ? (
                  <p className="mt-2 text-xs text-mist/50">바꿀 야외 장소 제안이 없습니다.</p>
                ) : null}
                <ul className="mt-2 flex max-h-56 flex-col gap-2 overflow-y-auto">
                  {rainyWithAlts.map((d) => (
                    <li key={d.date} className="text-xs">
                      <p className="text-gold">
                        {d.date}
                        {d.precipitation_probability_max != null
                          ? ` · 강수 ${d.precipitation_probability_max}%`
                          : ''}
                      </p>
                      {d.suggestions.map((s) => (
                        <div key={s.old_place_id} className="mt-1">
                          <p className="text-mist/80">{s.old_place_name} →</p>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {s.alternatives.map((alt) => (
                              <button
                                key={alt.place_id}
                                type="button"
                                disabled={busy}
                                className="border border-white/10 px-2 py-1 text-mist/85 hover:border-sea-bright/50"
                                onClick={() => void pick(d.date, s.old_place_id, alt)}
                              >
                                {alt.name}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            <p className="mt-2 text-[10px] text-mist/40">
              날씨 Open-Meteo · 뉴스 RSS · 예산은 Google 가격대 참고 (AI 창작 아님)
            </p>
          </div>
        ) : null}
      </div>
    </section>
  )
}
