[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('plan', 'code')]
    [string]$Mode,
    [string]$PlanPath = '',
    [string]$OutputPath = '',
    [string]$Focus = '',
    [int]$PollSeconds = 0,
    [int]$TimeoutSeconds = 0
)

$ErrorActionPreference = 'Stop'

function Resolve-DefaultValue {
    param(
        [string]$ExplicitValue,
        [string]$EnvName,
        [string]$FallbackValue
    )

    if ($ExplicitValue) { return $ExplicitValue }
    $envValue = [Environment]::GetEnvironmentVariable($EnvName)
    if ($envValue) { return $envValue }
    return $FallbackValue
}

$PollSeconds = [int](Resolve-DefaultValue -ExplicitValue "$PollSeconds" -EnvName 'AUTOPILOT_REVIEW_POLL_SECONDS' -FallbackValue '60')
$TimeoutSeconds = [int](Resolve-DefaultValue -ExplicitValue "$TimeoutSeconds" -EnvName 'AUTOPILOT_REVIEW_TIMEOUT_SECONDS' -FallbackValue '1800')

$opencodeCommand = Get-Command opencode -ErrorAction SilentlyContinue
if (-not $opencodeCommand) {
    throw 'opencode not found in PATH'
}

if ($Mode -eq 'plan') {
    if (-not $PlanPath) {
        throw 'Plan mode requires -PlanPath'
    }
    if (-not $OutputPath) {
        $OutputPath = [System.IO.Path]::ChangeExtension($PlanPath, '.review.txt')
    }
    $prompt = "/review-plan $PlanPath"
}
else {
    if (-not $OutputPath) {
        $OutputPath = 'automation/runtime/review-code.txt'
    }
    if ($Focus) {
        $prompt = "/review-code $Focus"
    }
    else {
        $prompt = '/review-code'
    }
}

$outputDirectory = Split-Path -Parent $OutputPath
if ($outputDirectory) {
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
}

$tempOutputPath = "$OutputPath.tmp"
$tempErrorPath = "$OutputPath.stderr.tmp"
New-Item -ItemType File -Force -Path $tempOutputPath | Out-Null
New-Item -ItemType File -Force -Path $tempErrorPath | Out-Null

$process = Start-Process -FilePath $opencodeCommand.Source `
    -ArgumentList @('run', $prompt) `
    -RedirectStandardOutput $tempOutputPath `
    -RedirectStandardError $tempErrorPath `
    -NoNewWindow `
    -PassThru

$startedAt = Get-Date
Write-Output "[review] mode=$Mode pid=$($process.Id)"
Write-Output "[review] output=$OutputPath"
Write-Output "[review] reviewer may be slow; polling every $PollSeconds s for up to $TimeoutSeconds s"

while (-not $process.HasExited) {
    Start-Sleep -Seconds $PollSeconds
    $process.Refresh()
    if ($process.HasExited) {
        break
    }

    $elapsed = [int]((Get-Date) - $startedAt).TotalSeconds
    Write-Output "[review] still running after ${elapsed}s"
    if ($TimeoutSeconds -gt 0 -and $elapsed -ge $TimeoutSeconds) {
        Stop-Process -Id $process.Id -Force
        throw "review timed out after ${elapsed}s"
    }
}

$stdoutText = Get-Content -Raw $tempOutputPath -ErrorAction SilentlyContinue
$stderrText = Get-Content -Raw $tempErrorPath -ErrorAction SilentlyContinue
$combinedOutput = @($stdoutText, $stderrText) -join [Environment]::NewLine
Set-Content -Path $OutputPath -Value $combinedOutput -Encoding utf8NoBOM
Remove-Item $tempOutputPath, $tempErrorPath -Force -ErrorAction SilentlyContinue

$verdictMatch = [regex]::Match($combinedOutput, '(?m)^VERDICT:\s*(.+)$')
$summaryMatch = [regex]::Match($combinedOutput, '(?m)^SUMMARY:\s*(.+)$')
$verdict = if ($verdictMatch.Success) { $verdictMatch.Groups[1].Value.Trim() } else { 'UNKNOWN' }
$summary = if ($summaryMatch.Success) { $summaryMatch.Groups[1].Value.Trim() } else { '' }
Set-Content -Path "$OutputPath.verdict.txt" -Value @("VERDICT=$verdict", "SUMMARY=$summary") -Encoding utf8NoBOM

Write-Output $combinedOutput
Write-Output "[review] verdict=$verdict"
