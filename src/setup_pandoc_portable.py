#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pandoc便携版安装脚本 - 跨平台支持
自动下载适合当前系统的Pandoc便携版到项目目录
"""

import os
import platform
import requests
import zipfile
import tarfile
from pathlib import Path
import tempfile

def get_system_info():
    """获取系统信息"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # 系统映射 - 支持Windows、macOS和Linux
    system_map = {
        'windows': 'windows',
        'linux': 'linux',
        'darwin': 'macOS'  # macOS
    }
    
    os_name = system_map.get(system)
    if not os_name:
        raise RuntimeError(f"不支持的操作系统: {system}")
    
    # 架构映射 - 根据实际下载链接格式
    if os_name == 'windows':
        # Windows使用x86_64命名
        arch_map = {
            'x86_64': 'x86_64',
            'amd64': 'x86_64',
            'arm64': 'arm64',
            'aarch64': 'arm64'
        }
    elif os_name == 'linux':
        # Linux使用amd64/arm64命名
        arch_map = {
            'x86_64': 'amd64',
            'amd64': 'amd64', 
            'arm64': 'arm64',
            'aarch64': 'arm64'
        }
    else:  # macOS
        # macOS使用x86_64/arm64命名
        arch_map = {
            'x86_64': 'x86_64',
            'amd64': 'x86_64',
            'arm64': 'arm64', 
            'aarch64': 'arm64'
        }
    
    arch = arch_map.get(machine)
    if not arch:
        # 默认架构
        if os_name == 'linux':
            arch = 'amd64'
        else:  # Windows和macOS
            arch = 'x86_64'
        print(f"警告: 未识别的架构 {machine}，使用默认架构 {arch}")
    
    return os_name, arch

def get_latest_pandoc_version():
    """获取Pandoc最新版本号"""
    try:
        url = "https://api.github.com/repos/jgm/pandoc/releases/latest"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data['tag_name']
    except Exception as e:
        print(f"获取版本信息失败，使用默认版本: {e}")
        return "3.1.8"  # 回退版本

def download_pandoc(os_name, arch, version):
    """下载对应系统的Pandoc"""
    
    # 构建下载URL - 根据你提供的正确链接格式
    if os_name == 'windows':
        # Windows格式: pandoc-3.8-windows-x86_64.zip
        filename = f"pandoc-{version}-windows-{arch}.zip"
        extract_func = extract_zip
    elif os_name == 'macOS':
        # macOS格式: pandoc-3.8-x86_64-macOS.zip 或 pandoc-3.8-arm64-macOS.zip
        filename = f"pandoc-{version}-{arch}-macOS.zip"
        extract_func = extract_zip
    else:  # linux
        # Linux格式: pandoc-3.8-linux-amd64.tar.gz 或 pandoc-3.8-linux-arm64.tar.gz
        filename = f"pandoc-{version}-linux-{arch}.tar.gz"
        extract_func = extract_tar
    
    base_url = f"https://github.com/jgm/pandoc/releases/download/{version}/{filename}"
    
    print(f"准备下载 {filename}...")
    print(f"目标平台: {os_name} {arch}")
    print()
    
    # 询问用户是否使用国内代理加速
    print("是否启用国内代理加速下载？(推荐中国大陆用户选择)")
    print("1. 是 - 使用 gh-proxy.com 代理加速")
    print("2. 否 - 直连GitHub下载")
    
    try:
        choice = input("请选择 (1/2，默认为1): ").strip()
        if choice == "" or choice == "1":
            url = f"https://gh-proxy.com/{base_url}"
            print(f"✅ 已启用代理加速下载")
        else:
            url = base_url
            print(f"✅ 使用直连下载")
    except (EOFError, KeyboardInterrupt):
        # 处理非交互环境，默认使用代理
        url = f"https://gh-proxy.com/{base_url}"
        print(f"⚠️  非交互环境，默认启用代理加速")
    
    print(f"下载地址: {url}")
    print(f"备用地址: {base_url}")
    print()
    
    def download_with_progress(download_url, desc="下载"):
        """带进度条的下载函数"""
        try:
            print(f"开始{desc}，请稍候...")
            response = requests.get(download_url, timeout=300, stream=True)
            response.raise_for_status()
            
            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))
            
            # 保存到临时文件，显示进度
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp_file:
                if total_size > 0:
                    print(f"文件大小: {total_size / 1024 / 1024:.1f} MB")
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            tmp_file.write(chunk)
                            downloaded += len(chunk)
                            # 显示简单进度
                            percent = (downloaded / total_size) * 100
                            print(f"\r下载进度: {percent:.1f}% ({downloaded / 1024 / 1024:.1f}/{total_size / 1024 / 1024:.1f} MB)", end="")
                    print()  # 换行
                else:
                    # 如果无法获取大小，直接下载
                    print("正在下载中...")
                    tmp_file.write(response.content)
                    print("下载完成")
                
                return tmp_file.name
                
        except Exception as e:
            raise e
    
    try:
        temp_path = download_with_progress(url, "代理下载" if "gh-proxy.com" in url else "直连下载")
        return temp_path, extract_func
        
    except Exception as e:
        print(f"下载失败: {e}")
        
        # 如果使用了代理且失败，尝试直连下载
        if "gh-proxy.com" in url:
            print("⚠️  代理下载失败，正在尝试直连GitHub下载...")
            try:
                temp_path = download_with_progress(base_url, "直连下载")
                print("✅ 直连下载成功")
                return temp_path, extract_func
                
            except Exception as direct_e:
                print(f"❌ 直连下载也失败: {direct_e}")
                return None, None
        else:
            return None, None

