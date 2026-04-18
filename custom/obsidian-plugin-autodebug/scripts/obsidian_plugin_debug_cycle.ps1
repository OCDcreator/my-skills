#Requires -Version 5.1

param(
  [Parameter(Mandatory = $true)]
  [string]$PluginId,

  [Parameter(Mandatory = $true)]
  [string]$TestVaultPluginDir,

  [string]$VaultName = "",
  [string]$ObsidianCommand = "",
  [string]$DeployFrom = "dist",
  [string]$OutputDir = ".obsidian-debug",
  [string[]]$BuildCommand = @("npm", "run", "build"),
  [int]$WatchSeconds = 20,
  [int]$PollIntervalMs = 1000,
  [int]$ConsoleLimit = 200,
  [string]$DomSelector = ".workspace-leaf.mod-active",
  [switch]$UseCdp,
  [string]$CdpHost = "127.0.0.1",
  [int]$CdpPort = 9222,
  [string]$CdpTargetTitleContains = "",
  [int]$CdpReloadDelayMs = 800,
  [string]$CdpEvalAfterReload = "",
  [string]$ScenarioName = "",
  [string]$ScenarioPath = "",
  [string]$ScenarioCommandId = "",
  [string]$SurfaceProfilePath = "",
  [int]$ScenarioSleepMs = 2000,
  [string]$AssertionsPath = "",
  [string]$CompareDiagnosisPath = "",
  [switch]$DomText,
  [switch]$SkipBuild,
  [switch]$SkipDeploy,
  [switch]$SkipReload,
  [switch]$SkipScreenshot,
  [switch]$SkipDom
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-OutputDirectory {
  param([string]$Path)

  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Path $Path | Out-Null
  }

  return (Resolve-Path -LiteralPath $Path).Path
}

function Get-Timestamp {
  return (Get-Date).ToString("o")
}

function Write-Section {
  param([string]$Message)

  Write-Host ""
  Write-Host "== $Message =="
}

function Resolve-ObsidianCommand {
  if ($ObsidianCommand.Trim().Length -gt 0) {
    if ($ObsidianCommand.EndsWith('.exe', [System.StringComparison]::OrdinalIgnoreCase)) {
      $comCandidate = [System.IO.Path]::ChangeExtension($ObsidianCommand, '.com')
      if (Test-Path -LiteralPath $comCandidate) {
        return $comCandidate
      }
    }
    return $ObsidianCommand
  }

  $command = Get-Command obsidian -ErrorAction SilentlyContinue
  if ($command) {
    return $command.Source
  }

  $fallbacks = @(
    "C:\Program Files\Obsidian\Obsidian.com",
    "C:\Program Files\Obsidian\Obsidian.exe",
    "$env:LOCALAPPDATA\Obsidian\Obsidian.exe"
  ) | Where-Object { $_ -and $_.Trim().Length -gt 0 }

  foreach ($candidate in $fallbacks) {
    if (Test-Path -LiteralPath $candidate) {
      return $candidate
    }
  }

  throw "Unable to locate the Obsidian command. Pass -ObsidianCommand explicitly."
}

function Get-ObsidianCliArgs {
  param(
    [string]$Command,
    [string[]]$Arguments = @()
  )

  $cliArgs = @()
  if ($VaultName.Trim().Length -gt 0) {
    $cliArgs += "vault=$VaultName"
  }
  $cliArgs += $Command
  $cliArgs += $Arguments
  return $cliArgs
}

function Invoke-ObsidianCli {
  param(
    [string]$Executable,
    [string]$Command,
    [string[]]$Arguments = @(),
    [switch]$AllowFailure,
    [switch]$Quiet
  )

  $cliArgs = Get-ObsidianCliArgs -Command $Command -Arguments $Arguments
  if (-not $Quiet) {
    Write-Host "$Executable $($cliArgs -join ' ')"
  }
  $previousErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $output = & $Executable @cliArgs 2>&1
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }
  $lastExitCodeVar = Get-Variable -Name LASTEXITCODE -ErrorAction SilentlyContinue
  $exitCode = if ($lastExitCodeVar) { [int]$lastExitCodeVar.Value } else { 0 }
  $text = ($output | ForEach-Object { "$_" }) -join [Environment]::NewLine

  if ($exitCode -ne 0 -and -not $AllowFailure) {
    throw "$Executable $($cliArgs -join ' ') failed with exit code $exitCode`n$text"
  }

  return $text
}

