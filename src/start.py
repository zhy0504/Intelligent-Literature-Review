#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文献检索系统 - 整合启动脚本 v3.0
集成基础版本的菜单系统和增强版本的并行检查功能
自动检测虚拟环境、依赖包，并启动程序
"""

import os
import sys
import subprocess
import platform
import json
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# 确保 Windows 下的控制台支持 UTF-8
if platform.system() == "Windows":
    try:
        import os
        os.system("chcp 65001 > nul")  # 设置控制台为UTF-8编码
    except:
        pass

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent  # src目录的父目录
sys.path.insert(0, str(project_root))

try:
    from advanced_cli import AdvancedCLI
    HAS_ADVANCED_CLI = True
except ImportError:
    HAS_ADVANCED_CLI = False
    print("[WARNING] 未找到 advanced_cli 模块，高级管理功能将不可用")


class EnvironmentError(Exception):
    """环境错误异常类"""
    def __init__(self, component: str, error_type: str, message: str, solution: str = None):
        self.component = component
        self.error_type = error_type
        self.message = message
        self.solution = solution
        super().__init__(f"[{component}] {error_type}: {message}")


class ProgressTracker:
    """进度跟踪器"""
    def __init__(self, total_steps: int):
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = time.time()
        self.step_times = {}
    
    def update(self, step_name: str, status: str = "PROCESSING"):
        self.current_step += 1
        elapsed = time.time() - self.start_time
        self.step_times[step_name] = elapsed
        
        percentage = (self.current_step / self.total_steps) * 100
        progress_bar = self._generate_progress_bar(percentage)
        
        print(f"\r[{self.current_step}/{self.total_steps}] {step_name}: {status} ")
        print(f"{progress_bar} {percentage:.1f}% - 用时: {elapsed:.1f}s", end="")
        
        if self.current_step == self.total_steps:
            print(f"\n[OK] 总用时: {elapsed:.1f}s")
        else:
            print()
    
    def _generate_progress_bar(self, percentage: float, width: int = 30) -> str:
        filled = int(width * percentage / 100)
        bar = "#" * filled + "." * (width - filled)
        return f"[{bar}]"


class SystemCache:
    """系统缓存管理器"""
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path(".system_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.environment_cache = self.cache_dir / "environment_check.json"
    
    def load_environment_cache(self) -> Dict[str, Any]:
        """加载环境检查缓存"""
        if self.environment_cache.exists():
            try:
                with open(self.environment_cache, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    cache_time = datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01'))
                    if (datetime.now() - cache_time).total_seconds() < 86400:
                        return cache_data
            except Exception:
                pass
        return {}
    
    def save_environment_cache(self, data: Dict[str, Any]):
        """保存环境检查缓存"""
        data['timestamp'] = datetime.now().isoformat()
        try:
            with open(self.environment_cache, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def clear_cache(self):
        """清除缓存"""
        if self.environment_cache.exists():
            self.environment_cache.unlink()


def print_status(message, status="INFO", show_time: bool = True):
    """状态信息打印"""
    prefix = {
        "OK": "[OK]",
        "ERROR": "[ERROR]", 
        "WARNING": "[WARNING]",
        "INFO": "[INFO]",
        "SUCCESS": "[SUCCESS]",
        "PROCESSING": "[PROCESSING]"
    }
    
    time_str = f"[{datetime.now().strftime('%H:%M:%S')}] " if show_time else ""
    print(f"{prefix.get(status, '[INFO]')} {time_str}{message}")


def print_section_header(title: str):
    """打印节标题"""
    print(f"\n{'='*60}")
    print(f"    {title}")
    print(f"{'='*60}")


def print_startup_banner():
    """打印启动横幅"""
    print()
    print("="*75)
    print()
    print("        智能文献检索系统 - 整合启动脚本")
    print("        Intelligent Literature Review System v3.0")
    print()
    print("        集成特性:")
    print("        - 快速菜单与高级管理")
    print("        - 并行环境检查")  
    print("        - 进度跟踪与缓存")
    print("        - 自动问题修复")
    print()
    print("="*75)


def get_venv_paths():
    """获取虚拟环境路径"""
    base_dir = Path(__file__).parent.parent  # 项目根目录
    venv_dir = base_dir / "venv"
    
    if platform.system() == "Windows":
        venv_python = venv_dir / "Scripts" / "python.exe"
        venv_pip = venv_dir / "Scripts" / "pip.exe"
    else:
        venv_python = venv_dir / "bin" / "python"
        venv_pip = venv_dir / "bin" / "pip"
    
    return base_dir, venv_dir, venv_python, venv_pip


def check_python_version(progress_tracker: ProgressTracker = None) -> bool:
    """检查Python版本"""
    if progress_tracker:
        progress_tracker.update("Python版本检查", "PROCESSING")
    
    version = sys.version_info
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        error_msg = "需要Python 3.8或更高版本"
        solution = "请升级Python到3.8或更高版本"
        raise EnvironmentError("Python版本", "版本过低", error_msg, solution)
    
    if progress_tracker:
        progress_tracker.update("Python版本检查", "OK")
    
    return True


def check_virtual_environment(progress_tracker: ProgressTracker = None) -> bool:
    """检查或创建虚拟环境"""
    if progress_tracker:
        progress_tracker.update("虚拟环境检查", "PROCESSING")
    
    base_dir, venv_dir, venv_python, venv_pip = get_venv_paths()
    
    if not venv_dir.exists() or not venv_python.exists():
        print_status("虚拟环境不存在，正在创建...")
        print_status(f"目标路径: {venv_dir}", "INFO")
        print_status(f"Python解释器: {sys.executable}", "INFO")
        
        try:
            cmd = [sys.executable, "-m", "venv", str(venv_dir)]
            print_status(f"执行命令: {' '.join(cmd)}", "INFO")
            
            result = subprocess.run(
                cmd, 
                check=True, 
                capture_output=True, 
                text=True, 
                timeout=300
            )
            
            if result.returncode != 0:
                print_status("虚拟环境创建失败 - 详细信息:", "ERROR")
                print_status(f"返回码: {result.returncode}", "ERROR")
                if result.stdout:
                    print_status(f"标准输出: {result.stdout}", "ERROR")
                if result.stderr:
                    print_status(f"错误输出: {result.stderr}", "ERROR")
                
                error_msg = f"虚拟环境创建失败: 返回码 {result.returncode}"
                if result.stderr:
                    error_msg += f"\n错误详情: {result.stderr}"
                solution = "检查Python安装、权限设置、磁盘空间和网络连接"
                raise EnvironmentError("虚拟环境", "创建失败", error_msg, solution)
            
            print_status("虚拟环境创建成功", "OK")
            
        except subprocess.TimeoutExpired:
            print_status("虚拟环境创建超时 - 详细信息:", "ERROR")
            print_status(f"超时时间: 300秒", "ERROR")
            print_status(f"可能原因: 网络缓慢、系统资源不足", "ERROR")
            
            error_msg = "虚拟环境创建超时 (超过300秒)"
            solution = "检查网络连接、系统资源，或尝试手动创建: python -m venv venv"
            raise EnvironmentError("虚拟环境", "创建超时", error_msg, solution)
            
        except subprocess.CalledProcessError as e:
            print_status("虚拟环境创建失败 - 详细信息:", "ERROR")
            print_status(f"返回码: {e.returncode}", "ERROR")
            print_status(f"执行命令: {e.cmd}", "ERROR")
            if e.stdout:
                print_status(f"标准输出: {e.stdout}", "ERROR")
            if e.stderr:
                print_status(f"错误输出: {e.stderr}", "ERROR")
            
            error_msg = f"虚拟环境创建失败: 返回码 {e.returncode}"
            if e.stderr:
                error_msg += f"\n错误详情: {e.stderr}"
            solution = "检查Python安装完整性、目录权限、磁盘空间"
            raise EnvironmentError("虚拟环境", "创建失败", error_msg, solution)
            
        except Exception as e:
            print_status("虚拟环境创建遇到意外错误:", "ERROR")
            print_status(f"异常类型: {type(e).__name__}", "ERROR")
            print_status(f"异常详情: {str(e)}", "ERROR")
            print_status(f"当前工作目录: {os.getcwd()}", "ERROR")
            print_status(f"Python版本: {sys.version}", "ERROR")
            
            error_msg = f"虚拟环境创建遇到意外错误: {type(e).__name__}: {str(e)}"
            solution = "检查系统环境、Python安装，或联系技术支持"
            raise EnvironmentError("虚拟环境", "意外错误", error_msg, solution)
    
    if progress_tracker:
        progress_tracker.update("虚拟环境检查", "OK")
    
    return True


def check_dependencies(progress_tracker: ProgressTracker = None, system_cache: SystemCache = None) -> bool:
    """检查依赖包"""
    if progress_tracker:
        progress_tracker.update("依赖包检查", "PROCESSING")
    
    base_dir, venv_dir, venv_python, venv_pip = get_venv_paths()
    
    # 检查requirements.txt文件
    requirements_file = base_dir / "requirements.txt"
    if not requirements_file.exists():
        error_msg = "requirements.txt文件不存在"
        solution = "请确保项目根目录包含requirements.txt文件"
        raise EnvironmentError("依赖包", "配置文件缺失", error_msg, solution)
    
    # 检查PowerShell缓存决定
    ps_cache_used = os.environ.get('PS_CACHE_USED', '').lower() == 'true'
    if ps_cache_used:
        print_status("使用PowerShell脚本中的缓存决定", "INFO")
        if progress_tracker:
            progress_tracker.update("依赖包检查", "OK")
        return True
    
    # 检查缓存
    cache_data = system_cache.load_environment_cache() if system_cache else {}
    if cache_data.get('dependencies_checked', False):
        print_status("使用缓存的依赖包检查结果", "INFO")
        if progress_tracker:
            progress_tracker.update("依赖包检查", "OK")
        return True
    
    # 检查依赖包
    try:
        result = subprocess.run([
            str(venv_python), "-c", """
