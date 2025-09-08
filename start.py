#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文献系统启动脚本
提供简化的启动界面和快速操作
"""

import os
import sys
import platform
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from advanced_cli import AdvancedCLI


def show_system_status_non_interactive(cli):
    """显示系统状态但不等待用户输入"""
    print("\n" + "=" * 60)
    print("系统状态详情")
    print("=" * 60)
    
    # Python版本
    version_ok, version_msg = cli.check_python_version()
    print(f"Python版本: {version_msg}")
    print(f"平台: {platform.system()} {platform.release()}")
    print(f"架构: {platform.machine()}")
    
    # 虚拟环境
    venv_status = cli.detect_virtual_environment()
    print(f"\n虚拟环境:")
    print(f"  状态: {venv_status['status']}")
    print(f"  路径: {cli.venv_path if venv_status['venv_exists'] else '不存在'}")
    print(f"  当前解释器: {venv_status['python_executable']}")
    
    # 依赖包
    req_status = cli.get_requirements_status()
    print(f"\n依赖包:")
    if req_status['file_exists']:
        print(f"  文件: {req_status['requirements_file']}")
        print(f"  总包数: {req_status['total_packages']}")
        print(f"  缺少: {len(req_status['missing_packages'])}")
        print(f"  过期: {len(req_status['outdated_packages'])}")
        
        if req_status['missing_packages']:
            print(f"  缺少包: {', '.join(req_status['missing_packages'])}")
        if req_status['outdated_packages']:
            print(f"  过期包: {', '.join(req_status['outdated_packages'])}")
    else:
        print("  依赖文件不存在")
    
    # AI配置
    ai_config = cli.check_ai_config()
    print(f"\nAI配置:")
    print(f"  文件: {ai_config['config_file']}")
    if ai_config['file_exists']:
        print(f"  有效服务: {ai_config['valid_services']}")
        print(f"  默认服务: {ai_config['default_service'] or '未设置'}")
        
        for service in ai_config['services']:
            status_icon = "[OK]" if service.get('valid', False) else "[ERR]"
            print(f"  {status_icon} {service['name']}: {service['status']}")
    
    # 提示词配置
    prompts_config = cli.check_prompts_config()
    print(f"\n提示词配置:")
    print(f"  文件: {prompts_config['config_file']}")
    if prompts_config['file_exists']:
        print(f"  提示词类型: {len(prompts_config['prompt_types'])}")
        print(f"  总提示词: {prompts_config['total_prompts']}")
    
    # 目录结构
    print(f"\n目录结构:")
    print(f"  数据目录: {'存在' if cli.data_dir.exists() else '不存在'}")
    print(f"  提示词目录: {'存在' if (cli.project_root / 'prompts').exists() else '不存在'}")
    
    # Pandoc状态检查
    pandoc_status = check_pandoc_status()
    print(f"\nPandoc (DOCX导出):")
    print(f"  状态: {pandoc_status['status']}")
    if pandoc_status['path']:
        print(f"  路径: {pandoc_status['path']}")
        print(f"  版本: {pandoc_status['version']}")
    else:
        print(f"  建议: 运行 'python src/setup_pandoc_portable.py' 安装便携版")
    
    # 数据文件详细检查
    print(f"\n数据文件:")
    check_data_files_status_simple(cli)


def check_pandoc_status():
    """检查Pandoc状态"""
    import subprocess
    import shutil
    
    # 先检查项目便携版
    project_root = Path(__file__).parent
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
        # 动态导入安装脚本
        import sys
        sys.path.insert(0, str(Path(__file__).parent / 'src'))
        
        # 导入并运行安装脚本
        import setup_pandoc_portable
        print("\n开始安装Pandoc便携版...")
        pandoc_path = setup_pandoc_portable.setup_pandoc_portable()
        
        if pandoc_path:
            print("[SUCCESS] Pandoc便携版安装成功!")
            return True
        else:
            print("[ERROR] Pandoc便携版安装失败")
            return False
            
    except Exception as e:
        print(f"安装过程出错: {e}")
        return False


def check_data_files_status_simple(cli):
    """简化的数据文件状态检查"""
    try:
        processed_files = ["processed_zky_data.csv", "processed_jcr_data.csv"]
        raw_files = ["zky.csv", "jcr.csv"]
        
        missing_processed = []
        for file_name in processed_files:
            file_path = cli.data_dir / file_name
            if file_path.exists():
                file_size = file_path.stat().st_size
                size_mb = file_size / (1024 * 1024)
                print(f"  [OK] {file_name} (预处理数据) - {size_mb:.2f} MB")
            else:
                missing_processed.append(file_name)
                print(f"  [MISSING] {file_name} (预处理数据)")
        
        if missing_processed:
            print(f"  [INFO] 预处理文件缺失，检查原始数据文件...")
            missing_raw = []
            
            for file_name in raw_files:
                file_path = cli.data_dir / file_name
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    size_mb = file_size / (1024 * 1024)
                    print(f"  [OK] {file_name} (原始数据) - {size_mb:.2f} MB")
                else:
                    missing_raw.append(file_name)
                    print(f"  [MISSING] {file_name} (原始数据)")
            
            if missing_raw:
                print(f"  [ERROR] 缺失数据文件: 预处理文件 {missing_processed} 和原始文件 {missing_raw}")
            else:
                print(f"  [WARNING] 发现原始数据文件，但预处理文件缺失")
                print(f"  [INFO] 快速设置将自动生成预处理文件")
        else:
            print(f"  [OK] 所有数据文件就绪")
            
    except Exception as e:
        print(f"  [ERROR] 检查数据文件时出错: {e}")


def generate_processed_data() -> bool:
    """生成预处理数据文件"""
    try:
        import subprocess
        import sys
        from pathlib import Path
        
        # 获取虚拟环境Python路径（与get_venv_paths逻辑一致）
        base_dir = Path(__file__).parent
        venv_dir = base_dir / "venv"
        
        if platform.system() == "Windows":
            venv_python = venv_dir / "Scripts" / "python.exe"
        else:
            venv_python = venv_dir / "bin" / "python"
        
        # 检查虚拟环境是否存在
        if not venv_python.exists():
            print(f"  [ERROR] 虚拟环境Python解释器不存在: {venv_python}")
            return False
        
        # 执行数据处理脚本
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
        
        print("  正在调用数据处理器...")
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=300,  # 5分钟超时
            cwd=str(base_dir)
        )
        
        # 显示处理输出
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"  {line}")
        
        if result.stderr and result.returncode != 0:
            print(f"  错误输出: {result.stderr}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("  [TIMEOUT] 数据处理超时（超过5分钟）")
        return False
    except Exception as e:
        print(f"  [ERROR] 调用数据处理器失败: {e}")
        return False


def start_literature_system():
    """启动文献系统，直接进入交互式检索"""
    import subprocess
    import sys
    
    print("\n启动文献系统 - 交互式检索模式")
    print("=" * 50)
    print("[INFO] 系统将先分析您的检索需求，显示总文献数后让您决定获取数量")
    print("=" * 50)
    
    # 检查Pandoc状态并提示
    pandoc_status = check_pandoc_status()
    if pandoc_status['status'] != '未安装':
        print(f"[OK] Pandoc状态: {pandoc_status['status']} - 支持DOCX导出")
    else:
        print("[WARNING] Pandoc未安装 - 仅支持Markdown格式")
        print("   运行 'python src/setup_pandoc_portable.py' 安装便携版支持DOCX导出")
    print()
    
    try:
        # 获取AI配置中的默认服务
        cli = AdvancedCLI()
        ai_config = cli.check_ai_config()
        default_service = ai_config.get('default_service')
        
        # 构建命令 - 使用配置文件中的默认AI服务
        cmd = [sys.executable, "intelligent_literature_system.py"]
        if default_service:
            cmd.extend(["--ai-config", default_service])
            print(f"使用默认AI服务: {default_service}")
        
        print(f"\n启动系统...")
        print(f"执行命令: {' '.join(cmd)}")
        print("=" * 60)
        print("[NOTE] 请在系统中输入您的检索需求")
        print("[NUMBER] 系统将在PubMed文献检索阶段显示总文献数并询问您要获取的数量")
        print("[CONFIG]  所有参数都将在系统中进行设置")
        
        # 运行命令
        result = subprocess.run(cmd)
        return result.returncode == 0
        
    except KeyboardInterrupt:
        print("\n用户取消")
        return False
    except Exception as e:
        print(f"启动失败: {e}")
        return False


def show_quick_menu():
    """显示快速菜单"""
    print("\n" + "=" * 50)
    print("智能文献系统快速启动")
    print("=" * 50)
    print("1. 系统状态检查")
    print("2. 启动文献系统")
    print("3. 高级管理")
    print("4. 帮助文档")
    print("0. 退出")
    print("=" * 50)
    print("[INFO] 系统启动时已自动检测并修复常见问题")


def quick_setup(cli):
    """快速设置 - 重定向到系统状态检查和启动逻辑"""
    print("\n[INFO] 快速设置功能已整合到系统启动检测中")
    print("正在执行系统状态检查...")
    cli.show_system_status()
    
    print("\n[INFO] 大部分设置问题会在系统启动时自动修复")
    print("如需手动处理特殊情况，请使用 'python start.py manage' 进入高级管理")


def show_help():
    """显示帮助文档"""
    print("\n" + "=" * 50)
    print("帮助文档")
    print("=" * 50)
    
    help_text = """
