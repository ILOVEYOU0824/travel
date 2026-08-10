import type { Place } from '../../types'

export function SwapPanel({
  loading,
  message,
  suggestions,
  onPick,
}: {
  loading: boolean
  message: string | null
  suggestions: Place[]
  onPick: (p: Place) => void
}) {
  return (
    <div className="border-t border-gold/25 bg-ink/50 px-4 py-3">
      <p className="text-[11px] tracking-wide text-gold">근처 · 같은 종류 후보 (Places)</p>
      {loading ? <p className="mt-2 text-xs text-mist/60">찾는 중…</p> : null}
      {message ? <p className="mt-2 text-xs text-mist/55">{message}</p> : null}
      <ul className="mt-2 flex flex-col gap-2">
        {suggestions.map((p) => (
          <li key={p.place_id}>
            <button
              type="button"
              className="w-full border border-white/10 bg-ink-soft/80 px-3 py-2 text-left hover:border-gold/40"
              onClick={() => onPick(p)}
            >
              <p className="font-display text-sm text-fog">{p.name}</p>
              <p className="mt-0.5 text-[11px] text-mist/55">
                {p.rating != null ? `★ ${p.rating.toFixed(1)}` : '평점 —'}
                {p.formatted_address ? ` · ${p.formatted_address}` : ''}
              </p>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
