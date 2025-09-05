#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医学综述文章生成器 - 简化版本
基于大纲和文献检索结果生成专业的中文医学综述文章
采用旧版本的简单直接架构，移除复杂的缓存和并行处理
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import yaml
import sys
import os
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai_client import AIClient, ConfigManager, ChatMessage
from src.prompts_manager import PromptsManager


@dataclass
class ReviewSection:
    """综述章节数据类"""
    title: str
    content: str
    word_count_suggestion: Optional[int] = None
    subsections: List['ReviewSection'] = None
    
    def __post_init__(self):
        if self.subsections is None:
            self.subsections = []


@dataclass
class Literature:
    """文献数据类"""
    id: int
    title: str
    authors: str
    journal: str
    year: int
    doi: str
    abstract: str
    url: str
    relevance_score: float = 0.0
    
    def get_ama_citation(self) -> str:
        """生成AMA格式引用"""
        return f"{self.authors}. {self.title}. {self.journal}. {self.year}. doi:{self.doi}"


class MedicalReviewGenerator:
    """医学综述文章生成器 - 简化版本"""
    
    def __init__(self, config_name: str = None, output_dir: str = "综述文章"):
        """
        初始化综述生成器
        
        Args:
            config_name: AI配置名称
            output_dir: 输出目录
        """
        self.config_manager = ConfigManager()
        self.ai_client = AIClient()
        self.config_name = config_name
        self.output_dir = output_dir
        self.model_id = None
        self.model_parameters = {
            "temperature": 0.3,  # 较低的温度保证专业性和一致性
            "stream": True,      # 启用流式输出进行测试
            "max_tokens": None   # 不限制输出长度，让AI自己决定
        }
        
        # 初始化提示词管理器
        self.prompts_manager = PromptsManager()
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化AI配置
        self.config = self._select_config()
        if self.config:
            self.adapter = self.ai_client.create_adapter(self.config)
            
            # 使用aiwave_gemini服务配置
            cached_model = self._load_cached_model_config()
            if cached_model:
                # 使用缓存的Gemini模型配置，但禁用流式输出
                self.model_id = cached_model['model_id']
                self.model_parameters = cached_model['parameters'].copy()
                self.model_parameters['stream'] = True   # Gemini模型启用流式输出进行测试
                print(f"使用Gemini模型配置: {self.model_id} (启用流式输出)")
            else:
                # 如果没有缓存，使用默认的Gemini模型
                self.model_id = "gemini-2.5-pro"  # 默认使用Gemini 2.5 Pro
                self.model_parameters['stream'] = True
                print(f"使用默认Gemini模型: {self.model_id} (启用流式输出)")
        else:
            raise RuntimeError("未找到可用的AI配置")
    
    def _select_config(self):
        """选择AI配置"""
        configs = self.config_manager.list_configs()
        
        if not configs:
            return None
        
        if self.config_name:
            return self.config_manager.get_config(self.config_name)
        else:
            # 使用aiwave_gemini服务，已测试可用
            return self.config_manager.get_config('ai_wave')
    
    def _load_cached_model_config(self):
        """加载缓存的模型配置，与意图分析器保持一致"""
        cache_file = "ai_model_cache.json"
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    # 检查缓存数据有效性
                    if cached_data.get('model_id'):
                        return cached_data
            except Exception as e:
                print(f"加载模型配置缓存失败: {e}")
        return None
    
    def load_outline(self, outline_file: str) -> List[ReviewSection]:
        """
        加载综述大纲
        
        Args:
            outline_file: 大纲文件路径
            
        Returns:
            List[ReviewSection]: 章节列表
        """
        try:
            with open(outline_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查文件内容是否包含错误信息（放宽条件）
            if len(content.strip()) < 30:
                print(f"大纲文件内容过短: {content[:100]}...")
                return []
            
            # 解析大纲结构
            sections = []
            lines = content.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 匹配章节标题和字数建议
                # 格式：## 1. 标题 (建议字数：XXX字) - 只处理二级及以下标题
                if line.startswith('#') and not line.startswith('# '):
                    # 匹配标题部分（排除一级标题）
                    header_match = re.match(r'#+\s*(\d+\.?\s*)?(.+)', line)
                    if header_match:
                        full_title = header_match.group(2).strip()
                        
                        # 提取字数建议
                        word_count = None
                        word_count_match = re.search(r'\(建议字数：(\d+)字?\)', full_title)
                        if word_count_match:
                            word_count = int(word_count_match.group(1))
                            # 从标题中移除字数建议部分
                            title = re.sub(r'\s*\(建议字数：\d+字?\)', '', full_title).strip()
                        else:
                            title = full_title
                        
                        current_section = ReviewSection(
                            title=title,
                            content="",
                            word_count_suggestion=word_count
                        )
                        sections.append(current_section)
                elif current_section and line:
                    # 将内容添加到当前章节
                    if current_section.content:
                        current_section.content += "\n" + line
                    else:
                        current_section.content = line
            
            return sections
            
        except Exception as e:
            print(f"加载大纲失败: {e}")
            return []
    
    def load_literature(self, literature_file: str) -> List[Literature]:
        """
        加载文献检索结果
        
        Args:
            literature_file: 文献文件路径
            
        Returns:
            List[Literature]: 文献列表
        """
        try:
            with open(literature_file, 'r', encoding='utf-8') as f:
                if literature_file.endswith('.json'):
                    data = json.load(f)
                elif literature_file.endswith('.csv'):
                    # 处理CSV格式
                    import csv
                    reader = csv.DictReader(f)
                    data = []
                    for i, row in enumerate(reader, 1):
                        if row.get('标题') and row.get('标题').strip():
                            data.append({
                                'id': i,
                                'title': row.get('标题', ''),
                                'authors': row.get('作者', ''),
                                'journal': row.get('期刊', ''),
                                'year': int(row.get('发表年份', '2023')) if row.get('发表年份') and row.get('发表年份').isdigit() else 2023,
                                'doi': row.get('DOI', ''),
                                'abstract': row.get('摘要', ''),
                                'url': row.get('URL', '')
                            })
                else:
                    # 假设是文本格式，每行一篇文献
                    lines = f.readlines()
                    data = []
                    for i, line in enumerate(lines, 1):
                        if line.strip():
                            # 简单解析文献信息
                            parts = line.strip().split('\t')
                            if len(parts) >= 3:
                                data.append({
                                    'id': i,
                                    'title': parts[0],
                                    'authors': parts[1] if len(parts) > 1 else "Unknown",
                                    'journal': parts[2] if len(parts) > 2 else "Unknown Journal",
                                    'year': int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 2023,
                                    'doi': parts[4] if len(parts) > 4 else "",
                                    'abstract': parts[5] if len(parts) > 5 else "",
                                    'url': parts[6] if len(parts) > 6 else ""
                                })
            
            # 转换为Literature对象
            literature_list = []
            for item in data:
                if isinstance(item, dict):
                    lit = Literature(
                        id=item.get('id', len(literature_list) + 1),
                        title=item.get('title', ''),
                        authors=item.get('authors', ''),
                        journal=item.get('journal', ''),
                        year=item.get('publication_date', '2023').split('-')[0] if item.get('publication_date') else '2023',
                        doi=item.get('doi', ''),
                        abstract=item.get('abstract', ''),
                        url=item.get('url', ''),
                        relevance_score=item.get('relevance_score', 0.0)
                    )
                    literature_list.append(lit)
            
            return literature_list
            
        except Exception as e:
            print(f"加载文献失败: {e}")
            return []
    
    def generate_section_content(self, section: ReviewSection, literature: List[Literature], context: str = "") -> str:
        """
        生成章节内容
        
        Args:
            section: 章节信息
            literature: 文献列表
            context: 上下文信息
            
        Returns:
            str: 生成的章节内容
        """
        # 构建提示词
        literature_info = ""
        for i, lit in enumerate(literature, 1):
            literature_info += f"\n[{i}] {lit.title}\n作者: {lit.authors}\n期刊: {lit.journal} ({lit.year})\n摘要: {lit.abstract}\n"
        
        word_count_hint = f"建议字数约{section.word_count_suggestion}字" if section.word_count_suggestion else "详细阐述"
        
        prompt = f"""
你是一位资深的医学综述撰写专家。请根据以下信息撰写综述文章的一个章节：

**章节标题**: {section.title}
**章节要求**: {section.content if section.content else "详细论述该主题"}
**字数要求**: {word_count_hint}

**可参考文献**:
{literature_info}

**上下文**: {context}

**撰写要求**:
1. 内容必须基于提供的文献信息，不得编造
2. 使用专业的医学术语和学术语言
3. 正文每个自然段落开头使用两个全角空格（　　）缩进
4. 在引用文献时使用中括号数字标注，如[1]、[2]等
5. 段落之间逻辑连贯，语言流畅自然
6. 不使用分点列项，写成连续的自然段落
7. 避免过度使用"此外"、"然而"等过渡词
8. 不要包含任何解释性文字，只输出章节正文内容

请直接输出章节内容，不要包含标题：
"""
        
        try:
            # 构建消息
            messages = [ChatMessage(role="user", content=prompt)]
            
            # 调用AI生成内容
            response = self.adapter.send_message(
                messages, 
                self.model_id, 
                self.model_parameters
            )
            
            # 格式化响应
            content = self.ai_client.format_response(response, self.adapter.config.api_type)
            
            # 清理内容
            content = content.strip()
            
            # 按段落处理，去除多余空行
            paragraphs = [para.strip() for para in content.split('\n') if para.strip()]
            formatted_paragraphs = []
            
            for para in paragraphs:
                # 确保段落开头有缩进
                if not para.startswith('　'):
                    para = '　　' + para
                formatted_paragraphs.append(para)
            
            # 段落之间只用一个空行分隔
            return '\n\n'.join(formatted_paragraphs)
            
        except Exception as e:
            print(f"生成章节内容失败 ({section.title}): {e}")
            return f"　　本章节内容生成失败，请检查AI服务配置。错误信息：{e}"
    
    def generate_complete_review_article(self, outline_file: str, literature_file: str, title: str = None) -> str:
        """
        生成完整的综述文章 - 一次性整体生成而非逐章节拼接
        
        Args:
            outline_file: 大纲文件路径
            literature_file: 文献文件路径
            title: 文章标题（可选）
            
        Returns:
            str: 生成的完整文章内容
        """
        print("开始生成完整医学综述文章...")
        
        # 加载大纲和文献
        print("加载综述大纲...")
        with open(outline_file, 'r', encoding='utf-8') as f:
            outline_content = f.read()
        
        print("加载文献检索结果...")
        literature = self.load_literature(literature_file)
        
        if "错误" in outline_content or len(outline_content.strip()) < 50:
            print("大纲内容无效")
            return ""
        
        if not literature:
            print("文献加载失败")
            return ""
        
        print(f"成功加载大纲和 {len(literature)} 篇文献")
        
        # 构建完整的文献信息
        literature_info = ""
        for i, lit in enumerate(literature, 1):
            literature_info += f"\n[{i}] {lit.title}\n作者: {lit.authors}\n期刊: {lit.journal} ({lit.year})\n摘要: {lit.abstract}\n"
        
        # 构建专业的提示词
        prompt = f"""你是一位资深的医学综述撰写专家。请根据以下大纲和文献，撰写一篇完整、连贯的医学综述文章。

**文章标题**: {title or "医学综述"}

**综述大纲**:
{outline_content}

**参考文献库**:
{literature_info}

**撰写要求**:
1. 严格按照提供的大纲结构撰写，保持层次分明
2. 内容必须基于提供的文献信息，不得编造事实
3. 使用专业的医学术语和学术语言
4. 正文每个自然段落开头使用两个全角空格（　　）缩进
5. 在引用文献时使用中括号数字标注，如[1]、[2]等，对应上述文献编号
6. 各章节之间保持逻辑连贯，形成完整的论述体系
7. 段落内语言流畅自然，避免生硬的拼接感
8. 结论部分要总结全文，提出展望
9. 输出完整的Markdown格式文章，包含标题层级

请直接输出完整的综述文章："""
        
        try:
            # 构建消息
            messages = [ChatMessage(role="user", content=prompt)]
            
            print("正在生成完整综述文章...")
            print(f"提示词长度: {len(prompt)} 字符")
            
            # 调用AI生成完整文章
            response = self.adapter.send_message(
                messages, 
                self.model_id, 
                self.model_parameters
            )
            
            # 格式化响应
            article_content = self.ai_client.format_response(response, self.adapter.config.api_type)
            
            # 添加参考文献
            if not "## 参考文献" in article_content:
                references = self.generate_references(literature)
                article_content += f"\n\n## 参考文献\n\n{references}"
            
            print("完整医学综述文章生成完成!")
            return article_content.strip()
            
        except Exception as e:
            print(f"完整文章生成失败: {e}")
            return ""
    
    def _build_default_review_prompt(self, title: str, outline_content: str, literature_info: str) -> str:
        """构建默认综述生成提示词（兼容性保证）"""
        return f"""
你是一位资深的医学综述撰写专家。请根据以下大纲和文献，撰写一篇完整、连贯的医学综述文章。

**文章标题**: {title or "医学综述"}

**综述大纲**:
{outline_content}

**参考文献库**:
{literature_info}

**撰写要求**:
1. 严格按照提供的大纲结构撰写，保持层次分明
2. 内容必须基于提供的文献信息，不得编造事实
3. 使用专业的医学术语和学术语言
4. 正文每个自然段落开头使用两个全角空格（　　）缩进
5. 在引用文献时使用中括号数字标注，如[1]、[2]等，对应上述文献编号
6. 各章节之间保持逻辑连贯，形成完整的论述体系
7. 段落内语言流畅自然，避免生硬的拼接感
8. 结论部分要总结全文，提出展望
9. 输出完整的Markdown格式文章，包含标题层级

请直接输出完整的综述文章：
"""
    
    def generate_references(self, literature: List[Literature]) -> str:
        """
        生成AMA格式的参考文献列表
        
        Args:
            literature: 文献列表
            
        Returns:
            str: 格式化的参考文献
        """
        references = []
        for i, lit in enumerate(literature, 1):
            ref = f"{i}. {lit.get_ama_citation()}"
            if lit.url:
                ref += f" Available from: {lit.url}"
            references.append(ref)
        
        return '\n'.join(references)
    
    def save_article(self, content: str, filename: str = None, user_input: str = None) -> str:
        """
        保存文章到文件
        
        Args:
            content: 文章内容
            filename: 文件名（可选）
            user_input: 用户输入内容（可选）
            
        Returns:
            str: 保存的文件路径
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if user_input:
                # 清理用户输入，移除特殊字符，限制长度
                clean_input = re.sub(r'[^\w\u4e00-\u9fff\s-]', '', user_input)
                clean_input = clean_input.strip()[:30]  # 限制为30个字符
                # 替换空格为下划线，确保文件名格式统一
                clean_input = re.sub(r'\s+', '_', clean_input)
                filename = f"综述-{clean_input}-{timestamp}.md"
            else:
                filename = f"综述-{timestamp}.md"
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"文章已保存到: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"保存文章失败: {e}")
            return ""
    
    def generate_from_files(self, outline_file: str, literature_file: str, 
                          title: str = None, output_filename: str = None, user_input: str = None) -> str:
        """
        从文件生成综述文章
        
        Args:
            outline_file: 大纲文件路径
            literature_file: 文献文件路径
            title: 文章标题
            output_filename: 输出文件名
            user_input: 用户输入内容
            
        Returns:
            str: 生成的文件路径
        """
        # 生成文章
        article_content = self.generate_complete_review_article(outline_file, literature_file, title)
        
        if not article_content:
            print("文章生成失败")
            return ""
        
        # 保存文章
        output_path = self.save_article(article_content, output_filename, user_input)
        
        # 显示统计信息
        word_count = len(article_content.replace(' ', '').replace('\n', ''))
        print(f"\n文章统计:")
        print(f"   总字数: {word_count:,}")
        print(f"   文件大小: {len(article_content.encode('utf-8')):,} 字节")
        
        return output_path


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="医学综述文章生成器")
    parser.add_argument("--outline", "-o", required=True, help="综述大纲文件路径")
    parser.add_argument("--literature", "-l", required=True, help="文献检索结果文件路径")
    parser.add_argument("--title", "-t", help="文章标题")
    parser.add_argument("--output", help="输出文件名")
    parser.add_argument("--config", "-c", help="AI配置名称")
    parser.add_argument("--output-dir", "-d", default="综述文章", help="输出目录")
    parser.add_argument("--user-input", "-u", help="用户输入信息，用于生成文件名")
    
    args = parser.parse_args()
    
    try:
        # 创建生成器
        generator = MedicalReviewGenerator(
            config_name=args.config,
            output_dir=args.output_dir
        )
        
        # 生成文章
        output_path = generator.generate_from_files(
            outline_file=args.outline,
            literature_file=args.literature,
            title=args.title,
            output_filename=args.output,
            user_input=args.user_input
        )
        
        if output_path:
            print(f"\n医学综述文章生成成功!")
            print(f"文件路径: {output_path}")
        else:
            print("\n文章生成失败")
            exit(1)
            
    except Exception as e:
        print(f"程序执行失败: {e}")
        exit(1)


if __name__ == "__main__":
    main()