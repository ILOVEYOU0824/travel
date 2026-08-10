# 카카오 로그인 + Supabase 설정 (사용자용)

코드는 환경 변수만 채우면 동작합니다. 아래를 순서대로 하세요.

## 1. Supabase

1. https://supabase.com 프로젝트 생성
2. **Project Settings → API** 에서 복사:
   - Project URL → `SUPABASE_URL` / `VITE_SUPABASE_URL`
   - `anon` `public` → `SUPABASE_ANON_KEY` / `VITE_SUPABASE_ANON_KEY`
   - `service_role` → `SUPABASE_SERVICE_ROLE_KEY` (backend만)
   - JWT Secret → `SUPABASE_JWT_SECRET`
3. **SQL Editor**에서 `supabase/migrations/001_trips.sql` 전체 실행
4. **Authentication → Providers → Kakao** Enable
5. **Authentication → URL Configuration**
   - Site URL: `http://localhost:5173`
   - Redirect URLs: `http://localhost:5173/**`

## 2. 카카오 개발자

1. https://developers.kakao.com 앱 생성
2. 키:
   - REST API 키 → Supabase Kakao **Client ID**
   - Client Secret 생성·활성화 → Supabase Kakao **Secret**
   - JavaScript 키 → `VITE_KAKAO_JS_KEY`
3. 카카오 로그인 ON
4. Redirect URI:
   - `https://<PROJECT_REF>.supabase.co/auth/v1/callback`
5. 플랫폼 / JavaScript 키
   - **JavaScript 키** → `VITE_KAKAO_JS_KEY` (REST 키와 다름)
   - [앱] → [플랫폼 키] → [JavaScript 키] → **JavaScript SDK 도메인**에 등록:
     - `http://127.0.0.1:5173`
     - `http://localhost:5173`
     - (배포 시) `https://실제도메인`
6. 카카오톡 공유 (Error 4019 방지)
   - 제품 설정에서 **카카오톡 공유** 사용 ON
   - [앱] → [제품 링크 관리] → **웹 도메인**에 위와 동일하게 등록
     (`127.0.0.1`과 `localhost`는 서로 다른 도메인 — 둘 다 넣기)
   - 브라우저 주소창 host와 등록 값이 정확히 같아야 함 (포트 포함)

## 3. .env

`backend/.env` · `frontend/.env` 에 위 값 입력 후 서버·Vite 재시작.
