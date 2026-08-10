@echo off
chcp 65001 >nul
cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
  echo [오류] backend\.venv 이 없습니다. 먼저 가상환경을 만들어 주세요.
  pause
  exit /b 1
)

echo 포트 8000 정리 중...
call "%~dp0free-port.bat" 8000
if errorlevel 1 (
  echo [오류] 포트 8000을 비울 수 없습니다. 해당 프로그램을 종료한 뒤 다시 시도하세요.
  pause
  exit /b 1
)

echo JapanTrip API 시작: http://127.0.0.1:8000
echo 종료하려면 이 창에서 Ctrl+C
echo.
".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pause