import sys
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
    except Exception:
        return {
            'requests': 'requests',
            'pandas': 'pandas', 
            'numpy': 'numpy',
            'PyYAML': 'yaml'
        }

required_packages = parse_requirements()
missing = []

for package_name, import_name in required_packages.items():
    try:
        __import__(import_name)
    except ImportError:
        missing.append(package_name)

if missing:
    print(f'缺少依赖包: {len(missing)} 个')
    for pkg in missing:
        print(f'  X {pkg}')
    exit(1)
else:
    print(f'+ 所有依赖包检查完成 ({len(required_packages)}/{len(required_packages)})')
"""
        ], capture_output=True, text=True, check=False, timeout=60)
        
        if result.stdout:
            print(result.stdout)
        
        if result.returncode != 0:
            print_status("发现缺失的依赖包，正在安装...", "WARNING")
            success = install_dependencies(system_cache)
            if success and system_cache:
                cache_data['dependencies_checked'] = True
                system_cache.save_environment_cache(cache_data)
            return success
        else:
            if system_cache:
                cache_data['dependencies_checked'] = True
                system_cache.save_environment_cache(cache_data)
            if progress_tracker:
                progress_tracker.update("依赖包检查", "OK")
            return True
            
    except subprocess.TimeoutExpired:
        error_msg = "依赖包检查超时"
        solution = "检查网络连接或手动安装依赖包"
        raise EnvironmentError("依赖包", "检查超时", error_msg, solution)
    except Exception as e:
        print_status(f"检查依赖包时出错: {e}", "ERROR")
        return install_dependencies(system_cache)


def install_dependencies(system_cache: SystemCache = None) -> bool:
    """安装依赖包"""
    base_dir, venv_dir, venv_python, venv_pip = get_venv_paths()
    requirements_file = base_dir / "requirements.txt"
    
    print_status("安装依赖包...")
    
    try:
        # 升级pip
        print_status("升级pip...")
        subprocess.run([
            str(venv_python), "-m", "pip", "install", "--upgrade", "pip"
        ], capture_output=True, text=True, timeout=120)
        
        # 尝试安装依赖包
        print_status("安装依赖包（官方源）...")
        result = subprocess.run([
            str(venv_pip), "install", "-r", str(requirements_file)
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print_status("依赖包安装完成", "OK")
            return True
        
        # 使用镜像源重试
        print_status("使用清华镜像源重新安装...", "INFO")
        result = subprocess.run([
            str(venv_pip), "install", "-r", str(requirements_file),
            "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
            "--trusted-host", "pypi.tuna.tsinghua.edu.cn"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print_status("依赖包安装完成（清华镜像）", "OK")
            return True
        
        error_msg = "依赖包安装失败"
        solution = "请检查网络连接，或手动执行：pip install -r requirements.txt"
        raise EnvironmentError("依赖包", "安装失败", error_msg, solution)
        
    except subprocess.TimeoutExpired:
        error_msg = "依赖包安装超时"
        solution = "检查网络连接或手动安装依赖包"
        raise EnvironmentError("依赖包", "安装超时", error_msg, solution)
    except Exception as e:
        error_msg = f"依赖包安装失败: {e}"
        solution = "检查Python环境和网络连接"
        raise EnvironmentError("依赖包", "安装异常", error_msg, solution)


def check_data_files(progress_tracker: ProgressTracker = None) -> bool:
    """检查数据文件"""
    if progress_tracker:
        progress_tracker.update("数据文件检查", "PROCESSING")
    
    base_dir, _, _, _ = get_venv_paths()
    data_dir = base_dir / "data"
    
    if not data_dir.exists():
        error_msg = "data目录不存在"
        solution = "请在项目根目录创建data目录并放入所需文件"
        raise EnvironmentError("数据文件", "目录缺失", error_msg, solution)
    
    # 检查预处理文件
    processed_files = ["processed_zky_data.csv", "processed_jcr_data.csv"]
    raw_files = ["zky.csv", "jcr.csv"]
    
    missing_processed = []
    for file_name in processed_files:
        file_path = data_dir / file_name
        if file_path.exists():
            file_size = file_path.stat().st_size
            size_mb = file_size / (1024 * 1024)
            print(f"    [OK] {file_name} (预处理数据) - {size_mb:.2f} MB")
        else:
            missing_processed.append(file_name)
            print(f"    [MISSING] {file_name} (预处理数据)")
    
    # 如果预处理文件缺失，检查原始文件
    if missing_processed:
        print_status("预处理文件缺失，检查原始数据文件...", "INFO")
        missing_raw = []
        
        for file_name in raw_files:
            file_path = data_dir / file_name
            if file_path.exists():
                file_size = file_path.stat().st_size
                size_mb = file_size / (1024 * 1024)
                print(f"    [OK] {file_name} (原始数据) - {size_mb:.2f} MB")
            else:
                missing_raw.append(file_name)
                print(f"    [MISSING] {file_name} (原始数据)")
        
        if missing_raw:
            error_msg = f"缺失数据文件: 预处理文件 {missing_processed} 和原始文件 {missing_raw}"
            solution = "请将原始数据文件 zky.csv 和 jcr.csv 放在 data/ 目录下"
            raise EnvironmentError("数据文件", "文件缺失", error_msg, solution)
        
        print_status("发现原始数据文件，系统运行时会自动生成预处理文件", "INFO")
    
    if progress_tracker:
        progress_tracker.update("数据文件检查", "OK")
    
    return True


def check_main_script(progress_tracker: ProgressTracker = None) -> bool:
    """检查核心程序脚本"""
    if progress_tracker:
        progress_tracker.update("核心程序检查", "PROCESSING")
    
    base_dir, _, _, _ = get_venv_paths()
    main_program = base_dir / "src" / "intelligent_literature_system.py"
    
    if not main_program.exists():
        error_msg = "主程序文件不存在: src/intelligent_literature_system.py"
        solution = "请确保主程序文件在src目录"
        raise EnvironmentError("主程序", "文件缺失", error_msg, solution)
    
    if progress_tracker:
        progress_tracker.update("核心程序检查", "OK")
    
    return True


def check_pandoc_status():
    """检查Pandoc状态"""
    import subprocess
    import shutil
    
    # 检查项目便携版
    project_root = Path(__file__).parent.parent  # 项目根目录
    system = platform.system().lower()
    
    portable_paths = {
        'windows': 'tools/pandoc/windows/pandoc.exe',
        'linux': 'tools/pandoc/linux/pandoc',
        'darwin': 'tools/pandoc/macos/pandoc'
    }
    
    if system in portable_paths:
        portable_path = project_root / portable_paths[system]
        if portable_path.exists():
            try:
                result = subprocess.run([str(portable_path), '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    version = result.stdout.split('\n')[0]
                    return {
                        'status': '已安装 (便携版)',
                        'path': str(portable_path),
                        'version': version
                    }
            except Exception:
                pass
    
    # 检查系统PATH中的pandoc
    pandoc_cmd = 'pandoc.exe' if system == 'windows' else 'pandoc'
    pandoc_path = shutil.which(pandoc_cmd)
    
    if pandoc_path:
        try:
            result = subprocess.run([pandoc_cmd, '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                return {
                    'status': '已安装 (系统)',
                    'path': pandoc_path,
                    'version': version
                }
        except Exception:
            pass
    
    return {
        'status': '未安装',
        'path': None,
        'version': None
    }


def install_pandoc_portable():
    """安装Pandoc便携版"""
    try:
        # 从src目录导入
        import setup_pandoc_portable
        print_status("开始安装Pandoc便携版...")
        pandoc_path = setup_pandoc_portable.setup_pandoc_portable()
        
        if pandoc_path:
            print_status("Pandoc便携版安装成功!", "SUCCESS")
            return True
        else:
            print_status("Pandoc便携版安装失败", "ERROR")
            return False
            
    except Exception as e:
        print_status(f"安装过程出错: {e}", "ERROR")
        return False


def generate_processed_data() -> bool:
    """生成预处理数据文件"""
    try:
        base_dir, venv_dir, venv_python, _ = get_venv_paths()
        
        if not venv_python.exists():
            print_status(f"虚拟环境Python解释器不存在: {venv_python}", "ERROR")
            return False
        
        cmd = [
            str(venv_python), 
            "-c", 
            """
