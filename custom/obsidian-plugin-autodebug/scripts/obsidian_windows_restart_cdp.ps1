#Requires -Version 5.1

param(
  [Parameter(Mandatory = $true)]
  [string]$AppPath,

  [int]$Port = 9222,
  [int]$WaitSeconds = 20,
  [string]$VaultUri = "",
  [int]$CloseWaitMs = 4000,
  [int]$ForceKillWaitMs = 2000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $AppPath)) {
  throw "Obsidian app executable not found: $AppPath"
}

function Wait-ForNoProcess {
  param(
    [string]$Name,
    [int]$TimeoutMs
  )

  $deadline = (Get-Date).AddMilliseconds($TimeoutMs)
  do {
    $remaining = Get-Process -Name $Name -ErrorAction SilentlyContinue
    if (-not $remaining) {
      return $true
    }
    Start-Sleep -Milliseconds 200
  } while ((Get-Date) -lt $deadline)

  return -not (Get-Process -Name $Name -ErrorAction SilentlyContinue)
}

function Test-CdpReady {
  param(
    [int]$ProbePort
  )

  try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:$ProbePort/json/list" -TimeoutSec 2 -UseBasicParsing
    return $response.StatusCode -ge 200 -and $response.StatusCode -lt 300
  } catch {
    return $false
  }
}

$processName = [System.IO.Path]::GetFileNameWithoutExtension($AppPath)
$existing = Get-Process -Name $processName -ErrorAction SilentlyContinue
if ($existing) {
  foreach ($proc in $existing) {
    try {
      if ($proc.MainWindowHandle -ne 0) {
        $null = $proc.CloseMainWindow()
      }
    } catch {
    }
  }

  if (-not (Wait-ForNoProcess -Name $processName -TimeoutMs $CloseWaitMs)) {
    Get-Process -Name $processName -ErrorAction SilentlyContinue | Stop-Process -Force
    if (-not (Wait-ForNoProcess -Name $processName -TimeoutMs $ForceKillWaitMs)) {
      throw "Timed out waiting for $processName to exit before restart."
    }
  }
}

Start-Sleep -Milliseconds 500
Start-Process -FilePath $AppPath -ArgumentList "--remote-debugging-port=$Port"

if ($VaultUri.Trim().Length -gt 0) {
  Start-Sleep -Seconds 1
  Start-Process $VaultUri | Out-Null
}

for ($index = 0; $index -lt $WaitSeconds; $index += 1) {
  if (Test-CdpReady -ProbePort $Port) {
    Write-Output "CDP ready on port $Port"
    exit 0
  }
  Start-Sleep -Seconds 1
}

throw "Timed out waiting for Obsidian CDP on port $Port"
