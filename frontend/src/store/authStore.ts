import type { Session, User } from '@supabase/supabase-js'
import { create } from 'zustand'
import {
  getSession,
  signInWithKakao,
  signOut,
  supabase,
  supabaseConfigured,
} from '../lib/supabase'

type AuthState = {
  configured: boolean
  ready: boolean
  session: Session | null
  user: User | null
  displayName: string | null
  avatarUrl: string | null
  error: string | null
  init: () => () => void
  loginWithKakao: () => Promise<void>
  logout: () => Promise<void>
}

function profileFromUser(user: User | null): { displayName: string | null; avatarUrl: string | null } {
  if (!user) return { displayName: null, avatarUrl: null }
  const meta = user.user_metadata ?? {}
  const displayName =
    (typeof meta.full_name === 'string' && meta.full_name) ||
    (typeof meta.name === 'string' && meta.name) ||
    (typeof meta.preferred_username === 'string' && meta.preferred_username) ||
    user.email ||
    null
  const avatarUrl =
    (typeof meta.avatar_url === 'string' && meta.avatar_url) ||
    (typeof meta.picture === 'string' && meta.picture) ||
    null
  return { displayName, avatarUrl }
}

export const useAuthStore = create<AuthState>((set) => ({
  configured: supabaseConfigured,
  ready: !supabaseConfigured,
  session: null,
  user: null,
  displayName: null,
  avatarUrl: null,
  error: null,

  init: () => {
    if (!supabase) {
      set({ ready: true })
      return () => undefined
    }
    let active = true
    void getSession().then((session) => {
      if (!active) return
      const user = session?.user ?? null
      set({
        ready: true,
        session,
        user,
        ...profileFromUser(user),
      })
    })
    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      const user = session?.user ?? null
      set({
        ready: true,
        session,
        user,
        error: null,
        ...profileFromUser(user),
      })
    })
    return () => {
      active = false
      data.subscription.unsubscribe()
    }
  },

  loginWithKakao: async () => {
    set({ error: null })
    try {
      await signInWithKakao()
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '카카오 로그인에 실패했습니다.',
      })
    }
  },

  logout: async () => {
    set({ error: null })
    try {
      await signOut()
      set({
        session: null,
        user: null,
        displayName: null,
        avatarUrl: null,
      })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : '로그아웃에 실패했습니다.',
      })
    }
  },
}))
