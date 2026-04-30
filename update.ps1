#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# --- 配置 ---
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

$RepoDir = Get-Location
$TmpDir = Join-Path $RepoDir ".tmp-skills"
$Status = "SUCCESS"
$Detail = "外部资源已同步，变更已提交并推送。"
$Branch = "main"
$RemoteUrl = $null
$CommitTs = $null
$CommitMsg = $null
$SourceErrors = 0
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

    if (-not $IgnoreExitCode -and $proc.ExitCode -ne 0) {
        throw "git $($Arguments -join ' ') failed (exit code $($proc.ExitCode)): $stderr"
    }

    return $stdout.Trim()
}

# --- 主流程 ---
try {
    Write-Line
    Write-Host "my-skills 外部资源更新助手"
    Write-Host ""
    Write-Host "这个脚本的用途："
    Write-Host "1. 从多个 GitHub 外部技能源下载最新内容"
    Write-Host "2. 从外部参考源下载最新设计参考"
    Write-Host "3. 复制到 external 目录"
    Write-Host "4. 如果有变化，就自动提交并推送"
    Write-Host ""
    Write-Host "当前仓库目录："
    Write-Host $RepoDir
    Write-Line
    Write-Host ""

    Write-Host "[重要提醒]"
    Write-Host "这个脚本会访问 GitHub，并可能修改 external 目录。"
    Write-Host "如果你只是想上传自己改的 custom 技能，请关闭窗口，改用 push.ps1。"
    Write-Host ""
    $Confirm = Read-Host "确认要更新外部资源并推送吗？请输入 Y 后回车继续"
    if ($Confirm -ne "Y") {
        $Status = "CANCELLED"
        $Detail = "你没有输入 Y，脚本已取消，没有改动任何文件。"
        throw "cancelled"
    }
    Write-Host ""

    # 步骤 1
    Write-Host "[步骤 1/7] 检查 Git 是否可用..."
    if (-not (Test-CommandExists "git")) {
        $Status = "ERROR"
        $Detail = "没有找到 Git。请先安装 Git for Windows，再重新双击这个脚本。"
        throw "git-not-found"
    }
    Write-Host "[OK] 已找到 Git"
    Write-Host ""

    # 步骤 2
    Write-Host "[步骤 2/7] 检查当前目录是不是 Git 仓库..."
    try {
        Invoke-Git @("rev-parse", "--is-inside-work-tree") | Out-Null
    } catch {
        $Status = "ERROR"
        $Detail = "当前目录不是 Git 仓库，所以无法更新、提交或推送。"
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
        $Detail = "没有找到名为 origin 的远端仓库，所以无法推送更新结果。"
        throw "no-remote"
    }
    Write-Host "[OK] 当前分支: $Branch"
    Write-Host "[OK] 远端地址: $RemoteUrl"
    Write-Host ""

    # 步骤 3
    Write-Host "[步骤 3/7] 准备临时下载目录..."
    if (Test-Path $TmpDir) {
        Remove-Item -Recurse -Force $TmpDir
    }
    New-Item -ItemType Directory -Path $TmpDir -Force | Out-Null
    if (-not (Test-Path $TmpDir)) {
        $Status = "ERROR"
        $Detail = "无法创建临时目录 .tmp-skills。可能是权限问题或文件被占用。"
        throw "tmp-dir-failed"
    }
    if (-not (Test-Path (Join-Path $RepoDir "external"))) {
        New-Item -ItemType Directory -Path (Join-Path $RepoDir "external") -Force | Out-Null
    }
    Write-Host "[OK] 临时目录已准备"
    Write-Host ""

    # 步骤 4
    Write-Host "[步骤 4/7] 下载并复制外部来源..."
    Write-Host ""
    Write-Host "[技能来源]"

    # 技能来源定义: (名称, 仓库URL, 分支, 源子目录, 目标子目录模式)
    $SkillSources = @(
        @{ Name = "anthropics-skills"; Url = "https://github.com/anthropics/skills.git"; Branch = "main"; SourceDir = "skills" },
        @{ Name = "awesome-claude-skills"; Url = "https://github.com/ComposioHQ/awesome-claude-skills.git"; Branch = "master"; SourceDir = "." },
        @{ Name = "claude-plugins-official"; Url = "https://github.com/anthropics/claude-plugins-official.git"; Branch = "main"; SourceDir = "plugins" },
        @{ Name = "baoyu-skills"; Url = "https://github.com/JimLiu/baoyu-skills.git"; Branch = "main"; SourceDir = "skills" },
        @{ Name = "axton-obsidian-visual-skills"; Url = "https://github.com/axtonliu/axton-obsidian-visual-skills.git"; Branch = "main"; SourceDir = "." },
        @{ Name = "kepano-obsidian-skills"; Url = "https://github.com/kepano/obsidian-skills.git"; Branch = "main"; SourceDir = "skills" },
        @{ Name = "taste-skill"; Url = "https://github.com/Leonxlnx/taste-skill.git"; Branch = "main"; SourceDir = "skills" },
        @{ Name = "html-ppt-skill"; Url = "https://github.com/lewislulu/html-ppt-skill.git"; Branch = "main"; SourceDir = "SKILL.md" },
        @{ Name = "ui-ux-pro-max-skill"; Url = "https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git"; Branch = "main"; SourceDir = ".claude/skills" }
    )

    $SkillIndex = 1
    foreach ($Src in $SkillSources) {
        Write-Host ""
        Write-Host "[技能 $SkillIndex/$($SkillSources.Count)] $($Src.Name)"
        $CloneDir = Join-Path $TmpDir $Src.Name
        $TargetDir = Join-Path $RepoDir "external" $Src.Name

        try {
            Invoke-Git @("clone", "--depth", "1", "--branch", $Src.Branch, $Src.Url, $CloneDir) -IgnoreExitCode | Out-Null
        } catch {
            $SourceErrors++
            Write-Host "[WARN] $($Src.Name) 下载失败"
            $SkillIndex++
            continue
        }

        $SourcePath = Join-Path $CloneDir $Src.SourceDir
        if (-not (Test-Path $SourcePath)) {
            $SourceErrors++
            Write-Host "[WARN] $($Src.Name) 下载失败或没有找到 $($Src.SourceDir) 目录"
            $SkillIndex++
            continue
        }

        # 复制逻辑
        if (Test-Path $TargetDir) {
            Remove-Item -Recurse -Force $TargetDir
        }
        New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

        if ($Src.SourceDir -eq ".") {
            # 根目录：复制所有包含 SKILL.md 的子目录
            Get-ChildItem -Directory $SourcePath | Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } | ForEach-Object {
                $Dest = Join-Path $TargetDir $_.Name
                Copy-Item -Recurse -Force $_.FullName $Dest
            }
        } elseif ($Src.SourceDir -eq "SKILL.md") {
            # 单文件技能：复制整个仓库（去除 .git）
            if (Test-Path (Join-Path $CloneDir ".git")) {
                Remove-Item -Recurse -Force (Join-Path $CloneDir ".git")
            }
            Copy-Item -Recurse -Force "$CloneDir\*" $TargetDir
        } elseif ($Src.Name -eq "claude-plugins-official") {
            # 特殊处理：plugins/* 和 external_plugins/*
            foreach ($SubDir in @("plugins", "external_plugins")) {
                $SubPath = Join-Path $SourcePath $SubDir
                if (Test-Path $SubPath) {
                    Get-ChildItem -Directory $SubPath | ForEach-Object {
                        Get-ChildItem -Directory $_.FullName | Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } | ForEach-Object {
                            $Dest = Join-Path $TargetDir $_.Name
                            Copy-Item -Recurse -Force $_.FullName $Dest
                        }
                    }
                }
            }
        } else {
            # 标准：复制 SourceDir 下包含 SKILL.md 的子目录
            Get-ChildItem -Directory $SourcePath | Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } | ForEach-Object {
                $Dest = Join-Path $TargetDir $_.Name
                Copy-Item -Recurse -Force $_.FullName $Dest
            }
        }

        Write-Host "[OK] $($Src.Name) 已复制"
        $SkillIndex++
    }

    Write-Host ""
    Write-Host ""
    Write-Host "[参考来源]"
    Write-Host "[参考 1/1] awesome-design-md"
    $RefCloneDir = Join-Path $TmpDir "awesome-design-md"
    $RefTargetDir = Join-Path $RepoDir "external" "awesome-design-md"

    try {
        Invoke-Git @("clone", "--depth", "1", "--branch", "main", "https://github.com/VoltAgent/awesome-design-md.git", $RefCloneDir) -IgnoreExitCode | Out-Null
    } catch {
        $SourceErrors++
        Write-Host "[WARN] awesome-design-md 下载失败"
    }

    $RefSourcePath = Join-Path $RefCloneDir "design-md"
    if (Test-Path $RefSourcePath) {
        if (Test-Path $RefTargetDir) {
            Remove-Item -Recurse -Force $RefTargetDir
        }
        New-Item -ItemType Directory -Path $RefTargetDir -Force | Out-Null
        Get-ChildItem -Directory $RefSourcePath | ForEach-Object {
            $Dest = Join-Path $RefTargetDir $_.Name
            Copy-Item -Recurse -Force $_.FullName $Dest
        }
        Write-Host "[OK] awesome-design-md 已复制"
    } else {
        $SourceErrors++
        Write-Host "[WARN] awesome-design-md 下载失败或没有找到 design-md 目录"
    }
    Write-Host ""

    # 步骤 5
    Write-Host "[步骤 5/7] 清理临时目录..."
    if (Test-Path $TmpDir) {
        Remove-Item -Recurse -Force $TmpDir
    }
    Write-Host "[OK] 临时目录已清理"
    Write-Host ""

    # 步骤 6
    Write-Host "[步骤 6/7] 检查这次更新有没有实际变化..."
    try {
        Invoke-Git @("add", "-A")
    } catch {
        $Status = "ERROR"
        $Detail = "git add -A 失败。通常是文件权限、路径或 Git 状态异常。"
        throw "git-add-failed"
    }

    $DiffExit = 0
    try {
        Invoke-Git @("diff", "--cached", "--quiet") -IgnoreExitCode | Out-Null
        $DiffExit = $LASTEXITCODE
    } catch {
        $DiffExit = $LASTEXITCODE
    }

    if ($DiffExit -eq 0) {
        if ($SourceErrors -eq 0) {
            $Status = "NO_CHANGES"
            $Detail = "外部资源没有新变化，所以无需提交和推送。"
        } else {
            $Status = "PARTIAL"
            $Detail = "部分来源下载失败，而且没有检测到可提交的新变化。"
        }
        throw "no-changes"
    }
    if ($DiffExit -ne 1) {
        $Status = "ERROR"
        $Detail = "检查暂存区是否有变更时失败。"
        throw "diff-check-failed"
    }
    Write-Host "[OK] 检测到外部来源有变化"
    Write-Host ""

    $CommitTs = Get-Date -Format "yyyy-MM-dd HH:mm"
    $CommitMsg = "sync external resources $CommitTs"

    # 步骤 7
    Write-Host "[步骤 7/7] 提交并推送更新结果..."
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

    if ($SourceErrors -eq 0) {
        $Status = "SUCCESS"
        $Detail = "外部资源已同步，变更已提交并推送。"
    } else {
        $Status = "PARTIAL"
        $Detail = "已提交并推送可用更新，但有部分来源下载失败。"
    }

