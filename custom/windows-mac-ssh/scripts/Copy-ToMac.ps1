#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$LocalPath,

    [Parameter(Mandatory = $true)]
    [string]$RemoteDirectory,

    [string]$Mac = 'dht@192.168.31.215',
    [int]$ConnectTimeout = 10,
    [int]$Port = 0,
    [switch]$Replace
)

function ConvertTo-ZshSingleQuoted {
    param([Parameter(Mandatory = $true)][string]$Value)
    return "'" + ($Value -replace "'", "'\''") + "'"
}

$item = Get-Item -LiteralPath $LocalPath -ErrorAction Stop
$leaf = $item.Name
$parent = if ($item.PSIsContainer) { $item.Parent.FullName } else { Split-Path -Parent $item.FullName }

$destQuoted = ConvertTo-ZshSingleQuoted $RemoteDirectory
$leafQuoted = ConvertTo-ZshSingleQuoted $leaf
$replaceFlag = if ($Replace) { '1' } else { '0' }

$remoteCommand = 'set -e; dest={0}; leaf={1}; replace={2}; case "$dest" in ""|"/"|"/Volumes") echo "Refusing unsafe destination: $dest" >&2; exit 2;; esac; mkdir -p -- "$dest"; if [ "$replace" = 1 ]; then target="$dest/$leaf"; case "$target" in "$dest"/*) rm -rf -- "$target";; *) echo "Refusing unsafe target: $target" >&2; exit 2;; esac; fi; cd -- "$dest"; tar -xf -' -f $destQuoted, $leafQuoted, $replaceFlag

$sshArgs = @('-o', 'BatchMode=yes', '-o', "ConnectTimeout=$ConnectTimeout")
if ($Port -gt 0) {
    $sshArgs += @('-p', "$Port")
}

tar -C $parent -cf - $leaf | ssh @sshArgs $Mac $remoteCommand
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    throw "Copy to $Mac failed with exit code $exitCode"
}
