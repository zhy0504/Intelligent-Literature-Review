@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo    智能文献系统启动脚本
echo ========================================
echo.

cd /d "%~dp0"

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python
    pause
    exit /b 1
)

REM 检查虚拟环境
if not exist "venv" (
    echo [信息] 正在创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo [成功] 虚拟环境创建成功
)

REM 检查虚拟环境中的Python
echo [信息] 使用虚拟环境中的Python...
if not exist "venv\Scripts\python.exe" (
    echo [错误] 虚拟环境Python不存在
    pause
    exit /b 1
)

REM 检查依赖文件
if not exist "requirements.txt" (
    echo [错误] 未找到requirements.txt文件
    pause
    exit /b 1
)

REM 安装依赖包（如果需要）
echo [信息] 检查依赖包...
venv\Scripts\python.exe -m pip install -r requirements.txt

REM 显示当前Python路径
echo [信息] 当前Python路径:
venv\Scripts\python.exe -c "import sys; print(sys.executable)"

REM 启动系统
echo.
echo [信息] 正在启动智能文献系统...
venv\Scripts\python.exe start.py %*

pause