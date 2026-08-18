# JapanTrip AI

날짜·지역을 입력하면 **Google Places에 있는 장소만**으로 일본 여행 일정을 만드는 웹 서비스입니다.  
이동시간은 Directions API로 계산하고, Claude는 후보 `place_id` 선택·일자 배정·자연어 리플랜만 담당합니다.

- Frontend: https://traveljapango.netlify.app  
- Backend API: https://travel-nz1w.onrender.com  
- Repository: https://github.com/ILOVEYOU0824/travel  

## 핵심 원칙

1. 장소 데이터는 Google Places API만 사용 (임의 생성 금지)  
2. 이동시간·거리는 Directions / Distance Matrix만 사용  
3. LLM 응답은 Structured Output + 서버 `place_id` 검증 후만 사용  
4. 검색 실패 시 임의 장소 생성 없이 안내  

## 스택

| 구분 | 기술 |
|------|------|
| Frontend | React, TypeScript, Vite, Zustand, Tailwind CSS |
| Backend | Python FastAPI, Pydantic |
| Maps | Google Places (New), Directions, Maps JS |
| LLM | Claude API (Anthropic) |
| Auth / DB | 카카오 로그인, Supabase |
| Cache | Redis (없으면 메모리 TTL) |
| Deploy | Netlify (FE), Render (BE) |

## 폴더 구조

```
travel/
├── frontend/          # React 앱
├── backend/           # FastAPI
├── supabase/          # trips 마이그레이션
├── docs/              # 실행 가이드 PDF 등
└── start-all.bat      # 로컬 한 번에 실행 (Windows)
```

## 로컬 실행

### 사전 준비

- Python 3.11+
- Node.js 20+
- (선택) Google Maps / Anthropic / Kakao / Supabase 키  
  키가 없으면 MOCK 모드로 UI·흐름 확인 가능

### 1) 환경 변수

```bash
# backend
copy backend\.env.example backend\.env

# frontend
copy frontend\.env.example frontend\.env
```

`backend/.env` 빠른 확인용:

```env
USE_MOCK_PLACES=true
USE_MOCK_ROUTES=true
USE_MOCK_LLM=true
```

실연동 시 MOCK을 `false`로 두고 API 키를 채웁니다.

### 2) 백엔드 가상환경 (최초 1회)

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 3) 실행

**Windows:** 프로젝트 루트에서 `start-all.bat` 실행  

또는 수동:

```bash
# terminal 1 — backend
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# terminal 2 — frontend
cd frontend
npm install
npm run dev
```

- 앱: http://127.0.0.1:5173  
- API docs: http://127.0.0.1:8000/docs  

로컬 frontend는 `VITE_API_BASE_URL`을 비워 두면 Vite `/api` 프록시를 사용합니다.

## 주요 API

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/itinerary/generate` | 일정 생성 |
| POST | `/api/v1/itinerary/replan` | 자연어 리플랜 |
| GET/POST | `/api/v1/trips` | 일정 저장·목록 |
| POST | `/api/v1/auth/kakao/exchange` | 카카오 토큰 교환 |

## 파이프라인

```
입력 → Places 후보 수집 → Claude 선택·배정 → place_id 검증
    → hydrate + Directions → 프론트(타임라인·지도)
```

리플랜도 동일합니다. intent 파싱 → (필요 시) Places 재검색 → 검증 → 경로 재계산.

## 기능 요약

- 일자별 일정 생성·지도 표시  
- 자연어 리플랜, 순서/장소 편집  
- 카카오 로그인 후 일정 저장·공유·PDF  
- 준비 CTA, 준비물 체크리스트  
- 날씨·예산 등 여행 참고 정보  

## 환경 변수 참고

- Backend: `backend/.env.example`  
- Frontend: `frontend/.env.example`  

`SUPABASE_SERVICE_ROLE_KEY`, `KAKAO_CLIENT_SECRET` 등은 **frontend에 넣지 마세요.**

## 라이선스 / 비고

학습·학술제 구현용 프로젝트입니다. Google / Anthropic / Kakao 등 외부 API 이용 약관을 준수하세요.