def extract_zip(zip_path, target_dir):
    """解压ZIP文件"""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(target_dir)

def extract_tar(tar_path, target_dir):
    """解压TAR.GZ文件"""
    with tarfile.open(tar_path, 'r:gz') as tar_ref:
        tar_ref.extractall(target_dir)

def setup_pandoc_portable():
    """设置便携版Pandoc"""
    # 项目根目录 - 修改为实际项目根目录
    project_root = Path(__file__).parent.parent
    
    # 获取系统信息
    os_name, arch = get_system_info()
    print(f"检测到系统: {os_name} {arch}")
    
    # 创建目标目录
    target_dir = project_root / "tools" / "pandoc" / os_name.lower()
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查是否已安装
    exec_name = "pandoc.exe" if os_name == 'windows' else "pandoc"
    pandoc_exec = target_dir / exec_name
    
    if pandoc_exec.exists():
        print(f"Pandoc便携版已存在: {pandoc_exec}")
        print("如需重新安装，请先删除tools/pandoc目录")
        return str(pandoc_exec)
    
    # 获取最新版本
    version = get_latest_pandoc_version()
    print(f"Pandoc版本: {version}")
    
    # 下载文件
    temp_file, extract_func = download_pandoc(os_name, arch, version)
    
    if not temp_file:
        return None
    
    try:
        print("解压文件...")
        
        # 解压到临时目录
        with tempfile.TemporaryDirectory() as temp_extract_dir:
            extract_func(temp_file, temp_extract_dir)
            
            # 查找pandoc可执行文件
            pandoc_found = False
            for root, dirs, files in os.walk(temp_extract_dir):
                for file in files:
                    if file == exec_name:
                        src_path = Path(root) / file
                        dest_path = target_dir / file
                        
                        # 复制可执行文件
                        import shutil
                        shutil.copy2(src_path, dest_path)
                        
                        # 设置执行权限（Linux/macOS）
                        if os_name != 'windows':
                            dest_path.chmod(0o755)
                        
                        print(f"Pandoc便携版安装完成: {dest_path}")
                        pandoc_found = True
                        break
                
                if pandoc_found:
                    break
            
            if not pandoc_found:
                print("解压文件中未找到pandoc可执行文件")
                return None
        
        # 清理临时文件
        os.unlink(temp_file)
        
        return str(pandoc_exec)
        
    except Exception as e:
        print(f"安装失败: {e}")
        # 清理临时文件
        if os.path.exists(temp_file):
            os.unlink(temp_file)
        return None

def main():
    """主函数"""
    print("Pandoc便携版安装脚本")
    print("=" * 50)
    
    pandoc_path = setup_pandoc_portable()
    
    if pandoc_path:
        print("\n安装成功!")
        print(f"Pandoc位置: {pandoc_path}")
        print("\n现在可以运行智能文献系统并自动导出DOCX格式!")
        
        # 测试安装
        print("\n测试Pandoc...")
        try:
            import subprocess
            result = subprocess.run([pandoc_path, '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                print(f"测试成功: {version_line}")
            else:
                print("Pandoc测试失败")
        except Exception as e:
            print(f"测试失败: {e}")
            
    else:
        print("\n安装失败")
        print("请手动安装Pandoc: https://pandoc.org/installing.html")

if __name__ == "__main__":
    main()