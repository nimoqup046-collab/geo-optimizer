@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>nul

echo ===== GEO REAL DATA IMPORT =====
echo [Note] This script imports into LOCAL database used by local backend.
echo [Note] For Railway online data, please upload from 素材池 page.

cd /d "%~dp0"

set "PY=backend\.venv\Scripts\python.exe"
set "PIP=backend\.venv\Scripts\pip.exe"
set "SCRIPT=scripts\import_real_assets.py"
set "SOURCE_ROOT=D:\geo_feedback_optimizer"
set "DEBUG=False"
if not "%~1"=="" set "SOURCE_ROOT=%~1"

if not exist "%PY%" (
  echo [ERROR] Python virtual environment not found: %PY%
  echo Please run ????.bat first.
  pause
  exit /b 1
)

if not exist "%SCRIPT%" (
  echo [ERROR] Import script not found: %SCRIPT%
  pause
  exit /b 1
)

if not exist "%SOURCE_ROOT%" (
  echo [ERROR] Source root not found: %SOURCE_ROOT%
  echo You can pass a custom path:
  echo   ??????.bat "D:\your\path"
  pause
  exit /b 1
)

echo Source root: %SOURCE_ROOT%

echo Checking backend dependencies...
"%PY%" -c "import sqlalchemy, openpyxl, pypdf, docx" >nul 2>nul
if errorlevel 1 (
  echo Installing missing dependencies from backend\requirements.txt ...
  "%PIP%" install -r backend\requirements.txt
  if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
  )
)

echo [1/2] Dry run preview...
"%PY%" "%SCRIPT%" --source-root "%SOURCE_ROOT%" --dry-run --max-count 20
if errorlevel 1 (
  echo [ERROR] Dry run failed.
  pause
  exit /b 1
)

echo [2/2] Importing core 20 files...
"%PY%" "%SCRIPT%" --source-root "%SOURCE_ROOT%" --max-count 20
if errorlevel 1 (
  echo [ERROR] Import failed.
  pause
  exit /b 1
)

echo [OK] Import completed.
echo Report: data\reports\import-report-latest.json
pause
