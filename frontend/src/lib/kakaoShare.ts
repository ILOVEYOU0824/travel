declare global {
  interface Window {
    Kakao?: {
      isInitialized: () => boolean
      init: (key: string) => void
      Share: {
        sendDefault: (settings: Record<string, unknown>) => void
      }
    }
  }
}

const JS_KEY = (import.meta.env.VITE_KAKAO_JS_KEY as string | undefined)?.trim() ?? ''

let scriptPromise: Promise<void> | null = null

function loadKakaoSdk(): Promise<void> {
  if (typeof window === 'undefined') return Promise.resolve()
  if (window.Kakao?.isInitialized()) return Promise.resolve()
  if (scriptPromise) return scriptPromise

  scriptPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>('script[data-kakao-sdk]')
    if (existing) {
      existing.addEventListener('load', () => resolve())
      existing.addEventListener('error', () => reject(new Error('카카오 SDK 로드 실패')))
      return
    }
    const script = document.createElement('script')
    script.src = 'https://t1.kakaocdn.net/kakao_js_sdk/2.7.4/kakao.min.js'
    script.async = true
    script.dataset.kakaoSdk = '1'
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('카카오 SDK 로드 실패'))
    document.head.appendChild(script)
  })
  return scriptPromise
}

export function kakaoShareConfigured(): boolean {
  return Boolean(JS_KEY)
}

export async function shareTripToKakao(payload: {
  title: string
  description: string
  shareUrl: string
  imageUrl?: string
}): Promise<void> {
  if (!JS_KEY) {
    throw new Error('VITE_KAKAO_JS_KEY가 없습니다. frontend/.env를 확인하세요.')
  }
  await loadKakaoSdk()
  const Kakao = window.Kakao
  if (!Kakao) throw new Error('카카오 SDK를 불러오지 못했습니다.')
  if (!Kakao.isInitialized()) Kakao.init(JS_KEY)

  const imageUrl =
    payload.imageUrl || `${window.location.origin}/generated/hero-alley-dusk.png`

  Kakao.Share.sendDefault({
    objectType: 'feed',
    content: {
      title: payload.title,
      description: payload.description,
      imageUrl,
      link: {
        mobileWebUrl: payload.shareUrl,
        webUrl: payload.shareUrl,
      },
    },
    buttons: [
      {
        title: '일정 보기',
        link: {
          mobileWebUrl: payload.shareUrl,
          webUrl: payload.shareUrl,
        },
      },
    ],
  })
}
