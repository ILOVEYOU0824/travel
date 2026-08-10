# JapanTrip AI

일본 여행 일정 AI 플래너. **장소 데이터는 Google Places API만 사용**하고, LLM은 후보 중 선택·정렬·자연어 intent 파싱만 담당한다.

상세 규칙은 `.cursor/rules/`를 따른다.

## 개발 단계

1. Google Places API 연동
2. Directions / Distance Matrix
3. LLM 일정 생성 + place_id 검증
4. 프론트 지도 + 일정 UI
5. 자연어 리플래닝
6. Agoda 딥링크
7. Redis 캐시, 에러 핸들링, 인증(선택)

## 현재 진행

- **1~5단계 + 마무리 완료**: Places / Routes / Claude / UI / 리플랜 / 캐시 / 일정 저장
- **Agoda 딥링크**: MVP 제외 — 예약은 사용자 직접
- 캐시: Redis 있으면 사용, 없으면 메모리 TTL 폴백
- 일정 저장: 로그인 없이 UUID 링크 (`/?trip=...`)

## 로컬 실행

```bash
# backend
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --reload

# frontend
cd frontend
npm run dev
```

- 앱: http://127.0.0.1:5173
- 일정 생성: `POST /api/v1/itinerary/generate`
- 자연어 재조정: `POST /api/v1/itinerary/replan`


## 환경 변수

`backend/.env.example` 참고. 기본은 `USE_MOCK_PLACES=true`.
