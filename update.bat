@echo off
:: Windows - Git Bash required
:: Usage: double-click or run in terminal

cd /d "%~dp0"

echo >>> Updating all submodules...
git submodule update --remote

git diff --quiet external/
if %errorlevel% equ 0 (
    echo >>> Already up to date, skip
    exit /b 0
)

echo >>> Changes detected, pushing...
git add external/
git commit -m "update submodules %date:~0,10%"
git push

echo >>> Done
pause