function Invoke-Build {
  param([string]$BuildLogPath)

  if ($BuildCommand.Count -lt 1) {
    throw "BuildCommand cannot be empty."
  }

  $buildExe = $BuildCommand[0]
  $buildArgs = @()
  if ($BuildCommand.Count -gt 1) {
    $buildArgs = $BuildCommand[1..($BuildCommand.Count - 1)]
  }

  Write-Section "Build"
  Write-Host "$buildExe $($buildArgs -join ' ')"
  & $buildExe @buildArgs 2>&1 | Tee-Object -FilePath $BuildLogPath
  if ($LASTEXITCODE -ne 0) {
    throw "Build failed with exit code $LASTEXITCODE. See $BuildLogPath"
  }
}

function Copy-DeployArtifacts {
  param(
    [string]$SourceDir,
    [string]$TargetDir,
    [string]$ReportPath
  )

  Write-Section "Deploy"

  if (-not (Test-Path -LiteralPath $SourceDir)) {
    throw "Deploy source does not exist: $SourceDir"
  }

  if (-not (Test-Path -LiteralPath $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir | Out-Null
  }

  $resolvedSource = (Resolve-Path -LiteralPath $SourceDir).Path
  $resolvedTarget = (Resolve-Path -LiteralPath $TargetDir).Path
  $requiredFiles = @("main.js", "manifest.json")
  $optionalFiles = @("styles.css")
  $report = @()

  foreach ($fileName in $requiredFiles + $optionalFiles) {
    $sourceFile = Join-Path $resolvedSource $fileName
    if (-not (Test-Path -LiteralPath $sourceFile)) {
      if ($requiredFiles -contains $fileName) {
        throw "Required deploy artifact missing: $sourceFile"
      }
      continue
    }

    $targetFile = Join-Path $resolvedTarget $fileName
    Copy-Item -LiteralPath $sourceFile -Destination $targetFile -Force
    $sourceHash = (Get-FileHash -LiteralPath $sourceFile -Algorithm SHA256).Hash
    $targetHash = (Get-FileHash -LiteralPath $targetFile -Algorithm SHA256).Hash
    $report += [ordered]@{
      file = $fileName
      source = $sourceFile
      target = $targetFile
      sha256 = $targetHash
      matched = $sourceHash -eq $targetHash
    }
  }

  $sourceAssets = Join-Path $resolvedSource "assets"
  if (Test-Path -LiteralPath $sourceAssets) {
    $targetAssets = Join-Path $resolvedTarget "assets"
    Copy-Item -LiteralPath $sourceAssets -Destination $targetAssets -Recurse -Force
    $report += [ordered]@{
      file = "assets/"
      source = $sourceAssets
      target = $targetAssets
      sha256 = $null
      matched = $true
    }
  }

  $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $ReportPath -Encoding UTF8
  Write-Host "Deploy report: $ReportPath"
}

function Watch-Console {
  param(
    [string]$Executable,
    [string]$ConsoleLogPath,
    [string]$ErrorsLogPath
  )

  Write-Section "Watch Console"
  $deadline = (Get-Date).AddSeconds($WatchSeconds)
  $previousConsoleText = ""
  $previousErrorsText = ""

  while ((Get-Date) -lt $deadline) {
    $consoleText = Invoke-ObsidianCli -Executable $Executable -Command "dev:console" -Arguments @("limit=$ConsoleLimit") -AllowFailure -Quiet
    $previousConsoleLines = @($(if ([string]::IsNullOrEmpty($previousConsoleText)) { @() } else { $previousConsoleText -split "`r?`n" }))
    $currentConsoleLines = @($(if ([string]::IsNullOrEmpty($consoleText)) { @() } else { $consoleText -split "`r?`n" }))
    $sharedPrefixLength = 0
    $maxPrefixLength = [Math]::Min(@($previousConsoleLines).Count, @($currentConsoleLines).Count)

    while ($sharedPrefixLength -lt $maxPrefixLength -and $previousConsoleLines[$sharedPrefixLength] -eq $currentConsoleLines[$sharedPrefixLength]) {
      $sharedPrefixLength++
    }

    foreach ($line in @($currentConsoleLines | Select-Object -Skip $sharedPrefixLength)) {
      $trimmed = $line.Trim()
      if ($trimmed.Length -eq 0) {
        continue
      }

      Add-Content -LiteralPath $ConsoleLogPath -Value "$(Get-Timestamp) $trimmed"
    }
    $previousConsoleText = $consoleText

    $errorsText = Invoke-ObsidianCli -Executable $Executable -Command "dev:errors" -AllowFailure -Quiet
    $normalizedErrorsText = (($errorsText -split "`r?`n") | Where-Object { $_.Trim().Length -gt 0 }) -join [Environment]::NewLine

    if (
      $normalizedErrorsText.Length -gt 0 -and
      $normalizedErrorsText -ne $previousErrorsText -and
      $normalizedErrorsText -ne "No errors captured."
    ) {
      Add-Content -LiteralPath $ErrorsLogPath -Value "$(Get-Timestamp)`n$normalizedErrorsText`n"
    }
    $previousErrorsText = $normalizedErrorsText

    Start-Sleep -Milliseconds $PollIntervalMs
  }

  if (-not (Test-Path -LiteralPath $ErrorsLogPath) -or (Get-Item -LiteralPath $ErrorsLogPath).Length -eq 0) {
    Set-Content -LiteralPath $ErrorsLogPath -Value "$(Get-Timestamp) No errors captured during watch window." -Encoding UTF8
  }
}

function Invoke-ScenarioRunner {
  param(
    [string]$Executable,
    [string]$OutputPath
  )

  $resolvedScenarioName = $ScenarioName.Trim()
  if ($resolvedScenarioName.Length -eq 0 -and $ScenarioCommandId.Trim().Length -gt 0) {
    $resolvedScenarioName = "open-plugin-view"
  }

  if ($resolvedScenarioName.Length -eq 0 -and $ScenarioPath.Trim().Length -eq 0) {
    return $null
  }

  $scriptPath = Join-Path $PSScriptRoot "obsidian_debug_scenario_runner.mjs"
  if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Scenario runner not found: $scriptPath"
  }

  $args = @(
    $scriptPath,
    "--obsidian-command", $Executable,
    "--plugin-id", $PluginId,
    "--scenario-sleep-ms", "$ScenarioSleepMs",
    "--output", $OutputPath
  )

  if ($VaultName.Trim().Length -gt 0) {
    $args += @("--vault-name", $VaultName)
  }
  if ($resolvedScenarioName.Length -gt 0) {
    $args += @("--scenario-name", $resolvedScenarioName)
  }
  if ($ScenarioPath.Trim().Length -gt 0) {
    $args += @("--scenario-path", $ScenarioPath)
  }
  if ($ScenarioCommandId.Trim().Length -gt 0) {
    $args += @("--scenario-command-id", $ScenarioCommandId)
  }
  if ($SurfaceProfilePath.Trim().Length -gt 0) {
    $args += @("--surface-profile", $SurfaceProfilePath)
  }
  if ($CdpHost.Trim().Length -gt 0) {
    $args += @("--cdp-host", $CdpHost)
  }
  if ($CdpPort -gt 0) {
    $args += @("--cdp-port", "$CdpPort")
  }
  if ($CdpTargetTitleContains.Trim().Length -gt 0) {
    $args += @("--cdp-target-title-contains", $CdpTargetTitleContains)
  }

  Write-Section "Scenario"
  Write-Host "node $($args -join ' ')"
  & node @args 2>&1 | ForEach-Object { Write-Host $_ }
  if ($LASTEXITCODE -ne 0) {
    throw "Scenario runner failed with exit code $LASTEXITCODE"
  }

  return $OutputPath
}

