#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# --- 配置 ---
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

$RepoDir = Get-Location
$Status = "SUCCESS"
$Detail = "已成功提交并推送到远端。"
$Branch = "main"
$RemoteUrl = $null
$CommitTs = $null
$CommitMsg = $null
$CommitDone = 0

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

    $script:LastGitExitCode = $proc.ExitCode

    if (-not $IgnoreExitCode -and $proc.ExitCode -ne 0) {
        throw "git $($Arguments -join ' ') failed (exit code $($proc.ExitCode)): $stderr"
    }

    return $stdout.Trim()
}

# --- 主流程 ---
try {
    Write-Line
    Write-Host "my-skills 一键推送助手"
    Write-Host ""
    Write-Host "这个窗口会直接告诉你："
    Write-Host "1. 当前做到哪一步"
    Write-Host "2. 如果失败，最常见的原因是什么"
    Write-Host "3. 你下一步可以直接复制什么命令"
    Write-Host ""
    Write-Host "当前仓库目录："
    Write-Host $RepoDir
    Write-Line
    Write-Host ""

    # 步骤 1
    Write-Host "[步骤 1/5] 检查 Git 是否可用..."
    if (-not (Test-CommandExists "git")) {
        $Status = "ERROR"
        $Detail = "没有找到 Git。请先安装 Git for Windows，再重新双击这个脚本。"
        throw "git-not-found"
    }
    Write-Host "[OK] 已找到 Git"
    Write-Host ""

    # 步骤 2
    Write-Host "[步骤 2/5] 检查当前目录是不是 Git 仓库..."
    try {
        Invoke-Git @("rev-parse", "--is-inside-work-tree") | Out-Null
    } catch {
        $Status = "ERROR"
        $Detail = "当前目录不是 Git 仓库，所以无法提交或推送。"
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
        $Detail = "没有找到名为 origin 的远端仓库，所以没有可推送的目标。"
        throw "no-remote"
    }
    Write-Host "[OK] 当前分支: $Branch"
    Write-Host "[OK] 远端地址: $RemoteUrl"
    Write-Host ""

    # 步骤 3
    Write-Host "[步骤 3/5] 暂存所有变更 (git add -A)..."
    try {
        Invoke-Git @("add", "-A")
    } catch {
        $Status = "ERROR"
        $Detail = "git add -A 执行失败。通常是文件权限、路径或 Git 状态异常。"
        throw "git-add-failed"
    }
    Write-Host "[OK] 已完成暂存"
    Write-Host ""

    # 步骤 4
    Write-Host "[步骤 4/5] 检查这次有没有新内容需要提交..."
    $DiffExit = 0
    try {
        Invoke-Git @("diff", "--cached", "--quiet") -IgnoreExitCode | Out-Null
        $DiffExit = $script:LastGitExitCode
    } catch {
        $DiffExit = $script:LastGitExitCode
    }

    if ($DiffExit -eq 0) {
        $Status = "NO_CHANGES"
        $Detail = "没有检测到新的变更，所以这次无需提交和推送。"
        throw "no-changes"
    }
    if ($DiffExit -ne 1) {
        $Status = "ERROR"
        $Detail = "检查暂存区是否有变更时失败。"
        throw "diff-check-failed"
    }
    Write-Host "[OK] 检测到有新变更，准备提交"
    Write-Host ""

    $CommitTs = Get-Date -Format "yyyy-MM-dd HH:mm"
    $CommitMsg = "sync $CommitTs"

    # 步骤 5
    Write-Host "[步骤 5/5] 创建提交并推送到远端..."
    Write-Host "[INFO] 提交信息: $CommitMsg"
    try {
        Invoke-Git @("commit", "-m", $CommitMsg)
    } catch {
        $Status = "ERROR"
        $Detail = "git commit 失败。常见原因是 Git 用户名/邮箱未配置，或提交钩子报错。"
        throw "commit-failed"
    }
    $CommitDone = 1
    Write-Host "[OK] 本地提交已创建"
    Write-Host ""

    Write-Host "[INFO] 正在推送到 origin/$Branch ..."
    try {
        Invoke-Git @("push", "origin", $Branch)
    } catch {
        $Status = "ERROR"
        $Detail = "git push 失败。常见原因是网络、SSH 权限、远端冲突，或当前账号无推送权限。"
        throw "push-failed"
    }
    Write-Host "[OK] 已成功推送到远端"
} catch {
    if ($_ -is [System.Management.Automation.ErrorRecord] -and $_.Exception.Message -eq "no-changes") {
        # 已处理
    }
}
finally {
    # --- 结束显示 ---
    Write-Host ""
    Write-Line
    switch ($Status) {
        "SUCCESS"    { Write-Host "结果：推送成功" }
        "NO_CHANGES" { Write-Host "结果：没有变更，不需要推送" }
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

    Write-Host "[看最近提交]"
    Write-Host "git -C `"$RepoDir`" log --oneline --decorate -n 5"
    Write-Host ""

    Write-Host "[重新推送当前分支]"
    Write-Host "git -C `"$RepoDir`" push origin $Branch"
    Write-Host ""

    Write-Host "[先拉最新再推 (常用于""远端比本地更新"")]"
    Write-Host "git -C `"$RepoDir`" pull --rebase origin $Branch"
    Write-Host "git -C `"$RepoDir`" push origin $Branch"
    Write-Host ""

    Write-Host "[检查 Git 身份信息 (常用于 commit 失败)]"
    Write-Host "git -C `"$RepoDir`" config user.name"
    Write-Host "git -C `"$RepoDir`" config user.email"
    Write-Host ""

    Write-Host "[设置 Git 身份信息 (把名字和邮箱改成你自己的)]"
    Write-Host "git -C `"$RepoDir`" config user.name `"你的名字`""
    Write-Host "git -C `"$RepoDir`" config user.email `"你的邮箱`""
    Write-Host ""

    Write-Host "[检查 GitHub SSH 登录 (常用于 push 权限失败)]"
    Write-Host "ssh -T git@github.com"
    Write-Host ""

    if ($Status -eq "ERROR") {
        Write-Line
        Write-Host "这次失败时，最常见的排查顺序："
        Write-Host "1. 先复制执行：git -C `"$RepoDir`" status --short --branch"
        Write-Host "2. 再复制执行：git -C `"$RepoDir`" remote -v"
        Write-Host "3. 如果提示远端有新提交，执行："
        Write-Host "   git -C `"$RepoDir`" pull --rebase origin $Branch"
        Write-Host "   git -C `"$RepoDir`" push origin $Branch"
        Write-Host "4. 如果提示权限或公钥问题，执行：ssh -T git@github.com"
        Write-Host "5. 如果提示作者身份未知，执行上面的 user.name / user.email 设置命令"
        Write-Host ""
        if ($CommitDone -eq 1) {
            Write-Host "补充说明：本地提交已经创建成功，只是还没有推送到远端。"
            Write-Host "你通常只需要修复权限/冲突问题后，再执行："
            Write-Host "git -C `"$RepoDir`" push origin $Branch"
            Write-Host ""
        }
    }

    Write-Line
    Write-Host "按 Enter 键关闭窗口..."
    Read-Host | Out-Null
    exit 0
}
