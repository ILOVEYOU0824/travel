import { usePlannerStore } from '../store/plannerStore'

export function SearchHintsBar({ compact = false }: { compact?: boolean }) {
  const hints = usePlannerStore((s) => s.result?.search_hints)
  const visible = (hints ?? []).filter((h) => h.status !== 'matched')
  if (!visible.length) return null

  return (
    <div
      className={`shrink-0 border-b border-amber-400/25 bg-amber-950/25 px-3 ${compact ? 'py-2' : 'px-4 py-3 sm:px-6'}`}
    >
      <div className={compact ? 'flex flex-col gap-1' : 'mx-auto flex max-w-7xl flex-col gap-2'}>
        <p className="jp-legend text-sm text-amber-100/90">검색 안내</p>
        <ul className={`flex flex-col gap-1.5 text-mist/85 ${compact ? 'text-xs' : 'gap-2 text-sm'}`}>
          {visible.map((h) => (
            <li key={`${h.kind}-${h.region}-${h.query}`} className="leading-relaxed">
              <p>{h.message}</p>
              {h.suggestions.length > 0 ? (
                <p className="mt-0.5 text-[11px] text-mist/55">
                  Places 후보: {h.suggestions.map((s) => s.name).join(' · ')}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
