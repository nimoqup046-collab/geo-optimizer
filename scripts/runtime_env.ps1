$ErrorActionPreference = "Stop"

Set-StrictMode -Version Latest

function Set-GeoRuntimeEnvironment {
  $defaults = @{
    SystemRoot = "C:\Windows"
    windir     = "C:\Windows"
    ComSpec    = "C:\Windows\System32\cmd.exe"
    PATHEXT    = ".COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC;.CPL"
  }

  foreach ($kv in $defaults.GetEnumerator()) {
    $envPath = "Env:{0}" -f $kv.Key
    $item = Get-Item -Path $envPath -ErrorAction SilentlyContinue
    $currentValue = if ($null -ne $item) { $item.Value } else { "" }
    if (-not $currentValue -or $kv.Key -eq "PATHEXT") {
      Set-Item -Path $envPath -Value $kv.Value
    }
  }

  if (-not (Test-Path $env:ComSpec)) {
    $env:ComSpec = "C:\Windows\System32\cmd.exe"
  }

  if (-not $env:PATHEXT -or $env:PATHEXT -notmatch "(^|;)\.EXE($|;)") {
    $env:PATHEXT = $defaults["PATHEXT"]
  }
}

function Join-GeoArgumentLine {
  param([string[]]$Arguments = @())

  $safeArgs = @($Arguments | Where-Object { $_ -ne $null })
  if ($safeArgs.Count -eq 0) {
    return ""
  }

  $encoded = foreach ($arg in $safeArgs) {
    if ($arg -match '[\s"]') {
      '"' + ($arg -replace '"', '\"') + '"'
    } else {
      $arg
    }
  }
  return ($encoded -join " ")
}

function Get-GeoExecutableFromPath {
  param([Parameter(Mandatory = $true)][string]$FileName)

  foreach ($entry in ($env:Path -split ";")) {
    if (-not $entry) {
      continue
    }
    $candidate = Join-Path $entry $FileName
    if (Test-Path $candidate) {
      return $candidate
    }
  }
  return $null
}

function Resolve-GeoPythonExe {
  param([string]$ProjectRoot = "")

  if ($ProjectRoot) {
    $venv = Join-Path $ProjectRoot "backend\.venv\Scripts\python.exe"
    if (Test-Path $venv) {
      return $venv
    }
  }

  $pyLauncher = Join-Path $env:SystemRoot "py.exe"
  if (Test-Path $pyLauncher) {
    try {
      $process = Invoke-GeoExternal -StepName "resolve python via py launcher" -FilePath $pyLauncher -Arguments @("-3.13", "-c", "import sys;print(sys.executable)") -IgnoreExitCode
      if ($process.ExitCode -eq 0) {
        $path = ($process.StdOut.Trim())
        if ($path -and (Test-Path $path)) {
          return $path
        }
      }
    } catch {}
  }

  if (Test-Path "C:\Python313\python.exe") {
    return "C:\Python313\python.exe"
  }

  $pythonFromPath = Get-GeoExecutableFromPath -FileName "python.exe"
  if ($pythonFromPath) {
    return $pythonFromPath
  }

  throw "Python executable not found. Checked backend/.venv, py launcher, C:\Python313, PATH."
}

function Resolve-GeoNpmCmd {
  if ($env:NVM_SYMLINK) {
    $nvmNpm = Join-Path $env:NVM_SYMLINK "npm.cmd"
    if (Test-Path $nvmNpm) {
      return $nvmNpm
    }
  }

  if (Test-Path "C:\nvm4w\nodejs\npm.cmd") {
    return "C:\nvm4w\nodejs\npm.cmd"
  }

  $npmFromPath = Get-GeoExecutableFromPath -FileName "npm.cmd"
  if ($npmFromPath) {
    return $npmFromPath
  }

  throw "npm.cmd not found. Checked NVM_SYMLINK, C:\nvm4w\nodejs, PATH."
}

