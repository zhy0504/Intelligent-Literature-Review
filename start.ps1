# Smart Literature System PowerShell Startup Script

# Fix encoding issues for Windows Chinese systems
$OutputEncoding = [System.Text.Encoding]::UTF8
[System.Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[System.Console]::InputEncoding = [System.Text.Encoding]::UTF8

# Set PowerShell to use UTF-8 for web requests and file operations
$PSDefaultParameterValues['*:Encoding'] = 'utf8'
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
$PSDefaultParameterValues['Set-Content:Encoding'] = 'utf8'

Write-Host ""
Write-Host "===========================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "        +-+-+-+-+-+-+-+-+-+-+   +-+-+-+-+-+-+-+-+-+" -ForegroundColor Yellow
Write-Host "        |I|N|T|E|L|L|I|G|E|N|T| |L|I|T|E|R|A|T|U|R|E|" -ForegroundColor Yellow  
Write-Host "        +-+-+-+-+-+-+-+-+-+-+   +-+-+-+-+-+-+-+-+-+" -ForegroundColor Yellow
Write-Host "                      +-+-+-+-+-+-+" -ForegroundColor Yellow
Write-Host "                      |R|E|V|I|E|W|" -ForegroundColor Yellow
Write-Host "                      +-+-+-+-+-+-+" -ForegroundColor Yellow
Write-Host ""
Write-Host "                #################################" -ForegroundColor Green
Write-Host "                #                               #" -ForegroundColor Green
Write-Host "                #    LITERATURE REVIEW SYSTEM  #" -ForegroundColor Green
Write-Host "                #            v2.0               #" -ForegroundColor Green
Write-Host "                #                               #" -ForegroundColor Green
Write-Host "                #   AI-Powered Research Tool    #" -ForegroundColor Green
Write-Host "                #                               #" -ForegroundColor Green
Write-Host "                #################################" -ForegroundColor Green
Write-Host ""
Write-Host "      Features: PubMed Search | Smart Analysis | Review Generation" -ForegroundColor White
Write-Host "      Platform: Cross-Platform | Progress Tracking | Fast Dependencies" -ForegroundColor White
Write-Host ""
Write-Host "===========================================================================" -ForegroundColor Cyan
Write-Host ""

# Set current directory
Set-Location $PSScriptRoot

# Enhanced Python installation check with diagnostics
function Test-PythonEnvironment {
    Write-Host "[INFO] Checking Python environment..." -ForegroundColor Cyan
    
    # Check Python installation
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        Write-Host "[ERROR] Python not found in PATH" -ForegroundColor Red
        Write-Host "[DEBUG] Current PATH:" -ForegroundColor Gray
        $env:PATH.Split(';') | ForEach-Object { Write-Host "  - $_" -ForegroundColor Gray }
        Write-Host "[HELP] Please install Python from https://python.org or check PATH configuration" -ForegroundColor Yellow
        return $false
    }
    
    # Check Python version
    try {
        $pythonVersion = & python --version 2>&1
        Write-Host "[INFO] Found Python: $pythonVersion" -ForegroundColor Green
        
        # Parse version for compatibility check
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $majorVersion = [int]$matches[1]
            $minorVersion = [int]$matches[2]
            
            if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 7)) {
                Write-Host "[WARNING] Python version $majorVersion.$minorVersion may not be fully compatible" -ForegroundColor Yellow
                Write-Host "[RECOMMEND] Python 3.7+ is recommended for best compatibility" -ForegroundColor Yellow
            }
        }
        
        # Show Python executable path
        $pythonPath = & python -c "import sys; print(sys.executable)" 2>&1
        Write-Host "[DEBUG] Python executable: $pythonPath" -ForegroundColor Gray
        
    } catch {
        Write-Host "[ERROR] Failed to get Python version: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    
    # Check venv module
    Write-Host "[INFO] Checking venv module..." -ForegroundColor Cyan
    try {
        $venvCheck = & python -m venv --help 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Python venv module not available" -ForegroundColor Red
            Write-Host "[DEBUG] venv check output: $venvCheck" -ForegroundColor Gray
            Write-Host "[HELP] Please reinstall Python with venv module or install python-venv package" -ForegroundColor Yellow
            return $false
        }
        Write-Host "[SUCCESS] Python venv module is available" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Failed to check venv module: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    
    return $true
}

