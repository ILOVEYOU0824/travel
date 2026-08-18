# -*- coding: utf-8 -*-
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

FONT = Path(r"C:\Windows\Fonts\malgun.ttf")
FONTB = Path(r"C:\Windows\Fonts\malgunbd.ttf")
OUT = Path(__file__).resolve().parent / "구현_포인터_실행 가이드 문서.pdf"
OUT_ALT = Path(__file__).resolve().parent / "구현_포인터_실행가이드.pdf"


class PDF(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_x(self.l_margin)
        self.set_font("Malgun", size=8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 8, str(self.page_no()), align="C")


def main() -> None:
    pdf = PDF(format="A4")
    pdf.set_margins(18, 12, 18)
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_font("Malgun", "", str(FONT))
    pdf.add_font("Malgun", "B", str(FONTB if FONTB.exists() else FONT))
    pdf.add_page()

    def write(text: str, *, bold: bool = False, size: float = 10, h: float = 5.2) -> None:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Malgun", "B" if bold else "", size)
        pdf.set_text_color(20, 20, 20)
        pdf.multi_cell(pdf.epw, h, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def h1(text: str) -> None:
        pdf.ln(1.5)
        write(text, bold=True, size=11, h=5.8)

    def b(text: str) -> None:
        write(f"- {text}", size=9.5, h=5.0)

    write("JapanTrip AI 실행 가이드", bold=True, size=14, h=7)
    write("팀명: 포인터(Pointer)  |  주제: Google 지도 연동 일본 여행 AI 플래너", size=9.5, h=5)

    h1("1. 개요")
    write(
        "날짜·지역 입력 → Google Places 장소만으로 일정 생성. 이동시간은 Directions API, "
        "일정 배정은 Claude(후보 place_id 선택) 사용.",
        size=9.5,
        h=5.0,
    )

    h1("2. 소스 코드")
    write("https://github.com/ILOVEYOU0824/travel", bold=True, size=9.5, h=5)
    b("Frontend: frontend/ (React, TypeScript, Vite)")
    b("Backend: backend/ (Python, FastAPI)")
    b("제출 전 Public 전환")

    h1("3. 배포 URL")
    b("FE: https://traveljapango.netlify.app")
    b("BE: https://travel-nz1w.onrender.com")

    h1("4. 실행 환경")
    b("Windows 10/11, Python 3.11+, Node.js 20+")
    b("키: Google Maps, Anthropic, Kakao, Supabase (없으면 MOCK 모드)")

    h1("5. 로컬 실행")
    write("클론", bold=True, size=9.5, h=5)
    b("git clone https://github.com/ILOVEYOU0824/travel.git && cd travel")
    write("백엔드", bold=True, size=9.5, h=5)
    b("cd backend → python -m venv .venv → .venv\\Scripts\\activate")
    b("pip install -r requirements.txt")
    b(".env.example → .env 복사")
    b("MOCK: USE_MOCK_PLACES=true, USE_MOCK_ROUTES=true, USE_MOCK_LLM=true")
    b("uvicorn app.main:app --reload --host 127.0.0.1 --port 8000")
    write("프론트엔드", bold=True, size=9.5, h=5)
    b("cd frontend → npm install")
    b(".env.example → .env 복사 (로컬은 VITE_API_BASE_URL 비움)")
    b("npm run dev → http://127.0.0.1:5173")
    b("또는 루트 start-all.bat")

    h1("6. 환경 변수")
    write("backend/.env", bold=True, size=9.5, h=5)
    b("GOOGLE_MAPS_API_KEY, ANTHROPIC_API_KEY")
    b("USE_MOCK_PLACES, USE_MOCK_ROUTES, USE_MOCK_LLM")
    b("KAKAO_REST_API_KEY, KAKAO_CLIENT_SECRET")
    b("SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET")
    b("PUBLIC_FRONTEND_URL, CORS_ORIGINS")
    write("frontend/.env", bold=True, size=9.5, h=5)
    b("VITE_GOOGLE_MAPS_API_KEY, VITE_API_BASE_URL")
    b("VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY")
    b("VITE_KAKAO_JS_KEY, VITE_KAKAO_REST_API_KEY")
    b("SERVICE_ROLE / CLIENT_SECRET은 frontend에 넣지 않음")

    h1("7. 시연")
    b("접속 → 카카오 로그인 → 일정 생성 → 일정/지도/리플랜/저장 확인")
    b("API: POST /api/v1/itinerary/generate , POST /api/v1/itinerary/replan")
    b("로컬 docs: http://127.0.0.1:8000/docs")

    try:
        pdf.output(str(OUT))
        target = OUT
    except PermissionError:
        pdf.output(str(OUT_ALT))
        target = OUT_ALT
    print(target)
    print("pages check next")


if __name__ == "__main__":
    main()
