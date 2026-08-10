import { createClient, type Session, type SupabaseClient } from '@supabase/supabase-js'

const url = (import.meta.env.VITE_SUPABASE_URL as string | undefined)?.trim() ?? ''
const anon = (import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined)?.trim() ?? ''
const kakaoRestKey =
  (import.meta.env.VITE_KAKAO_REST_API_KEY as string | undefined)?.trim() ?? ''

export const supabaseConfigured = Boolean(url && anon)

export const supabase: SupabaseClient | null = supabaseConfigured
  ? createClient(url, anon, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : null

export async function getAccessToken(): Promise<string | null> {
  if (!supabase) return null
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}

export async function getSession(): Promise<Session | null> {
  if (!supabase) return null
  const { data } = await supabase.auth.getSession()
  return data.session
}

/**
 * 카카오 OIDC authorize URL — account_email 미포함 (KOE205 회피).
 * prompt=login: 브라우저 카카오 세션이 있어도 계정 로그인 화면을 다시 띄움.
 * @see https://developers.kakao.com/docs/latest/ko/kakaologin/rest-api#request-code-request-query
 */
export function kakaoAuthorizeUrl(): string {
  if (!kakaoRestKey) {
    throw new Error('VITE_KAKAO_REST_API_KEY가 없습니다. frontend/.env를 확인하세요.')
  }
  const redirectUri = `${window.location.origin}/auth/kakao`
  const params = new URLSearchParams({
    client_id: kakaoRestKey,
    redirect_uri: redirectUri,
    response_type: 'code',
    // email 제외 — 개인 앱 권한 없음
    scope: 'openid profile_nickname profile_image',
    // 로그아웃 후 재로그인 시 이전 계정으로 자동 승인되지 않게
    prompt: 'login',
  })
  return `https://kauth.kakao.com/oauth/authorize?${params.toString()}`
}

export async function signInWithKakao(): Promise<void> {
  if (!supabase) {
    throw new Error('Supabase가 설정되지 않았습니다. frontend/.env를 확인하세요.')
  }
  window.location.assign(kakaoAuthorizeUrl())
}

export async function completeKakaoLogin(code: string): Promise<void> {
  if (!supabase) {
    throw new Error('Supabase가 설정되지 않았습니다.')
  }
  const redirectUri = `${window.location.origin}/auth/kakao`
  const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
  const res = await fetch(`${API_BASE}/api/v1/auth/kakao/exchange`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, redirect_uri: redirectUri }),
  })
  if (!res.ok) {
    let detail = `카카오 로그인 실패 (${res.status})`
    try {
      const body = (await res.json()) as { detail?: string }
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  const data = (await res.json()) as { id_token: string }
  const { error } = await supabase.auth.signInWithIdToken({
    provider: 'kakao',
    token: data.id_token,
  })
  if (error) throw error
}

export async function signOut(): Promise<void> {
  if (!supabase) return
  const { error } = await supabase.auth.signOut()
  if (error) throw error
}
