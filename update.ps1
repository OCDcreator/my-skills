#Requires -Version 5.1
# Thin wrapper: delegates to Python core logic.
# The canonical implementation lives in scripts/update_external.py.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

$Python = $null
if (Get-Command "python3" -ErrorAction SilentlyContinue) {
    $Python = "python3"
} elseif (Get-Command "python" -ErrorAction SilentlyContinue) {
    $Python = "python"
}

if (-not $Python) {
    Write-Host "ERROR: Python is required but not found." -ForegroundColor Red
    Write-Host "Please install Python 3 and try again."
    exit 1
}

& $Python scripts/update_external.py @args
exit $LASTEXITCODE