function Invoke-Diagnosis {
  param(
    [string]$SummaryPath,
    [string]$OutputPath
  )

  $scriptPath = Join-Path $PSScriptRoot "obsidian_debug_analyze.mjs"
  if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Diagnosis script not found: $scriptPath"
  }

  $args = @(
    $scriptPath,
    "--summary", $SummaryPath,
    "--output", $OutputPath
  )
  if ($AssertionsPath.Trim().Length -gt 0) {
    $args += @("--assertions", $AssertionsPath)
  }
  if ($DomSelector.Trim().Length -gt 0) {
    $args += @("--dom-selector", $DomSelector)
  }

  Write-Section "Diagnosis"
  Write-Host "node $($args -join ' ')"
  & node @args 2>&1 | ForEach-Object { Write-Host $_ }
  if ($LASTEXITCODE -ne 0) {
    throw "Diagnosis failed with exit code $LASTEXITCODE"
  }
}

function Invoke-Comparison {
  param(
    [string]$BaselinePath,
    [string]$CandidatePath,
    [string]$OutputPath
  )

  if ($BaselinePath.Trim().Length -eq 0) {
    return
  }

  $scriptPath = Join-Path $PSScriptRoot "obsidian_debug_compare.mjs"
  if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Comparison script not found: $scriptPath"
  }

  $args = @(
    $scriptPath,
    "--baseline", $BaselinePath,
    "--candidate", $CandidatePath,
    "--output", $OutputPath
  )

  Write-Section "Comparison"
  Write-Host "node $($args -join ' ')"
  & node @args 2>&1 | ForEach-Object { Write-Host $_ }
  if ($LASTEXITCODE -ne 0) {
    throw "Comparison failed with exit code $LASTEXITCODE"
  }
}

