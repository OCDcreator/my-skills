#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Script,

    [string]$Mac = 'dht@192.168.31.215',
    [string]$WorkingDirectory,
    [string]$Label = "mac-job-$(Get-Date -Format 'yyyyMMdd-HHmmss')",
    [string]$LogPath,
    [int]$ConnectTimeout = 10,
    [int]$Port = 0
)

. "$PSScriptRoot/ConvertTo-ZshSingleQuoted.ps1"

$safeLabel = ($Label -replace '[^A-Za-z0-9._-]', '-').Trim('-')
if (-not $safeLabel) {
    throw 'Label must contain at least one safe character'
}

$effectiveScript = $Script
if ($WorkingDirectory) {
    $effectiveScript = "cd $(ConvertTo-ZshSingleQuoted $WorkingDirectory)`n$effectiveScript"
}
$lfScript = $effectiveScript -replace "`r`n", "`n" -replace "`r", "`n"
$payload = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($lfScript))

$labelQuoted = ConvertTo-ZshSingleQuoted $safeLabel
$logAssignment = if ($LogPath) {
    'log_path=' + (ConvertTo-ZshSingleQuoted $LogPath)
} else {
    'log_path="$job_dir/$label.log"'
}

$remoteScript = @"
set -e
label=$labelQuoted
job_dir="`$HOME/.cache/windows-mac-ssh/jobs"
mkdir -p -- "`$job_dir"
script_path="`$job_dir/`$label.zsh"
$logAssignment
printf '%s' '$payload' | /usr/bin/base64 -D > "`$script_path"
chmod 700 "`$script_path"
nohup /bin/zsh "`$script_path" > "`$log_path" 2>&1 < /dev/null &
pid=`$!
(disown %+ 2>/dev/null || disown %1 2>/dev/null || true)
printf 'pid=%s\nlog=%s\nscript=%s\n' "`$pid" "`$log_path" "`$script_path"
"@

$lfRemoteScript = $remoteScript -replace "`r`n", "`n" -replace "`r", "`n"
$remotePayload = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($lfRemoteScript))
$sshArgs = @('-o', 'BatchMode=yes', '-o', "ConnectTimeout=$ConnectTimeout")
if ($Port -gt 0) {
    $sshArgs += @('-p', "$Port")
}

ssh @sshArgs $Mac "printf '%s' '$remotePayload' | /usr/bin/base64 -D | /bin/zsh -s"
if ($LASTEXITCODE -ne 0) {
    throw "Starting background job on $Mac failed with exit code $LASTEXITCODE"
}
