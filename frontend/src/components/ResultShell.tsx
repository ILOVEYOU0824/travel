import { lazy, Suspense, useState } from 'react'
import { budgetTierLabel } from '../lib/format'
import { usePlannerStore } from '../store/plannerStore'
import { AuthBar } from './AuthBar'
import { DayTimeline } from './DayTimeline'
import { ReplanBar } from './ReplanBar'
import { SaveBar } from './SaveBar'
import { SearchHintsBar } from './SearchHintsBar'
import { PrepChecklist } from './PrepChecklist'
import { TripControlsBar } from './TripControlsBar'
import { TripInsightsBar } from './TripInsightsBar'

const ItineraryMap = lazy(() =>
  import('./ItineraryMap').then((m) => ({ default: m.ItineraryMap })),
)

type ResultTab = 'itinerary' | 'map' | 'prepare' | 'edit' | 'info'

const TABS: Array<{ id: ResultTab; label: string; short: string }> = [
  { id: 'itinerary', label: '일정·이동', short: '일정' },
  { id: 'map', label: '지도(크게)', short: '지도' },
  { id: 'prepare', label: '저장·준비', short: '준비' },
  { id: 'edit', label: '일정 수정', short: '수정' },
  { id: 'info', label: '여행 참고', short: '참고' },
]

/** 결과 화면: 텍스트 일정·이동이 주, 지도는 보조 */
export function ResultShell() {
  const result = usePlannerStore((s) => s.result)
  const selectedDayIndex = usePlannerStore((s) => s.selectedDayIndex)
  const reset = usePlannerStore((s) => s.reset)
  const [tab, setTab] = useState<ResultTab>('itinerary')

  if (!result) return null

  const day = result.days[selectedDayIndex]

  return (
    <div className="washi-bg flex h-[100svh] flex-col overflow-hidden text-fog">
      <header className="shrink-0 border-b border-white/10 px-3 py-2.5 sm:px-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2.5">
            <img src="/generated/seal-tabi.png" alt="" className="h-8 w-8 shrink-0 object-contain" />
            <div className="min-w-0">
              <p className="font-display text-base tracking-wide text-fog sm:text-lg">
                JapanTrip
                <span className="ml-1.5 text-[10px] tracking-[0.2em] text-gold">旅</span>
              </p>
              <p className="truncate text-[11px] text-mist/55">
                {result.budget_tier ? `${budgetTierLabel(result.budget_tier)} · ` : ''}
                Google 지도 실제 장소만
                {result.validation.removed_items_count > 0
                  ? ` · ${result.validation.removed_items_count}곳 제외`
                  : ''}
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <AuthBar />
            <button type="button" onClick={reset} className="jp-btn jp-btn-ghost text-xs">
              다시 만들기
            </button>
          </div>
        </div>
      </header>

      <SearchHintsBar compact />

      <div className="flex min-h-0 flex-1">
        {/* 데스크톱 사이드 탭 */}
        <nav
          aria-label="결과 메뉴"
          className="hidden w-28 shrink-0 flex-col gap-1 border-r border-white/10 bg-ink/40 p-2 lg:flex"
        >
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`rounded-sm px-2 py-2.5 text-left text-xs tracking-wide transition ${
                tab === t.id
                  ? 'bg-ember/25 text-fog ring-1 ring-gold/40'
                  : 'text-mist/70 hover:bg-white/5 hover:text-fog'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          {/* 모바일 상단 탭 */}
          <div className="flex shrink-0 gap-1 overflow-x-auto border-b border-white/10 px-2 py-1.5 lg:hidden">
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={`jp-tab shrink-0 ${tab === t.id ? 'jp-tab-active' : ''}`}
              >
                {t.short}
              </button>
            ))}
          </div>

          {/* 일정: 텍스트만 전체 폭 — 지도는 「지도」 탭 (길쭉한 옆 지도 제거) */}
          {tab === 'itinerary' ? (
            <section className="relative min-h-0 flex-1 overflow-y-auto overscroll-contain p-3 sm:p-5">
              <img
                src="/generated/ui-timeline-panel.png"
                alt=""
                className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-[0.07]"
              />
              <div className="relative mx-auto max-w-3xl">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <p className="text-xs text-mist/55">
                    이동·노선은 아래 텍스트 요약을 보세요. 지도가 필요하면 「지도」 탭으로.
                  </p>
                  <button
                    type="button"
                    className="jp-btn jp-btn-secondary text-xs"
                    onClick={() => setTab('map')}
                  >
                    지도 보기
                  </button>
                </div>
                <DayTimeline days={result.days} selectedDayIndex={selectedDayIndex} />
              </div>
            </section>
          ) : null}

          {tab === 'map' ? (
            <section className="flex min-h-0 flex-1 flex-col overflow-hidden">
              <div className="flex shrink-0 items-center justify-between gap-2 border-b border-white/10 px-3 py-2">
                <p className="text-xs text-mist/60">
                  위치·동선 확인용입니다. 노선·시간은 「일정·이동」 탭 텍스트를 보세요.
                </p>
                <button
                  type="button"
                  className="jp-btn jp-btn-ghost text-xs"
                  onClick={() => setTab('itinerary')}
                >
                  일정으로
                </button>
              </div>
              <div className="min-h-0 flex-1">
                <Suspense
                  fallback={
                    <div className="flex h-full min-h-[240px] items-center justify-center bg-ink-soft text-sm text-mist/60">
                      지도 불러오는 중…
                    </div>
                  }
                >
                  <ItineraryMap day={day} />
                </Suspense>
              </div>
            </section>
          ) : null}

          {tab === 'prepare' ? (
            <section className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
              <SaveBar embedded />
              <TripControlsBar embedded />
              {(result.budget_note || result.flight_note) && (
                <div className="space-y-1 border-t border-white/10 px-4 py-3 text-xs text-mist/60">
                  {result.budget_note ? <p>{result.budget_note}</p> : null}
                  {result.flight_note ? <p className="text-gold/80">{result.flight_note}</p> : null}
                </div>
              )}
              <PrepChecklist />
            </section>
          ) : null}

          {tab === 'edit' ? (
            <section className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
              <ReplanBar embedded />
            </section>
          ) : null}

          {tab === 'info' ? (
            <section className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
              <TripInsightsBar embedded />
            </section>
          ) : null}
        </div>
      </div>
    </div>
  )
}
