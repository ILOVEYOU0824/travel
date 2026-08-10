import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { KakaoAuthCallback } from './components/KakaoAuthCallback.tsx'

const path = window.location.pathname.replace(/\/$/, '') || '/'
const rootEl = document.getElementById('root')!

createRoot(rootEl).render(
  <StrictMode>{path === '/auth/kakao' ? <KakaoAuthCallback /> : <App />}</StrictMode>,
)
