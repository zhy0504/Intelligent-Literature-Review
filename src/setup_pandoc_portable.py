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
    
    # 系统映射
    system_map = {
        'windows': 'windows',
        'linux': 'linux',
        'darwin': 'macOS'  # macOS
    }
    
    # 架构映射
    arch_map = {
        'x86_64': 'x86_64',
        'amd64': 'x86_64',
        'arm64': 'arm64',
        'aarch64': 'arm64'
    }
    
    os_name = system_map.get(system, system)
    arch = arch_map.get(machine, 'x86_64')  # 默认x86_64
    
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
    
    # 构建下载URL
    if os_name == 'windows':
        filename = f"pandoc-{version}-windows-{arch}.zip"
        extract_func = extract_zip
    elif os_name == 'macOS':
        filename = f"pandoc-{version}-{arch}-macOS.tar.gz"
        extract_func = extract_tar
    else:  # linux
        filename = f"pandoc-{version}-linux-{arch}.tar.gz"
        extract_func = extract_tar
    
    url = f"https://github.com/jgm/pandoc/releases/download/{version}/{filename}"
    
    print(f"下载 {filename}...")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, timeout=300)  # 5分钟超时
        response.raise_for_status()
        
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp_file:
            tmp_file.write(response.content)
            temp_path = tmp_file.name
        
        return temp_path, extract_func
        
    except Exception as e:
        print(f"下载失败: {e}")
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
    # 项目根目录
    project_root = Path(__file__).parent
    
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
                        
                        print(f"✅ Pandoc便携版安装完成: {dest_path}")
                        pandoc_found = True
                        break
                
                if pandoc_found:
                    break
            
            if not pandoc_found:
                print("❌ 解压文件中未找到pandoc可执行文件")
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
        print("\n🎉 安装成功!")
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
                print(f"✅ {version_line}")
            else:
                print("❌ Pandoc测试失败")
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            
    else:
        print("\n❌ 安装失败")
        print("请手动安装Pandoc: https://pandoc.org/installing.html")

if __name__ == "__main__":
    main()