# Environment diagnostics function  
function Test-SystemEnvironment {
    Write-Host "[INFO] Checking system environment..." -ForegroundColor Cyan
    
    # Check disk space (at least 1GB free)
    try {
        # Get the drive letter from current path (works better than Get-PSDrive for all drive types)
        $currentDrive = (Get-Location).Drive
        if ($currentDrive) {
            $freeSpaceGB = [math]::Round($currentDrive.Free / 1GB, 2)
            Write-Host "[INFO] Available disk space: ${freeSpaceGB}GB" -ForegroundColor Cyan
            
            if ($freeSpaceGB -lt 1) {
                Write-Host "[ERROR] Insufficient disk space (${freeSpaceGB}GB available, 1GB+ required)" -ForegroundColor Red
                return $false
            }
        } else {
            # Alternative method using WMI
            $driveLetter = (Get-Location).Path.Substring(0,2)
            $disk = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='$driveLetter'"
            if ($disk) {
                $freeSpaceGB = [math]::Round($disk.FreeSpace / 1GB, 2)
                Write-Host "[INFO] Available disk space: ${freeSpaceGB}GB" -ForegroundColor Cyan
                
                if ($freeSpaceGB -lt 1) {
                    Write-Host "[ERROR] Insufficient disk space (${freeSpaceGB}GB available, 1GB+ required)" -ForegroundColor Red
                    return $false
                }
            } else {
                Write-Host "[WARNING] Could not determine disk space for drive $driveLetter" -ForegroundColor Yellow
            }
        }
    } catch {
        Write-Host "[WARNING] Could not check disk space: $($_.Exception.Message)" -ForegroundColor Yellow
        # Try one more alternative method
        try {
            $driveLetter = (Get-Location).Path.Substring(0,2)
            $freeSpace = (Get-ChildItem $driveLetter\ | Measure-Object -Property Length -Sum).Sum
            Write-Host "[INFO] Disk space check completed with alternative method" -ForegroundColor Cyan
        } catch {
            Write-Host "[DEBUG] All disk space check methods failed" -ForegroundColor Gray
        }
    }
    
    # Check write permissions
    try {
        $testFile = Join-Path $PWD "test_write_permission.tmp"
        "test" | Out-File -FilePath $testFile -ErrorAction Stop
        Remove-Item $testFile -ErrorAction SilentlyContinue
        Write-Host "[SUCCESS] Write permissions OK" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] No write permission in current directory" -ForegroundColor Red
        Write-Host "[DEBUG] Permission error: $($_.Exception.Message)" -ForegroundColor Gray
        return $false
    }
    
    # Check if running as admin (informational)
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if ($isAdmin) {
        Write-Host "[INFO] Running with Administrator privileges" -ForegroundColor Cyan
    } else {
        Write-Host "[INFO] Running as regular user" -ForegroundColor Cyan
    }
    
    return $true
}

# Run diagnostics
if (-not (Test-PythonEnvironment)) {
    Read-Host "Press Enter to exit"
    exit 1
}

if (-not (Test-SystemEnvironment)) {
    Read-Host "Press Enter to exit" 
    exit 1
}