import sys
import os
sys.path.append('src')
try:
    from data_processor import JournalDataProcessor
    print('正在处理中科院和JCR数据...')
    processor = JournalDataProcessor()
    processor.process_separate()
    print('数据处理完成')
except Exception as e:
    print(f'数据处理失败: {e}')
    sys.exit(1)
"""
        ]
        
        print_status("正在调用数据处理器...")
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=300,
            cwd=str(base_dir)
        )
        
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"  {line}")
        
        if result.stderr and result.returncode != 0:
            print_status(f"错误输出: {result.stderr}", "ERROR")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print_status("数据处理超时（超过5分钟）", "ERROR")
        return False
    except Exception as e:
        print_status(f"调用数据处理器失败: {e}", "ERROR")
        return False


def parallel_environment_checks(force_check: bool = False) -> Dict[str, bool]:
    """并行执行环境检查"""
    system_cache = SystemCache()
    
    print_section_header("环境检查")
    
    # 检查是否有缓存以及是否强制重新检查
    if not force_check:
        cache_data = system_cache.load_environment_cache()
        if cache_data.get('dependencies_checked'):
            cache_time = cache_data.get('timestamp', '')
            
            # 检查是否从PowerShell脚本传来的缓存决定
            ps_cache_used = os.environ.get('PS_CACHE_USED', '').lower() == 'true'
            ps_cache_asked = os.environ.get('PS_CACHE_ASKED', '').lower() == 'true'
            
            if ps_cache_used:
                print_status("使用PowerShell脚本中的缓存决定", "INFO")
                return {
                    "Python版本": True,
                    "虚拟环境": True,
                    "依赖包": True,
                    "数据文件": True,
                    "核心程序": True
                }
            elif ps_cache_asked:
                print_status("PowerShell脚本已询问过缓存使用，执行完整检查", "INFO")
                # 跳过缓存，直接进行完整检查
                pass  
            else:
                print(f"发现环境检查缓存 (时间: {cache_time[:19]})")
                
                try:
                    choice = input("是否使用缓存结果？(Y/n): ").strip().lower()
                    if choice in ['', 'y', 'yes']:
                        print_status("使用缓存的环境检查结果", "INFO")
                        return {
                            "Python版本": True,
                            "虚拟环境": True,
                            "依赖包": True,
                            "数据文件": True,
                            "核心程序": True
                        }
                    else:
                        print_status("重新执行环境检查", "INFO")
                except (EOFError, KeyboardInterrupt):
                    print_status("使用缓存的环境检查结果", "INFO")
                    return {
                        "Python版本": True,
                        "虚拟环境": True,
                        "依赖包": True,
                        "数据文件": True,
                        "核心程序": True
                    }
    
    # 使用线程池并行执行检查（不使用共享进度跟踪器）
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_check = {
            executor.submit(check_python_version): "Python版本",
            executor.submit(check_virtual_environment): "虚拟环境",
            executor.submit(check_data_files): "数据文件",
            executor.submit(check_main_script): "核心程序"
        }
        
        results = {}
        errors = []
        completed = 0
        total = len(future_to_check)
        
        for future in as_completed(future_to_check):
            check_name = future_to_check[future]
            completed += 1
            try:
                result = future.result()
                results[check_name] = result
                print_status(f"[{completed}/{total}] {check_name}: {'通过' if result else '失败'}", "OK" if result else "ERROR")
                if not result:
                    errors.append(f"{check_name}检查失败")
            except EnvironmentError as e:
                results[check_name] = False
                errors.append(f"{check_name}: {e.message}")
                print_status(f"[{completed}/{total}] {check_name}: 错误 - {e.message}", "ERROR")
                if e.solution:
                    print_status(f"解决方案: {e.solution}", "INFO")
            except Exception as e:
                results[check_name] = False
                errors.append(f"{check_name}: {str(e)}")
                print_status(f"[{completed}/{total}] {check_name}: 异常 - {str(e)}", "ERROR")
    
    # 依赖包检查（串行）
    # 检查PowerShell缓存决定
    ps_cache_used = os.environ.get('PS_CACHE_USED', '').lower() == 'true'
    if ps_cache_used:
        print_status(f"[{total + 1}/{total + 1}] 依赖包: 通过 (使用PowerShell缓存)", "OK")
        results["依赖包"] = True
    else:
        print_status(f"[{completed + 1}/{total + 1}] 依赖包检查: 进行中...", "PROCESSING")
        try:
            dep_result = check_dependencies(None, system_cache)
            results["依赖包"] = dep_result
            print_status(f"[{total + 1}/{total + 1}] 依赖包: {'通过' if dep_result else '失败'}", "OK" if dep_result else "ERROR")
            if not dep_result:
                errors.append("依赖包检查失败")
        except EnvironmentError as e:
            results["依赖包"] = False
            errors.append(f"依赖包: {e.message}")
            print_status(f"[{total + 1}/{total + 1}] 依赖包: 错误 - {e.message}", "ERROR")
            if e.solution:
                print_status(f"解决方案: {e.solution}", "INFO")
        except Exception as e:
            results["依赖包"] = False
            errors.append(f"依赖包: {str(e)}")
            print_status(f"[{total + 1}/{total + 1}] 依赖包: 异常 - {str(e)}", "ERROR")
    
    if errors:
        print_status(f"发现 {len(errors)} 个问题:", "ERROR")
        for error in errors:
            print(f"  - {error}")
        return results
    
    # 所有检查通过，保存缓存
    cache_data = {"dependencies_checked": True}
    system_cache.save_environment_cache(cache_data)
    
    print_status("所有环境检查通过！", "SUCCESS")
    return results


def start_literature_system():
    """启动文献系统"""
    print_section_header("启动文献系统")
    print_status("系统将先分析您的检索需求，显示总文献数后让您决定获取数量", "INFO")
    
    # 检查Pandoc状态
    pandoc_status = check_pandoc_status()
    if pandoc_status['status'] != '未安装':
        print_status(f"Pandoc状态: {pandoc_status['status']} - 支持DOCX导出", "OK")
    else:
        print_status("Pandoc未安装 - 正在自动安装便携版...", "WARNING")
        if install_pandoc_portable():
            print_status("Pandoc便携版安装成功 - 现在支持DOCX导出", "SUCCESS")
        else:
            print_status("Pandoc安装失败 - 仅支持Markdown格式", "WARNING")
            print_status("您可以手动安装Pandoc或稍后重试", "INFO")
    
    try:
        base_dir, _, _, _ = get_venv_paths()
        
        # 构建启动命令
        cmd = [sys.executable, str(base_dir / "src" / "intelligent_literature_system.py")]
        
        # 如果有高级CLI，获取AI配置
        if HAS_ADVANCED_CLI:
            try:
                cli = AdvancedCLI()
                ai_config = cli.check_ai_config()
                default_service = ai_config.get('default_service')
                if default_service:
                    cmd.extend(["--ai-config", default_service])
                    print_status(f"使用默认AI服务: {default_service}", "INFO")
            except Exception:
                pass
        
        print_status("启动系统...", "INFO")
        print_status(f"执行命令: {' '.join(cmd)}", "INFO")
        
        # 运行命令
        result = subprocess.run(cmd, cwd=str(base_dir))
        return result.returncode == 0
        
    except KeyboardInterrupt:
        print_status("用户取消", "WARNING")
        return False
    except Exception as e:
        print_status(f"启动失败: {e}", "ERROR")
        return False


def show_quick_menu():
    """显示快速菜单"""
    print_section_header("智能文献系统快速启动")
    print("1. 系统状态检查")
    print("2. 启动文献系统") 
    print("3. 高级管理" + ("" if HAS_ADVANCED_CLI else " (不可用)"))
    print("4. 帮助文档")
    print("0. 退出")
    print("=" * 60)


def show_help():
    """显示帮助文档"""
    print_section_header("帮助文档")
    
    help_text = """
