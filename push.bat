@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title my-skills - Git Push Helper

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
if errorlevel 1 (
    set "STATUS=ERROR"
    set "DETAIL=无法进入脚本所在目录。"
    goto :finish
)

set "REPO_DIR=%CD%"
set "STATUS=SUCCESS"
set "DETAIL=已成功提交并推送到远端。"
set "BRANCH=main"
set "REMOTE_URL="
set "COMMIT_TS="
set "COMMIT_MSG="
set "COMMIT_DONE=0"

call :line
echo my-skills 一键推送助手
echo.
echo 这个窗口会直接告诉你：
echo 1. 当前做到哪一步
echo 2. 如果失败，最常见的原因是什么
echo 3. 你下一步可以直接复制什么命令
echo.
echo 当前仓库目录：
echo %REPO_DIR%
call :line
echo.

echo [步骤 1/5] 检查 Git 是否可用...
where git >nul 2>nul
if errorlevel 1 (
    set "STATUS=ERROR"
    set "DETAIL=没有找到 Git。请先安装 Git for Windows，再重新双击这个脚本。"
    goto :finish
)
echo [OK] 已找到 Git
echo.

echo [步骤 2/5] 检查当前目录是不是 Git 仓库...
git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
    set "STATUS=ERROR"
    set "DETAIL=当前目录不是 Git 仓库，所以无法提交或推送。"
    goto :finish
)
for /f "delims=" %%i in ('git branch --show-current 2^>nul') do set "BRANCH=%%i"
for /f "delims=" %%i in ('git remote get-url origin 2^>nul') do set "REMOTE_URL=%%i"
if not defined BRANCH set "BRANCH=main"
if not defined REMOTE_URL (
    set "STATUS=ERROR"
    set "DETAIL=没有找到名为 origin 的远端仓库，所以没有可推送的目标。"
    goto :finish
)
echo [OK] 当前分支: !BRANCH!
echo [OK] 远端地址: !REMOTE_URL!
echo.

echo [步骤 3/5] 暂存所有变更 ^(git add -A^)...
git add -A
if errorlevel 1 (
    set "STATUS=ERROR"
    set "DETAIL=git add -A 执行失败。通常是文件权限、路径或 Git 状态异常。"
    goto :finish
)
echo [OK] 已完成暂存
echo.

echo [步骤 4/5] 检查这次有没有新内容需要提交...
git diff --cached --quiet
set "DIFF_EXIT=%errorlevel%"
if "%DIFF_EXIT%"=="0" (
    set "STATUS=NO_CHANGES"
    set "DETAIL=没有检测到新的变更，所以这次无需提交和推送。"
    goto :finish
)
if not "%DIFF_EXIT%"=="1" (
    set "STATUS=ERROR"
    set "DETAIL=检查暂存区是否有变更时失败。"
    goto :finish
)
echo [OK] 检测到有新变更，准备提交
echo.

for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm'" 2^>nul`) do set "COMMIT_TS=%%i"
if not defined COMMIT_TS set "COMMIT_TS=%date% %time%"
set "COMMIT_MSG=sync !COMMIT_TS!"

echo [步骤 5/5] 创建提交并推送到远端...
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
echo [OK] 已成功推送到远端
goto :finish

:finish
echo.
call :line
if /i "%STATUS%"=="SUCCESS" (
    echo 结果：推送成功
) else if /i "%STATUS%"=="NO_CHANGES" (
    echo 结果：没有变更，不需要推送
) else (
    echo 结果：执行失败
)
echo 说明：%DETAIL%
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

echo [看最近提交]
echo git -C "%REPO_DIR%" log --oneline --decorate -n 5
echo.

echo [重新推送当前分支]
echo git -C "%REPO_DIR%" push origin !BRANCH!
echo.

echo [先拉最新再推 ^(常用于“远端比本地更新”^)]
echo git -C "%REPO_DIR%" pull --rebase origin !BRANCH!
echo git -C "%REPO_DIR%" push origin !BRANCH!
echo.

echo [检查 Git 身份信息 ^(常用于 commit 失败^)]
echo git -C "%REPO_DIR%" config user.name
echo git -C "%REPO_DIR%" config user.email
echo.

echo [设置 Git 身份信息 ^(把名字和邮箱改成你自己的^)]
echo git -C "%REPO_DIR%" config user.name "你的名字"
echo git -C "%REPO_DIR%" config user.email "你的邮箱"
echo.

echo [检查 GitHub SSH 登录 ^(常用于 push 权限失败^)]
echo ssh -T git@github.com
echo.

if /i "%STATUS%"=="ERROR" (
    call :line
    echo 这次失败时，最常见的排查顺序：
    echo 1. 先复制执行：git -C "%REPO_DIR%" status --short --branch
    echo 2. 再复制执行：git -C "%REPO_DIR%" remote -v
    echo 3. 如果提示远端有新提交，执行：
    echo    git -C "%REPO_DIR%" pull --rebase origin !BRANCH!
    echo    git -C "%REPO_DIR%" push origin !BRANCH!
    echo 4. 如果提示权限或公钥问题，执行：ssh -T git@github.com
    echo 5. 如果提示作者身份未知，执行上面的 user.name / user.email 设置命令
    echo.
    if "%COMMIT_DONE%"=="1" (
        echo 补充说明：本地提交已经创建成功，只是还没有推送到远端。
        echo 你通常只需要修复权限/冲突问题后，再执行：
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
