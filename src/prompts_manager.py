#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提示词配置管理器
负责加载、管理和应用AI提示词配置
"""

import yaml
import os
from typing import Dict, Any, Optional
from datetime import datetime

class PromptsManager:
    """提示词配置管理器"""
    
    def __init__(self, config_path: str = "prompts/prompts_config.yaml"):
        """
        初始化提示词管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = {}
        self.load_config()
    
    def load_config(self) -> bool:
        """
        加载提示词配置文件
        
        Returns:
            bool: 加载成功返回True
        """
        try:
            if not os.path.exists(self.config_path):
                print(f"[WARN]  提示词配置文件不存在: {self.config_path}")
                self._create_default_config()
                return False
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            print("成功加载提示词配置:", self.config_path)
            return True
            
        except Exception as e:
            print("加载提示词配置失败:", e)
            return False
    
    def _create_default_config(self):
        """创建默认配置文件"""
        print("创建默认提示词配置文件...")
        # 这里可以创建一个最小的默认配置
        default_config = {
            "version": "1.0.0",
            "description": "默认提示词配置",
            "intent_analysis": {
                "system_prompt": "你是一位专业的医学文献检索专家。",
                "user_prompt_template": "请分析以下用户查询：{user_input}"
            }
        }
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, ensure_ascii=False, indent=2)
            print("默认配置已创建:", self.config_path)
        except Exception as e:
            print(f"创建默认配置失败: {e}")
    
    def get_prompt(self, category: str, prompt_type: str = "user_prompt_template") -> str:
        """
        获取指定类别的提示词
        
        Args:
            category: 提示词类别 (intent_analysis, outline_generation, review_generation)
            prompt_type: 提示词类型 (system_prompt, user_prompt_template)
            
        Returns:
            str: 提示词内容
        """
        try:
            return self.config.get(category, {}).get(prompt_type, "")
        except Exception as e:
            print(f"获取提示词失败 ({category}.{prompt_type}): {e}")
            return ""
    
    def get_intent_analysis_prompt(self, user_input: str) -> str:
        """
        获取意图分析提示词
        
        Args:
            user_input: 用户输入
            
        Returns:
            str: 格式化的提示词
        """
        from datetime import datetime
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        template = self.get_prompt("intent_analysis", "user_prompt_template")
        
        # 添加当前日期信息到提示词
        date_info = f"""
当前日期: {current_date.strftime('%Y年%m月%d日')} (第{current_year}年)
**重要：基于当前日期({current_year}年{current_month}月)精确计算年份限制**
  - "近年来"或"最近"：{current_year-2}-{current_year}年
  - "近3年"：{current_year-2}-{current_year}年
  - "近5年"：{current_year-4}-{current_year}年
  - "近10年"：{current_year-9}-{current_year}年
  - "最近几年"：{current_year-3}-{current_year}年
  - "过去5年"：{current_year-4}-{current_year}年
  - "2020年以来"：2020-{current_year}年
  - "疫情期间"或"COVID期间"：2020-{current_year}年

示例 - 用户输入"近5年高影响因子研究"：
基于当前日期({current_year}年)，"近5年"应解析为{current_year-4}-{current_year}年
"""
        
        # 格式化提示词
        formatted_prompt = template.format(user_input=user_input)
        
        # 在用户输入之前插入日期信息
        if "用户输入:" in formatted_prompt:
            prompt_parts = formatted_prompt.split("用户输入:", 1)
            final_prompt = prompt_parts[0] + date_info + "用户输入:" + prompt_parts[1]
        else:
            final_prompt = date_info + formatted_prompt
            
        return final_prompt
    
    def get_outline_generation_prompt(self, topic: str, literature_summary: str) -> str:
        """
        获取大纲生成提示词
        
        Args:
            topic: 研究主题
            literature_summary: 文献摘要
            
        Returns:
            str: 格式化的提示词
        """
        template = self.get_prompt("outline_generation", "user_prompt_template")
        return template.format(topic=topic, literature_summary=literature_summary)
    
    def get_review_generation_prompt(self, title: str, outline_content: str, literature_info: str) -> str:
        """
        获取综述生成提示词
        
        Args:
            title: 文章标题
            outline_content: 大纲内容
            literature_info: 文献信息
            
        Returns:
            str: 格式化的提示词
        """
        template = self.get_prompt("review_generation", "user_prompt_template")
        return template.format(
            title=title,
            outline_content=outline_content,
            literature_info=literature_info
        )
    
    def get_config_value(self, key_path: str, default_value: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key_path: 配置键路径，用点分隔 (如: config.word_counts.introduction)
            default_value: 默认值
            
        Returns:
            Any: 配置值
        """
        try:
            keys = key_path.split('.')
            value = self.config
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default_value
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """
        更新配置
        
        Args:
            updates: 更新内容
            
        Returns:
            bool: 更新成功返回True
        """
        try:
            # 递归更新配置
            def deep_update(base_dict, update_dict):
                for key, value in update_dict.items():
                    if isinstance(value, dict) and key in base_dict:
                        deep_update(base_dict[key], value)
                    else:
                        base_dict[key] = value
            
            deep_update(self.config, updates)
            
            # 保存到文件
            return self.save_config()
            
        except Exception as e:
            print(f"更新配置失败: {e}")
            return False
    
    def save_config(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            bool: 保存成功返回True
        """
        try:
            # 更新最后修改时间
            self.config['last_updated'] = datetime.now().strftime('%Y-%m-%d')
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, ensure_ascii=False, indent=2, 
                         default_flow_style=False, allow_unicode=True)
            
            print(f"配置已保存: {self.config_path}")
            return True
            
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def show_config_info(self):
        """显示配置信息"""
        print("\n提示词配置信息:")
        print("=" * 50)
        print(f"版本: {self.config.get('version', 'N/A')}")
        print(f"描述: {self.config.get('description', 'N/A')}")
        print(f"最后更新: {self.config.get('last_updated', 'N/A')}")
        print(f"配置文件: {self.config_path}")
        
        # 显示可用的提示词类别
        categories = []
        for key in self.config.keys():
            if isinstance(self.config[key], dict) and 'system_prompt' in self.config[key]:
                categories.append(key)
        
        print(f"可用提示词类别: {', '.join(categories)}")
        print("=" * 50)
    
    def validate_config(self) -> bool:
        """
        验证配置文件的完整性
        
        Returns:
            bool: 验证通过返回True
        """
        required_categories = ['intent_analysis', 'outline_generation', 'review_generation']
        required_fields = ['system_prompt', 'user_prompt_template']
        
        missing_items = []
        
        for category in required_categories:
            if category not in self.config:
                missing_items.append(f"缺失类别: {category}")
                continue
                
            for field in required_fields:
                if field not in self.config[category]:
                    missing_items.append(f"缺失字段: {category}.{field}")
        
        if missing_items:
            print("配置验证失败:")
            for item in missing_items:
                print(f"  - {item}")
            return False
        else:
            print("配置验证通过")
            return True


