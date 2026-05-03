#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# --- 配置 ---
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

$RepoDir = Get-Location
$Status = "SUCCESS"
$Detail = "已用远端 origin/main 覆盖本地内容。"
$Branch = "main"
$RemoteUrl = $null

# --- 辅助函数 ---
function Write-Line {
    Write-Host "============================================================"
}

function Test-CommandExists {
    param([string]$Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

function Invoke-Git {
    param(
        [string[]]$Arguments,
        [switch]$IgnoreExitCode
    )
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "git"
    $psi.Arguments = $Arguments -join " "
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8

    $proc = [System.Diagnostics.Process]::Start($psi)
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()

    if (-not $IgnoreExitCode -and $proc.ExitCode -ne 0) {
        throw "git $($Arguments -join ' ') failed (exit code $($proc.ExitCode)): $stderr"
    }

    return $stdout.Trim()
}

# --- 主流程 ---
try {
    Write-Line
    Write-Host "my-skills 一键拉取覆盖助手"
    Write-Host ""
    Write-Host "这个脚本的用途："
    Write-Host "1. 从 GitHub 拉取最新远端信息"
    Write-Host "2. 用远端 origin/main 强制覆盖本地 main"
    Write-Host "3. 如果本地有未提交修改，这些修改会被丢弃"
    Write-Host ""
    Write-Host "当前仓库目录："
    Write-Host $RepoDir
    Write-Line
    Write-Host ""

    Write-Host "[重要提醒]"
    Write-Host "这是一个""覆盖本地""的脚本，不是普通同步。"
    Write-Host "如果你本地有没提交的修改，运行后可能找不回来。"
    Write-Host ""
    Write-Host "如果你只是想保存本地修改并上传，请关闭窗口，改用 push.ps1。"
    Write-Host ""
    $Confirm = Read-Host "确认要用远端覆盖本地吗？请输入 Y 后回车继续"
    if ($Confirm -ne "Y") {
        $Status = "CANCELLED"
        $Detail = "你没有输入 Y，脚本已取消，没有改动任何文件。"
        throw "cancelled"
    }
    Write-Host ""

    # 步骤 1
    Write-Host "[步骤 1/4] 检查 Git 是否可用..."
    if (-not (Test-CommandExists "git")) {
        $Status = "ERROR"
        $Detail = "没有找到 Git。请先安装 Git for Windows，再重新双击这个脚本。"
        throw "git-not-found"
    }
    Write-Host "[OK] 已找到 Git"
    Write-Host ""

    # 步骤 2
    Write-Host "[步骤 2/4] 检查当前目录是不是 Git 仓库..."
    try {
        Invoke-Git @("rev-parse", "--is-inside-work-tree") | Out-Null
    } catch {
        $Status = "ERROR"
        $Detail = "当前目录不是 Git 仓库，所以无法拉取远端内容。"
        throw "not-git-repo"
    }

    try {
        $Branch = Invoke-Git @("branch", "--show-current")
    } catch {
        $Branch = "main"
    }

    try {
        $RemoteUrl = Invoke-Git @("remote", "get-url", "origin")
    } catch {
        $RemoteUrl = $null
    }

    if ([string]::IsNullOrEmpty($RemoteUrl)) {
        $Status = "ERROR"
        $Detail = "没有找到名为 origin 的远端仓库，所以不知道从哪里拉取。"
        throw "no-remote"
    }
    Write-Host "[OK] 当前分支: $Branch"
    Write-Host "[OK] 远端地址: $RemoteUrl"
    Write-Host ""

    # 步骤 3
    Write-Host "[步骤 3/4] 从远端获取最新信息..."
    try {
        Invoke-Git @("fetch", "origin")
    } catch {
        $Status = "ERROR"
        $Detail = "git fetch 失败。常见原因是网络、GitHub SSH 权限或远端地址错误。"
        throw "fetch-failed"
    }
    Write-Host "[OK] 已获取远端信息"
    Write-Host ""

    # 步骤 4
    Write-Host "[步骤 4/4] 用 origin/main 覆盖本地..."
    try {
        Invoke-Git @("rev-parse", "--verify", "origin/main") | Out-Null
    } catch {
        $Status = "ERROR"
        $Detail = "远端没有 origin/main，可能默认分支不是 main。请先查看 git branch -r。"
        throw "no-origin-main"
    }

    try {
        Invoke-Git @("reset", "--hard", "origin/main")
    } catch {
        $Status = "ERROR"
        $Detail = "git reset --hard origin/main 失败。可能有文件被占用或 Git 状态异常。"
        throw "reset-failed"
    }
    Write-Host "[OK] 本地已覆盖为 origin/main"
} catch {
    if ($_ -is [System.Management.Automation.ErrorRecord] -and $_.Exception.Message -eq "cancelled") {
        # 已处理
    }
}
finally {
    # --- 结束显示 ---
    Write-Host ""
    Write-Line
    switch ($Status) {
        "SUCCESS"    { Write-Host "结果：拉取覆盖成功" }
        "CANCELLED"  { Write-Host "结果：已取消" }
        default      { Write-Host "结果：执行失败" }
    }
    Write-Host "说明：$Detail"
    Write-Line
    Write-Host ""

    Write-Host "当前仓库状态："
    try { Invoke-Git @("status", "--short", "--branch") | Write-Host } catch { }
    Write-Host ""

    Write-Host "最近 5 条提交："
    try { Invoke-Git @("log", "--oneline", "--decorate", "-n", "5") | Write-Host } catch { }
    Write-Host ""

    Write-Line
    Write-Host "如果你不确定下一步怎么做，可以直接复制下面这些命令："
    Write-Line
    Write-Host ""

    Write-Host "[看仓库状态]"
    Write-Host "git -C `"$RepoDir`" status --short --branch"
    Write-Host ""

    Write-Host "[看远端地址]"
    Write-Host "git -C `"$RepoDir`" remote -v"
    Write-Host ""

    Write-Host "[查看远端分支]"
    Write-Host "git -C `"$RepoDir`" branch -r"
    Write-Host ""

    Write-Host "[普通拉取，不强制覆盖]"
    Write-Host "git -C `"$RepoDir`" pull --rebase origin main"
    Write-Host ""

    Write-Host "[强制覆盖本地，谨慎使用]"
    Write-Host "git -C `"$RepoDir`" fetch origin"
    Write-Host "git -C `"$RepoDir`" reset --hard origin/main"
    Write-Host ""

    Write-Host "[检查 GitHub SSH 登录]"
    Write-Host "ssh -T git@github.com"
    Write-Host ""

    if ($Status -eq "ERROR") {
        Write-Line
        Write-Host "这次失败时，最常见的排查顺序："
        Write-Host "1. 先复制执行：git -C `"$RepoDir`" status --short --branch"
        Write-Host "2. 再复制执行：git -C `"$RepoDir`" remote -v"
        Write-Host "3. 如果提示权限或公钥问题，执行：ssh -T git@github.com"
        Write-Host "4. 如果提示没有 origin/main，执行：git -C `"$RepoDir`" branch -r"
        Write-Host "5. 如果文件被占用，关闭编辑器或同步工具后重试"
        Write-Host ""
    }

    Write-Line
    Write-Host "按 Enter 键关闭窗口..."
    Read-Host | Out-Null
    exit 0
}
