import { useEffect, useRef, useState } from 'react'
import { completeKakaoLogin } from '../lib/supabase'

/** /auth/kakao?code=... → id_token 교환 후 홈으로 */
export function KakaoAuthCallback() {
  const [message, setMessage] = useState('카카오 로그인 처리 중…')
  const started = useRef(false)

  useEffect(() => {
    // React Strict Mode 이중 mount / 인가코드 1회성 → 중복 exchange 방지
    if (started.current) return
    started.current = true

    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const err = params.get('error')
    const errDesc = params.get('error_description')
    if (err) {
      setMessage(errDesc || err)
      return
    }
    if (!code) {
      setMessage('인가 코드가 없습니다.')
      return
    }

    const consumeKey = `kakao_code_${code}`
    if (sessionStorage.getItem(consumeKey)) {
      setMessage('이미 처리된 로그인입니다. 홈으로 이동합니다…')
      window.location.replace('/')
      return
    }
    sessionStorage.setItem(consumeKey, '1')

    void completeKakaoLogin(code)
      .then(() => {
        window.location.replace('/')
      })
      .catch((e: unknown) => {
        sessionStorage.removeItem(consumeKey)
        setMessage(e instanceof Error ? e.message : '로그인에 실패했습니다.')
      })
  }, [])

  return (
    <div className="washi-bg flex min-h-screen items-center justify-center px-6 text-fog">
      <p className="max-w-md text-center text-sm text-mist/85">{message}</p>
    </div>
  )
}