def main():
    """测试和管理提示词配置"""
    import argparse
    
    parser = argparse.ArgumentParser(description="提示词配置管理器")
    parser.add_argument('--config', '-c', default='prompts_config.yaml', help='配置文件路径')
    parser.add_argument('--validate', '-v', action='store_true', help='验证配置文件')
    parser.add_argument('--info', '-i', action='store_true', help='显示配置信息')
    parser.add_argument('--test', '-t', action='store_true', help='测试提示词生成')
    
    args = parser.parse_args()
    
    # 创建提示词管理器
    prompts_mgr = PromptsManager(args.config)
    
    if args.info:
        prompts_mgr.show_config_info()
    
    if args.validate:
        prompts_mgr.validate_config()
    
    if args.test:
        print("\n测试提示词生成:")
        print("-" * 30)
        
        # 测试意图分析提示词
        intent_prompt = prompts_mgr.get_intent_analysis_prompt("糖尿病治疗")
        print("意图分析提示词预览:")
        print(intent_prompt[:200] + "..." if len(intent_prompt) > 200 else intent_prompt)
        
        # 测试大纲生成提示词  
        outline_prompt = prompts_mgr.get_outline_generation_prompt("糖尿病", "相关文献摘要...")
        print("\n大纲生成提示词预览:")
        print(outline_prompt[:200] + "..." if len(outline_prompt) > 200 else outline_prompt)


if __name__ == "__main__":
    main()