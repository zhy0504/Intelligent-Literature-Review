#!/bin/bash
# 智能文献系统Linux/Mac启动脚本

echo "========================================"
echo "   智能文献系统启动脚本"
echo "========================================"
echo

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
echo "[信息] 安装依赖包..."
venv/bin/python -m pip install -r requirements.txt

# 显示当前Python路径
echo "[信息] 当前Python路径:"
venv/bin/python -c "import sys; print(sys.executable)"

# 启动系统
echo
echo "[信息] 正在启动智能文献系统..."
venv/bin/python start.py "$@"