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

# Enhanced Python installation check with diagnostics
check_python_environment() {
    echo "[INFO] Checking Python environment..."
    
    # Check Python3 installation
    if ! command -v python3 &> /dev/null; then
        echo "[ERROR] Python3 not found in PATH"
        echo "[DEBUG] Current PATH:"
        echo "$PATH" | tr ':' '\n' | sed 's/^/  - /'
        echo "[HELP] Please install Python3 using your system package manager"
        echo "       Ubuntu/Debian: sudo apt install python3 python3-venv"
        echo "       CentOS/RHEL: sudo yum install python3 python3-venv"  
        echo "       macOS: brew install python3"
        return 1
    fi
    
    # Check Python version
    python_version=$(python3 --version 2>&1)
    echo "[INFO] Found Python: $python_version"
    
    # Parse version for compatibility check
    if [[ $python_version =~ Python\ ([0-9]+)\.([0-9]+) ]]; then
        major_version=${BASH_REMATCH[1]}
        minor_version=${BASH_REMATCH[2]}
        
        if [ "$major_version" -lt 3 ] || ([ "$major_version" -eq 3 ] && [ "$minor_version" -lt 7 ]); then
            echo "[WARNING] Python version $major_version.$minor_version may not be fully compatible"
            echo "[RECOMMEND] Python 3.7+ is recommended for best compatibility"
        fi
    fi
    
    # Show Python executable path
    python_path=$(python3 -c "import sys; print(sys.executable)" 2>&1)
    echo "[DEBUG] Python executable: $python_path"
    
    # Check venv module
    echo "[INFO] Checking venv module..."
    if ! python3 -m venv --help &> /dev/null; then
        echo "[ERROR] Python venv module not available"
        echo "[DEBUG] venv check failed"
        echo "[HELP] Please install python3-venv package:"
        echo "       Ubuntu/Debian: sudo apt install python3-venv"
        echo "       CentOS/RHEL: sudo yum install python3-venv"
        echo "       macOS: venv should be included with Python3"
        return 1
    fi
    echo "[SUCCESS] Python venv module is available"
    
    return 0
}

# Environment diagnostics function
check_system_environment() {
    echo "[INFO] Checking system environment..."
    
    # Check disk space (at least 1GB free)
    if command -v df &> /dev/null; then
        # Try different df options for better compatibility
        if df_output=$(df -BG . 2>/dev/null | awk 'NR==2{print $4}'); then
            # Remove 'G' suffix and convert to number
            free_space_gb=$(echo "$df_output" | sed 's/G$//')
            echo "[INFO] Available disk space: ${free_space_gb}GB"
        elif df_output=$(df -k . 2>/dev/null | awk 'NR==2{print $4}'); then
            # Convert KB to GB
            free_space_kb="$df_output"
            free_space_gb=$((free_space_kb / 1024 / 1024))
            echo "[INFO] Available disk space: ${free_space_gb}GB"
        elif df_output=$(df . 2>/dev/null | awk 'NR==2{print $4}'); then
            # Default df output, assume 1K blocks
            free_space_blocks="$df_output"
            free_space_gb=$((free_space_blocks / 1024 / 1024))
            echo "[INFO] Available disk space: ${free_space_gb}GB"
        else
            echo "[WARNING] Could not determine disk space using df command"
            free_space_gb=2  # Assume sufficient space to continue
        fi
        
        if [ "$free_space_gb" -lt 1 ]; then
            echo "[ERROR] Insufficient disk space (${free_space_gb}GB available, 1GB+ required)"
            return 1
        fi
    else
        echo "[WARNING] df command not available, skipping disk space check"
        # Try alternative methods
        if command -v stat &> /dev/null; then
            echo "[INFO] Using alternative disk space check method"
        else
            echo "[WARNING] No disk space check method available"
        fi
    fi
    
    # Check write permissions
    test_file="test_write_permission.tmp"
    if echo "test" > "$test_file" 2>/dev/null; then
        rm -f "$test_file" 2>/dev/null
        echo "[SUCCESS] Write permissions OK"
    else
        echo "[ERROR] No write permission in current directory"
        echo "[DEBUG] Permission error for: $(pwd)"
        return 1
    fi
    
    # Check if running as root (informational)
    if [ "$EUID" -eq 0 ]; then
        echo "[INFO] Running with root privileges"
    else
        echo "[INFO] Running as regular user"
    fi
    
    # Check system info
    if command -v uname &> /dev/null; then
        system_info=$(uname -a)
        echo "[DEBUG] System: $system_info"
    fi
    
    return 0
}

