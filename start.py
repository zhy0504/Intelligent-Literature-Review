#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文献系统启动脚本
提供简化的启动界面和快速操作
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from advanced_cli import AdvancedCLI


def start_literature_system():
    """启动文献系统，直接进入交互式检索"""
    import subprocess
    import sys
    
    print("\n启动文献系统 - 交互式检索模式")
    print("=" * 50)
    print("[INFO] 系统将先分析您的检索需求，显示总文献数后让您决定获取数量")
    print("=" * 50)
    
    try:
        # 构建命令 - 使用纯交互式模式，不预设任何参数
        cmd = [sys.executable, "intelligent_literature_system.py"]
        
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
    print("2. 快速设置（首次使用）")
    print("3. 启动文献系统")
    print("4. 高级管理")
    print("5. 帮助文档")
    print("0. 退出")
    print("=" * 50)


def quick_setup(cli):
    """快速设置"""
    print("\n快速设置向导")
    print("-" * 30)
    
    # 检查Python版本
    version_ok, version_msg = cli.check_python_version()
    print(f"Python版本: {version_msg}")
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
    
    # 根据AI配置状态显示相应的提示
    if ai_config['valid_services'] > 0:
        print(f"[OK] AI配置已完成，已有 {ai_config['valid_services']} 个有效服务")
        if ai_config['invalid_services'] > 0:
            print(f"[WARN] 有 {ai_config['invalid_services']} 个服务配置不完整，可编辑 ai_config.yaml 优化")
    else:
        print("[ERROR] 请编辑AI配置文件 ai_config.yaml，添加您的API密钥")


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