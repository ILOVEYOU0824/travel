import { useEffect } from 'react'
import { AuthBar } from './components/AuthBar'
import { DayTimeline } from './components/DayTimeline'
import { ItineraryMap } from './components/ItineraryMap'
import { LoadingOverlay } from './components/LoadingOverlay'
import { PlannerForm } from './components/PlannerForm'
import { ReplanBar } from './components/ReplanBar'
import { SaveBar } from './components/SaveBar'
import { SearchHintsBar } from './components/SearchHintsBar'
import { TripControlsBar } from './components/TripControlsBar'
import { TripInsightsBar } from './components/TripInsightsBar'
import { TripsPanel } from './components/TripsPanel'
import { budgetTierLabel } from './lib/format'
import { useAuthStore } from './store/authStore'
import { usePlannerStore } from './store/plannerStore'

export default function App() {
  const result = usePlannerStore((s) => s.result)
  const loading = usePlannerStore((s) => s.loading)
  const error = usePlannerStore((s) => s.error)
  const selectedDayIndex = usePlannerStore((s) => s.selectedDayIndex)
  const reset = usePlannerStore((s) => s.reset)
  const openTrip = usePlannerStore((s) => s.openTrip)
  const authInit = useAuthStore((s) => s.init)
  const authReady = useAuthStore((s) => s.ready)
  const authUser = useAuthStore((s) => s.user)
  const loginWithKakao = useAuthStore((s) => s.loginWithKakao)

  useEffect(() => authInit(), [authInit])

  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get('trip')
    if (id) void openTrip(id)
  }, [openTrip])

  return (
    <>
      <LoadingOverlay />

      {!result ? (
        <div className="washi-bg min-h-screen text-fog">
          {/* 1뷰포트: 브랜드 + 헤드라인 + CTA + 풀블리드 히어로만 */}
          <section className="relative flex min-h-[100svh] flex-col justify-end overflow-hidden">
            <img
              src="/generated/hero-alley-dusk.png"
              alt=""
              className="hero-kenburns absolute inset-0 h-full w-full object-cover"
            />
            <div
              aria-hidden
              className="absolute inset-0 bg-gradient-to-t from-ink via-ink/60 to-ink/25"
            />
            <div
              aria-hidden
              className="anim-pulse pointer-events-none absolute inset-x-0 bottom-0 h-48 bg-gradient-to-t from-ember/20 to-transparent"
            />

            {authUser ? (
              <div className="absolute right-4 top-4 z-20 sm:right-6 sm:top-6">
                <AuthBar />
              </div>
            ) : null}

            <div className="relative z-10 mx-auto w-full max-w-5xl px-6 pb-16 pt-28 sm:pb-20">
              <div className="anim-rise flex items-end gap-4">
                <img
                  src="/generated/seal-tabi.png"
                  alt=""
                  className="anim-seal jp-brand-mark"
                />
                <div>
                  <p className="font-display text-sm tracking-[0.38em] text-gold">JapanTrip</p>
                  <p className="mt-1 font-display text-xs tracking-[0.3em] text-fog/60">
                    旅 · 실제 지도로 짜는 일정
                  </p>
                </div>
              </div>
              <h1 className="anim-rise mt-6 max-w-xl font-display text-4xl leading-[1.12] text-fog sm:text-5xl">
                고요한 골목부터
                <br />
                오늘의 동선까지
              </h1>
              <p className="anim-rise mt-4 max-w-md text-sm leading-relaxed text-mist/88 sm:text-base">
                Google 지도에 있는 장소만 골라 일정을 만듭니다. 없는 맛집·관광지는 만들지 않습니다.
              </p>
              <div className="anim-rise-delay mt-9 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  className={
                    authReady && !authUser
                      ? 'jp-btn jp-btn-kakao px-8 py-3.5 text-sm'
                      : 'jp-btn jp-btn-primary px-8 py-3.5 text-sm'
                  }
                  onClick={() => {
                    if (authReady && !authUser) {
                      void loginWithKakao()
                      return
                    }
                    document.getElementById('planner')?.scrollIntoView({ behavior: 'smooth' })
                  }}
                >
                  {authReady && !authUser ? '카카오로 로그인' : '일정 짜기'}
                </button>
                <a href="#saved" className="jp-btn jp-btn-secondary text-sm">
                  저장한 일정
                </a>
              </div>
            </div>
          </section>

          {/* 폼은 히어로 아래 */}
          <section id="planner" className="relative border-t border-white/10 px-6 py-14">
            <div className="mx-auto max-w-xl">
              <div className="jp-section-rule mb-8" />
              <h2 className="anim-rise font-display text-2xl tracking-wide text-fog">여행 정보</h2>
              <p className="anim-rise mt-2 text-sm text-mist/65">
                카카오 로그인 후 날짜·지역·경비를 넣으면 Places 후보 안에서만 고릅니다.
              </p>
              <div className="mt-8">
                <PlannerForm />
              </div>
              {loading ? (
                <p className="mt-6 text-sm text-mist/60">요청을 처리하는 중입니다…</p>
              ) : null}
              {error ? (
                <p className="mt-4 rounded-sm border border-ember/40 bg-ember/10 px-3 py-2 text-sm text-ember">
                  {error}
                </p>
              ) : null}

              <div id="saved" className="mt-12 border-t border-white/10 pt-8">
                <div className="jp-section-rule mb-6" />
                <h3 className="font-display text-lg tracking-wide text-fog">저장된 일정</h3>
                <p className="mt-1 text-xs text-mist/55">
                  로그인하면 내 계정 일정이, 비로그인이면 이 기기에서 연 공유 링크가 보입니다.
                </p>
                <div className="mt-4">
                  <TripsPanel />
                </div>
              </div>
            </div>
          </section>
        </div>
      ) : (
        <div className="washi-bg min-h-screen text-fog">
          <header className="border-b border-white/10 px-4 py-4 sm:px-6">
            <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
              <div className="flex min-w-0 items-start gap-3">
                <img
                  src="/generated/seal-tabi.png"
                  alt=""
                  className="mt-0.5 h-10 w-10 object-contain"
                />
                <div className="min-w-0">
                  <p className="font-display text-xl tracking-wide text-fog">
                    JapanTrip
                    <span className="ml-2 text-xs tracking-[0.2em] text-gold">旅</span>
                  </p>
                  <p className="mt-0.5 text-xs text-mist/55">
                    Google 지도 데이터 기준 · 실제 장소만
                    {result.validation.removed_items_count > 0
                      ? ` · 확인되지 않은 ${result.validation.removed_items_count}곳 제외`
                      : ''}
                  </p>
                  {result.budget_tier ? (
                    <p className="mt-0.5 text-xs text-sea-bright/90">
                      예산 티어: {budgetTierLabel(result.budget_tier)}
                      {result.budget_krw_per_person != null
                        ? ` · 1인 총경비 ${result.budget_krw_per_person.toLocaleString('ko-KR')}원`
                        : ''}
                      {result.travelers != null &&
                      result.travelers > 1 &&
                      result.budget_krw_total != null
                        ? ` · 일행 합계 ${result.budget_krw_total.toLocaleString('ko-KR')}원`
                        : ''}
                    </p>
                  ) : null}
                  {result.budget_note ? (
                    <p className="mt-0.5 max-w-xl text-xs text-mist/50">{result.budget_note}</p>
                  ) : null}
                  {result.flight_note ? (
                    <p className="mt-0.5 max-w-xl text-xs text-gold/80">{result.flight_note}</p>
                  ) : null}
                </div>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-2">
                <AuthBar />
                <button type="button" onClick={reset} className="jp-btn jp-btn-ghost">
                  다시 만들기
                </button>
              </div>
            </div>
          </header>

          <SaveBar />
          <SearchHintsBar />
          <TripControlsBar />
          <ReplanBar />
          <TripInsightsBar />

          <div className="mx-auto grid max-w-7xl gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] lg:items-start lg:gap-6 lg:p-6">
            <section className="anim-rise jp-panel jp-timeline-shell relative min-h-[420px] overflow-hidden p-4">
              <img
                src="/generated/ui-timeline-panel.png"
                alt=""
                className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-[0.09]"
              />
              <div className="relative">
                <DayTimeline days={result.days} selectedDayIndex={selectedDayIndex} />
              </div>
            </section>
            <section className="h-[min(70vh,560px)] overflow-hidden border border-white/10 lg:sticky lg:top-4 lg:h-[calc(100vh-7.5rem)] lg:min-h-[420px]">
              <ItineraryMap day={result.days[selectedDayIndex]} />
            </section>
          </div>
        </div>
      )}
    </>
  )
}