catch {
    if ($_ -is [System.Management.Automation.ErrorRecord] -and $_.Exception.Message -eq "cancelled") {
        # 已处理
    } elseif ($_.Exception.Message -notin @("no-changes", "cancelled")) {
        # 错误已在上面设置 Status 和 Detail
    }
}
finally {
    # --- 结束显示 ---
    Write-Host ""
    Write-Line
    switch ($Status) {
        "SUCCESS"    { Write-Host "结果：更新并推送成功" }
        "NO_CHANGES" { Write-Host "结果：没有新变化" }
        "CANCELLED"  { Write-Host "结果：已取消" }
        "PARTIAL"    { Write-Host "结果：部分成功，需要查看警告" }
        default      { Write-Host "结果：执行失败" }
    }
    Write-Host "说明：$Detail"
    if ($SourceErrors -ne 0) {
        Write-Host "来源警告数量：$SourceErrors"
    }
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

    Write-Host "[重新推送当前分支]"
    Write-Host "git -C `"$RepoDir`" push origin $Branch"
    Write-Host ""

    Write-Host "[先拉最新再推]"
    Write-Host "git -C `"$RepoDir`" pull --rebase origin $Branch"
    Write-Host "git -C `"$RepoDir`" push origin $Branch"
    Write-Host ""

    Write-Host "[检查 GitHub SSH 登录]"
    Write-Host "ssh -T git@github.com"
    Write-Host ""

    Write-Host "[手动运行 Unix 版更新脚本]"
    Write-Host "bash `"$RepoDir\update.sh`""
    Write-Host ""

    Write-Host "[删除临时目录，常用于上次更新中断]"
    Write-Host "Remove-Item -Recurse -Force `"$RepoDir\.tmp-skills`""
    Write-Host ""

    if ($Status -eq "ERROR") {
        Write-Line
        Write-Host "这次失败时，最常见的排查顺序："
        Write-Host "1. 如果 clone 失败，先确认网络能访问 GitHub"
        Write-Host "2. 如果 push 失败，执行：ssh -T git@github.com"
        Write-Host "3. 如果远端比本地新，执行 pull --rebase 后再 push"
        Write-Host "4. 如果提示作者身份未知，先配置 git user.name 和 user.email"
        Write-Host "5. 如果临时目录删不掉，关闭占用窗口后执行 Remove-Item 命令"
        Write-Host ""
        if ($CommitDone -eq 1) {
            Write-Host "补充说明：本地提交已经创建成功，只是还没有推送到远端。"
            Write-Host "你通常只需要修复权限或冲突问题后，再执行："
            Write-Host "git -C `"$RepoDir`" push origin $Branch"
            Write-Host ""
        }
    }

    Write-Line
    Write-Host "按 Enter 键关闭窗口..."
    Read-Host | Out-Null
    exit 0
}