智能文献系统使用指南:

1. 首次使用
   - 运行 'python src/start.py' 系统会自动检测并修复问题
   - 编辑 ai_config.yaml 添加您的API密钥
   - 运行系统状态检查确认环境

2. 日常使用
   - 运行 'python src/start.py' 选择2启动系统
   - 运行 'python src/start.py start' 直接启动
   - 运行 'python src/start.py manage' 进入高级管理

3. 常用命令
   - python src/start.py              # 显示快速菜单
   - python src/start.py start        # 启动系统
   - python src/start.py manage       # 高级管理
   - python src/start.py status       # 系统状态
   - python src/start.py --check-only # 仅检查环境
   - python src/start.py --force-check # 强制重新检查（忽略缓存）

4. 配置文件
   - ai_config.yaml: AI服务配置
   - prompts_config.yaml: 提示词配置
   - requirements.txt: 依赖包列表

5. 数据文件
   - data/zky.csv, data/jcr.csv: 原始数据
   - data/processed_*.csv: 预处理数据（自动生成）

6. 故障排除
   - 运行环境检查诊断问题
   - 检查ai_config.yaml中的API密钥
   - 确保有足够的系统内存和磁盘空间
"""
    print(help_text)


def auto_fix_environment():
    """自动修复环境问题"""
    print_section_header("自动环境修复")
    
    issues = []
    auto_fixed = []
    
    # 基本环境检查
    try:
        check_python_version()
    except EnvironmentError as e:
        issues.append(f"Python版本: {e.message}")
    
    # 虚拟环境
    try:
        base_dir, venv_dir, _, _ = get_venv_paths()
        if not venv_dir.exists():
            print_status("检测到虚拟环境不存在，正在自动创建...")
            check_virtual_environment()
            auto_fixed.append("虚拟环境已创建")
    except EnvironmentError as e:
        print_status(f"虚拟环境自动创建失败:", "ERROR")
        print_status(f"错误类型: {e.category}", "ERROR")
        print_status(f"错误状态: {e.status}", "ERROR") 
        print_status(f"错误信息: {e.message}", "ERROR")
        if e.solution:
            print_status(f"建议解决方案: {e.solution}", "INFO")
        issues.append(f"虚拟环境: {e.message}")
    except Exception as e:
        print_status(f"虚拟环境检查遇到意外错误:", "ERROR")
        print_status(f"异常类型: {type(e).__name__}", "ERROR")
        print_status(f"异常详情: {str(e)}", "ERROR")
        issues.append(f"虚拟环境: 意外错误 - {str(e)}")
    
    # Pandoc
    pandoc_status = check_pandoc_status()
    if pandoc_status['status'] == '未安装':
        print_status("检测到Pandoc未安装，正在自动安装便携版...")
        if install_pandoc_portable():
            auto_fixed.append("Pandoc便携版已安装")
        else:
            issues.append("Pandoc未安装(无法导出DOCX)")
    
    # 数据文件处理
    try:
        base_dir, _, _, _ = get_venv_paths()
        data_dir = base_dir / "data"
        processed_files = ["processed_zky_data.csv", "processed_jcr_data.csv"]
        raw_files = ["zky.csv", "jcr.csv"]
        
        missing_processed = [f for f in processed_files if not (data_dir / f).exists()]
        missing_raw = [f for f in raw_files if not (data_dir / f).exists()]
        
        if missing_processed and not missing_raw:
            print_status("检测到预处理文件缺失但原始数据存在，正在自动生成...")
            if generate_processed_data():
                auto_fixed.append("数据预处理文件已生成")
            else:
                issues.append("数据预处理文件生成失败")
        elif missing_raw:
            issues.append(f"缺少数据文件: {', '.join(raw_files)}")
    except Exception as e:
        issues.append(f"数据文件检查失败: {e}")
    
    # 显示结果
    if auto_fixed:
        print_status("自动修复完成:", "SUCCESS")
        for fix in auto_fixed:
            print(f"   [OK] {fix}")
    
    if issues:
        print_status("仍需注意的问题:", "WARNING")
        for issue in issues:
            print(f"   - {issue}")
    
    if not issues:
        print_status("系统环境检查正常，所有问题已自动修复", "SUCCESS")
    
    return len(issues) == 0


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="智能文献系统整合启动脚本", add_help=False)
    parser.add_argument("command", nargs="?", choices=[
        "start", "manage", "status", "check"
    ], help="要执行的命令")
    parser.add_argument("--check-only", action="store_true", help="仅检查环境")
    parser.add_argument("--force-check", action="store_true", help="强制重新检查（忽略缓存）")
    parser.add_argument("--help", "-h", action="store_true", help="显示帮助")
    
    try:
        args = parser.parse_args()
    except:
        args = argparse.Namespace(command=None, check_only=False, force_check=False, help=False)
    
    # 打印启动横幅
    print_startup_banner()
    
    if args.help:
        show_help()
        return
    
    if args.check_only:
        print_section_header("环境检查模式")
        results = parallel_environment_checks(force_check=args.force_check)
        failed_checks = [name for name, result in results.items() if not result]
        
        if failed_checks:
            print_status(f"以下检查未通过: {', '.join(failed_checks)}", "ERROR")
            sys.exit(1)
        else:
            print_status("系统准备就绪！", "SUCCESS")
        return
    
    if args.command == "start":
        if start_literature_system():
            print_status("系统启动成功", "SUCCESS")
        else:
            print_status("系统启动失败", "ERROR")
            sys.exit(1)
        return
    
    if args.command == "manage":
        if HAS_ADVANCED_CLI:
            cli = AdvancedCLI()
            cli.run()
        else:
            print_status("高级管理功能不可用，缺少 advanced_cli 模块", "ERROR")
        return
    
    if args.command == "status":
        if HAS_ADVANCED_CLI:
            cli = AdvancedCLI()
            cli.show_system_status()
        else:
            results = parallel_environment_checks(force_check=args.force_check)
            failed_checks = [name for name, result in results.items() if not result]
            if not failed_checks:
                print_status("系统状态正常", "SUCCESS")
            else:
                print_status(f"发现问题: {', '.join(failed_checks)}", "WARNING")
        return
    
    if args.command == "check":
        print_section_header("详细系统检查")
        try:
            from cli import main as basic_main
            basic_main()
        except ImportError:
            print_status("详细检查功能不可用，缺少 cli 模块", "WARNING")
            results = parallel_environment_checks(force_check=args.force_check)
        return
    
    # 默认交互模式
    print_status("启动前自动检测系统环境...")
    
    # 使用带缓存询问功能的环境检查
    try:
        results = parallel_environment_checks(force_check=args.force_check)
        failed_checks = [name for name, result in results.items() if not result]
        
        if failed_checks:
            print_status(f"检测到环境问题: {', '.join(failed_checks)}", "WARNING")
            print_status("建议先解决问题再启动系统", "INFO")
            # 尝试自动修复
            if not auto_fix_environment():
                print_status("自动修复失败，请手动解决环境问题", "WARNING")
        else:
            print_status("系统环境检查通过", "SUCCESS")
    except Exception as e:
        print_status(f"环境检查失败: {e}", "ERROR")
        # 回退到自动修复
        if not auto_fix_environment():
            print_status("检测到环境问题，建议先解决问题再启动系统", "WARNING")
    
    # 显示快速菜单
    while True:
        show_quick_menu()
        choice = input("\n请选择操作: ").strip()
        
        if choice == "1":
            if HAS_ADVANCED_CLI:
                cli = AdvancedCLI()
                cli.show_system_status()
            else:
                results = parallel_environment_checks(force_check=args.force_check)
        
        elif choice == "2":
            if start_literature_system():
                print_status("系统启动成功", "SUCCESS")
            else:
                print_status("系统启动失败", "ERROR")
        
        elif choice == "3":
            if HAS_ADVANCED_CLI:
                cli = AdvancedCLI()
                cli.run()
            else:
                print_status("高级管理功能不可用，缺少 advanced_cli 模块", "ERROR")
        
        elif choice == "4":
            show_help()
        
        elif choice == "0":
            print_status("感谢使用智能文献系统!", "INFO")
            break
        
        else:
            print_status("无效选择，请重新输入", "WARNING")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断操作")
        sys.exit(0)
    except Exception as e:
        print_status(f"程序异常: {e}", "ERROR")
        sys.exit(1)