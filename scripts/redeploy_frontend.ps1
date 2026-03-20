[CmdletBinding()]
param(
  [switch]$SkipInstall,
  [switch]$SkipDeploy,
  [switch]$PurgeTempLogs,
  [string]$RailwayService = "geo-frontend"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $Root "frontend"

function Invoke-External {
  param(
    [Parameter(Mandatory = $true)][string]$StepName,
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(Mandatory = $false)][string[]]$Arguments = @(),
    [Parameter(Mandatory = $false)][string]$WorkingDirectory = ""
  )

  $startInfo = @{
    FilePath     = $FilePath
    ArgumentList = $Arguments
    NoNewWindow  = $true
    Wait         = $true
    PassThru     = $true
  }
  if ($WorkingDirectory) {
    $startInfo.WorkingDirectory = $WorkingDirectory
  }

  $proc = Start-Process @startInfo

  if ($proc.ExitCode -ne 0) {
    throw "$StepName failed with exit code $($proc.ExitCode)"
  }
}

function Resolve-NpmCmd {
  if ($env:NVM_SYMLINK) {
    $nvmNpm = Join-Path $env:NVM_SYMLINK "npm.cmd"
    if (Test-Path $nvmNpm) {
      return $nvmNpm
    }
  }

  $nvmDefault = "C:\nvm4w\nodejs\npm.cmd"
  if (Test-Path $nvmDefault) {
    return $nvmDefault
  }

  $cmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
  if ($cmd) {
    return $cmd.Source
  }

  throw "npm.cmd not found. Install Node.js and npm before redeploy."
}

function Resolve-NodeExe([string]$NpmCmdPath) {
  $candidate = Join-Path (Split-Path -Parent $NpmCmdPath) "node.exe"
  if (Test-Path $candidate) {
    return $candidate
  }

  $cmd = Get-Command node.exe -ErrorAction SilentlyContinue
  if ($cmd) {
    return $cmd.Source
  }

  throw "node.exe not found. Install Node.js before redeploy."
}

function Remove-IfExists([string]$Path) {
  if (Test-Path $Path) {
    Remove-Item -Path $Path -Recurse -Force
    Write-Host "[clean] removed $Path"
  }
}

if (-not (Test-Path (Join-Path $FrontendDir "package.json"))) {
  throw "frontend/package.json not found: $FrontendDir"
}

$npmCmd = Resolve-NpmCmd
$nodeDir = Split-Path -Parent $npmCmd
$nodeExe = Resolve-NodeExe -NpmCmdPath $npmCmd
$npmCli = Join-Path $nodeDir "node_modules\npm\bin\npm-cli.js"
if (-not (Test-Path $npmCli)) {
  throw "npm-cli.js not found: $npmCli"
}

Write-Host "===== FRONTEND REDEPLOY ====="
Write-Host "npm: $npmCmd"
Write-Host "node: $nodeExe"
Write-Host "frontend: $FrontendDir"

Write-Host ""
Write-Host "[1/4] Cleaning previous build artifacts..."
Remove-IfExists (Join-Path $FrontendDir "dist")
Remove-IfExists (Join-Path $FrontendDir ".vite")
Remove-IfExists (Join-Path $FrontendDir "node_modules\.vite")

if ($PurgeTempLogs) {
  Write-Host "[clean] Purging temporary logs and local probes..."
  Remove-IfExists (Join-Path $FrontendDir "build.log")
  Remove-IfExists (Join-Path $FrontendDir "install.log")
  Remove-IfExists (Join-Path $FrontendDir "install_dev.log")
  Remove-IfExists (Join-Path $FrontendDir "pw_install.log")
  Remove-IfExists (Join-Path $FrontendDir "pw_install_browser.log")
  Remove-IfExists (Join-Path $FrontendDir "tmp_live_check.js")
}

if (-not $SkipInstall) {
  Write-Host ""
  Write-Host "[2/4] Installing dependencies..."
  if (Test-Path (Join-Path $FrontendDir "package-lock.json")) {
    Invoke-External `
      -StepName "npm ci" `
      -FilePath $nodeExe `
      -Arguments @($npmCli, "--prefix", $FrontendDir, "ci") `
      -WorkingDirectory $FrontendDir
  } else {
    Invoke-External `
      -StepName "npm install" `
      -FilePath $nodeExe `
      -Arguments @($npmCli, "--prefix", $FrontendDir, "install") `
      -WorkingDirectory $FrontendDir
  }
} else {
  Write-Host ""
  Write-Host "[2/4] Skipped dependency installation."
}

Write-Host ""
Write-Host "[3/4] Building frontend..."
$viteCli = Join-Path $FrontendDir "node_modules\vite\bin\vite.js"
if (-not (Test-Path $viteCli)) {
  throw "vite cli not found. Run redeploy without -SkipInstall first. Missing: $viteCli"
}
Invoke-External `
  -StepName "vite build" `
  -FilePath $nodeExe `
  -Arguments @($viteCli, "build") `
  -WorkingDirectory $FrontendDir

$distIndex = Join-Path $FrontendDir "dist\index.html"
if (-not (Test-Path $distIndex)) {
  throw "Build output verification failed: $distIndex not found."
}
Write-Host "[ok] Build output verified: $distIndex"

if (-not $SkipDeploy) {
  Write-Host ""
  Write-Host "[4/4] Deploying to Railway service '$RailwayService'..."
  $railway = Get-Command railway -ErrorAction SilentlyContinue
  if (-not $railway) {
    throw "Railway CLI not found. Install Railway CLI or run with -SkipDeploy."
  }

  Push-Location $Root
  try {
    Invoke-External `
      -StepName "railway up --service $RailwayService" `
      -FilePath $railway.Source `
      -Arguments @("up", "--service", $RailwayService)
  } finally {
    Pop-Location
  }
} else {
  Write-Host ""
  Write-Host "[4/4] Skipped Railway deploy."
}

Write-Host ""
Write-Host "Frontend redeploy flow completed."
