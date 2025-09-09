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

# Install dependencies (if needed)
Write-Host "[INFO] Checking dependencies with progress indicator..." -ForegroundColor Yellow
& "venv\Scripts\python.exe" -c "
# 美化的依赖包检查
import sys
import time
import re

def parse_requirements():
    '''动态解析requirements.txt文件'''
    try:
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        packages = {}
        for line in lines:
            line = line.strip()
            # 跳过注释和空行
            if line.startswith('#') or not line:
                continue
            
            # 解析包名 (移除版本要求)
            package_name = re.split(r'[><=!]', line)[0].strip()
            
            # 特殊映射关系
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
        # 如果无法读取requirements.txt，使用基本包列表
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
    filled = int(percentage / 5)  # 20个字符的进度条
    bar = '#' * filled + '.' * (20 - filled)
    # Windows PowerShell优化：使用固定宽度格式避免重叠
    line = f'[{bar}] {percentage:3d}% ({current:2d}/{total:2d}) {package_name:<20} {status:<10}'
    print(f'\r{line:<80}', end='', flush=True)

for package_name, import_name in required_packages.items():
    show_progress(checked_count, total_packages, package_name, 'checking...')
    time.sleep(0.1)  # 短暂延迟使进度条可见
    
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

print()  # 换行
print()

if missing:
    print(f'Missing dependencies: {len(missing)} packages')
    for pkg in missing:
        print(f'  X {pkg}')
    exit(1)
else:
    print(f'+ All dependencies checked ({total_packages}/{total_packages})')
    # 只显示关键包的版本信息
    key_packages = ['requests', 'pandas', 'numpy', 'PyYAML']
    for pkg in key_packages:
        if pkg in version_info:
            print(f'  + {pkg}: {version_info[pkg]}')
    if len(version_info) > len(key_packages):
        print(f'  + Other {len(version_info) - len(key_packages)} packages installed')
"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARNING] Missing dependencies found, installing..." -ForegroundColor Yellow
    
    # 第一次尝试：使用官方PyPI源安装
    Write-Host "[INFO] Trying to install from official PyPI source..." -ForegroundColor Cyan
    & "venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Dependencies installed successfully (Official PyPI)" -ForegroundColor Green
    } else {
        # 第二次尝试：使用清华大学镜像源
        Write-Host "[INFO] Official source failed, switching to Tsinghua mirror..." -ForegroundColor Yellow
        & "venv\Scripts\python.exe" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --quiet
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[SUCCESS] Dependencies installed successfully (Tsinghua Mirror)" -ForegroundColor Green
        } else {
            # 第三次尝试：使用阿里云镜像源
            Write-Host "[INFO] Tsinghua mirror failed, switching to Aliyun mirror..." -ForegroundColor Yellow
            & "venv\Scripts\python.exe" -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com --quiet
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "[SUCCESS] Dependencies installed successfully (Aliyun Mirror)" -ForegroundColor Green
            } else {
                Write-Host "[ERROR] All installation sources failed" -ForegroundColor Red
                Write-Host "[HELP] Please check network connection or install manually: pip install -r requirements.txt" -ForegroundColor Cyan
                Read-Host "Press Enter to exit"
                exit 1
            }
        }
    }
}

# Show current Python path
Write-Host "[INFO] Current Python path:" -ForegroundColor Cyan
& "venv\Scripts\python.exe" -c "import sys; print(sys.executable)"

# Start system
Write-Host ""
Write-Host "[INFO] Starting Smart Literature System..." -ForegroundColor Green
& "venv\Scripts\python.exe" start.py $args

Read-Host "Press Enter to exit"