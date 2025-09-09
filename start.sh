#!/bin/bash
# 智能文献系统Linux/Mac启动脚本

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

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "[信息] 正在创建虚拟环境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[错误] 创建虚拟环境失败"
        exit 1
    fi
    echo "[成功] 虚拟环境创建成功"
fi

# 直接使用虚拟环境中的Python
echo "[信息] 使用虚拟环境Python..."
if [ ! -f "venv/bin/python" ]; then
    echo "[错误] 虚拟环境Python不存在"
    exit 1
fi

# 检查依赖
if [ ! -f "requirements.txt" ]; then
    echo "[错误] 未找到requirements.txt文件"
    exit 1
fi

# 安装依赖（如果需要）
echo "[信息] 检查依赖包（带进度条）..."
venv/bin/python -c "
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

print(f'正在检查 {total_packages} 个依赖包...')
print()

def show_progress(current, total, package_name='', status=''):
    percentage = int((current / total) * 100)
    filled = int(percentage / 5)  # 20个字符的进度条
    bar = '#' * filled + '.' * (20 - filled)
    # 跨平台优化：使用固定宽度格式避免文本重叠
    line = f'[{bar}] {percentage:3d}% ({current:2d}/{total:2d}) {package_name:<20} {status:<10}'
    print(f'\r{line:<80}', end='', flush=True)

for package_name, import_name in required_packages.items():
    show_progress(checked_count, total_packages, package_name, '检查中...')
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
    print(f'缺少依赖包: {len(missing)} 个')
    for pkg in missing:
        print(f'  X {pkg}')
    exit(1)
else:
    print(f'+ 所有依赖包检查完成 ({total_packages}/{total_packages})')
    # 只显示关键包的版本信息
    key_packages = ['requests', 'pandas', 'numpy', 'PyYAML']
    for pkg in key_packages:
        if pkg in version_info:
            print(f'  + {pkg}: {version_info[pkg]}')
    if len(version_info) > len(key_packages):
        print(f'  + 其他 {len(version_info) - len(key_packages)} 个包已安装')
"

if [ $? -ne 0 ]; then
    echo "[警告] 发现缺失依赖包，正在安装..."
    
    # 第一次尝试：使用官方PyPI源安装
    echo "[信息] 尝试从官方PyPI源安装依赖包..."
    venv/bin/python -m pip install -r requirements.txt --quiet
    
    if [ $? -eq 0 ]; then
        echo "[成功] 依赖包安装完成（官方PyPI源）"
    else
        # 第二次尝试：使用清华大学镜像源
        echo "[信息] 官方源失败，切换到清华大学镜像源..."
        venv/bin/python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --quiet
        
        if [ $? -eq 0 ]; then
            echo "[成功] 依赖包安装完成（清华镜像）"
        else
            # 第三次尝试：使用阿里云镜像源
            echo "[信息] 清华镜像失败，切换到阿里云镜像源..."
            venv/bin/python -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com --quiet
            
            if [ $? -eq 0 ]; then
                echo "[成功] 依赖包安装完成（阿里云镜像）"
            else
                echo "[错误] 所有安装源都失败"
                echo "[帮助] 请检查网络连接，或手动执行：pip install -r requirements.txt"
                exit 1
            fi
        fi
    fi
fi

# 显示当前Python路径
echo "[信息] 当前Python路径:"
venv/bin/python -c "import sys; print(sys.executable)"

# 启动系统
echo
echo "[信息] 正在启动智能文献系统..."
venv/bin/python start.py "$@"