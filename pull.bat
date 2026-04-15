@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title my-skills - Git Pull Overwrite Helper

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
if errorlevel 1 (
    set "STATUS=ERROR"
    set "DETAIL=无法进入脚本所在目录。"
    goto :finish
)

set "REPO_DIR=%CD%"
set "STATUS=SUCCESS"
set "DETAIL=已用远端 origin/main 覆盖本地内容。"
set "BRANCH=main"
set "REMOTE_URL="

call :line
echo my-skills 一键拉取覆盖助手
echo.
echo 这个脚本的用途：
echo 1. 从 GitHub 拉取最新远端信息
echo 2. 用远端 origin/main 强制覆盖本地 main
echo 3. 如果本地有未提交修改，这些修改会被丢弃
echo.
echo 当前仓库目录：
echo %REPO_DIR%
call :line
echo.

echo [重要提醒]
echo 这是一个“覆盖本地”的脚本，不是普通同步。
echo 如果你本地有没提交的修改，运行后可能找不回来。
echo.
echo 如果你只是想保存本地修改并上传，请关闭窗口，改用 push.bat。
echo.
set /p "CONFIRM=确认要用远端覆盖本地吗？请输入 Y 后回车继续："
if /i not "%CONFIRM%"=="Y" (
    set "STATUS=CANCELLED"
    set "DETAIL=你没有输入 Y，脚本已取消，没有改动任何文件。"
    goto :finish
)
echo.

echo [步骤 1/4] 检查 Git 是否可用...
where git >nul 2>nul
if errorlevel 1 (
    set "STATUS=ERROR"
    set "DETAIL=没有找到 Git。请先安装 Git for Windows，再重新双击这个脚本。"
    goto :finish
)
echo [OK] 已找到 Git
echo.

echo [步骤 2/4] 检查当前目录是不是 Git 仓库...
git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
    set "STATUS=ERROR"
    set "DETAIL=当前目录不是 Git 仓库，所以无法拉取远端内容。"
    goto :finish
)
for /f "delims=" %%i in ('git branch --show-current 2^>nul') do set "BRANCH=%%i"
for /f "delims=" %%i in ('git remote get-url origin 2^>nul') do set "REMOTE_URL=%%i"
if not defined BRANCH set "BRANCH=main"
if not defined REMOTE_URL (
    set "STATUS=ERROR"
    set "DETAIL=没有找到名为 origin 的远端仓库，所以不知道从哪里拉取。"
    goto :finish
)
echo [OK] 当前分支: !BRANCH!
echo [OK] 远端地址: !REMOTE_URL!
echo.

echo [步骤 3/4] 从远端获取最新信息...
git fetch origin
if errorlevel 1 (
    set "STATUS=ERROR"
    set "DETAIL=git fetch 失败。常见原因是网络、GitHub SSH 权限或远端地址错误。"
    goto :finish
)
echo [OK] 已获取远端信息
echo.

echo [步骤 4/4] 用 origin/main 覆盖本地...
git rev-parse --verify origin/main >nul 2>nul
if errorlevel 1 (
    set "STATUS=ERROR"
    set "DETAIL=远端没有 origin/main，可能默认分支不是 main。请先查看 git branch -r。"
    goto :finish
)
git reset --hard origin/main
if errorlevel 1 (
    set "STATUS=ERROR"
    set "DETAIL=git reset --hard origin/main 失败。可能有文件被占用或 Git 状态异常。"
    goto :finish
)
echo [OK] 本地已覆盖为 origin/main
goto :finish

:finish
echo.
call :line
if /i "%STATUS%"=="SUCCESS" (
    echo 结果：拉取覆盖成功
) else if /i "%STATUS%"=="CANCELLED" (
    echo 结果：已取消
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

echo [查看远端分支]
echo git -C "%REPO_DIR%" branch -r
echo.

echo [普通拉取，不强制覆盖]
echo git -C "%REPO_DIR%" pull --rebase origin main
echo.

echo [强制覆盖本地，谨慎使用]
echo git -C "%REPO_DIR%" fetch origin
echo git -C "%REPO_DIR%" reset --hard origin/main
echo.

echo [检查 GitHub SSH 登录]
echo ssh -T git@github.com
echo.

if /i "%STATUS%"=="ERROR" (
    call :line
    echo 这次失败时，最常见的排查顺序：
    echo 1. 先复制执行：git -C "%REPO_DIR%" status --short --branch
    echo 2. 再复制执行：git -C "%REPO_DIR%" remote -v
    echo 3. 如果提示权限或公钥问题，执行：ssh -T git@github.com
    echo 4. 如果提示没有 origin/main，执行：git -C "%REPO_DIR%" branch -r
    echo 5. 如果文件被占用，关闭编辑器或同步工具后重试
    echo.
)

call :line
echo 按任意键关闭窗口...
pause >nul
exit /b 0

:line
echo ============================================================
exit /b 0
