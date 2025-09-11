#!/bin/bash
# Smart Literature System Linux/Mac Startup Script

echo ""
echo "==========================================================================="
echo ""
echo "        +-+-+-+-+-+-+-+-+-+-+   +-+-+-+-+-+-+-+-+-+"
echo "        |I|N|T|E|L|L|I|G|E|N|T| |L|I|T|E|R|A|T|U|R|E|"
echo "        +-+-+-+-+-+-+-+-+-+-+   +-+-+-+-+-+-+-+-+-+"
echo "                      +-+-+-+-+-+-+"
echo "                      |R|E|V|I|E|W|"
echo "                      +-+-+-+-+-+-+"
echo ""
echo "                #################################"
echo "                #                               #"
echo "                #    LITERATURE REVIEW SYSTEM  #"
echo "                #            v2.0               #"
echo "                #                               #"
echo "                #   AI-Powered Research Tool    #"
echo "                #                               #"
echo "                #################################"
echo ""
echo "      Features: PubMed Search | Smart Analysis | Review Generation"
echo "      Platform: Cross-Platform | Progress Tracking | Fast Dependencies"
echo ""
echo "==========================================================================="
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found, please install Python3 first"
    exit 1
fi

# Check virtual environment
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment"
        exit 1
    fi
    echo "[SUCCESS] Virtual environment created successfully"
fi

# Check virtual environment Python
echo "[INFO] Using virtual environment Python..."
if [ ! -f "venv/bin/python" ]; then
    echo "[ERROR] Virtual environment Python not found"
    exit 1
fi

# Check requirements file
if [ ! -f "requirements.txt" ]; then
    echo "[ERROR] requirements.txt file not found"
    exit 1
fi

# Check for existing cache
CACHE_FILE=".system_cache/environment_check.json"
USE_CACHE=false
SKIP_DEPENDENCY_CHECK=false
CACHE_ASKED=false

if [ -f "$CACHE_FILE" ]; then
    # Check if cache is less than 24 hours old
    if command -v python3 &> /dev/null; then
        CACHE_VALID=$(python3 -c "
import json
import os
from datetime import datetime
try:
    with open('$CACHE_FILE', 'r') as f:
        cache_data = json.load(f)
    cache_time = datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01'))
    time_diff = (datetime.now() - cache_time).total_seconds()
    if time_diff < 86400:  # 24 hours
        print('valid')
        print(cache_data.get('timestamp', ''))
    else:
        print('expired')
except:
    print('invalid')
" 2>/dev/null)
        
        if echo "$CACHE_VALID" | grep -q "valid"; then
            CACHE_TIME=$(echo "$CACHE_VALID" | tail -n 1 | cut -d'T' -f1-2 | tr 'T' ' ')
            echo "[INFO] Found environment check cache (Time: $CACHE_TIME)"
            
            read -p "Use cached results? Default is Yes (Y/n): " response
            CACHE_ASKED=true
            
            if [ -z "$response" ] || [ "$response" = "y" ] || [ "$response" = "Y" ] || [ "$response" = "yes" ]; then
                echo "[INFO] Using cached environment check results"
                USE_CACHE=true
                SKIP_DEPENDENCY_CHECK=true
            else
                echo "[INFO] Re-running environment check"
            fi
        fi
    fi
fi

# Install dependencies (if needed)
if [ "$SKIP_DEPENDENCY_CHECK" = false ]; then
    echo "[INFO] Checking dependencies with progress indicator..."
    venv/bin/python -c "
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
    if [ $? -ne 0 ]; then
        echo "[WARNING] Missing dependencies found, installing with speed test..."
        
        # Simple mirror speed testing
        echo "[INFO] Testing mirror speeds to find the fastest source..."
        
        declare -A mirrors
        mirrors["Official PyPI"]="https://pypi.org/simple/"
        mirrors["Tsinghua TUNA"]="https://pypi.tuna.tsinghua.edu.cn/simple" 
        mirrors["USTC"]="https://pypi.mirrors.ustc.edu.cn/simple"
        mirrors["Aliyun"]="https://mirrors.aliyun.com/pypi/simple"
        
        declare -A mirror_args
        mirror_args["Official PyPI"]=""
        mirror_args["Tsinghua TUNA"]="-i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn"
        mirror_args["USTC"]="-i https://pypi.mirrors.ustc.edu.cn/simple --trusted-host pypi.mirrors.ustc.edu.cn"
        mirror_args["Aliyun"]="-i https://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com"
        
        fastest_mirror=""
        fastest_time=9999
        
        for mirror_name in "Official PyPI" "Tsinghua TUNA" "USTC" "Aliyun"; do
            echo -n "  Testing $mirror_name..."
            
            start_time=$(date +%s%3N)
            # Test HTTP response - accept 200, 301, 302 status codes
            response_code=$(curl -s --head --connect-timeout 5 -w "%{http_code}" "${mirrors[$mirror_name]}" 2>/dev/null | tail -1)
            if [ $? -eq 0 ] && ([ "$response_code" = "200" ] || [ "$response_code" = "301" ] || [ "$response_code" = "302" ]); then
                end_time=$(date +%s%3N)
                response_time=$((end_time - start_time))
                echo " ${response_time}ms"
                
                if [ $response_time -lt $fastest_time ]; then
                    fastest_time=$response_time
                    fastest_mirror="$mirror_name"
                fi
            elif [ $? -ne 0 ]; then
                echo " Timeout/Error"
            else
                echo " Failed"
            fi
        done
        
        if [ -n "$fastest_mirror" ]; then
            echo "[SUCCESS] Fastest mirror: $fastest_mirror (${fastest_time}ms)"
            echo "[INFO] Installing dependencies with progress display..."
            
            install_cmd="venv/bin/python -m pip install -r requirements.txt --progress-bar on --no-warn-script-location ${mirror_args[$fastest_mirror]}"
            eval $install_cmd
            
            if [ $? -eq 0 ]; then
                echo "[SUCCESS] Dependencies installed successfully from $fastest_mirror"
            else
                echo "[ERROR] Installation failed"
                exit 1
            fi
        else
            echo "[ERROR] All mirrors are unreachable"
            exit 1
        fi
    fi
else
    echo "[INFO] Skipping dependency check and mirror testing (using cache)"
fi

# Show current Python path
echo "[INFO] Current Python path:"
venv/bin/python -c "import sys; print(sys.executable)"

# Start system
echo ""
echo "[INFO] Starting Smart Literature System..."

# Pass appropriate arguments based on cache usage and whether cache was asked
if [ "$USE_CACHE" = true ]; then
    # Tell Python script that we already checked cache and user chose to use it
    export PS_CACHE_USED="true"
    export PS_CACHE_ASKED="true"
elif [ "$CACHE_ASKED" = true ]; then
    # Tell Python script that we asked about cache but user chose not to use it
    export PS_CACHE_ASKED="true"
fi

venv/bin/python src/start.py "$@"

# Clean up environment variables
unset PS_CACHE_USED
unset PS_CACHE_ASKED