# Run diagnostics
if ! check_python_environment; then
    exit 1
fi

if ! check_system_environment; then
    exit 1
fi

# Enhanced virtual environment creation with detailed error logging
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    
    # Create error log file
    error_log_file="venv_creation_error.log"
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[DEBUG] Running: python3 -m venv venv"
    
    # Capture both stdout and stderr
    if stdout_stderr_output=$(python3 -m venv venv 2>&1); then
        echo "[SUCCESS] Virtual environment created successfully"
        
        # Verify venv structure
        if [ -f "venv/bin/python" ]; then
            echo "[VERIFY] Virtual environment structure is correct"
        else
            echo "[WARNING] Virtual environment created but structure seems incomplete"
            echo "[DEBUG] Contents of venv directory:"
            if [ -d "venv" ]; then
                ls -la venv/ | sed 's/^/  - /'
            fi
        fi
    else
        exit_code=$?
        
        # Log detailed error information
        cat > "$error_log_file" << EOF
=== Virtual Environment Creation Error Log ===
Timestamp: $timestamp
Command: python3 -m venv venv
Exit Code: $exit_code
Current Directory: $(pwd)
Python Version: $(python3 --version 2>&1)
Python Path: $(python3 -c "import sys; print(sys.executable)" 2>&1)

=== Command Output ===
$stdout_stderr_output

=== Environment Info ===
System: $(uname -a 2>/dev/null || echo "Unknown")
Shell: $SHELL
User: $(whoami)
UID/GID: $(id)
umask: $(umask)

=== PATH Environment ===
$(echo "$PATH" | tr ':' '\n' | sed 's/^/  - /')

=== Disk Space ===
$(
    if command -v df &> /dev/null; then
        if df_info=$(df -h . 2>/dev/null); then
            echo "$df_info"
        elif df_info=$(df . 2>/dev/null); then
            echo "$df_info"
        else
            echo "Could not get disk space information"
        fi
    else
        echo "df command not available"
    fi
)

=== Mount Information ===
$(mount 2>/dev/null | grep "$(df . 2>/dev/null | awk 'NR==2{print $1}')" || echo "Mount info not available")

=== Memory Info ===
$(free -h 2>/dev/null || echo "Memory info not available")

=== Directory Permissions ===
$(ls -ld . 2>/dev/null)

=== Python Module Check ===
$(python3 -m venv --help 2>&1 || echo "venv module help failed")
EOF
        
        echo "[ERROR] Failed to create virtual environment (Exit Code: $exit_code)"
        echo "[ERROR] Detailed error log saved to: $error_log_file"
        echo ""
        echo "=== Error Details ==="
        echo "$stdout_stderr_output"
        echo ""
        echo "=== Common Solutions ==="
        echo "1. Install python3-venv package:"
        echo "   Ubuntu/Debian: sudo apt install python3-venv"
        echo "   CentOS/RHEL: sudo yum install python3-venv"
        echo "   Fedora: sudo dnf install python3-venv"
        echo "2. Check if Python3 development headers are installed:"
        echo "   Ubuntu/Debian: sudo apt install python3-dev"
        echo "   CentOS/RHEL: sudo yum install python3-devel"
        echo "3. Ensure sufficient disk space (1GB+ free)"
        echo "4. Check directory permissions and ownership"
        echo "5. Try a different Python3 installation"
        echo "6. Check if SELinux or AppArmor is blocking operations"
        
        exit 1
    fi
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

# Skip banner since shell script already showed it
export PS_SKIP_BANNER="true"

venv/bin/python src/start.py "$@"

# Clean up environment variables
unset PS_CACHE_USED
unset PS_CACHE_ASKED
unset PS_SKIP_BANNER

# Wait for user input like PowerShell version
read -p "Press Enter to exit..."