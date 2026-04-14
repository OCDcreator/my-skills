@echo off
:: Windows - Git Bash required
:: Run in Git Bash for best compatibility, or use update.sh directly

cd /d "%~dp0"

echo =========================================
echo   My-Skills Auto Sync
echo =========================================
echo.

set REPO_ROOT=%cd%
set TMP_DIR=%REPO_ROOT%\.tmp-skills

:: Remove old temp dir
if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%"
mkdir "%TMP_DIR%"

set total_copied=0

:: --- anthropics/skills ---
echo ^>^> [anthropics-skills] Cloning...
git clone --depth 1 --branch main https://github.com/anthropics/skills.git "%TMP_DIR%\anthropics-skills" 2>nul
if exist "%TMP_DIR%\anthropics-skills\skills" (
    echo     Copying skills...
    xcopy /e /i /y /q "%TMP_DIR%\anthropics-skills\skills" "%REPO_ROOT%\anthropics-skills\" >nul
    echo     Done
) else (
    echo     ERROR: Failed to clone or skills dir not found
)
echo.

:: --- awesome-claude-skills ---
echo ^>^> [awesome-claude-skills] Cloning...
git clone --depth 1 --branch master https://github.com/ComposioHQ/awesome-claude-skills.git "%TMP_DIR%\awesome-claude-skills" 2>nul
if exist "%TMP_DIR%\awesome-claude-skills" (
    echo     Copying skills...
    :: Copy root-level skill directories (those with SKILL.md)
    for /d %%d in ("%TMP_DIR%\awesome-claude-skills\*") do (
        if exist "%%d\SKILL.md" (
            xcopy /e /i /y /q "%%d" "%REPO_ROOT%\awesome-claude-skills\%%~nxd\" >nul 2>nul
        )
    )
    echo     Done
) else (
    echo     ERROR: Failed to clone
)
echo.

:: --- claude-plugins-official ---
echo ^>^> [claude-plugins-official] Cloning...
git clone --depth 1 --branch main https://github.com/anthropics/claude-plugins-official.git "%TMP_DIR%\claude-plugins-official" 2>nul
if exist "%TMP_DIR%\claude-plugins-official\plugins" (
    echo     Copying skills...
    :: Walk plugins/*/skills/*/SKILL.md structure
    for /d %%p in ("%TMP_DIR%\claude-plugins-official\plugins\*") do (
        for /d %%s in ("%%p\skills\*") do (
            if exist "%%s\SKILL.md" (
                xcopy /e /i /y /q "%%s" "%REPO_ROOT%\claude-plugins-official\%%~nxs\" >nul 2>nul
            )
        )
    )
    :: Also check external_plugins/*/skills/*/SKILL.md
    for /d %%p in ("%TMP_DIR%\claude-plugins-official\external_plugins\*") do (
        for /d %%s in ("%%p\skills\*") do (
            if exist "%%s\SKILL.md" (
                xcopy /e /i /y /q "%%s" "%REPO_ROOT%\claude-plugins-official\%%~nxs\" >nul 2>nul
            )
        )
    )
    echo     Done
) else (
    echo     ERROR: Failed to clone or plugins dir not found
)
echo.

:: --- axton-obsidian-visual-skills ---
echo ^>^> [axton-obsidian-visual-skills] Cloning...
git clone --depth 1 --branch main https://github.com/axtonliu/axton-obsidian-visual-skills.git "%TMP_DIR%\axton-obsidian-visual-skills" 2>nul
if exist "%TMP_DIR%\axton-obsidian-visual-skills" (
    echo     Copying skills...
    for /d %%d in ("%TMP_DIR%\axton-obsidian-visual-skills\*") do (
        if exist "%%d\SKILL.md" (
            xcopy /e /i /y /q "%%d" "%REPO_ROOT%\axton-obsidian-visual-skills\%%~nxd\" >nul 2>nul
        )
    )
    echo     Done
) else (
    echo     ERROR: Failed to clone
)
echo.

:: Cleanup
rmdir /s /q "%TMP_DIR%" 2>nul

:: Check changes
git diff --quiet
if %errorlevel% equ 0 (
    git diff --cached --quiet
    if %errorlevel% equ 0 (
        echo ^>^> No changes, nothing to commit
        pause
        exit /b 0
    )
)

echo ^>^> Changes detected:
git status --short
echo.

git add -A
git commit -m "sync skills %date:~0,10% %time:~0,5%"
git push

echo.
echo ^>^> Done! Pushed to remote.
pause
