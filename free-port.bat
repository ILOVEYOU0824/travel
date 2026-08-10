@echo off
REM Usage: free-port.bat 5173
REM Kills whatever is LISTENing on the given TCP port (process tree).
setlocal
set "PORT=%~1"
if "%PORT%"=="" (
  echo [오류] 포트 번호가 필요합니다. 예: free-port.bat 5173
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='SilentlyContinue';" ^
  "$conns = Get-NetTCPConnection -LocalPort %PORT% -State Listen;" ^
  "if (-not $conns) { exit 0 };" ^
  "foreach ($c in @($conns)) {" ^
  "  $procId = $c.OwningProcess;" ^
  "  if ($procId -and $procId -ne 0) {" ^
  "    & taskkill.exe /F /PID $procId /T | Out-Null;" ^
  "  }" ^
  "};" ^
  "Start-Sleep -Milliseconds 500;" ^
  "if (Get-NetTCPConnection -LocalPort %PORT% -State Listen) { exit 1 } else { exit 0 }"

exit /b %ERRORLEVEL%
