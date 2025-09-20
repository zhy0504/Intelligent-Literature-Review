@echo off
setlocal EnableExtensions
chcp 65001 >nul

REM Smart Literature System - Enhanced PowerShell Bypass Launcher

echo [INFO] Starting Smart Literature System...
echo [INFO] Bypassing PowerShell execution policy restrictions...

REM Get script directory dynamically
set "ROOT=%~dp0"
set "PS1=%ROOT%start.ps1"

REM Check if PowerShell script exists
if not exist "%PS1%" (
    echo [ERROR] PowerShell script not found: %PS1%
    pause
    exit /b 1
)

REM Try PowerShell 7 first, fallback to Windows PowerShell
where pwsh >nul 2>&1
if %errorlevel%==0 (
    set "SHELL=pwsh"
    echo [INFO] Using PowerShell 7
) else (
    set "SHELL=powershell"
    echo [INFO] Using Windows PowerShell
)

REM Unblock file from internet zone (silent)
"%SHELL%.exe" -NoProfile -ExecutionPolicy Bypass -Command "Unblock-File -LiteralPath '%PS1%'" >nul 2>&1

REM Change to script directory and execute
pushd "%ROOT%"
"%SHELL%.exe" -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
set "RC=%errorlevel%"
popd

endlocal & exit /b %RC%