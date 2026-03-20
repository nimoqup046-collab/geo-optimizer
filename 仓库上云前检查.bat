@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"
set "PY313=C:\Python313\python.exe"

echo ===== REPO PREFLIGHT CHECK =====
echo Root: %ROOT%

if exist "%PY313%" (
  "%PY313%" "%ROOT%scripts\repo_preflight.py"
) else (
  py -3 "%ROOT%scripts\repo_preflight.py"
)

if errorlevel 1 (
  echo [ERROR] Repo preflight failed. See data\reports\repo-preflight-latest.json
  pause
  exit /b 1
)

echo [OK] Repo preflight passed.
pause
exit /b 0
