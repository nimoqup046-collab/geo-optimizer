$ErrorActionPreference = "Stop"

. "$PSScriptRoot\runtime_env.ps1"
Set-GeoRuntimeEnvironment

$Root = Split-Path -Parent $PSScriptRoot
$RunDir = Join-Path $Root "data\run"

function Stop-ByPidFile([string]$Name, [string]$PidFilePath) {
  if (-not (Test-Path $PidFilePath)) {
    Write-Host "${Name}: PID file not found. Skip."
    return
  }

  $pidValue = (Get-Content -Raw $PidFilePath).Trim()
  if (-not $pidValue) {
    Remove-Item -Force $PidFilePath -ErrorAction SilentlyContinue
    Write-Host "${Name}: PID file is empty and has been removed."
    return
  }

  $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
  if ($proc) {
    Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
    Write-Host "$Name stopped. PID=$pidValue"
  } else {
    Write-Host "$Name process not found. PID=$pidValue"
  }

  Remove-Item -Force $PidFilePath -ErrorAction SilentlyContinue
}

Write-Host "===== GEO V1 STOP FLOW ====="
Stop-ByPidFile -Name "Backend" -PidFilePath (Join-Path $RunDir "backend.pid")
Stop-ByPidFile -Name "Frontend" -PidFilePath (Join-Path $RunDir "frontend.pid")
Write-Host "Stop flow finished."