function Invoke-CdpReloadTrace {
  param(
    [string]$OutputPath
  )

  $scriptPath = Join-Path $PSScriptRoot "obsidian_cdp_reload_and_trace.mjs"
  if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "CDP script not found: $scriptPath"
  }

  $summaryPath = "$OutputPath.summary.json"
  $args = @(
    $scriptPath,
    "--plugin-id", $PluginId,
    "--host", $CdpHost,
    "--port", "$CdpPort",
    "--duration-seconds", "$WatchSeconds",
    "--reload-delay-ms", "$CdpReloadDelayMs",
    "--output", $OutputPath,
    "--summary", $summaryPath
  )

  if ($CdpTargetTitleContains.Trim().Length -gt 0) {
    $args += @("--target-title-contains", $CdpTargetTitleContains)
  }
  if ($CdpEvalAfterReload.Trim().Length -gt 0) {
    $args += @("--eval-after-reload", $CdpEvalAfterReload)
  }

  Write-Section "CDP Reload Trace"
  Write-Host "node $($args -join ' ')"
  & node @args 2>&1 | ForEach-Object { Write-Host $_ }
  if ($LASTEXITCODE -ne 0) {
    throw "CDP reload trace failed with exit code $LASTEXITCODE"
  }

  return $summaryPath
}

$resolvedOutputDir = New-OutputDirectory -Path $OutputDir
$resolvedObsidianCommand = Resolve-ObsidianCommand
$buildLogPath = Join-Path $resolvedOutputDir "build.log"
$deployReportPath = Join-Path $resolvedOutputDir "deploy-report.json"
$consoleLogPath = Join-Path $resolvedOutputDir "console-watch.log"
$errorsLogPath = Join-Path $resolvedOutputDir "errors.log"
$screenshotPath = Join-Path $resolvedOutputDir "screenshot.png"
$domPath = Join-Path $resolvedOutputDir ($(if ($DomText) { "dom.txt" } else { "dom.html" }))
$summaryPath = Join-Path $resolvedOutputDir "summary.json"
$diagnosisPath = Join-Path $resolvedOutputDir "diagnosis.json"
$scenarioReportPath = Join-Path $resolvedOutputDir "scenario-report.json"
$comparisonPath = Join-Path $resolvedOutputDir "comparison.json"
$cdpTracePath = Join-Path $resolvedOutputDir "cdp-reload-trace.log"
$cdpSummaryPath = $null
$resolvedScenarioReportPath = $null

Write-Section "Preflight"
$versionText = Invoke-ObsidianCli -Executable $resolvedObsidianCommand -Command "version" -AllowFailure -Quiet
Set-Content -LiteralPath (Join-Path $resolvedOutputDir "obsidian-version.txt") -Value $versionText -Encoding UTF8

if (-not $SkipBuild) {
  Invoke-Build -BuildLogPath $buildLogPath
}

if (-not $SkipDeploy) {
  Copy-DeployArtifacts -SourceDir $DeployFrom -TargetDir $TestVaultPluginDir -ReportPath $deployReportPath
}

