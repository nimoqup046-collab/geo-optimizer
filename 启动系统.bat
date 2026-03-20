@echo off
setlocal

echo.
echo ===== GEO V1 START =====
echo.

set "PS_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
"%PS_EXE%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_system.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERROR] Start failed. Exit code: %EXIT_CODE%
  echo Check logs in data\run\*.log
  pause
  exit /b %EXIT_CODE%
)

echo.
echo [DONE] Start finished.
pause
exit /b 0