智能文献系统使用指南:

1. 首次使用
   - 运行 'python start.py' 系统会自动检测并修复常见问题
   - 编辑 ai_config.yaml 添加您的API密钥
   - 运行 'python start.py' 选择1检查系统状态

2. 日常使用
   - 运行 'python start.py' 选择2启动系统
   - 运行 'python start.py start' 直接启动系统
   - 运行 'python start.py manage' 进入高级管理模式

3. 常用命令
   - python start.py                    # 显示快速菜单（自动检测问题）
   - python start.py quick_setup        # 系统状态检查（兼容旧命令）
   - python start.py start              # 启动系统
   - python start.py manage             # 高级管理
   - python start.py status             # 系统状态
   - python start.py check              # 详细检查
   - python start.py setup_venv         # 创建虚拟环境
   - python start.py install_deps        # 安装依赖
   - python start.py setup_ai           # 重置AI配置
   - python start.py setup_prompts      # 重置提示词配置

4. 配置文件
   - ai_config.yaml: AI服务配置
   - prompts/prompts_config.yaml: 提示词配置
   - requirements.txt: 依赖包列表

5. 目录结构
   - data/: 数据文件目录
   - output/: 输出文件目录
   - src/: 源代码目录
   - prompts/: 提示词配置目录
   - logs/: 日志文件目录
   - backups/: 备份文件目录

