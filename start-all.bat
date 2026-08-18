@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo JapanTrip 시작
echo   API  http://127.0.0.1:8000
echo   앱   http://127.0.0.1:5173
echo.

if not exist "backend\.venv\Scripts\python.exe" (
  echo [오류] backend\.venv 이 없습니다.
  echo backend에서 python -m venv .venv 후 pip install -r requirements.txt 를 실행하세요.
  pause
  exit /b 1
)

if not exist "frontend\package.json" (
  echo [오류] frontend 폴더를 찾을 수 없습니다.
  pause
  exit /b 1
)

echo 포트 정리 중...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='SilentlyContinue'; foreach ($port in 8000,5173) {" ^
  "  Get-NetTCPConnection -LocalPort $port -State Listen | ForEach-Object {" ^
  "    if ($_.OwningProcess) { taskkill.exe /F /PID $_.OwningProcess /T | Out-Null }" ^
  "  }" ^
  "}"

if not exist "frontend\node_modules\" (
  echo npm install 실행 중...
  pushd frontend
  call npm install
  if errorlevel 1 (
    echo [오류] npm install 실패
    popd
    pause
    exit /b 1
  )
  popd
)

echo 백엔드·프론트 창을 엽니다...
start "JapanTrip Backend" cmd /k "cd /d ""%~dp0backend"" && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
timeout /t 2 /nobreak >nul
start "JapanTrip Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev -- --host 127.0.0.1 --port 5173 --strictPort"

echo 완료. 브라우저에서 http://127.0.0.1:5173 접속
timeout /t 3 >nul
