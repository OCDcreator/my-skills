@echo off
REM build_review_gui.bat — 编译 review_gui.exe
REM
REM 流程：
REM   1. 定位 EUI-NEO 源码树（首次会 clone）
REM   2. 把 review_gui 接入 EUI-NEO 树（add_subdirectory）
REM   3. CMake 配置 + 编译
REM   4. 产物 review_gui.exe 复制到 ../bin/
REM
REM 用法：在 review_gui 目录下运行 build_review_gui.bat
REM 前置：已安装 VS 2022 (MSVC 14.44+) + Git + CMake 3.14+

setlocal enabledelayedexpansion

REM === 路径设置 ===
set "REVIEW_DIR=%~dp0"
set "REVIEW_DIR=%REVIEW_DIR:~0,-1%"
set "SKILL_DIR=%REVIEW_DIR%\.."
set "EUI_ROOT=C:\Users\lt\.cache\eui-neo-src"
set "BUILD_DIR=%EUI_ROOT%\build"

echo === [1/5] 检查 EUI-NEO 源码树 ===
if not exist "%EUI_ROOT%\CMakeLists.txt" (
    echo 首次运行，clone EUI-NEO 源码到 %EUI_ROOT%
    git clone --depth 1 https://github.com/sudoevolve/EUI-NEO.git "%EUI_ROOT%"
    if errorlevel 1 (echo CLONE_FAILED & exit /b 1)
) else (
    echo EUI-NEO 源码已存在: %EUI_ROOT%
)

echo === [2/5] 接入 review_gui 到 EUI-NEO 树 ===
REM 复制 review_gui 源码到 EUI-NEO 树下（避免污染源 skill 目录）
set "TARGET_SUB=%EUI_ROOT%\review_gui_build"
if not exist "%TARGET_SUB%" mkdir "%TARGET_SUB%"
copy /y "%REVIEW_DIR%\review_gui.cpp" "%TARGET_SUB%\review_gui.cpp" >nul
copy /y "%REVIEW_DIR%\CMakeLists.txt" "%TARGET_SUB%\CMakeLists.txt" >nul

REM 在 EUI-NEO 根 CMakeLists 追加 add_subdirectory（幂等：检测标记）
findstr /c:"review_gui_build" "%EUI_ROOT%\CMakeLists.txt" >nul
if errorlevel 1 (
    echo add_subdirectory(review_gui_build^) >> "%EUI_ROOT%\CMakeLists.txt"
    echo 已追加 add_subdirectory
)

echo === [3/5] 加载 MSVC 环境 ===
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x64 >nul 2>&1
if errorlevel 1 (echo VCVARS_FAILED & exit /b 1)
echo MSVC ready

echo === [4/5] CMake 配置 ===
if not exist "%BUILD_DIR%\CMakeCache.txt" (
    cmake -S "%EUI_ROOT%" -B "%BUILD_DIR%" -G "Ninja" -DCMAKE_BUILD_TYPE=Release -DEUI_BUILD_APPS=OFF -DEUI_ENABLE_INSTALL=OFF -DEUI_DEPS_MODE=bundled
    if errorlevel 1 (echo CONFIGURE_FAILED & exit /b 1)
) else (
    echo 复用已有配置
)

echo === [5/5] 编译 review_gui ===
cmake --build "%BUILD_DIR%" --config Release --target review_gui
if errorlevel 1 (echo BUILD_FAILED & exit /b 1)

echo === 复制产物到 bin/ ===
if not exist "%SKILL_DIR%\bin" mkdir "%SKILL_DIR%\bin"
copy /y "%BUILD_DIR%\review_gui.exe" "%SKILL_DIR%\bin\review_gui.exe"
echo.
echo BUILD_OK: %SKILL_DIR%\bin\review_gui.exe
dir "%SKILL_DIR%\bin\review_gui.exe"