6. 故障排除
   - 如果遇到依赖问题，运行 'python start.py install_deps'
   - 如果遇到AI连接问题，检查 ai_config.yaml 中的API密钥
   - 如果遇到内存问题，确保有足够的系统内存
   - 如果遇到文件权限问题，确保有读写权限

更多信息请参考项目文档或运行 'python start.py manage' 进入高级管理模式。
"""
    
    print(help_text)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="智能文献系统启动脚本")
    parser.add_argument("command", nargs="?", choices=[
        "quick_setup", "start", "manage", "status", "check", 
        "setup_venv", "install_deps", "setup_ai", "setup_prompts", "help"
    ], help="要执行的命令")
    
    args = parser.parse_args()
    
    cli = AdvancedCLI()
    
    if args.command == "quick_setup":
        quick_setup(cli)
    
    elif args.command == "start":
        if cli.start_project("interactive"):
            print("系统启动成功")
        else:
            print("系统启动失败")
    
    elif args.command == "manage":
        cli.run()
    
    elif args.command == "status":
        cli.show_system_status()
    
    elif args.command == "check":
        from cli import main as basic_main
        basic_main()
    
    elif args.command == "setup_venv":
        if cli.create_virtual_environment():
            print("虚拟环境创建成功")
        else:
            print("虚拟环境创建失败")
    
    elif args.command == "install_deps":
        if cli.install_dependencies():
            print("依赖包安装成功")
        else:
            print("依赖包安装失败")
    
    elif args.command == "setup_ai":
        if cli.setup_ai_config():
            print("AI配置设置成功")
        else:
            print("AI配置设置失败")
    
    elif args.command == "setup_prompts":
        if cli.setup_prompts_config():
            print("提示词配置设置成功")
        else:
            print("提示词配置设置失败")
    
    elif args.command == "help":
        show_help()
    
    else:
        # 启动前自动检测系统状态（包括Pandoc）
        print("\n正在检测系统环境...")
        
        # 基本环境检查
        version_ok, version_msg = cli.check_python_version()
        venv_status = cli.detect_virtual_environment()
        req_status = cli.get_requirements_status()
        pandoc_status = check_pandoc_status()
        
        # 自动修复系统问题
        issues = []
        auto_fixed = []
        
        print("正在自动检测并修复系统问题...")
        
        # 1. Python版本检查（无法自动修复）
        if not version_ok:
            issues.append("Python版本过低")
        
        # 2. 自动创建虚拟环境
        if not venv_status['venv_exists']:
            print("检测到虚拟环境不存在，正在自动创建...")
            if cli.create_virtual_environment():
                auto_fixed.append("虚拟环境已创建")
                # 重新检查虚拟环境状态
                venv_status = cli.detect_virtual_environment()
                # 重新检查依赖状态（因为虚拟环境变了）
                req_status = cli.get_requirements_status()
            else:
                issues.append("虚拟环境创建失败")
        
        # 3. 自动安装依赖包
        if req_status['missing_packages']:
            print(f"检测到{len(req_status['missing_packages'])}个依赖包缺失，正在自动安装...")
            if cli.install_dependencies():
                auto_fixed.append(f"{len(req_status['missing_packages'])}个依赖包已安装")
            else:
                issues.append(f"缺少{len(req_status['missing_packages'])}个依赖包")
        
        # 4. 自动安装Pandoc
        if pandoc_status['status'] == '未安装':
            print("检测到Pandoc未安装，正在自动安装便携版...")
            if install_pandoc_portable():
                auto_fixed.append("Pandoc便携版已安装")
                # 重新检查Pandoc状态
                pandoc_status = check_pandoc_status()
            else:
                issues.append("Pandoc未安装(无法导出DOCX)")
        
        # 5. 自动设置提示词配置
        prompts_config = cli.check_prompts_config()
        if not prompts_config['file_exists']:
            print("检测到提示词配置缺失，正在自动生成...")
            if cli.setup_prompts_config():
                auto_fixed.append("提示词配置已生成")
            else:
                issues.append("提示词配置生成失败")
        
        # 6. 检查AI配置（需要用户手动设置）
        ai_config = cli.check_ai_config()
        if ai_config['valid_services'] == 0:
            issues.append("AI配置需要手动设置API密钥")
        
        # 7. 自动处理数据文件
        try:
            from pathlib import Path
            data_dir = Path("data")
            processed_files = ["processed_zky_data.csv", "processed_jcr_data.csv"]
            raw_files = ["zky.csv", "jcr.csv"]
            
            missing_processed = [f for f in processed_files if not (data_dir / f).exists()]
            missing_raw = [f for f in raw_files if not (data_dir / f).exists()]
            
            if missing_processed and not missing_raw:
                print("检测到预处理文件缺失但原始数据存在，正在自动生成...")
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
            print("\n[SUCCESS] 自动修复完成:")
            for fix in auto_fixed:
                print(f"   [OK] {fix}")
        
        if issues:
            print("\n[WARNING] 仍需注意的问题:")
            for issue in issues:
                print(f"   - {issue}")
            # 只有在存在非AI配置问题时才推荐快速设置
            non_ai_issues = [i for i in issues if "AI配置" not in i]
            if non_ai_issues:
                print("建议运行 '2. 完整设置向导' 处理其他问题")
            if "AI配置需要手动设置API密钥" in issues:
                print("请编辑 ai_config.yaml 添加您的API密钥")
        else:
            print("\n[SUCCESS] 系统环境检查正常，所有问题已自动修复")
        
        print(f"\nPandoc状态: {pandoc_status['status']}")
        
        # 显示快速菜单
        while True:
            show_quick_menu()
            choice = input("\n请选择操作: ").strip()
            
            if choice == "1":
                cli.show_system_status()
            
            elif choice == "2":
                if start_literature_system():
                    print("系统启动成功")
                else:
                    print("系统启动失败")
            
            elif choice == "3":
                cli.run()
            
            elif choice == "4":
                show_help()
            
            elif choice == "0":
                print("感谢使用智能文献系统!")
                break
            
            else:
                print("无效选择，请重新输入")


if __name__ == "__main__":
    main()