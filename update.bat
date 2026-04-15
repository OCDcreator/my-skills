@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title my-skills - External Skills Update Helper

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
if errorlevel 1 (
    set "STATUS=ERROR"
    set "DETAIL=无法进入脚本所在目录。"
    goto :finish
)

set "REPO_DIR=%CD%"
set "TMP_DIR=%REPO_DIR%\.tmp-skills"
set "STATUS=SUCCESS"
set "DETAIL=外部技能已同步，变更已提交并推送。"
set "BRANCH=main"
set "REMOTE_URL="
set "COMMIT_TS="
set "COMMIT_MSG="
set "SOURCE_ERRORS=0"
set "COMMIT_DONE=0"

call :line
echo my-skills 外部技能更新助手
echo.
echo 这个脚本的用途：
echo 1. 从多个 GitHub 技能源下载最新内容
echo 2. 复制到 external 目录
echo 3. 如果有变化，就自动提交并推送
echo.
echo 当前仓库目录：
echo %REPO_DIR%
call :line
echo.

echo [重要提醒]
echo 这个脚本会访问 GitHub，并可能修改 external 目录。
echo 如果你只是想上传自己改的 custom 技能，请关闭窗口，改用 push.bat。
echo.
set /p "CONFIRM=确认要更新外部技能并推送吗？请输入 Y 后回车继续："
if /i not "%CONFIRM%"=="Y" (
    set "STATUS=CANCELLED"
    set "DETAIL=你没有输入 Y，脚本已取消，没有改动任何文件。"
    goto :finish
)
echo.

echo [步骤 1/7] 检查 Git 是否可用...
where git >nul 2>nul
if errorlevel 1 (
    set "STATUS=ERROR"
    set "DETAIL=没有找到 Git。请先安装 Git for Windows，再重新双击这个脚本。"
    goto :finish
)
echo [OK] 已找到 Git
echo.

echo [步骤 2/7] 检查当前目录是不是 Git 仓库...
git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
    set "STATUS=ERROR"
    set "DETAIL=当前目录不是 Git 仓库，所以无法更新、提交或推送。"
    goto :finish
)
for /f "delims=" %%i in ('git branch --show-current 2^>nul') do set "BRANCH=%%i"
for /f "delims=" %%i in ('git remote get-url origin 2^>nul') do set "REMOTE_URL=%%i"
if not defined BRANCH set "BRANCH=main"
if not defined REMOTE_URL (
    set "STATUS=ERROR"
    set "DETAIL=没有找到名为 origin 的远端仓库，所以无法推送更新结果。"
    goto :finish
)
echo [OK] 当前分支: !BRANCH!
echo [OK] 远端地址: !REMOTE_URL!
echo.

echo [步骤 3/7] 准备临时下载目录...
if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%"
mkdir "%TMP_DIR%"
if errorlevel 1 (
    set "STATUS=ERROR"
    set "DETAIL=无法创建临时目录 .tmp-skills。可能是权限问题或文件被占用。"
    goto :finish
)
if not exist "%REPO_DIR%\external" mkdir "%REPO_DIR%\external"
echo [OK] 临时目录已准备
echo.

echo [步骤 4/7] 下载并复制外部技能...
echo.

echo [1/6] anthropics-skills
git clone --depth 1 --branch main https://github.com/anthropics/skills.git "%TMP_DIR%\anthropics-skills"
if exist "%TMP_DIR%\anthropics-skills\skills" (
    if not exist "%REPO_DIR%\external\anthropics-skills" mkdir "%REPO_DIR%\external\anthropics-skills"
    xcopy /e /i /y /q "%TMP_DIR%\anthropics-skills\skills" "%REPO_DIR%\external\anthropics-skills\" >nul
    echo [OK] anthropics-skills 已复制
) else (
    set /a SOURCE_ERRORS+=1
    echo [WARN] anthropics-skills 下载失败或没有找到 skills 目录
)
echo.

echo [2/6] awesome-claude-skills
git clone --depth 1 --branch master https://github.com/ComposioHQ/awesome-claude-skills.git "%TMP_DIR%\awesome-claude-skills"
if exist "%TMP_DIR%\awesome-claude-skills" (
    if not exist "%REPO_DIR%\external\awesome-claude-skills" mkdir "%REPO_DIR%\external\awesome-claude-skills"
    for /d %%d in ("%TMP_DIR%\awesome-claude-skills\*") do (
        if exist "%%d\SKILL.md" (
            xcopy /e /i /y /q "%%d" "%REPO_DIR%\external\awesome-claude-skills\%%~nxd\" >nul 2>nul
        )
    )
    echo [OK] awesome-claude-skills 已复制
) else (
    set /a SOURCE_ERRORS+=1
    echo [WARN] awesome-claude-skills 下载失败
)
echo.

