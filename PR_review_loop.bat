@echo off
chcp 65001 >nul
setlocal
set ROOT=%~dp0
cd /d "%ROOT%"

set PR_NUM=%1
if "%PR_NUM%"=="" (
  echo Usage: PR_review_loop.bat ^<PR_NUMBER^>
  pause
  exit /b 1
)

echo ===== PR Review Loop =====
python scripts\pr_review_loop.py --pr %PR_NUM%
set CODE=%ERRORLEVEL%
if not "%CODE%"=="0" (
  echo [ERROR] PR review loop failed. Exit code: %CODE%
) else (
  echo [OK] PR review loop completed.
)
pause
exit /b %CODE%
