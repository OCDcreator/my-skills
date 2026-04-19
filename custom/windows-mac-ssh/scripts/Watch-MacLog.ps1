#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$LogPath,

    [string]$Mac = 'dht@192.168.31.215',
    [int]$Lines = 80,
    [switch]$Follow,
    [int]$ConnectTimeout = 10,
    [int]$Port = 0
)

function ConvertTo-ZshSingleQuoted {
    param([Parameter(Mandatory = $true)][string]$Value)
    return "'" + ($Value -replace "'", "'\''") + "'"
}

$quotedLog = ConvertTo-ZshSingleQuoted $LogPath
$mode = if ($Follow) { '-f' } else { '' }
$remoteCommand = "tail -n $Lines $mode -- $quotedLog"

$sshArgs = @('-o', 'BatchMode=yes', '-o', "ConnectTimeout=$ConnectTimeout")
if ($Port -gt 0) {
    $sshArgs += @('-p', "$Port")
}

ssh @sshArgs $Mac $remoteCommand
if ($LASTEXITCODE -ne 0) {
    throw "Watching log on $Mac failed with exit code $LASTEXITCODE"
}
