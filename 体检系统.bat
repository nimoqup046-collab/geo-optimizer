@echo off
setlocal

echo.
echo ===== GEO V1 DOCTOR =====
echo.

set "PY_EXE="
if exist "%~dp0backend\.venv\Scripts\python.exe" set "PY_EXE=%~dp0backend\.venv\Scripts\python.exe"
if "%PY_EXE%"=="" for /f "usebackq delims=" %%i in (`py -3.13 -c "import sys;print(sys.executable)" 2^>nul`) do set "PY_EXE=%%i"
if "%PY_EXE%"=="" if exist "C:\Python313\python.exe" set "PY_EXE=C:\Python313\python.exe"
if "%PY_EXE%"=="" set "PY_EXE=python"

"%PY_EXE%" "%~dp0scripts\doctor.py"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
  echo [PASS] Doctor passed. See data\reports\doctor-report-latest.json
) else (
  echo [FAIL] Doctor failed. See data\reports\doctor-report-latest.json
)
pause
exit /b %EXIT_CODE%

