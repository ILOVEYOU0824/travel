import { useEffect, useState } from 'react'
import { JAPAN_TRAVEL_TIPS } from '../lib/japanTravelTips'
import { usePlannerStore } from '../store/plannerStore'

const FRAMES = [
  '/generated/loading-samurai-slash.png',
  '/generated/loading-bamboo-cut.png',
  '/generated/loading-torii-night.png',
  '/generated/loading-shinkansen-night.png',
  '/generated/loading-lantern-alley.png',
  '/generated/loading-fuji-dawn.png',
  '/generated/loading-momiji-temple.png',
  '/generated/loading-koi-splash.png',
  '/generated/loading-sakura-path.png',
] as const

const TIPS_GENERATE = [
  'Places에서 실제 장소만 모으는 중…',
  '후보 안에서 하루 동선을 고르는 중…',
  'Google 경로로 이동 시간을 재는 중…',
  '공항·열차·숙소 안내를 붙이는 중…',
]

const TIPS_REPLAN = [
  '요청을 읽고 일정을 다시 짜는 중…',
  '새 후보를 Places에서 찾는 중…',
  '이동 경로를 다시 계산하는 중…',
]

const TIPS_SAVE = ['일정을 안전하게 저장하는 중…', '공유 링크를 준비하는 중…']

export function LoadingOverlay() {
  const loading = usePlannerStore((s) => s.loading)
  const replanning = usePlannerStore((s) => s.replanning)
  const saving = usePlannerStore((s) => s.saving)
  const loadingStep = usePlannerStore((s) => s.loadingStep)

  const active = loading || replanning || saving
  const [frame, setFrame] = useState(0)
  const [tipIndex, setTipIndex] = useState(0)
  const [honeyTipIndex, setHoneyTipIndex] = useState(0)
  const [progress, setProgress] = useState(12)

  const tips = saving ? TIPS_SAVE : replanning ? TIPS_REPLAN : TIPS_GENERATE
  const title = saving ? '저장 중' : replanning ? '일정 다시 짜는 중' : '일정을 짜는 중'
  const subtitle = loadingStep || tips[tipIndex % tips.length]
  const showHoneyTips = loading || replanning
  const honeyTip = JAPAN_TRAVEL_TIPS[honeyTipIndex % JAPAN_TRAVEL_TIPS.length]

  useEffect(() => {
    if (!active) {
      setFrame(0)
      setTipIndex(0)
      setHoneyTipIndex(Math.floor(Math.random() * JAPAN_TRAVEL_TIPS.length))
      setProgress(12)
      return
    }
    setFrame(Math.floor(Math.random() * FRAMES.length))
    setHoneyTipIndex(Math.floor(Math.random() * JAPAN_TRAVEL_TIPS.length))
    const frameTimer = window.setInterval(() => {
      setFrame((f) => (f + 1) % FRAMES.length)
    }, 1100)
    const tipTimer = window.setInterval(() => {
      setTipIndex((i) => i + 1)
    }, 2200)
    const honeyTimer = window.setInterval(() => {
      setHoneyTipIndex((i) => i + 1)
    }, 5000)
    const progTimer = window.setInterval(() => {
      setProgress((p) => (p >= 92 ? 18 : p + 7 + Math.floor(Math.random() * 6)))
    }, 900)
    return () => {
      window.clearInterval(frameTimer)
      window.clearInterval(tipTimer)
      window.clearInterval(honeyTimer)
      window.clearInterval(progTimer)
    }
  }, [active])

  if (!active) return null

  return (
    <div className="jp-loading-root fixed inset-0 z-50 flex items-center justify-center px-6">
      <div aria-hidden className="jp-loading-veil absolute inset-0" />
      <div className="anim-rise relative z-10 w-full max-w-lg overflow-hidden border border-gold/35 bg-ink/92 shadow-[0_28px_70px_rgba(0,0,0,0.6)]">
        <div className="relative aspect-[5/4] w-full overflow-hidden bg-ink">
          {FRAMES.map((src, i) => (
            <img
              key={src}
              src={src}
              alt=""
              className={`jp-loading-frame absolute inset-0 h-full w-full object-cover ${
                i === frame ? 'jp-loading-frame-active' : ''
              }`}
            />
          ))}
          <div className="jp-loading-slash" aria-hidden />
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_35%,rgba(15,18,20,0.55)_100%)]" />
          <div className="absolute inset-x-0 bottom-0 h-28 bg-gradient-to-t from-ink via-ink/75 to-transparent" />
          <div className="absolute left-3 top-3 border border-gold/40 bg-ink/50 px-2 py-1 font-display text-[10px] tracking-[0.28em] text-gold/90 backdrop-blur-sm">
            一刀 · {String(frame + 1).padStart(2, '0')}/{String(FRAMES.length).padStart(2, '0')}
          </div>
          <img
            src="/generated/seal-tabi.png"
            alt=""
            className="anim-seal absolute bottom-3 right-3 h-14 w-14 object-contain opacity-95 drop-shadow-[0_4px_12px_rgba(0,0,0,0.55)]"
          />
        </div>

        <div className="relative px-5 py-5 text-center">
          <img
            src="/generated/ui-day-header.png"
            alt=""
            className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-[0.12]"
          />
          <div className="relative">
            {showHoneyTips ? (
              <div className="mb-4 border border-gold/25 bg-ink/55 px-3 py-2.5 text-left">
                <p className="font-display text-[10px] tracking-[0.28em] text-gold/80">旅の豆知識 · 꿀팁</p>
                <p
                  key={honeyTipIndex}
                  className="anim-rise mt-1.5 text-sm leading-relaxed text-fog/90"
                >
                  {honeyTip}
                </p>
              </div>
            ) : null}

            <p className="font-display text-[11px] tracking-[0.35em] text-gold/85">一刀 · 旅を編む</p>
            <p className="mt-2 font-display text-xl tracking-[0.14em] text-fog">{title}</p>
            <p className="mt-2 min-h-[2.5rem] text-sm leading-relaxed text-mist/75">{subtitle}</p>

            <div className="mx-auto mt-4 flex gap-1.5">
              {FRAMES.map((src, i) => (
                <span
                  key={src}
                  className={`h-1 flex-1 transition-all duration-500 ${
                    i === frame ? 'bg-gradient-to-r from-ember via-gold to-sea-bright' : 'bg-white/12'
                  }`}
                />
              ))}
            </div>
            <div className="mx-auto mt-3 h-[3px] w-full max-w-xs overflow-hidden bg-white/10">
              <div
                className="jp-loading-bar h-full bg-gradient-to-r from-ember via-gold to-sea-bright transition-[width] duration-700 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="mt-3 text-[11px] tracking-wide text-mist/45">
              장소·경로는 Google · 일정 배정만 AI
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