# Enhanced virtual environment creation with detailed error logging
if (-not (Test-Path "venv")) {
    Write-Host "[INFO] Creating virtual environment..." -ForegroundColor Yellow
    
    # Create error log file
    $errorLogFile = "venv_creation_error.log"
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    Write-Host "[DEBUG] Running: python -m venv venv" -ForegroundColor Gray
    
    # Capture both stdout and stderr
    try {
        $process = Start-Process -FilePath "python" -ArgumentList "-m", "venv", "venv" -NoNewWindow -Wait -PassThru -RedirectStandardOutput "venv_stdout.tmp" -RedirectStandardError "venv_stderr.tmp"
        
        $exitCode = $process.ExitCode
        $stdout = ""
        $stderr = ""
        
        if (Test-Path "venv_stdout.tmp") {
            $stdout = Get-Content "venv_stdout.tmp" -Raw -ErrorAction SilentlyContinue
            Remove-Item "venv_stdout.tmp" -ErrorAction SilentlyContinue
        }
        
        if (Test-Path "venv_stderr.tmp") {
            $stderr = Get-Content "venv_stderr.tmp" -Raw -ErrorAction SilentlyContinue  
            Remove-Item "venv_stderr.tmp" -ErrorAction SilentlyContinue
        }
        
        if ($exitCode -ne 0) {
            # Log detailed error information
            $errorDetails = @"
=== Virtual Environment Creation Error Log ===
Timestamp: $timestamp
Command: python -m venv venv
Exit Code: $exitCode
Current Directory: $PWD
Python Version: $(& python --version 2>&1)
Python Path: $(& python -c "import sys; print(sys.executable)" 2>&1)

=== Standard Output ===
$stdout

=== Standard Error ===
$stderr

=== Environment Info ===
PowerShell Version: $($PSVersionTable.PSVersion)
OS Version: $([Environment]::OSVersion.VersionString)
Architecture: $([Environment]::ProcessorArchitecture)
Available Memory: $([math]::Round((Get-WmiObject -Class Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2))GB

=== PATH Environment ===
$($env:PATH.Split(';') | ForEach-Object { "  - $_" } | Out-String)

=== Disk Space ===
$(
    try {
        $currentDrive = (Get-Location).Drive
        if ($currentDrive) {
            "Drive: $($currentDrive.Name) - Free: $([math]::Round($currentDrive.Free/1GB,2))GB - Total: $([math]::Round(($currentDrive.Used + $currentDrive.Free)/1GB,2))GB"
        } else {
            $driveLetter = (Get-Location).Path.Substring(0,2)
            $disk = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='$driveLetter'"
            if ($disk) {
                "Drive: $driveLetter - Free: $([math]::Round($disk.FreeSpace/1GB,2))GB - Total: $([math]::Round($disk.Size/1GB,2))GB"
            } else {
                "Could not determine disk space"
            }
        }
    } catch {
        "Disk space check failed: $($_.Exception.Message)"
    }
)
"@
            
            # Write to log file
            $errorDetails | Out-File -FilePath $errorLogFile -Encoding UTF8
            
            Write-Host "[ERROR] Failed to create virtual environment (Exit Code: $exitCode)" -ForegroundColor Red
            Write-Host "[ERROR] Detailed error log saved to: $errorLogFile" -ForegroundColor Red
            Write-Host ""
            Write-Host "=== Error Details ===" -ForegroundColor Red
            if ($stderr) {
                Write-Host "[STDERR] $stderr" -ForegroundColor Red
            }
            if ($stdout) {
                Write-Host "[STDOUT] $stdout" -ForegroundColor Yellow
            }
            
            Write-Host ""
            Write-Host "=== Common Solutions ===" -ForegroundColor Yellow
            Write-Host "1. Check if Python installation includes venv module" -ForegroundColor White
            Write-Host "2. Try running PowerShell as Administrator" -ForegroundColor White
            Write-Host "3. Check antivirus software blocking file creation" -ForegroundColor White
            Write-Host "4. Ensure sufficient disk space (1GB+ free)" -ForegroundColor White
            Write-Host "5. Check file path doesn't contain special characters" -ForegroundColor White
            Write-Host "6. Try different Python installation or reinstall Python" -ForegroundColor White
            
            Read-Host "Press Enter to exit"
            exit 1
        } else {
            Write-Host "[SUCCESS] Virtual environment created successfully" -ForegroundColor Green
            
            # Verify venv structure
            if (Test-Path "venv\Scripts\python.exe") {
                Write-Host "[VERIFY] Virtual environment structure is correct" -ForegroundColor Green
            } else {
                Write-Host "[WARNING] Virtual environment created but structure seems incomplete" -ForegroundColor Yellow
                Write-Host "[DEBUG] Contents of venv directory:" -ForegroundColor Gray
                if (Test-Path "venv") {
                    Get-ChildItem "venv" | ForEach-Object { Write-Host "  - $($_.Name)" -ForegroundColor Gray }
                }
            }
        }
        
    } catch {
        # Handle process creation errors
        $errorDetails = @"
=== Virtual Environment Creation Error Log ===
Timestamp: $timestamp
Command: python -m venv venv  
Error Type: Process Creation Failed
Exception: $($_.Exception.Message)
Current Directory: $PWD
Python Check: $(Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)

=== Full Exception ===
$($_.Exception | Format-List * | Out-String)
"@
        
        $errorDetails | Out-File -FilePath $errorLogFile -Encoding UTF8
        
        Write-Host "[ERROR] Failed to start virtual environment creation process" -ForegroundColor Red
        Write-Host "[ERROR] Exception: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "[ERROR] Detailed error log saved to: $errorLogFile" -ForegroundColor Red
        
        Read-Host "Press Enter to exit"
        exit 1
    }
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

# Check for existing cache
$cacheFile = ".system_cache\environment_check.json"
$useCache = $false
$skipDependencyCheck = $false
$cacheAsked = $false

if (Test-Path $cacheFile) {
    try {
        # Use UTF-8 encoding when reading cache file
        $cacheContent = Get-Content $cacheFile -Raw -Encoding UTF8 | ConvertFrom-Json
        $cacheTime = [DateTime]$cacheContent.timestamp
        $timeDiff = (Get-Date) - $cacheTime
        
        if ($timeDiff.TotalSeconds -lt 86400) {  # 24 hours
            Write-Host "[INFO] Found environment check cache (Time: $($cacheTime.ToString('yyyy-MM-dd HH:mm:ss')))" -ForegroundColor Cyan
            
            $response = Read-Host "Use cached results? Default is Yes (Y/n)"
            $cacheAsked = $true
            
            if ($response -eq "" -or $response.ToLower() -eq "y" -or $response.ToLower() -eq "yes") {
                Write-Host "[INFO] Using cached environment check results" -ForegroundColor Green
                $useCache = $true
                $skipDependencyCheck = $true
            } else {
                Write-Host "[INFO] Re-running environment check" -ForegroundColor Yellow
            }
        }
    } catch {
        Write-Host "[WARNING] Failed to read cache file, proceeding with full check" -ForegroundColor Yellow
    }
}

# Install dependencies (if needed)
if (-not $skipDependencyCheck) {
    Write-Host "[INFO] Checking dependencies with progress indicator..." -ForegroundColor Yellow
& "venv\Scripts\python.exe" -c "
import sys
import time
import re

def parse_requirements():
    try:
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        packages = {}
        for line in lines:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            
            package_name = re.split(r'[><=!]', line)[0].strip()
            
            import_mapping = {
                'PyYAML': 'yaml',
                'python-dateutil': 'dateutil',
                'beautifulsoup4': 'bs4',
                'python-dotenv': 'dotenv',
                'lxml': 'lxml',
                'charset-normalizer': 'charset_normalizer'
            }
            
            import_name = import_mapping.get(package_name, package_name.lower())
            packages[package_name] = import_name
            
        return packages
    except Exception as e:
        return {
            'requests': 'requests',
            'pandas': 'pandas', 
            'numpy': 'numpy',
            'PyYAML': 'yaml'
        }

required_packages = parse_requirements()
total_packages = len(required_packages)
checked_count = 0
missing = []
version_info = {}

print(f'Checking {total_packages} dependencies...')
print()

def show_progress(current, total, package_name='', status=''):
    percentage = int((current / total) * 100)
    filled = int(percentage / 5)
    bar = '#' * filled + '.' * (20 - filled)
    line = f'[{bar}] {percentage:3d}% ({current:2d}/{total:2d}) {package_name:<20} {status:<10}'
    print(f'\r{line:<80}', end='', flush=True)

for package_name, import_name in required_packages.items():
    show_progress(checked_count, total_packages, package_name, 'checking...')
    time.sleep(0.1)
    
    try:
        module = __import__(import_name)
        version = getattr(module, '__version__', 'unknown')
        version_info[package_name] = version
        checked_count += 1
        show_progress(checked_count, total_packages, package_name, 'OK')
    except ImportError as e:
        missing.append(package_name)
        checked_count += 1
        show_progress(checked_count, total_packages, package_name, 'MISSING')

print()
print()

if missing:
    print(f'Missing dependencies: {len(missing)} packages')
    for pkg in missing:
        print(f'  X {pkg}')
    exit(1)
else:
    print(f'+ All dependencies checked ({total_packages}/{total_packages})')
    key_packages = ['requests', 'pandas', 'numpy', 'PyYAML']
    for pkg in key_packages:
        if pkg in version_info:
            print(f'  + {pkg}: {version_info[pkg]}')
    if len(version_info) > len(key_packages):
        print(f'  + Other {len(version_info) - len(key_packages)} packages installed')
"

    # 只有在依赖包检查失败时才执行镜像测速和安装
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARNING] Missing dependencies found, installing with speed test..." -ForegroundColor Yellow
        
        # Simple mirror speed testing
        Write-Host "[INFO] Testing mirror speeds to find the fastest source..." -ForegroundColor Cyan
        
        $mirrors = @(
            @{Name="Official PyPI"; Url="https://pypi.org/simple/"; Args=@()},
            @{Name="Tsinghua TUNA"; Url="https://pypi.tuna.tsinghua.edu.cn/simple"; Args=@("-i", "https://pypi.tuna.tsinghua.edu.cn/simple", "--trusted-host", "pypi.tuna.tsinghua.edu.cn")},
            @{Name="USTC"; Url="https://pypi.mirrors.ustc.edu.cn/simple"; Args=@("-i", "https://pypi.mirrors.ustc.edu.cn/simple", "--trusted-host", "pypi.mirrors.ustc.edu.cn")},
            @{Name="Aliyun"; Url="https://mirrors.aliyun.com/pypi/simple"; Args=@("-i", "https://mirrors.aliyun.com/pypi/simple", "--trusted-host", "mirrors.aliyun.com")}
        )
        
        $fastestMirror = $null
        $fastestTime = [double]::MaxValue
    
    foreach ($mirror in $mirrors) {
        Write-Host "  Testing $($mirror.Name)..." -NoNewline
        
        try {
            $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            $ProgressPreference = 'SilentlyContinue'
            
            $response = Invoke-WebRequest -Uri $mirror.Url -Method Head -TimeoutSec 5 -ErrorAction Stop -UseBasicParsing
            $stopwatch.Stop()
            
            if ($response -and ($response.StatusCode -eq 200 -or $response.StatusCode -eq 301 -or $response.StatusCode -eq 302)) {
                $responseTime = $stopwatch.ElapsedMilliseconds
                Write-Host " ${responseTime}ms" -ForegroundColor Green
                
                if ($responseTime -lt $fastestTime) {
                    $fastestTime = $responseTime
                    $fastestMirror = $mirror
                }
            } else {
                Write-Host " Failed" -ForegroundColor Red
            }
        } catch {
            if ($stopwatch) { $stopwatch.Stop() }
            Write-Host " Timeout/Error" -ForegroundColor Red
        }
    }
    
    if ($fastestMirror) {
        Write-Host "[SUCCESS] Fastest mirror: $($fastestMirror.Name) (${fastestTime}ms)" -ForegroundColor Green
        Write-Host "[INFO] Installing dependencies..." -ForegroundColor Cyan
        
        $pipPath = "venv\Scripts\pip.exe"
        $installArgs = @("install", "-r", "requirements.txt", "--progress-bar", "on", "--no-warn-script-location") + $fastestMirror.Args
        
        & $pipPath $installArgs
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[SUCCESS] Dependencies installed successfully from $($fastestMirror.Name)" -ForegroundColor Green
        } else {
            Write-Host "[ERROR] Installation failed" -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }
        } else {
            Write-Host "[DEBUG] No fastest mirror found after testing all mirrors!" -ForegroundColor Gray
            Write-Host "[ERROR] All mirrors are unreachable" -ForegroundColor Red
            Write-Host "[DEBUG] Tested mirrors:" -ForegroundColor Gray
            foreach ($mirror in $mirrors) {
                Write-Host "[DEBUG]   - $($mirror.Name): $($mirror.Url)" -ForegroundColor Gray
            }
            Read-Host "Press Enter to exit"
            exit 1
        }
    }
} else {
    Write-Host "[INFO] Skipping dependency check and mirror testing (using cache)" -ForegroundColor Green
}

# Show current Python path
Write-Host "[INFO] Current Python path:" -ForegroundColor Cyan
& "venv\Scripts\python.exe" -c "import sys; print(sys.executable)"

# Start system
Write-Host ""
Write-Host "[INFO] Starting Smart Literature System..." -ForegroundColor Green

# Pass appropriate arguments based on cache usage and whether cache was asked
if ($useCache) {
    # Tell Python script that we already checked cache and user chose to use it
    $env:PS_CACHE_USED = "true"
    $env:PS_CACHE_ASKED = "true"
} elseif ($cacheAsked) {
    # Tell Python script that we asked about cache but user chose not to use it
    $env:PS_CACHE_ASKED = "true"
}

# Skip banner since PowerShell script already showed it
$env:PS_SKIP_BANNER = "true"

& "venv\Scripts\python.exe" src\start.py $args

# Clean up environment variables
Remove-Item env:PS_CACHE_USED -ErrorAction SilentlyContinue
Remove-Item env:PS_CACHE_ASKED -ErrorAction SilentlyContinue
Remove-Item env:PS_SKIP_BANNER -ErrorAction SilentlyContinue

Read-Host "Press Enter to exit"