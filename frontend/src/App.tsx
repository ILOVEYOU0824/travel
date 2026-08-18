import { lazy, Suspense, useEffect } from 'react'
import { AuthBar } from './components/AuthBar'
import { JobChrome } from './components/JobChrome'
import { LoadingOverlay } from './components/LoadingOverlay'
import { PlannerForm } from './components/PlannerForm'
import { TripsPanel } from './components/TripsPanel'
import { useAuthStore } from './store/authStore'
import { usePlannerStore } from './store/plannerStore'

const ResultShell = lazy(() =>
  import('./components/ResultShell').then((m) => ({ default: m.ResultShell })),
)

function KakaoMark() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden>
      <path
        fill="currentColor"
        d="M12 4C6.7 4 2.4 7.24 2.4 11.22c0 2.52 1.66 4.74 4.18 6.05-.14.5-.88 3.14-.91 3.35 0 0-.18.15.08.28.22.11.48-.01.48-.01 1.9-1.3 2.74-1.87 3.15-2.16.85.12 1.72.19 2.62.19 5.3 0 9.6-3.24 9.6-7.22S17.3 4 12 4z"
      />
    </svg>
  )
}

export default function App() {
  const screen = usePlannerStore((s) => s.screen)
  const result = usePlannerStore((s) => s.result)
  const loading = usePlannerStore((s) => s.loading)
  const error = usePlannerStore((s) => s.error)
  const openTrip = usePlannerStore((s) => s.openTrip)
  const showResult = usePlannerStore((s) => s.showResult)
  const authInit = useAuthStore((s) => s.init)
  const authReady = useAuthStore((s) => s.ready)
  const authUser = useAuthStore((s) => s.user)
  const authError = useAuthStore((s) => s.error)
  const loginWithKakao = useAuthStore((s) => s.loginWithKakao)

  useEffect(() => authInit(), [authInit])

  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get('trip')
    if (id) void openTrip(id)
  }, [openTrip])

  const showPlan = screen === 'result' && result

  return (
    <>
      <LoadingOverlay />
      <JobChrome />

      {!showPlan ? (
        <div className="washi-bg min-h-screen text-fog">
          <section className="relative flex min-h-[100svh] flex-col overflow-hidden">
            <img
              src="/generated/hero-alley-dusk.png"
              alt=""
              className="hero-kenburns absolute inset-0 h-full w-full object-cover"
            />
            <div
              aria-hidden
              className="absolute inset-0 bg-gradient-to-t from-ink via-ink/45 to-ink/20"
            />

            <header className="relative z-20 flex items-center justify-between gap-3 px-4 py-4 sm:px-6">
              <div className="flex items-center gap-2.5">
                <img src="/generated/seal-tabi.png" alt="" className="h-8 w-8 object-contain" />
                <p className="font-display text-sm tracking-[0.28em] text-fog">JapanTrip</p>
              </div>
              <div className="flex items-center gap-2">
                {result ? (
                  <button
                    type="button"
                    onClick={() => showResult()}
                    className="jp-btn jp-btn-secondary text-xs"
                  >
                    현재 일정
                  </button>
                ) : null}
                <AuthBar />
              </div>
            </header>

            <div className="relative z-10 flex min-h-0 flex-1 flex-col items-center justify-center px-6 pb-16 text-center sm:px-10 sm:pb-20">
              <div className="max-w-xl">
                <p className="font-display text-xs tracking-[0.38em] text-gold/90">
                  旅 · 실제 지도로 이어 쓰는 일정
                </p>
                <h1 className="mt-3 font-display text-3xl leading-[1.15] text-fog sm:text-4xl">
                  설렘이 도착하는 순간,
                </h1>
                <p className="mt-2 text-sm leading-relaxed text-mist/70 sm:text-base">
                  Google 지도 속 장소만 골라 하루를 자연스럽게 연결합니다.
                </p>
              </div>

              <div className="mt-10 flex flex-wrap justify-center gap-3">
                {!authReady ? (
                  <span className="text-sm text-mist/55">확인 중…</span>
                ) : !authUser ? (
                  <button
                    type="button"
                    className="jp-btn jp-btn-kakao px-10 py-4 text-base"
                    onClick={() => void loginWithKakao()}
                  >
                    <KakaoMark />
                    카카오톡 로그인
                  </button>
                ) : (
                  <button
                    type="button"
                    className="jp-btn jp-btn-primary px-10 py-4 text-base"
                    onClick={() =>
                      document.getElementById('planner')?.scrollIntoView({ behavior: 'smooth' })
                    }
                  >
                    일정 짜기
                  </button>
                )}
                <a href="#saved" className="jp-btn jp-btn-secondary px-10 py-4 text-base">
                  저장된 일정 보기
                </a>
              </div>

              {authError ? (
                <p className="mt-4 text-xs text-ember" role="alert">
                  {authError}
                </p>
              ) : null}
            </div>
          </section>

          <section id="planner" className="relative scroll-mt-6 border-t border-white/10 px-6 py-14">
            <div className="mx-auto max-w-xl">
              <h2 className="font-display text-2xl tracking-wide text-fog">여행 정보</h2>
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

              <div id="saved" className="mt-12 scroll-mt-6 border-t border-white/10 pt-8">
                <h3 className="font-display text-lg tracking-wide text-fog">저장된 일정</h3>
                <div className="mt-4">
                  <TripsPanel />
                </div>
              </div>
            </div>
          </section>
        </div>
      ) : (
        <Suspense
          fallback={
            <div className="flex h-[100svh] items-center justify-center bg-ink text-sm text-mist/60">
              일정 화면 불러오는 중…
            </div>
          }
        >
          <ResultShell />
        </Suspense>
      )}
    </>
  )
}
