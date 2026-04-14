@echo off
:: Windows - Git Bash required
:: Run in Git Bash for best compatibility
:: Usage: double-click or run in terminal

cd /d "%~dp0"

echo >>> Committing and pushing all changes...
git add -A

git diff --cached --quiet
if %errorlevel% equ 0 (
    echo >>> No changes, skip
    exit /b 0
)

git commit -m "sync %date:~0,10% %time:~0,5%"
git push

echo >>> Done
pause