Write-Section "Clear Buffers"
Invoke-ObsidianCli -Executable $resolvedObsidianCommand -Command "dev:debug" -Arguments @("on") -AllowFailure | Out-Null
Invoke-ObsidianCli -Executable $resolvedObsidianCommand -Command "dev:console" -Arguments @("clear") -AllowFailure | Out-Null
Invoke-ObsidianCli -Executable $resolvedObsidianCommand -Command "dev:errors" -Arguments @("clear") -AllowFailure | Out-Null

if ($UseCdp -and -not $SkipReload) {
  $cdpSummaryPath = Invoke-CdpReloadTrace -OutputPath $cdpTracePath
} elseif (-not $SkipReload) {
  Write-Section "Reload Plugin"
  Invoke-ObsidianCli -Executable $resolvedObsidianCommand -Command "plugin:reload" -Arguments @("id=$PluginId") | Out-Null
}

$resolvedScenarioReportPath = Invoke-ScenarioRunner -Executable $resolvedObsidianCommand -OutputPath $scenarioReportPath

if (-not $UseCdp) {
  Watch-Console -Executable $resolvedObsidianCommand -ConsoleLogPath $consoleLogPath -ErrorsLogPath $errorsLogPath
}

if (-not $SkipScreenshot) {
  Write-Section "Screenshot"
  Invoke-ObsidianCli -Executable $resolvedObsidianCommand -Command "dev:screenshot" -Arguments @("path=$screenshotPath") -AllowFailure |
    Set-Content -LiteralPath (Join-Path $resolvedOutputDir "screenshot-command.txt") -Encoding UTF8
}

if (-not $SkipDom) {
  Write-Section "DOM"
  $domArgs = @("selector=$DomSelector", "all")
  if ($DomText) {
    $domArgs += "text"
  }
  Invoke-ObsidianCli -Executable $resolvedObsidianCommand -Command "dev:dom" -Arguments $domArgs -AllowFailure |
    Set-Content -LiteralPath $domPath -Encoding UTF8
}

$summary = [ordered]@{
  timestamp = Get-Timestamp
  repoDir = (Get-Location).Path
  pluginId = $PluginId
  vaultName = $VaultName
  obsidianCommand = $resolvedObsidianCommand
  testVaultPluginDir = $TestVaultPluginDir
  outputDir = $resolvedOutputDir
  buildLog = if ($SkipBuild -or -not (Test-Path -LiteralPath $buildLogPath)) { $null } else { $buildLogPath }
  deployReport = if ($SkipDeploy -or -not (Test-Path -LiteralPath $deployReportPath)) { $null } else { $deployReportPath }
  scenarioReport = if ($resolvedScenarioReportPath -and (Test-Path -LiteralPath $resolvedScenarioReportPath)) { $resolvedScenarioReportPath } else { $null }
  assertionsPath = if ($AssertionsPath.Trim().Length -gt 0) { $AssertionsPath } else { $null }
  comparisonReport = if ($CompareDiagnosisPath.Trim().Length -gt 0) { $comparisonPath } else { $null }
  consoleLog = if ($UseCdp -or -not (Test-Path -LiteralPath $consoleLogPath)) { $null } else { $consoleLogPath }
  errorsLog = if (Test-Path -LiteralPath $errorsLogPath) { $errorsLogPath } else { $null }
  useCdp = $UseCdp.IsPresent
  cdpTrace = if ($UseCdp -and -not $SkipReload -and (Test-Path -LiteralPath $cdpTracePath)) { $cdpTracePath } else { $null }
  cdpSummary = if ($cdpSummaryPath -and (Test-Path -LiteralPath $cdpSummaryPath)) { $cdpSummaryPath } else { $null }
  screenshot = if ($SkipScreenshot -or -not (Test-Path -LiteralPath $screenshotPath)) { $null } else { $screenshotPath }
  dom = if ($SkipDom -or -not (Test-Path -LiteralPath $domPath)) { $null } else { $domPath }
  watchSeconds = $WatchSeconds
  consoleLimit = $ConsoleLimit
}

$summary | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $summaryPath -Encoding UTF8

Invoke-Diagnosis -SummaryPath $summaryPath -OutputPath $diagnosisPath
Invoke-Comparison -BaselinePath $CompareDiagnosisPath -CandidatePath $diagnosisPath -OutputPath $comparisonPath

Write-Section "Done"
Write-Host "Summary: $summaryPath"
