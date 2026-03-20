@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"
set "PY313=C:\Python313\python.exe"
set "CODE_REPO=D:\my-projects\geo-optimizer"
set "DATA_REPO=D:\geo_feedback_optimizer"

echo ===== INSTALL MAIN PUSH GUARD =====
echo Code repo: %CODE_REPO%
echo Data repo: %DATA_REPO%

if exist "%PY313%" (
  "%PY313%" "%ROOT%scripts\install_main_guard_hook.py" --repo "%CODE_REPO%" --repo "%DATA_REPO%"
) else (
  py -3 "%ROOT%scripts\install_main_guard_hook.py" --repo "%CODE_REPO%" --repo "%DATA_REPO%"
)

if errorlevel 1 (
  echo [ERROR] Install hook failed.
  pause
  exit /b 1
)

echo [OK] main push guard installed for both repos.
pause
exit /b 0
