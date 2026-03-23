@echo off
chcp 65001 >nul
setlocal
set ROOT=%~dp0
cd /d "%ROOT%"

echo ===== PR Runtime Check =====
python scripts\pr_runtime_check.py
set CODE=%ERRORLEVEL%
if not "%CODE%"=="0" (
  echo [ERROR] PR runtime check failed. Exit code: %CODE%
) else (
  echo [OK] PR runtime check passed.
)
pause
exit /b %CODE%
