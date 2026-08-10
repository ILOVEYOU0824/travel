@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo JapanTrip 서버를 두 창에서 시작합니다.
echo   API  http://127.0.0.1:8000
echo   앱   http://127.0.0.1:5173
echo.
echo 기존 서버가 있으면 포트를 비운 뒤 다시 시작합니다...
call "%~dp0free-port.bat" 8000
call "%~dp0free-port.bat" 5173
echo.

start "JapanTrip Backend" cmd /k "%~dp0start-backend.bat"
timeout /t 2 /nobreak >nul
start "JapanTrip Frontend" cmd /k "%~dp0start-frontend.bat"

echo 백엔드·프론트 창이 열렸습니다. 이 창은 닫아도 됩니다.
timeout /t 3 >nul
