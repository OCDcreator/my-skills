@echo off
:: Windows - Git Bash required
:: Usage: double-click or run in terminal

cd /d "%~dp0"

echo >>> Fetching remote...
git fetch origin

echo >>> Overwriting local...
git reset --hard origin/main

echo >>> Updating submodules...
git submodule update --init --recursive

echo >>> Done
pause