function Resolve-GeoNodeExe {
  if ($env:NVM_SYMLINK) {
    $nvmNode = Join-Path $env:NVM_SYMLINK "node.exe"
    if (Test-Path $nvmNode) {
      return $nvmNode
    }
  }

  if (Test-Path "C:\nvm4w\nodejs\node.exe") {
    return "C:\nvm4w\nodejs\node.exe"
  }

  $nodeFromPath = Get-GeoExecutableFromPath -FileName "node.exe"
  if ($nodeFromPath) {
    return $nodeFromPath
  }

  throw "node.exe not found. Checked NVM_SYMLINK, C:\nvm4w\nodejs, PATH."
}

function Resolve-GeoGitExe {
  $candidates = @(
    "C:\Program Files\Git\cmd\git.exe",
    "C:\Program Files\Git\bin\git.exe"
  )
  foreach ($candidate in $candidates) {
    if (Test-Path $candidate) {
      return $candidate
    }
  }

  $gitFromPath = Get-GeoExecutableFromPath -FileName "git.exe"
  if ($gitFromPath) {
    return $gitFromPath
  }

  throw "git.exe not found. Checked Program Files and PATH."
}

function Invoke-GeoExternal {
  param(
    [Parameter(Mandatory = $true)][string]$StepName,
    [Parameter(Mandatory = $true)][string]$FilePath,
    [string[]]$Arguments = @(),
    [string]$WorkingDirectory = "",
    [int]$TimeoutSeconds = 1800,
    [switch]$IgnoreExitCode
  )

  if (-not (Test-Path $FilePath)) {
    throw "[$StepName] executable not found: $FilePath"
  }

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.UseShellExecute = $false
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.CreateNoWindow = $true
  if ($WorkingDirectory) {
    $psi.WorkingDirectory = $WorkingDirectory
  }

  $argLine = Join-GeoArgumentLine -Arguments $Arguments
  $ext = [System.IO.Path]::GetExtension($FilePath).ToLowerInvariant()
  if ($ext -eq ".cmd" -or $ext -eq ".bat") {
    $cmdExe = if ($env:ComSpec -and (Test-Path $env:ComSpec)) { $env:ComSpec } else { "C:\Windows\System32\cmd.exe" }
    $psi.FileName = $cmdExe
    $quotedFile = '"' + $FilePath + '"'
    $psi.Arguments = "/d /c $quotedFile $argLine"
    $renderedCommand = "$cmdExe /d /c $quotedFile $argLine"
  } else {
    $psi.FileName = $FilePath
    $psi.Arguments = $argLine
    $renderedCommand = "$FilePath $argLine"
  }

  $process = [System.Diagnostics.Process]::Start($psi)
  $stdoutTask = $process.StandardOutput.ReadToEndAsync()
  $stderrTask = $process.StandardError.ReadToEndAsync()
  $completed = $process.WaitForExit($TimeoutSeconds * 1000)
  if (-not $completed) {
    try { $process.Kill() } catch {}
    throw "[$StepName] timeout after $TimeoutSeconds seconds. command=$renderedCommand"
  }
  [System.Threading.Tasks.Task]::WaitAll(@($stdoutTask, $stderrTask), 5000) | Out-Null
  $stdOut = $stdoutTask.Result
  $stdErr = $stderrTask.Result
  $exitCode = $process.ExitCode

  if (-not $IgnoreExitCode -and $exitCode -ne 0) {
    $stderrTail = ($stdErr -split "`r?`n" | Where-Object { $_ } | Select-Object -Last 8) -join " | "
    if (-not $stderrTail) {
      $stderrTail = ($stdOut -split "`r?`n" | Where-Object { $_ } | Select-Object -Last 8) -join " | "
    }
    throw "[$StepName] failed. exit=$exitCode command=$renderedCommand stderr_tail=$stderrTail"
  }

  return [pscustomobject]@{
    ExitCode = $exitCode
    StdOut   = $stdOut
    StdErr   = $stdErr
    Command  = $renderedCommand
  }
}

function Get-GeoRuntimeSnapshot {
  return [ordered]@{
    SystemRoot = $env:SystemRoot
    windir     = $env:windir
    ComSpec    = $env:ComSpec
    PATHEXT    = $env:PATHEXT
  }
}
