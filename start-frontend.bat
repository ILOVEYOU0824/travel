@echo off
chcp 65001 >nul
cd /d "%~dp0frontend"

if not exist "package.json" (
  echo [오류] frontend 폴더를 찾을 수 없습니다.
  pause
  exit /b 1
)

if not exist "node_modules\" (
  echo node_modules 없음 — npm install 실행 중...
  call npm install
  if errorlevel 1 (
    echo [오류] npm install 실패
    pause
    exit /b 1
  )
)

echo 포트 5173 정리 중...
call "%~dp0free-port.bat" 5173
if errorlevel 1 (
  echo [오류] 포트 5173을 비울 수 없습니다. 해당 프로그램을 종료한 뒤 다시 시도하세요.
  pause
  exit /b 1
)

echo JapanTrip 앱 시작: http://127.0.0.1:5173
echo 종료하려면 이 창에서 Ctrl+C
echo.
call npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
pause
