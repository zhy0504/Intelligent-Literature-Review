#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文献系统高级CLI客户端
提供交互式菜单、配置管理、系统监控等功能
"""

import os
import sys
import subprocess
import json
import yaml
import platform
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from cli import IntelligentLiteratureCLI


class AdvancedCLI(IntelligentLiteratureCLI):
    """高级CLI客户端"""
    
    def __init__(self):
        super().__init__()
        self.history_file = self.project_root / ".cli_history.json"
        self.log_file = self.project_root / "logs" / "cli.log"
        self.output_dir = self.project_root / "综述文章"
        
        # 创建日志目录
        self.log_file.parent.mkdir(exist_ok=True)
        
        # 加载历史记录
        self.history = self._load_history()
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """加载历史记录"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_history(self):
        """保存历史记录"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history[-100:], f, indent=2, ensure_ascii=False)  # 保存最近100条记录
        except Exception as e:
            print(f"保存历史记录失败: {e}")
    
    def _log_action(self, action: str, details: Dict[str, Any] = None):
        """记录操作日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details or {}
        }
        
        self.history.append(log_entry)
        self._save_history()
        
        # 写入日志文件
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"{log_entry['timestamp']} - {action}\n")
                if details:
                    f.write(f"  Details: {json.dumps(details, ensure_ascii=False)}\n")
        except Exception as e:
            print(f"写入日志失败: {e}")
    
    def show_welcome(self):
        """显示欢迎信息"""
        print("=" * 60)
        print("    智能文献系统高级CLI客户端")
        print("=" * 60)
        print("版本: 1.0.0")
        print(f"项目路径: {self.project_root}")
        print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
    
    def show_menu(self):
        """显示主菜单"""
        print("\n主菜单:")
        print("1. 系统状态检查")
        print("2. 虚拟环境管理")
        print("3. 依赖包管理")
        print("4. AI配置管理")
        print("5. 提示词配置管理")
        print("6. 项目启动")
        print("7. 数据管理")
        print("8. 日志和监控")
        print("9. 系统工具")
        print("0. 退出")
    
    def show_system_status(self):
        """显示详细系统状态"""
        print("\n" + "=" * 60)
        print("系统状态详情")
        print("=" * 60)
        
        # Python版本
        version_ok, version_msg = self.check_python_version()
        print(f"Python版本: {version_msg}")
        print(f"平台: {platform.system()} {platform.release()}")
        print(f"架构: {platform.machine()}")
        
        # 虚拟环境
        venv_status = self.detect_virtual_environment()
        print(f"\n虚拟环境:")
        print(f"  状态: {venv_status['status']}")
        print(f"  路径: {self.venv_path if venv_status['venv_exists'] else '不存在'}")
        print(f"  当前解释器: {venv_status['python_executable']}")
        
        # 依赖包
        req_status = self.get_requirements_status()
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
        ai_config = self.check_ai_config()
        print(f"\nAI配置:")
        print(f"  文件: {ai_config['config_file']}")
        if ai_config['file_exists']:
            print(f"  有效服务: {ai_config['valid_services']}")
            print(f"  默认服务: {ai_config['default_service'] or '未设置'}")
            
            for service in ai_config['services']:
                status_icon = "[OK]" if service.get('valid', False) else "[ERR]"
                print(f"  {status_icon} {service['name']}: {service['status']}")
        
        # 提示词配置
        prompts_config = self.check_prompts_config()
        print(f"\n提示词配置:")
        print(f"  文件: {prompts_config['config_file']}")
        if prompts_config['file_exists']:
            print(f"  提示词类型: {len(prompts_config['prompt_types'])}")
            print(f"  总提示词: {prompts_config['total_prompts']}")
        
        # 目录结构
        print(f"\n目录结构:")
        print(f"  数据目录: {'存在' if self.data_dir.exists() else '不存在'}")
        print(f"  输出目录: {'存在' if self.output_dir.exists() else '不存在'}")
        print(f"  提示词目录: {'存在' if (self.project_root / 'prompts').exists() else '不存在'}")
        
        input("\n按回车键继续...")
    
    def manage_virtual_environment(self):
        """虚拟环境管理"""
        while True:
            print("\n" + "=" * 60)
            print("虚拟环境管理")
            print("=" * 60)
            
            venv_status = self.detect_virtual_environment()
            print(f"当前状态: {venv_status['status']}")
            
            print("\n选项:")
            print("1. 创建虚拟环境")
            print("2. 激活虚拟环境")
            print("3. 删除虚拟环境")
            print("4. 查看虚拟环境信息")
            print("0. 返回主菜单")
            
            choice = input("\n请选择操作: ").strip()
            
            if choice == "1":
                if venv_status['venv_exists']:
                    print("虚拟环境已存在")
                else:
                    if self.create_virtual_environment():
                        self._log_action("创建虚拟环境", {"path": str(self.venv_path)})
                        print("虚拟环境创建成功")
                    else:
                        print("虚拟环境创建失败")
            
            elif choice == "2":
                activate_cmd = self.activate_virtual_environment()
                if activate_cmd:
                    print(f"激活命令:")
                    print(f"  Windows: {activate_cmd}")
                    print(f"  Linux/Mac: {activate_cmd}")
                    print("请在命令行中执行此命令")
                else:
                    print("虚拟环境不存在")
            
            elif choice == "3":
                if venv_status['venv_exists']:
                    confirm = input("确定要删除虚拟环境吗? (y/N): ").lower()
                    if confirm == 'y':
                        try:
                            shutil.rmtree(self.venv_path)
                            self._log_action("删除虚拟环境", {"path": str(self.venv_path)})
                            print("虚拟环境删除成功")
                        except Exception as e:
                            print(f"删除虚拟环境失败: {e}")
                else:
                    print("虚拟环境不存在")
            
            elif choice == "4":
                print(f"\n虚拟环境详细信息:")
                print(f"  路径: {venv_status['venv_path']}")
                print(f"  状态: {venv_status['status']}")
                print(f"  平台: {venv_status['platform']}")
                print(f"  当前解释器: {venv_status['python_executable']}")
                if venv_status['venv_python']:
                    print(f"  虚拟环境Python: {venv_status['venv_python']}")
            
            elif choice == "0":
                break
            
            else:
                print("无效选择")
    
    def manage_dependencies(self):
        """依赖包管理"""
        while True:
            print("\n" + "=" * 60)
            print("依赖包管理")
            print("=" * 60)
            
            req_status = self.get_requirements_status()
            print(f"依赖文件: {req_status['requirements_file']}")
            if req_status['file_exists']:
                print(f"总包数: {req_status['total_packages']}")
                print(f"缺少: {len(req_status['missing_packages'])}")
                print(f"过期: {len(req_status['outdated_packages'])}")
            
            print("\n选项:")
            print("1. 查看依赖包详情")
            print("2. 安装依赖包")
            print("3. 升级依赖包")
            print("4. 安装特定包")
            print("5. 创建requirements.txt")
            print("0. 返回主菜单")
            
            choice = input("\n请选择操作: ").strip()
            
            if choice == "1":
                self.show_dependency_details(req_status)
            
            elif choice == "2":
                if self.install_dependencies():
                    self._log_action("安装依赖包")
                    print("依赖包安装成功")
                else:
                    print("依赖包安装失败")
            
            elif choice == "3":
                if self.install_dependencies(upgrade=True):
                    self._log_action("升级依赖包")
                    print("依赖包升级成功")
                else:
                    print("依赖包升级失败")
            
            elif choice == "4":
                package_name = input("输入包名: ").strip()
                if package_name:
                    self.install_package(package_name)
            
            elif choice == "5":
                self.create_requirements_file()
            
            elif choice == "0":
                break
            
            else:
                print("无效选择")
    
    def show_dependency_details(self, req_status):
        """显示依赖包详情"""
        print("\n依赖包详情:")
        print("-" * 60)
        
        for pkg in req_status['packages']:
            status_icon = "✓" if pkg['installed'] else "✗"
            version_info = f"{pkg['installed_version'] or '未安装'}"
            if pkg['required_version']:
                version_info += f" (要求: {pkg['required_version']})"
            
            print(f"{status_icon} {pkg['name']}: {version_info}")
        
        input("\n按回车键继续...")
    
    def install_package(self, package_name: str):
        """安装特定包"""
        try:
            print(f"正在安装 {package_name}...")
            cmd = [sys.executable, "-m", "pip", "install", package_name]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"{package_name} 安装成功")
            self._log_action("安装包", {"package": package_name})
        except subprocess.CalledProcessError as e:
            print(f"安装失败: {e}")
    
    def create_requirements_file(self):
        """创建requirements.txt文件"""
        try:
            print("正在生成requirements.txt...")
            cmd = [sys.executable, "-m", "pip", "freeze"]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            with open(self.requirements_file, 'w', encoding='utf-8') as f:
                f.write(result.stdout)
            
            print(f"requirements.txt 已创建: {self.requirements_file}")
            self._log_action("创建requirements文件")
        except Exception as e:
            print(f"创建requirements.txt失败: {e}")
    
    def manage_ai_config(self):
        """AI配置管理"""
        while True:
            print("\n" + "=" * 60)
            print("AI配置管理")
            print("=" * 60)
            
            ai_config = self.check_ai_config()
            print(f"配置文件: {ai_config['config_file']}")
            print(f"有效服务: {ai_config['valid_services']}")
            print(f"默认服务: {ai_config['default_service'] or '未设置'}")
            
            print("\n选项:")
            print("1. 查看AI配置详情")
            print("2. 重置AI配置")
            print("3. 编辑AI配置")
            print("4. 测试AI连接")
            print("5. 切换默认服务")
            print("0. 返回主菜单")
            
            choice = input("\n请选择操作: ").strip()
            
            if choice == "1":
                self.show_ai_config_details(ai_config)
            
            elif choice == "2":
                if self.setup_ai_config():
                    self._log_action("重置AI配置")
                    print("AI配置设置成功")
                else:
                    print("AI配置设置失败")
            
            elif choice == "3":
                self.edit_ai_config()
            
            elif choice == "4":
                self.test_ai_connection()
            
            elif choice == "5":
                self.switch_default_service(ai_config)
            
            elif choice == "0":
                break
            
            else:
                print("无效选择")
    
    def show_ai_config_details(self, ai_config):
        """显示AI配置详情"""
        print("\nAI配置详情:")
        print("-" * 60)
        
        for service in ai_config['services']:
            status_icon = "[OK]" if service.get('valid', False) else "[ERR]"
            print(f"{status_icon} {service['name']}")
            print(f"  类型: {service['api_type']}")
            print(f"  状态: {service['status']}")
            print(f"  API密钥: {'已设置' if service['has_api_key'] else '未设置'}")
            print(f"  基础URL: {service['base_url'] or '未设置'}")
            print(f"  默认模型: {service['default_model'] or '未设置'}")
            print()
        
        input("按回车键继续...")
    
    def edit_ai_config(self):
        """编辑AI配置"""
        if not self.ai_config_file.exists():
            print("AI配置文件不存在，请先重置AI配置")
            return
        
        try:
            print(f"正在打开编辑器: {self.ai_config_file}")
            
            # 根据系统选择编辑器
            if platform.system() == "Windows":
                editor = os.environ.get("EDITOR", "notepad")
            else:
                editor = os.environ.get("EDITOR", "nano")
            
            subprocess.run([editor, str(self.ai_config_file)])
            self._log_action("编辑AI配置")
            print("AI配置已更新")
            
        except Exception as e:
            print(f"编辑AI配置失败: {e}")
    
    def test_ai_connection(self):
        """测试AI连接"""
        print("\n测试AI服务连接...")
        print("-" * 50)
        
        # 加载AI配置
        ai_config = self.check_ai_config()
        
        if ai_config['valid_services'] == 0:
            print("没有找到有效的AI服务配置")
            print("请先配置AI服务或检查API密钥")
            input("\n按回车键继续...")
            return
        
        # 导入AI客户端
        try:
            sys.path.insert(0, str(self.project_root / "src"))
            from ai_client import AIConfig, OpenAIAdapter, GeminiAdapter
        except ImportError as e:
            print(f"无法导入AI客户端: {e}")
            input("\n按回车键继续...")
            return
        
        # 测试每个有效的服务
        print(f"找到 {ai_config['valid_services']} 个有效服务，开始测试连接...\n")
        
        for service_info in ai_config['services']:
            if not service_info.get('valid', False):
                continue
                
            service_name = service_info.get('name', 'unknown')
            print(f"正在测试服务: {service_info.get('name', service_name)}")
            print(f"  类型: {service_info.get('api_type', 'unknown')}")
            print(f"  地址: {service_info.get('base_url', 'unknown')}")
            
            try:
                # 创建AI配置
                config = AIConfig(
                    name=service_name,
                    api_key=service_info.get('api_key', ''),
                    base_url=service_info.get('base_url', ''),
                    api_type=service_info.get('api_type', 'openai'),
                    timeout=service_info.get('timeout', 900)
                )
                
                # 根据API类型创建适配器
                if config.api_type == 'openai':
                    adapter = OpenAIAdapter(config, enable_cache=False, enable_retry=False)
                elif config.api_type == 'gemini':
                    adapter = GeminiAdapter(config, enable_cache=False, enable_retry=False)
                else:
                    print(f"  [ERR] 不支持的API类型: {config.api_type}")
                    continue
                
                # 测试连接
                result = adapter.test_connection()
                
                if result['status'] == 'success':
                    print(f"  [OK] {result['message']}")
                    
                    # 尝试获取可用模型
                    try:
                        models = adapter.get_available_models()
                        if models:
                            model_names = [model.id for model in models[:3]]  # 显示前3个模型
                            print(f"  [INFO] 可用模型: {', '.join(model_names)}{'...' if len(models) > 3 else ''}")
                        else:
                            print(f"  [WARN] 未找到可用模型")
                    except Exception as e:
                        print(f"  [WARN] 无法获取模型列表: {e}")
                        
                else:
                    print(f"  [ERR] {result['message']}")
                    
            except Exception as e:
                print(f"  [ERR] 测试失败: {e}")
            
            print()
        
        print("连接测试完成")
        input("\n按回车键继续...")
    
    def switch_default_service(self, ai_config):
        """切换默认服务"""
        valid_services = [s for s in ai_config['services'] if s.get('valid', False)]
        
        if not valid_services:
            print("没有有效的AI服务")
            return
        
        print("\n可用的AI服务:")
        for i, service in enumerate(valid_services, 1):
            print(f"{i}. {service['name']}")
        
        try:
            choice = int(input("选择默认服务: ")) - 1
            if 0 <= choice < len(valid_services):
                selected_service = valid_services[choice]
                print(f"已设置默认服务: {selected_service['name']}")
                self._log_action("切换默认服务", {"service": selected_service['name']})
            else:
                print("无效选择")
        except ValueError:
            print("请输入有效数字")
    
    def manage_prompts_config(self):
        """提示词配置管理"""
        while True:
            print("\n" + "=" * 60)
            print("提示词配置管理")
            print("=" * 60)
            
            prompts_config = self.check_prompts_config()
            print(f"配置文件: {prompts_config['config_file']}")
            print(f"提示词类型: {len(prompts_config['prompt_types'])}")
            print(f"总提示词: {prompts_config['total_prompts']}")
            
            print("\n选项:")
            print("1. 查看提示词配置详情")
            print("2. 重置提示词配置")
            print("3. 编辑提示词配置")
            print("4. 添加自定义提示词")
            print("0. 返回主菜单")
            
            choice = input("\n请选择操作: ").strip()
            
            if choice == "1":
                self.show_prompts_config_details(prompts_config)
            
            elif choice == "2":
                if self.setup_prompts_config():
                    self._log_action("重置提示词配置")
                    print("提示词配置设置成功")
                else:
                    print("提示词配置设置失败")
            
            elif choice == "3":
                self.edit_prompts_config()
            
            elif choice == "4":
                self.add_custom_prompt()
            
            elif choice == "0":
                break
            
            else:
                print("无效选择")
    
    def show_prompts_config_details(self, prompts_config):
        """显示提示词配置详情"""
        print("\n提示词配置详情:")
        print("-" * 60)
        
        for prompt_type in prompts_config['prompt_types']:
            print(f"{prompt_type['type']}:")
            print(f"  提示词数量: {prompt_type['prompt_count']}")
            print(f"  有效提示词: {prompt_type['valid_prompts']}")
            print()
        
        input("按回车键继续...")
    
    def edit_prompts_config(self):
        """编辑提示词配置"""
        if not self.prompts_config_file.exists():
            print("提示词配置文件不存在，请先重置提示词配置")
            return
        
        try:
            print(f"正在打开编辑器: {self.prompts_config_file}")
            
            if platform.system() == "Windows":
                editor = os.environ.get("EDITOR", "notepad")
            else:
                editor = os.environ.get("EDITOR", "nano")
            
            subprocess.run([editor, str(self.prompts_config_file)])
            self._log_action("编辑提示词配置")
            print("提示词配置已更新")
            
        except Exception as e:
            print(f"编辑提示词配置失败: {e}")
    
    def add_custom_prompt(self):
        """添加自定义提示词"""
        print("添加自定义提示词")
        prompt_type = input("提示词类型: ").strip()
        prompt_name = input("提示词名称: ").strip()
        prompt_content = input("提示词内容: ").strip()
        
        if not all([prompt_type, prompt_name, prompt_content]):
            print("请填写完整信息")
            return
        
        try:
            # 加载现有配置
            if self.prompts_config_file.exists():
                with open(self.prompts_config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
            else:
                config = {}
            
            # 添加新提示词
            if prompt_type not in config:
                config[prompt_type] = {}
            config[prompt_type][prompt_name] = prompt_content
            
            # 保存配置
            with open(self.prompts_config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            self._log_action("添加自定义提示词", {"type": prompt_type, "name": prompt_name})
            print("自定义提示词添加成功")
            
        except Exception as e:
            print(f"添加自定义提示词失败: {e}")
    
    def manage_data(self):
        """数据管理"""
        while True:
            print("\n" + "=" * 60)
            print("数据管理")
            print("=" * 60)
            
            print(f"数据目录: {self.data_dir}")
            print(f"输出目录: {self.output_dir}")
            
            # 显示目录大小
            data_size = self.get_dir_size(self.data_dir)
            output_size = self.get_dir_size(self.output_dir)
            
            print(f"数据目录大小: {data_size}")
            print(f"输出目录大小: {output_size}")
            
            print("\n选项:")
            print("1. 查看数据文件")
            print("2. 清理临时文件")
            print("3. 备份数据")
            print("4. 恢复数据")
            print("0. 返回主菜单")
            
            choice = input("\n请选择操作: ").strip()
            
            if choice == "1":
                self.show_data_files()
            
            elif choice == "2":
                self.clean_temp_files()
            
            elif choice == "3":
                self.backup_data()
            
            elif choice == "4":
                self.restore_data()
            
            elif choice == "0":
                break
            
            else:
                print("无效选择")
    
    def get_dir_size(self, path: Path) -> str:
        """获取目录大小"""
        try:
            total_size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
            return self.format_size(total_size)
        except:
            return "无法计算"
    
    def format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def show_data_files(self):
        """显示数据文件"""
        print("\n数据文件:")
        print("-" * 60)
        
        if self.data_dir.exists():
            for file_path in self.data_dir.rglob('*'):
                if file_path.is_file():
                    size = self.format_size(file_path.stat().st_size)
                    print(f"{file_path.relative_to(self.project_root)} ({size})")
        else:
            print("数据目录不存在")
        
        input("\n按回车键继续...")
    
    def clean_temp_files(self):
        """清理临时文件"""
        temp_patterns = ['*.tmp', '*.temp', '*.log', '__pycache__', '*.pyc']
        
        cleaned_count = 0
        for pattern in temp_patterns:
            for file_path in self.project_root.rglob(pattern):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                        cleaned_count += 1
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                        cleaned_count += 1
                except Exception as e:
                    print(f"删除失败 {file_path}: {e}")
        
        print(f"清理了 {cleaned_count} 个临时文件")
        self._log_action("清理临时文件", {"count": cleaned_count})
    
    def backup_data(self):
        """备份数据"""
        backup_dir = self.project_root / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        backup_path = backup_dir / backup_name
        
        try:
            # 备份数据和输出目录
            shutil.copytree(self.data_dir, backup_path / "data")
            shutil.copytree(self.output_dir, backup_path / "output")
            
            # 备份配置文件
            if self.ai_config_file.exists():
                shutil.copy2(self.ai_config_file, backup_path / "ai_config.yaml")
            if self.prompts_config_file.exists():
                shutil.copy2(self.prompts_config_file, backup_path / "prompts_config.yaml")
            
            print(f"备份完成: {backup_path}")
            self._log_action("备份数据", {"backup_path": str(backup_path)})
            
        except Exception as e:
            print(f"备份失败: {e}")
    
    def restore_data(self):
        """恢复数据"""
        backup_dir = self.project_root / "backups"
        if not backup_dir.exists():
            print("没有找到备份目录")
            return
        
        backups = [d for d in backup_dir.iterdir() if d.is_dir()]
        if not backups:
            print("没有找到备份")
            return
        
        print("可用的备份:")
        for i, backup in enumerate(sorted(backups, reverse=True), 1):
            print(f"{i}. {backup.name}")
        
        try:
            choice = int(input("选择要恢复的备份: ")) - 1
            if 0 <= choice < len(backups):
                backup_path = sorted(backups, reverse=True)[choice]
                
                confirm = input(f"确定要恢复备份 {backup_path.name} 吗? (y/N): ").lower()
                if confirm == 'y':
                    self.restore_from_backup(backup_path)
            else:
                print("无效选择")
        except ValueError:
            print("请输入有效数字")
    
    def restore_from_backup(self, backup_path: Path):
        """从备份恢复数据"""
        try:
            # 恢复数据目录
            if (backup_path / "data").exists():
                if self.data_dir.exists():
                    shutil.rmtree(self.data_dir)
                shutil.copytree(backup_path / "data", self.data_dir)
            
            # 恢复输出目录
            if (backup_path / "output").exists():
                if self.output_dir.exists():
                    shutil.rmtree(self.output_dir)
                shutil.copytree(backup_path / "output", self.output_dir)
            
            # 恢复配置文件
            if (backup_path / "ai_config.yaml").exists():
                shutil.copy2(backup_path / "ai_config.yaml", self.ai_config_file)
            if (backup_path / "prompts_config.yaml").exists():
                shutil.copy2(backup_path / "prompts_config.yaml", self.prompts_config_file)
            
            print(f"恢复完成: {backup_path.name}")
            self._log_action("恢复数据", {"backup_path": str(backup_path)})
            
        except Exception as e:
            print(f"恢复失败: {e}")
    
    def show_logs_and_monitoring(self):
        """显示日志和监控"""
        while True:
            print("\n" + "=" * 60)
            print("日志和监控")
            print("=" * 60)
            
            print(f"日志文件: {self.log_file}")
            print(f"历史记录: {len(self.history)} 条")
            
            print("\n选项:")
            print("1. 查看操作历史")
            print("2. 查看日志文件")
            print("3. 查看系统性能")
            print("4. 清理日志")
            print("0. 返回主菜单")
            
            choice = input("\n请选择操作: ").strip()
            
            if choice == "1":
                self.show_operation_history()
            
            elif choice == "2":
                self.show_log_file()
            
            elif choice == "3":
                self.show_system_performance()
            
            elif choice == "4":
                self.clean_logs()
            
            elif choice == "0":
                break
            
            else:
                print("无效选择")
    
    def show_operation_history(self):
        """显示操作历史"""
        print("\n操作历史:")
        print("-" * 60)
        
        for entry in self.history[-20:]:  # 显示最近20条记录
            timestamp = entry['timestamp'][:19]  # 只显示日期时间部分
            print(f"{timestamp} - {entry['action']}")
            if entry['details']:
                print(f"  {entry['details']}")
        
        input("\n按回车键继续...")
    
    def show_log_file(self):
        """显示日志文件"""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                print("\n日志文件内容:")
                print("-" * 60)
                for line in lines[-50:]:  # 显示最后50行
                    print(line.rstrip())
                
                input("\n按回车键继续...")
            except Exception as e:
                print(f"读取日志文件失败: {e}")
        else:
            print("日志文件不存在")
    
    def show_system_performance(self):
        """显示系统性能"""
        print("\n系统性能信息:")
        print("-" * 60)
        
        # 内存使用情况
        try:
            import psutil
            memory = psutil.virtual_memory()
            print(f"内存使用: {memory.percent}%")
            print(f"可用内存: {self.format_size(memory.available)}")
            print(f"总内存: {self.format_size(memory.total)}")
        except ImportError:
            print("psutil模块未安装，无法显示内存信息")
        
        # 磁盘使用情况
        try:
            disk_usage = shutil.disk_usage(self.project_root)
            print(f"磁盘使用: {disk_usage.used / disk_usage.total * 100:.1f}%")
            print(f"可用空间: {self.format_size(disk_usage.free)}")
            print(f"总空间: {self.format_size(disk_usage.total)}")
        except Exception as e:
            print(f"获取磁盘信息失败: {e}")
        
        # 项目文件统计
        try:
            py_files = list(self.project_root.rglob('*.py'))
            total_lines = sum(len(open(f, 'r', encoding='utf-8').readlines()) for f in py_files)
            print(f"Python文件: {len(py_files)}")
            print(f"代码行数: {total_lines}")
        except Exception as e:
            print(f"统计代码信息失败: {e}")
        
        input("\n按回车键继续...")
    
    def clean_logs(self):
        """清理日志"""
        confirm = input("确定要清理所有日志吗? (y/N): ").lower()
        if confirm == 'y':
            try:
                if self.log_file.exists():
                    self.log_file.unlink()
                
                # 清理历史记录
                self.history.clear()
                self._save_history()
                
                print("日志清理完成")
                self._log_action("清理日志")
            except Exception as e:
                print(f"清理日志失败: {e}")
    
    def show_system_tools(self):
        """显示系统工具"""
        while True:
            print("\n" + "=" * 60)
            print("系统工具")
            print("=" * 60)
            
            print("\n选项:")
            print("1. 系统诊断")
            print("2. 环境信息")
            print("3. 重置配置")
            print("4. 生成报告")
            print("0. 返回主菜单")
            
            choice = input("\n请选择操作: ").strip()
            
            if choice == "1":
                self.run_system_diagnosis()
            
            elif choice == "2":
                self.show_environment_info()
            
            elif choice == "3":
                self.reset_config()
            
            elif choice == "4":
                self.generate_report()
            
            elif choice == "0":
                break
            
            else:
                print("无效选择")
    
    def run_system_diagnosis(self):
        """运行系统诊断"""
        print("\n系统诊断:")
        print("-" * 60)
        
        # 检查Python版本
        version_ok, version_msg = self.check_python_version()
        print(f"Python版本: {'✓' if version_ok else '✗'} {version_msg}")
        
        # 检查虚拟环境
        venv_status = self.detect_virtual_environment()
        print(f"虚拟环境: {'✓' if venv_status['venv_exists'] else '✗'} {venv_status['status']}")
        
        # 检查依赖
        req_status = self.get_requirements_status()
        deps_ok = len(req_status['missing_packages']) == 0
        print(f"依赖包: {'✓' if deps_ok else '✗'} {len(req_status['missing_packages'])} 个缺失")
        
        # 检查AI配置
        ai_config = self.check_ai_config()
        ai_ok = ai_config['valid_services'] > 0
        print(f"AI配置: {'✓' if ai_ok else '✗'} {ai_config['valid_services']} 个有效服务")
        
        # 检查目录结构
        dirs_ok = all([
            self.data_dir.exists(),
            self.output_dir.exists(),
            (self.project_root / 'prompts').exists()
        ])
        print(f"目录结构: {'✓' if dirs_ok else '✗'}")
        
        # 整体状态
        all_ok = all([version_ok, venv_status['venv_exists'], deps_ok, ai_ok, dirs_ok])
        print(f"\n整体状态: {'✓ 系统正常' if all_ok else '✗ 需要修复'}")
        
        input("\n按回车键继续...")
    
    def show_environment_info(self):
        """显示环境信息"""
        print("\n环境信息:")
        print("-" * 60)
        
        # 系统信息
        print(f"操作系统: {platform.system()} {platform.release()}")
        print(f"架构: {platform.machine()}")
        print(f"Python版本: {platform.python_version()}")
        print(f"Python路径: {sys.executable}")
        
        # 环境变量
        print(f"\n环境变量:")
        important_vars = ['PATH', 'PYTHONPATH', 'VIRTUAL_ENV', 'CONDA_DEFAULT_ENV']
        for var in important_vars:
            value = os.environ.get(var, '未设置')
            print(f"  {var}: {value}")
        
        # 项目信息
        print(f"\n项目信息:")
        print(f"  项目根目录: {self.project_root}")
        print(f"  虚拟环境: {self.venv_path}")
        print(f"  配置文件: {self.ai_config_file}")
        print(f"  日志文件: {self.log_file}")
        
        input("\n按回车键继续...")
    
    def reset_config(self):
        """重置配置"""
        print("重置配置:")
        print("1. 重置AI配置")
        print("2. 重置提示词配置")
        print("3. 重置所有配置")
        print("0. 取消")
        
        choice = input("选择要重置的配置: ").strip()
        
        if choice == "1":
            if self.ai_config_file.exists():
                self.ai_config_file.unlink()
                print("AI配置已重置")
                self._log_action("重置AI配置")
        
        elif choice == "2":
            if self.prompts_config_file.exists():
                self.prompts_config_file.unlink()
                print("提示词配置已重置")
                self._log_action("重置提示词配置")
        
        elif choice == "3":
            if self.ai_config_file.exists():
                self.ai_config_file.unlink()
            if self.prompts_config_file.exists():
                self.prompts_config_file.unlink()
            print("所有配置已重置")
            self._log_action("重置所有配置")
        
        elif choice == "0":
            return
        
        else:
            print("无效选择")
    
    def generate_report(self):
        """生成系统报告"""
        report_file = self.project_root / "system_report.txt"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("智能文献系统报告\n")
                f.write("=" * 50 + "\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # 系统信息
                f.write("系统信息:\n")
                f.write(f"  操作系统: {platform.system()} {platform.release()}\n")
                f.write(f"  Python版本: {platform.python_version()}\n")
                f.write(f"  架构: {platform.machine()}\n\n")
                
                # 虚拟环境
                venv_status = self.detect_virtual_environment()
                f.write("虚拟环境:\n")
                f.write(f"  状态: {venv_status['status']}\n")
                f.write(f"  路径: {venv_status['venv_path']}\n\n")
                
                # 依赖包
                req_status = self.get_requirements_status()
                f.write("依赖包:\n")
                f.write(f"  总包数: {req_status['total_packages']}\n")
                f.write(f"  缺少包: {len(req_status['missing_packages'])}\n")
                f.write(f"  过期包: {len(req_status['outdated_packages'])}\n\n")
                
                # AI配置
                ai_config = self.check_ai_config()
                f.write("AI配置:\n")
                f.write(f"  有效服务: {ai_config['valid_services']}\n")
                f.write(f"  默认服务: {ai_config['default_service'] or '未设置'}\n\n")
                
                # 目录信息
                f.write("目录信息:\n")
                f.write(f"  数据目录: {self.data_dir}\n")
                f.write(f"  输出目录: {self.output_dir}\n")
                f.write(f"  数据大小: {self.get_dir_size(self.data_dir)}\n")
                f.write(f"  输出大小: {self.get_dir_size(self.output_dir)}\n\n")
                
                # 操作历史
                f.write("最近操作:\n")
                for entry in self.history[-10:]:
                    f.write(f"  {entry['timestamp'][:19]} - {entry['action']}\n")
            
            print(f"系统报告已生成: {report_file}")
            self._log_action("生成系统报告")
            
        except Exception as e:
            print(f"生成报告失败: {e}")
    
    def run(self):
        """运行交互式CLI"""
        self.show_welcome()
        
        while True:
            self.show_menu()
            choice = input("\n请选择操作: ").strip()
            
            if choice == "1":
                self.show_system_status()
            
            elif choice == "2":
                self.manage_virtual_environment()
            
            elif choice == "3":
                self.manage_dependencies()
            
            elif choice == "4":
                self.manage_ai_config()
            
            elif choice == "5":
                self.manage_prompts_config()
            
            elif choice == "6":
                self.start_project_interactive()
            
            elif choice == "7":
                self.manage_data()
            
            elif choice == "8":
                self.show_logs_and_monitoring()
            
            elif choice == "9":
                self.show_system_tools()
            
            elif choice == "0":
                print("感谢使用智能文献系统CLI客户端!")
                break
            
            else:
                print("无效选择，请重新输入")
    
    def start_project_interactive(self):
        """交互式启动项目"""
        print("\n启动项目:")
        print("1. 交互式模式")
        print("2. 批处理模式")
        print("0. 取消")
        
        choice = input("选择启动模式: ").strip()
        
        if choice == "1":
            mode = "interactive"
        elif choice == "2":
            mode = "batch"
        elif choice == "0":
            return
        else:
            print("无效选择")
            return
        
        if self.start_project(mode):
            self._log_action("启动项目", {"mode": mode})
            print("项目启动成功")
        else:
            print("项目启动失败")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="智能文献系统高级CLI客户端")
    parser.add_argument("--basic", action="store_true", help="使用基础CLI模式")
    parser.add_argument("--interactive", "-i", action="store_true", help="启动交互式模式")
    
    args = parser.parse_args()
    
    if args.basic:
        # 使用基础CLI
        from cli import main as basic_main
        basic_main()
    else:
        # 使用高级CLI
        cli = AdvancedCLI()
        
        if args.interactive or len(sys.argv) == 1:
            cli.run()
        else:
            # 如果没有指定交互式模式，显示帮助
            parser.print_help()


if __name__ == "__main__":
    main()