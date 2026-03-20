$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$RunDir = Join-Path $Root "data\run"
New-Item -ItemType Directory -Path (Join-Path $Root "data\uploads") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Root "data\exports") -Force | Out-Null
New-Item -ItemType Directory -Path $RunDir -Force | Out-Null

function Assert-LastExitCode([string]$StepName) {
  if ($null -eq $LASTEXITCODE) {
    if (-not $?) {
      throw "$StepName failed without exit code."
    }
    return
  }

  if ($LASTEXITCODE -ne 0) {
    throw "$StepName failed with exit code $LASTEXITCODE"
  }
}

function Invoke-External {
  param(
    [Parameter(Mandatory = $true)][string]$StepName,
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(Mandatory = $false)][string[]]$Arguments = @()
  )

  & $FilePath @Arguments
  Assert-LastExitCode -StepName $StepName
}

function Resolve-PythonExe {
  try {
    $pyPath = (& py -3.13 -c "import sys; print(sys.executable)" 2>$null).Trim()
    if ($pyPath -and (Test-Path $pyPath)) {
      return $pyPath
    }
  } catch {}

  if (Test-Path "C:\Python313\python.exe") {
    return "C:\Python313\python.exe"
  }

  $cmd = Get-Command python -ErrorAction SilentlyContinue
  if ($cmd) {
    return $cmd.Source
  }

  throw "Python not found. Install Python 3.13 or add it to PATH."
}

function Resolve-NpmCmd {
  if ($env:NVM_SYMLINK) {
    $nvmNpm = Join-Path $env:NVM_SYMLINK "npm.cmd"
    if (Test-Path $nvmNpm) {
      return $nvmNpm
    }
  }

  if (Test-Path "C:\nvm4w\nodejs\npm.cmd") {
    return "C:\nvm4w\nodejs\npm.cmd"
  }

  $cmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
  if ($cmd) {
    return $cmd.Source
  }

  throw "npm not found. Install Node.js and npm."
}

function Ensure-ProcessStopped([string]$PidFilePath) {
  if (-not (Test-Path $PidFilePath)) {
    return
  }

  $pidValue = (Get-Content -Raw $PidFilePath).Trim()
  if (-not $pidValue) {
    Remove-Item -Force $PidFilePath -ErrorAction SilentlyContinue
    return
  }

  $process = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
  if ($process) {
    Write-Host "Found existing process PID=$pidValue. Stopping..."
    Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
  }

  Remove-Item -Force $PidFilePath -ErrorAction SilentlyContinue
}

function Start-ManagedProcess(
  [string]$Name,
  [string]$FilePath,
  [string[]]$ProcessArgs,
  [string]$WorkingDir,
  [string]$PidFilePath,
  [string]$StdOutPath,
  [string]$StdErrPath
) {
  if (-not $ProcessArgs -or $ProcessArgs.Count -eq 0) {
    throw "$Name process arguments are empty."
  }

  Ensure-ProcessStopped -PidFilePath $PidFilePath
  $proc = Start-Process `
    -FilePath $FilePath `
    -ArgumentList $ProcessArgs `
    -WorkingDirectory $WorkingDir `
    -PassThru `
    -WindowStyle Normal `
    -RedirectStandardOutput $StdOutPath `
    -RedirectStandardError $StdErrPath
  Set-Content -Path $PidFilePath -Value $proc.Id -NoNewline
  Write-Host "$Name started. PID=$($proc.Id)"
}

Write-Host "===== GEO V1 START FLOW ====="

$pythonExe = Resolve-PythonExe
$npmCmd = Resolve-NpmCmd
$venvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"

Write-Host "Python: $pythonExe"
Write-Host "npm:    $npmCmd"

if (-not (Test-Path $venvPython)) {
  Write-Host "Creating backend/.venv ..."
  Invoke-External -StepName "create venv" -FilePath $pythonExe -Arguments @("-m", "venv", (Join-Path $BackendDir ".venv"))
}

if (-not (Test-Path $venvPython)) {
  throw "venv python not found after creation: $venvPython"
}

if (-not (Test-Path (Join-Path $BackendDir ".env"))) {
  Write-Host "Creating backend/.env from .env.example ..."
  Copy-Item -Path (Join-Path $BackendDir ".env.example") -Destination (Join-Path $BackendDir ".env")
}

Write-Host "Installing backend dependencies..."
Invoke-External -StepName "upgrade pip" -FilePath $venvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip")
Invoke-External -StepName "install backend requirements" -FilePath $venvPython -Arguments @("-m", "pip", "install", "-r", (Join-Path $BackendDir "requirements.txt"))
Invoke-External -StepName "verify backend dependencies" -FilePath $venvPython -Arguments @("-c", "import fastapi,uvicorn,sqlalchemy")

Write-Host "Installing frontend dependencies..."
Invoke-External -StepName "install frontend dependencies" -FilePath $npmCmd -Arguments @("--prefix", $FrontendDir, "install")

$backendPidFile = Join-Path $RunDir "backend.pid"
$frontendPidFile = Join-Path $RunDir "frontend.pid"
$backendOut = Join-Path $RunDir "backend.out.log"
$backendErr = Join-Path $RunDir "backend.err.log"
$frontendOut = Join-Path $RunDir "frontend.out.log"
$frontendErr = Join-Path $RunDir "frontend.err.log"

Write-Host "Starting backend service..."
Start-ManagedProcess `
  -Name "Backend" `
  -FilePath $venvPython `
  -ProcessArgs @("main.py") `
  -WorkingDir $BackendDir `
  -PidFilePath $backendPidFile `
  -StdOutPath $backendOut `
  -StdErrPath $backendErr

Start-Sleep -Seconds 3

Write-Host "Starting frontend service..."
Start-ManagedProcess `
  -Name "Frontend" `
  -FilePath $npmCmd `
  -ProcessArgs @("--prefix", $FrontendDir, "run", "dev") `
  -WorkingDir $FrontendDir `
  -PidFilePath $frontendPidFile `
  -StdOutPath $frontendOut `
  -StdErrPath $frontendErr

Write-Host ""
Write-Host "Service URLs:"
Write-Host "  Backend:  http://localhost:8000"
Write-Host "  Frontend: http://localhost:5173"
Write-Host "  Docs:     http://localhost:8000/docs"
Write-Host ""
Write-Host "PID files:"
Write-Host "  $backendPidFile"
Write-Host "  $frontendPidFile"
