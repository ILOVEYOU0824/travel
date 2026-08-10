import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // OG 공유 미리보기 (크롤러 HTML / 브라우저 → SPA 리다이렉트)
      '/share': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
