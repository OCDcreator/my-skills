@echo off
:: Windows - Git Bash required
cd /d "%~dp0"

echo ^>^> Fetching remote...
git fetch origin

echo ^>^> Overwriting local...
git reset --hard origin/main

echo ^>^> Done
pause
