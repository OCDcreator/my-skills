#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$LocalPath,

    [Parameter(Mandatory = $true)]
    [string]$RemotePath,

    [string]$Mac = 'dht@192.168.31.215',
    [string[]]$RelativePath,
    [int]$ConnectTimeout = 10,
    [int]$Port = 0
)

function ConvertTo-ZshSingleQuoted {
    param([Parameter(Mandatory = $true)][string]$Value)
    return "'" + ($Value -replace "'", "'\''") + "'"
}

function Invoke-RemoteZsh {
    param([Parameter(Mandatory = $true)][string]$RemoteScript)
    $lfScript = $RemoteScript -replace "`r`n", "`n" -replace "`r", "`n"
    $payload = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($lfScript))
    $sshArgs = @('-o', 'BatchMode=yes', '-o', "ConnectTimeout=$ConnectTimeout")
    if ($Port -gt 0) {
        $sshArgs += @('-p', "$Port")
    }
    & ssh @sshArgs $Mac "printf '%s' '$payload' | /usr/bin/base64 -D | /bin/zsh -s"
    if ($LASTEXITCODE -ne 0) {
        throw "Remote hash command failed on $Mac with exit code $LASTEXITCODE"
    }
}

$localItem = Get-Item -LiteralPath $LocalPath -ErrorAction Stop
$remoteQuoted = ConvertTo-ZshSingleQuoted $RemotePath

if (-not $localItem.PSIsContainer) {
    $localHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $localItem.FullName).Hash.ToLowerInvariant()
    $remoteScript = @"
set -e
hash=`$(shasum -a 256 -- $remoteQuoted | awk '{print `$1}')
printf '%s\n' "`$hash"
"@
    $remoteHash = (Invoke-RemoteZsh -RemoteScript $remoteScript | Select-Object -Last 1).Trim().ToLowerInvariant()
    if ($localHash -ne $remoteHash) {
        throw "Hash mismatch: local=$localHash remote=$remoteHash"
    }
    "match file sha256=$localHash"
    return
}

$baseLength = $localItem.FullName.TrimEnd('\').Length + 1
$targetRelatives = if ($RelativePath) {
    $RelativePath | ForEach-Object { ($_ -replace '\\', '/').TrimStart('./') }
} else {
    Get-ChildItem -LiteralPath $localItem.FullName -Recurse -File | ForEach-Object {
        $_.FullName.Substring($baseLength).Replace('\', '/')
    }
}

$localLines = foreach ($relative in ($targetRelatives | Sort-Object -Unique)) {
    $fullPath = Join-Path $localItem.FullName ($relative -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        "MISSING  $relative"
    } else {
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $fullPath).Hash.ToLowerInvariant()
        "$hash  $relative"
    }
}

if ($RelativePath) {
    $remoteRelatives = ($targetRelatives | ForEach-Object { ConvertTo-ZshSingleQuoted $_ }) -join ' '
    $remoteScript = @"
set -e
cd -- $remoteQuoted
for f in $remoteRelatives; do
  if [ -f "`$f" ]; then
    hash=`$(shasum -a 256 -- "`$f" | awk '{print `$1}')
    printf '%s  %s\n' "`$hash" "`$f"
  else
    printf 'MISSING  %s\n' "`$f"
  fi
done
"@
} else {
    $remoteScript = @"
set -e
cd -- $remoteQuoted
find . -type f | LC_ALL=C sort | while IFS= read -r f; do
  rel=`${f#./}
  hash=`$(shasum -a 256 -- "`$f" | awk '{print `$1}')
  printf '%s  %s\n' "`$hash" "`$rel"
done
"@
}

$remoteLines = Invoke-RemoteZsh -RemoteScript $remoteScript | Where-Object { $_ -match '\S' }
$localSorted = @($localLines | Sort-Object)
$remoteSorted = @($remoteLines | Sort-Object)

$diff = Compare-Object -ReferenceObject $localSorted -DifferenceObject $remoteSorted
if ($diff) {
    $diff | Format-Table -AutoSize | Out-String | Write-Host
    throw "Windows/Mac hash comparison failed"
}

"match files=$($localSorted.Count)"
