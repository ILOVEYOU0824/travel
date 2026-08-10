import { useAuthStore } from '../store/authStore'

export function AuthBar() {
  const configured = useAuthStore((s) => s.configured)
  const ready = useAuthStore((s) => s.ready)
  const user = useAuthStore((s) => s.user)
  const displayName = useAuthStore((s) => s.displayName)
  const avatarUrl = useAuthStore((s) => s.avatarUrl)
  const error = useAuthStore((s) => s.error)
  const logout = useAuthStore((s) => s.logout)

  // 비로그인 UI는 히어로 CTA만 사용 — 우측 상단 로그인 버튼 없음
  if (!configured || !ready || !user) {
    return null
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {avatarUrl ? (
        <img
          src={avatarUrl}
          alt=""
          className="h-7 w-7 rounded-full border border-white/15 object-cover"
        />
      ) : null}
      <span className="max-w-[10rem] truncate text-xs text-mist/80">
        {displayName || '카카오 사용자'}
      </span>
      <button type="button" onClick={() => void logout()} className="jp-btn jp-btn-ghost text-xs">
        로그아웃
      </button>
      {error ? <p className="w-full text-[11px] text-ember">{error}</p> : null}
    </div>
  )
}