echo [3/6] claude-plugins-official
git clone --depth 1 --branch main https://github.com/anthropics/claude-plugins-official.git "%TMP_DIR%\claude-plugins-official"
if exist "%TMP_DIR%\claude-plugins-official\plugins" (
    if not exist "%REPO_DIR%\external\claude-plugins-official" mkdir "%REPO_DIR%\external\claude-plugins-official"
    for /d %%p in ("%TMP_DIR%\claude-plugins-official\plugins\*") do (
        for /d %%s in ("%%p\skills\*") do (
            if exist "%%s\SKILL.md" (
                xcopy /e /i /y /q "%%s" "%REPO_DIR%\external\claude-plugins-official\%%~nxs\" >nul 2>nul
            )
        )
    )
    for /d %%p in ("%TMP_DIR%\claude-plugins-official\external_plugins\*") do (
        for /d %%s in ("%%p\skills\*") do (
            if exist "%%s\SKILL.md" (
                xcopy /e /i /y /q "%%s" "%REPO_DIR%\external\claude-plugins-official\%%~nxs\" >nul 2>nul
            )
        )
    )
    echo [OK] claude-plugins-official 已复制
) else (
    set /a SOURCE_ERRORS+=1
    echo [WARN] claude-plugins-official 下载失败或没有找到 plugins 目录
)
echo.

echo [4/6] baoyu-skills
git clone --depth 1 --branch main https://github.com/JimLiu/baoyu-skills.git "%TMP_DIR%\baoyu-skills"
if exist "%TMP_DIR%\baoyu-skills\skills" (
    if not exist "%REPO_DIR%\external\baoyu-skills" mkdir "%REPO_DIR%\external\baoyu-skills"
    xcopy /e /i /y /q "%TMP_DIR%\baoyu-skills\skills" "%REPO_DIR%\external\baoyu-skills\" >nul
    echo [OK] baoyu-skills 已复制
) else (
    set /a SOURCE_ERRORS+=1
    echo [WARN] baoyu-skills 下载失败或没有找到 skills 目录
)
echo.

echo [5/6] axton-obsidian-visual-skills
git clone --depth 1 --branch main https://github.com/axtonliu/axton-obsidian-visual-skills.git "%TMP_DIR%\axton-obsidian-visual-skills"
if exist "%TMP_DIR%\axton-obsidian-visual-skills" (
    if not exist "%REPO_DIR%\external\axton-obsidian-visual-skills" mkdir "%REPO_DIR%\external\axton-obsidian-visual-skills"
    for /d %%d in ("%TMP_DIR%\axton-obsidian-visual-skills\*") do (
        if exist "%%d\SKILL.md" (
            xcopy /e /i /y /q "%%d" "%REPO_DIR%\external\axton-obsidian-visual-skills\%%~nxd\" >nul 2>nul
        )
    )
    echo [OK] axton-obsidian-visual-skills 已复制
) else (
    set /a SOURCE_ERRORS+=1
    echo [WARN] axton-obsidian-visual-skills 下载失败
)
echo.

echo [6/7] kepano-obsidian-skills
git clone --depth 1 --branch main https://github.com/kepano/obsidian-skills.git "%TMP_DIR%\kepano-obsidian-skills"
if exist "%TMP_DIR%\kepano-obsidian-skills\skills" (
    if not exist "%REPO_DIR%\external\kepano-obsidian-skills" mkdir "%REPO_DIR%\external\kepano-obsidian-skills"
    xcopy /e /i /y /q "%TMP_DIR%\kepano-obsidian-skills\skills" "%REPO_DIR%\external\kepano-obsidian-skills\" >nul
    echo [OK] kepano-obsidian-skills 已复制
) else (
    set /a SOURCE_ERRORS+=1
    echo [WARN] kepano-obsidian-skills 下载失败或没有找到 skills 目录
)
echo.

echo [7/7] taste-skill
git clone --depth 1 --branch master https://github.com/Leonxlnx/taste-skill.git "%TMP_DIR%\taste-skill"
if exist "%TMP_DIR%\taste-skill\skills" (
    if not exist "%REPO_DIR%\external\taste-skill" mkdir "%REPO_DIR%\external\taste-skill"
    xcopy /e /i /y /q "%TMP_DIR%\taste-skill\skills" "%REPO_DIR%\external\taste-skill\" >nul
    echo [OK] taste-skill 已复制
) else (
    set /a SOURCE_ERRORS+=1
    echo [WARN] taste-skill 下载失败或没有找到 skills 目录
)
echo.

echo [步骤 5/7] 清理临时目录...
if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%"
echo [OK] 临时目录已清理
echo.

