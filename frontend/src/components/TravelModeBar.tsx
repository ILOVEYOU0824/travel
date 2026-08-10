import type { TravelModePref } from '../types'
import { usePlannerStore } from '../store/plannerStore'

const MODES: Array<{ id: TravelModePref; label: string }> = [
  { id: 'AUTO', label: '자동' },
  { id: 'WALK', label: '도보' },
  { id: 'TRANSIT', label: '대중교통' },
  { id: 'DRIVE', label: '자동차' },
]

export function TravelModeBar() {
  const travelMode = usePlannerStore((s) => s.travelMode)
  const recomputingTravel = usePlannerStore((s) => s.recomputingTravel)
  const loadingStep = usePlannerStore((s) => s.loadingStep)
  const setTravelModeAndRecompute = usePlannerStore((s) => s.setTravelModeAndRecompute)

  return (
    <div className="border-b border-white/10 px-4 py-2 sm:px-6">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-2">
        <p className="jp-legend shrink-0 text-sm">이동</p>
        <div className="flex flex-wrap gap-1.5">
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
          <p className="text-xs text-mist/65 sm:ml-2">
            <span className="mr-1.5 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-gold" />
            {loadingStep || '경로 다시 계산 중…'}
          </p>
        ) : null}
      </div>
    </div>
  )
}
