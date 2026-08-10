import type { TravelModePref } from '../types'
import { usePlannerStore } from '../store/plannerStore'

const PREP_LINKS = [
  {
    key: 'visitjapan',
    label: 'Visit Japan',
    url: 'https://www.vjw.digital.go.jp/main/#/vjwplo001',
    className: 'jp-btn jp-btn-visit text-xs',
    title: 'Visit Japan Web 입국 수속',
  },
  {
    key: 'insurance',
    label: '여행자 보험',
    url: 'https://insurance.pay.naver.com/travel',
    className: 'jp-btn jp-btn-insurance text-xs',
    title: '네이버페이 해외여행보험 비교',
  },
] as const

const MODES: Array<{ id: TravelModePref; label: string }> = [
  { id: 'AUTO', label: '자동' },
  { id: 'WALK', label: '도보' },
  { id: 'TRANSIT', label: '대중교통' },
  { id: 'DRIVE', label: '자동차' },
]

/** 준비 CTA + 이동수단 */
export function TripControlsBar({ embedded = false }: { embedded?: boolean }) {
  const prepCtas = usePlannerStore((s) => s.result?.prep_ctas)
  const arrivalCta = usePlannerStore(
    (s) => s.result?.days[0]?.arrival_from_airport?.connectivity_cta,
  )
  const travelMode = usePlannerStore((s) => s.travelMode)
  const recomputingTravel = usePlannerStore((s) => s.recomputingTravel)
  const loadingStep = usePlannerStore((s) => s.loadingStep)
  const setTravelModeAndRecompute = usePlannerStore((s) => s.setTravelModeAndRecompute)

  const ctas = prepCtas?.length ? prepCtas : arrivalCta ? [arrivalCta] : []

  return (
    <div className={embedded ? 'px-4 py-4' : 'border-b border-white/10 px-4 py-2.5 sm:px-6'}>
      <div className={`flex flex-col gap-4 ${embedded ? '' : 'mx-auto max-w-7xl gap-2.5'}`}>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5">
          <p className="jp-legend shrink-0 text-sm">준비</p>
          {PREP_LINKS.map((link) => (
            <a
              key={link.key}
              href={link.url}
              target="_blank"
              rel="noreferrer"
              className={link.className}
              title={link.title}
            >
              {link.label}
            </a>
          ))}
          {ctas.map((cta) => (
            <a
              key={`${cta.provider}-${cta.label}`}
              href={cta.url}
              target="_blank"
              rel="noreferrer sponsored"
              className={`jp-btn text-xs ${
                cta.provider === 'kkday' ? 'jp-btn-kkday' : 'jp-btn-klook'
              }`}
              title={cta.hint}
            >
              {cta.label.replace(/^KKday에서\s*/, '').replace(/^Klook에서\s*/, '')}
            </a>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5">
          <p className="jp-legend shrink-0 text-sm">이동</p>
          <div className="flex flex-wrap gap-1">
            {MODES.map((m) => (
              <button
                key={m.id}
                type="button"
                disabled={recomputingTravel}
                onClick={() => void setTravelModeAndRecompute(m.id)}
                className={`jp-tab ${travelMode === m.id ? 'jp-tab-active' : ''}`}
              >
                {m.label}
              </button>
            ))}
          </div>
          {recomputingTravel ? (
            <p className="text-xs text-mist/60">
              <span className="mr-1.5 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-gold" />
              {loadingStep || '경로 다시 계산 중…'}
            </p>
          ) : null}
        </div>
      </div>
    </div>
  )
}
