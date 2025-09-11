# Smart Literature System PowerShell Startup Script

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

# Check for existing cache
$cacheFile = ".system_cache\environment_check.json"
$useCache = $false
$skipDependencyCheck = $false
$cacheAsked = $false

if (Test-Path $cacheFile) {
    try {
        $cacheContent = Get-Content $cacheFile -Raw | ConvertFrom-Json
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
            $response = Invoke-WebRequest -Uri $mirror.Url -Method Head -TimeoutSec 5 -ErrorAction Stop
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
            Write-Host " Timeout/Error" -ForegroundColor Red
        }
    }
    
    if ($fastestMirror) {
        Write-Host "[SUCCESS] Fastest mirror: $($fastestMirror.Name) (${fastestTime}ms)" -ForegroundColor Green
        Write-Host "[INFO] Installing dependencies with progress display..." -ForegroundColor Cyan
        
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
            Write-Host "[ERROR] All mirrors are unreachable" -ForegroundColor Red
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

& "venv\Scripts\python.exe" src\start.py $args

# Clean up environment variables
Remove-Item env:PS_CACHE_USED -ErrorAction SilentlyContinue
Remove-Item env:PS_CACHE_ASKED -ErrorAction SilentlyContinue

Read-Host "Press Enter to exit"