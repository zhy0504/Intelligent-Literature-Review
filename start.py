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
    
    # 数据文件详细检查
    print(f"\n数据文件:")
    check_data_files_status_simple(cli)


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
    print("2. 快速设置（含完整状态检查 + 自动配置）")
    print("3. 启动文献系统")
    print("4. 高级管理")
    print("5. 帮助文档")
    print("0. 退出")
    print("=" * 50)


def quick_setup(cli):
    """快速设置"""
    print("\n快速设置向导")
    print("-" * 30)
    
    # 首先显示完整的系统状态检查（但不等待用户输入）
    print("正在进行系统状态检查...")
    print("=" * 50)
    
    # 调用系统状态检查但不等待输入
    show_system_status_non_interactive(cli)
    
    # 根据检查结果询问是否继续设置
    print("\n" + "=" * 50)
    print("基于上述检查结果，开始快速设置")
    print("=" * 50)
    
    # 检查Python版本
    version_ok, version_msg = cli.check_python_version()
    print(f"\nPython版本: {version_msg}")
    if not version_ok:
        print("请升级Python版本")
        return
    
    # 检查虚拟环境
    venv_status = cli.detect_virtual_environment()
    print(f"虚拟环境: {venv_status['status']}")
    
    if not venv_status['venv_exists']:
        print("正在创建虚拟环境...")
        if cli.create_virtual_environment():
            print("虚拟环境创建成功")
        else:
            print("虚拟环境创建失败")
            return
    
    # 检查依赖
    req_status = cli.get_requirements_status()
    if req_status['missing_packages']:
        print("正在安装依赖包...")
        cli.install_dependencies()
    
    # 重置AI配置
    ai_config = cli.check_ai_config()
    if ai_config['valid_services'] == 0:
        print("正在重置AI配置...")
        cli.setup_ai_config()
    
    # 设置提示词配置
    prompts_config = cli.check_prompts_config()
    if not prompts_config['file_exists']:
        print("正在重置提示词配置...")
        cli.setup_prompts_config()
    
    print("\n快速设置完成!")
    
    # 检查数据文件状态并给出提示
    print("\n" + "=" * 50)
    print("数据文件状态检查")
    print("=" * 50)
    
    try:
        from pathlib import Path
        data_dir = Path("data")
        processed_files = ["processed_zky_data.csv", "processed_jcr_data.csv"]
        raw_files = ["zky.csv", "jcr.csv"]
        
        missing_processed = []
        missing_raw = []
        
        # 检查预处理文件
        for file_name in processed_files:
            if not (data_dir / file_name).exists():
                missing_processed.append(file_name)
        
        # 检查原始文件
        for file_name in raw_files:
            if not (data_dir / file_name).exists():
                missing_raw.append(file_name)
        
        if not missing_processed:
            print("[OK] 预处理数据文件完整，系统可直接使用")
        elif not missing_raw:
            print("[INFO] 预处理文件缺失，但原始数据文件存在")
            print("[INFO] 正在生成预处理文件...")
            
            # 在虚拟环境中生成预处理文件
            if generate_processed_data():
                print("[SUCCESS] 预处理文件生成完成！")
                print("[INFO] 系统现在完全就绪，可以直接使用")
            else:
                print("[ERROR] 预处理文件生成失败")
                print("[INFO] 系统首次运行时会自动重试生成预处理文件")
        else:
            print("[WARNING] 缺少数据文件！")
            print(f"[MISSING] 需要的文件: {', '.join(raw_files)}")
            print("[SOLUTION] 请将 zky.csv 和 jcr.csv 文件放入 data/ 目录")
            print("           这些文件包含中科院分区和JCR分区数据，是系统筛选期刊的重要依据")
    
    except Exception as e:
        print(f"[ERROR] 检查数据文件时出错: {e}")
    
    # 根据AI配置状态显示相应的提示
    if ai_config['valid_services'] > 0:
        print(f"\n[OK] AI配置已完成，已有 {ai_config['valid_services']} 个有效服务")
        if ai_config['invalid_services'] > 0:
            print(f"[WARN] 有 {ai_config['invalid_services']} 个服务配置不完整，可编辑 ai_config.yaml 优化")
    else:
        print("\n[ERROR] 请编辑AI配置文件 ai_config.yaml，添加您的API密钥")


def show_help():
    """显示帮助文档"""
    print("\n" + "=" * 50)
    print("帮助文档")
    print("=" * 50)
    
    help_text = """
智能文献系统使用指南:

1. 首次使用
   - 运行 'python start.py quick_setup' 进行快速设置
   - 编辑 ai_config.yaml 添加您的API密钥
   - 运行 'python start.py check' 检查系统状态

2. 日常使用
   - 运行 'python start.py start' 启动系统
   - 运行 'python start.py manage' 进入高级管理模式
   - 运行 'python start.py status' 查看系统状态

3. 常用命令
   - python start.py                    # 显示快速菜单
   - python start.py quick_setup        # 快速设置
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
        # 显示快速菜单
        while True:
            show_quick_menu()
            choice = input("\n请选择操作: ").strip()
            
            if choice == "1":
                cli.show_system_status()
            
            elif choice == "2":
                quick_setup(cli)
            
            elif choice == "3":
                if start_literature_system():
                    print("系统启动成功")
                else:
                    print("系统启动失败")
            
            elif choice == "4":
                cli.run()
            
            elif choice == "5":
                show_help()
            
            elif choice == "0":
                print("感谢使用智能文献系统!")
                break
            
            else:
                print("无效选择，请重新输入")


if __name__ == "__main__":
    main()