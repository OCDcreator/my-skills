@echo off
setlocal
:: Windows - Git Bash required
:: Run in Git Bash for best compatibility
:: Usage: double-click or run in terminal

cd /d "%~dp0"

echo [INFO] Committing and pushing all changes...
git add -A
if errorlevel 1 (
    echo [ERROR] git add failed
    exit /b 1
)

git diff --cached --quiet
if errorlevel 1 goto commit_and_push
if errorlevel 0 (
    echo [INFO] No changes, skip
    exit /b 0
)
echo [ERROR] git diff --cached --quiet failed
exit /b 1

:commit_and_push
git commit -m "sync %date:~0,10% %time:~0,5%"
if errorlevel 1 (
    echo [ERROR] git commit failed
    exit /b 1
)

git push
if errorlevel 1 (
    echo [ERROR] git push failed
    exit /b 1
)

echo [INFO] Done
pause
