# Smart Literature System PowerShell Startup Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Smart Literature System Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set current directory
Set-Location $PSScriptRoot

# Check Python installation
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python not found, please install Python first" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "[INFO] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create virtual environment" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "[SUCCESS] Virtual environment created successfully" -ForegroundColor Green
}

# Check virtual environment Python
Write-Host "[INFO] Using virtual environment Python..." -ForegroundColor Cyan
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "[ERROR] Virtual environment Python not found" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check requirements file
if (-not (Test-Path "requirements.txt")) {
    Write-Host "[ERROR] requirements.txt file not found" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Install dependencies (if needed)
Write-Host "[INFO] Checking dependencies..." -ForegroundColor Yellow
& "venv\Scripts\python.exe" -m pip install -r requirements.txt

# Show current Python path
Write-Host "[INFO] Current Python path:" -ForegroundColor Cyan
& "venv\Scripts\python.exe" -c "import sys; print(sys.executable)"

# Start system
Write-Host ""
Write-Host "[INFO] Starting Smart Literature System..." -ForegroundColor Green
& "venv\Scripts\python.exe" start.py $args

Read-Host "Press Enter to exit"