echo [步骤 6/7] 检查这次更新有没有实际变化...
git add -A
if errorlevel 1 (
    set "STATUS=ERROR"
    set "DETAIL=git add -A 失败。通常是文件权限、路径或 Git 状态异常。"
    goto :finish
)
git diff --cached --quiet
set "DIFF_EXIT=%errorlevel%"
if "%DIFF_EXIT%"=="0" (
    if "%SOURCE_ERRORS%"=="0" (
        set "STATUS=NO_CHANGES"
        set "DETAIL=外部技能没有新变化，所以无需提交和推送。"
    ) else (
        set "STATUS=PARTIAL"
        set "DETAIL=部分技能源下载失败，而且没有检测到可提交的新变化。"
    )
    goto :finish
)
if not "%DIFF_EXIT%"=="1" (
    set "STATUS=ERROR"
    set "DETAIL=检查暂存区是否有变更时失败。"
    goto :finish
)
echo [OK] 检测到外部技能有变化
echo.

for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm'" 2^>nul`) do set "COMMIT_TS=%%i"
if not defined COMMIT_TS set "COMMIT_TS=%date% %time%"
set "COMMIT_MSG=sync external skills !COMMIT_TS!"

echo [步骤 7/7] 提交并推送更新结果...
echo [INFO] 提交信息: !COMMIT_MSG!
git commit -m "!COMMIT_MSG!"
if errorlevel 1 (
    set "STATUS=ERROR"
    set "DETAIL=git commit 失败。常见原因是 Git 用户名/邮箱未配置，或提交钩子报错。"
    goto :finish
)
set "COMMIT_DONE=1"
echo [OK] 本地提交已创建
echo.

echo [INFO] 正在推送到 origin/!BRANCH! ...
git push origin !BRANCH!
if errorlevel 1 (
    set "STATUS=ERROR"
    set "DETAIL=git push 失败。常见原因是网络、SSH 权限、远端冲突，或当前账号无推送权限。"
    goto :finish
)
if "%SOURCE_ERRORS%"=="0" (
    set "STATUS=SUCCESS"
    set "DETAIL=外部技能已同步，变更已提交并推送。"
) else (
    set "STATUS=PARTIAL"
    set "DETAIL=已提交并推送可用更新，但有部分技能源下载失败。"
)
goto :finish

:finish
echo.
call :line
if /i "%STATUS%"=="SUCCESS" (
    echo 结果：更新并推送成功
) else if /i "%STATUS%"=="NO_CHANGES" (
    echo 结果：没有新变化
) else if /i "%STATUS%"=="CANCELLED" (
    echo 结果：已取消
) else if /i "%STATUS%"=="PARTIAL" (
    echo 结果：部分成功，需要查看警告
) else (
    echo 结果：执行失败
)
echo 说明：%DETAIL%
if not "%SOURCE_ERRORS%"=="0" echo 技能源警告数量：%SOURCE_ERRORS%
call :line
echo.

echo 当前仓库状态：
git status --short --branch 2>nul
echo.

echo 最近 5 条提交：
git log --oneline --decorate -n 5 2>nul
echo.

call :line
echo 如果你不确定下一步怎么做，可以直接复制下面这些命令：
call :line
echo.

echo [看仓库状态]
echo git -C "%REPO_DIR%" status --short --branch
echo.

echo [看远端地址]
echo git -C "%REPO_DIR%" remote -v
echo.

echo [重新推送当前分支]
echo git -C "%REPO_DIR%" push origin !BRANCH!
echo.

echo [先拉最新再推]
echo git -C "%REPO_DIR%" pull --rebase origin !BRANCH!
echo git -C "%REPO_DIR%" push origin !BRANCH!
echo.

echo [检查 GitHub SSH 登录]
echo ssh -T git@github.com
echo.

echo [手动运行 Unix 版更新脚本]
echo bash "%REPO_DIR%\update.sh"
echo.

echo [删除临时目录，常用于上次更新中断]
echo rmdir /s /q "%REPO_DIR%\.tmp-skills"
echo.

if /i "%STATUS%"=="ERROR" (
    call :line
    echo 这次失败时，最常见的排查顺序：
    echo 1. 如果 clone 失败，先确认网络能访问 GitHub
    echo 2. 如果 push 失败，执行：ssh -T git@github.com
    echo 3. 如果远端比本地新，执行 pull --rebase 后再 push
    echo 4. 如果提示作者身份未知，先配置 git user.name 和 user.email
    echo 5. 如果临时目录删不掉，关闭占用窗口后执行 rmdir 命令
    echo.
    if "%COMMIT_DONE%"=="1" (
        echo 补充说明：本地提交已经创建成功，只是还没有推送到远端。
        echo 你通常只需要修复权限或冲突问题后，再执行：
        echo git -C "%REPO_DIR%" push origin !BRANCH!
        echo.
    )
)

call :line
echo 按任意键关闭窗口...
pause >nul
exit /b 0

:line
echo ============================================================
exit /b 0
