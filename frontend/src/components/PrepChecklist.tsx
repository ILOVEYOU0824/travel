import { useEffect, useMemo, useState } from 'react'
import {
  PREP_CHECKLIST,
  PREP_CHECKLIST_STORAGE_KEY,
  allPrepItemIds,
} from '../data/prepChecklist'
import { useAuthStore } from '../store/authStore'

type CheckedMap = Record<string, boolean>

function storageKey(userId: string | null): string {
  return `${PREP_CHECKLIST_STORAGE_KEY}:${userId ?? 'anon'}`
}

function loadChecked(userId: string | null): CheckedMap {
  try {
    const raw = localStorage.getItem(storageKey(userId))
    if (!raw) return {}
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object') return {}
    return parsed as CheckedMap
  } catch {
    return {}
  }
}

function saveChecked(userId: string | null, next: CheckedMap) {
  try {
    localStorage.setItem(storageKey(userId), JSON.stringify(next))
  } catch {
    /* quota / private mode */
  }
}

export function PrepChecklist() {
  const userId = useAuthStore((s) => s.user?.id ?? null)
  const [checked, setChecked] = useState<CheckedMap>(() => loadChecked(userId))

  useEffect(() => {
    setChecked(loadChecked(userId))
  }, [userId])

  const ids = useMemo(() => allPrepItemIds(), [])
  const done = ids.filter((id) => checked[id]).length
  const total = ids.length

  function toggle(id: string) {
    setChecked((prev) => {
      const next = { ...prev, [id]: !prev[id] }
      saveChecked(userId, next)
      return next
    })
  }

  return (
    <div className="border-t border-white/10 px-4 py-4">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="jp-legend text-sm">준비물 체크리스트</p>
          <p className="mt-1 text-[11px] text-mist/45">체크하면 이 기기·계정에 자동 저장됩니다.</p>
        </div>
        <p className="text-[11px] tabular-nums text-mist/55">
          {done}/{total}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {PREP_CHECKLIST.map((cat) => (
          <div key={cat.id} className="min-w-0">
            <p className="mb-2 border-b border-white/10 pb-1.5 text-xs font-medium tracking-wide text-fog">
              {cat.title}
            </p>
            <ul className="space-y-1">
              {cat.items.map((item) => {
                const on = Boolean(checked[item.id])
                return (
                  <li key={item.id}>
                    <label
                      className={`flex cursor-pointer items-start gap-2.5 rounded-md px-2 py-1.5 transition-colors ${
                        on ? 'bg-white/[0.06] text-fog' : 'text-mist/80 hover:bg-white/[0.04]'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={on}
                        onChange={() => toggle(item.id)}
                        className="mt-0.5 h-3.5 w-3.5 shrink-0 rounded border-white/30 bg-ink accent-gold"
                      />
                      <span
                        className={`text-xs leading-snug ${on ? 'text-mist/50 line-through' : ''}`}
                      >
                        {item.label}
                      </span>
                    </label>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </div>
    </div>
  )
}
