@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo JapanTrip 서버를 종료합니다 (8000, 5173)...
call "%~dp0free-port.bat" 8000
call "%~dp0free-port.bat" 5173
echo 종료 완료.
