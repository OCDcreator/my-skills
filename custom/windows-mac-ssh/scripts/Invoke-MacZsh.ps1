#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, ValueFromPipeline = $true)]
    [string]$Script,

    [string]$Mac = 'dht@192.168.31.215',
    [string]$WorkingDirectory,
    [int]$ConnectTimeout = 10,
    [int]$Port = 0,
    [switch]$Interactive,
    [switch]$CleanEnv,
    [switch]$NoThrow
)

begin {
    function ConvertTo-ZshSingleQuoted {
        param([Parameter(Mandatory = $true)][string]$Value)
        return "'" + ($Value -replace "'", "'\''") + "'"
    }
}

process {
    $effectiveScript = $Script
    if ($WorkingDirectory) {
        $effectiveScript = "cd $(ConvertTo-ZshSingleQuoted $WorkingDirectory)`n$effectiveScript"
    }

    $lfScript = $effectiveScript -replace "`r`n", "`n" -replace "`r", "`n"
    $payload = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($lfScript))

    if ($CleanEnv) {
        $runner = 'env -i HOME="$HOME" USER="$USER" LOGNAME="$LOGNAME" SHELL=/bin/zsh PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" /bin/zsh -f -s'
    } else {
        $runner = '/bin/zsh -s'
    }

    $remoteCommand = "printf '%s' '$payload' | /usr/bin/base64 -D | $runner"
    $sshArgs = @()
    if (-not $Interactive) {
        $sshArgs += @('-o', 'BatchMode=yes')
    }
    $sshArgs += @('-o', "ConnectTimeout=$ConnectTimeout")
    if ($Port -gt 0) {
        $sshArgs += @('-p', "$Port")
    }

    & ssh @sshArgs $Mac $remoteCommand
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        if ($NoThrow) {
            exit $exitCode
        }
        throw "Remote zsh command failed on $Mac with exit code $exitCode"
    }
}
