import { useEffect, useState } from 'react'
import { deleteTrip, listTrips } from '../api/itinerary'
import type { TripSummary } from '../types'
import { useAuthStore } from '../store/authStore'
import { usePlannerStore } from '../store/plannerStore'

const LOCAL_TRIPS_KEY = 'japantrip_saved_ids'

function rememberedIds(): string[] {
  try {
    const raw = localStorage.getItem(LOCAL_TRIPS_KEY)
    return raw ? (JSON.parse(raw) as string[]) : []
  } catch {
    return []
  }
}

function forgetId(id: string) {
  try {
    const next = rememberedIds().filter((x) => x !== id)
    localStorage.setItem(LOCAL_TRIPS_KEY, JSON.stringify(next))
  } catch {
    /* ignore */
  }
}

export function TripsPanel() {
  const openTrip = usePlannerStore((s) => s.openTrip)
  const user = useAuthStore((s) => s.user)
  const authReady = useAuthStore((s) => s.ready)
  const replanning = usePlannerStore((s) => s.replanning)
  const [trips, setTrips] = useState<TripSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function refresh() {
    setLoading(true)
    setError(null)
    try {
      const all = await listTrips()
      if (user) {
        setTrips(all)
      } else {
        const mine = new Set(rememberedIds())
        const filtered = all.filter((t) => mine.has(t.id))
        setTrips(filtered.length ? filtered : all.slice(0, 5))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '목록을 불러오지 못했습니다.')
      setTrips([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!authReady) return
    void refresh()
  }, [authReady, user?.id])

  async function onDelete(id: string) {
    if (!window.confirm('이 공유 일정을 삭제할까요?')) return
    try {
      await deleteTrip(id)
      forgetId(id)
      setTrips((prev) => prev.filter((t) => t.id !== id))
    } catch (err) {
      setError(err instanceof Error ? err.message : '삭제에 실패했습니다.')
    }
  }

  if (!authReady || loading) {
    return <p className="text-xs text-mist/50">저장된 일정을 불러오는 중…</p>
  }

  if (error) {
    return <p className="text-xs text-ember/90">{error}</p>
  }

  if (!trips.length) {
    return (
      <p className="text-xs text-mist/45">
        {user
          ? '아직 저장된 일정이 없습니다. 일정을 만들고 저장해 보세요.'
          : '아직 저장된 일정이 없습니다. 로그인하면 계정별 목록이 보여요.'}
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      {replanning ? (
        <p className="text-xs text-gold/80">일정 수정이 끝난 뒤 다른 저장본을 열 수 있습니다.</p>
      ) : null}
      <ul className="flex flex-col gap-2">
      {trips.map((t) => (
        <li
          key={t.id}
          className="jp-panel flex flex-wrap items-center justify-between gap-2 !py-2.5"
        >
          <button
            type="button"
            disabled={replanning}
            onClick={() => {
              if (replanning) return
              void openTrip(t.id)
            }}
            className="min-w-0 flex-1 text-left text-sm text-fog hover:text-gold disabled:opacity-50"
          >
            <span className="block truncate font-medium">{t.title}</span>
            <span className="block text-[11px] text-mist/45">
              {(t.updated_at || t.created_at || '').slice(0, 10)}
            </span>
          </button>
          <button
            type="button"
            onClick={() => void onDelete(t.id)}
            className="jp-btn jp-btn-ghost text-xs"
          >
            삭제
          </button>
        </li>
      ))}
      </ul>
    </div>
  )
}
