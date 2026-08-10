# Render + Netlify 배포 체크리스트

## 순서

1. GitHub에 코드 push
2. **Render**에 백엔드 배포
3. **Netlify**에 프론트 배포
4. 카카오·Supabase·Google 콘솔에 도메인 등록
5. 일정 저장 → 카톡 공유 → 폰에서 열어 확인

## 1) Render (backend)

- Root / Build: `backend` 폴더
- Start 예: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment (필수):

```
APP_ENV=production
USE_MOCK_PLACES=false
USE_MOCK_ROUTES=false
USE_MOCK_LLM=false
GOOGLE_MAPS_API_KEY=...
ANTHROPIC_API_KEY=...
PUBLIC_FRONTEND_URL=https://(넷플리파이도메인)
CORS_ORIGINS=https://(넷플리파이도메인),http://localhost:5173,http://127.0.0.1:5173
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_JWT_SECRET=...
KAKAO_REST_API_KEY=...
KAKAO_CLIENT_SECRET=...
```

배포 후 URL 예: `https://japantrip-api.onrender.com` → `/health` 200 확인.

## 2) Netlify (frontend)

- Base directory: `frontend`
- Build: `npm run build`
- Publish: `dist`
- Environment:

```
VITE_API_BASE_URL=https://(렌더백엔드도메인)
VITE_GOOGLE_MAPS_API_KEY=...
VITE_SUPABASE_URL=...
VITE_SUPABASE_ANON_KEY=...
VITE_KAKAO_JS_KEY=...
VITE_KAKAO_REST_API_KEY=...
```

## 3) 콘솔 등록

### 카카오 Developers
- JavaScript SDK 도메인: `https://(넷플리파이)`
- 제품 링크 관리 웹 도메인:
  - `https://(넷플리파이)`
  - `https://(렌더)` ← 공유 링크가 `/share`로 Render를 씀

### Supabase
- Site URL: Netlify URL
- Redirect URLs: `https://(넷플리파이)/**`, `https://(넷플리파이)/auth/kakao`

### Google Cloud (Maps)
- Maps JS / Places 등 API 키 제한에 Netlify HTTP referrer 추가

## 4) 확인
1. Netlify에서 카카오 로그인
2. 일정 생성·저장
3. 카톡 공유 → 폰에서 링크 열기 → 일정 화면
