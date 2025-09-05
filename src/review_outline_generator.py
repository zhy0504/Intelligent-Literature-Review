#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医学文献综述大纲生成器
基于文献摘要生成结构化的综述写作大纲和字数规划
"""

import json
import os
import re
import time
import threading
import hashlib
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.ai_client import AIClient, ConfigManager, ChatMessage
from src.prompts_manager import PromptsManager


class OutlineGeneratorConfig:
    """大纲生成器配置类"""
    def __init__(self):
        self.max_workers = 4  # 最大工作线程数
        self.cache_size = 500  # 缓存大小
        self.cache_ttl = 7200  # 缓存有效期（秒）- 2小时
        # self.max_abstracts = 100  # 移除固定限制，根据输入处理
        self.batch_size = 50  # 批处理大小
        self.enable_parallel = True  # 启用并行处理
        self.enable_caching = True  # 启用缓存
        self.retry_attempts = 3  # 重试次数
        self.memory_limit_mb = 300  # 内存限制（MB）


class OutlineCache:
    """大纲生成结果缓存管理器"""
    def __init__(self, config: OutlineGeneratorConfig):
        self.config = config
        self.cache = {}
        self.access_times = {}
        self.lock = threading.Lock()
        self.stats = {'hits': 0, 'misses': 0, 'evictions': 0}
    
    def _generate_key(self, abstracts_hash: str, research_topic: str) -> str:
        """生成缓存键"""
        content = f"{abstracts_hash}:{research_topic}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _hash_abstracts(self, abstracts: List[str]) -> str:
        """生成摘要列表的哈希值"""
        content = "|".join(sorted(abstracts))
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get(self, abstracts: List[str], research_topic: str) -> Optional[str]:
        """获取缓存的大纲结果"""
        if not self.config.enable_caching:
            return None
            
        abstracts_hash = self._hash_abstracts(abstracts)
        key = self._generate_key(abstracts_hash, research_topic)
        
        with self.lock:
            if key in self.cache:
                # 检查是否过期
                if time.time() - self.access_times[key] < self.config.cache_ttl:
                    self.access_times[key] = time.time()
                    self.stats['hits'] += 1
                    return self.cache[key]
                else:
                    # 过期删除
                    del self.cache[key]
                    del self.access_times[key]
                    self.stats['evictions'] += 1
            
            self.stats['misses'] += 1
            return None
    
    def put(self, abstracts: List[str], research_topic: str, outline: str):
        """存储大纲结果"""
        if not self.config.enable_caching:
            return
            
        abstracts_hash = self._hash_abstracts(abstracts)
        key = self._generate_key(abstracts_hash, research_topic)
        
        with self.lock:
            # 检查缓存大小
            if len(self.cache) >= self.config.cache_size:
                # LRU淘汰
                oldest_key = min(self.access_times.keys(), key=self.access_times.get)
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
                self.stats['evictions'] += 1
            
            self.cache[key] = outline
            self.access_times[key] = time.time()
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'cache_size': len(self.cache),
            'max_cache_size': self.config.cache_size,
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'evictions': self.stats['evictions'],
            'hit_rate': hit_rate
        }


@dataclass
class OutlineSection:
    """大纲章节"""
    title: str
    word_count: int
    level: int = 1
    subsections: List['OutlineSection'] = None
    
    def __post_init__(self):
        if self.subsections is None:
            self.subsections = []


class ReviewOutlineGenerator:
    """综述大纲生成器"""
    
    def __init__(self, ai_config_name: str = None, generator_config: OutlineGeneratorConfig = None):
        """
        初始化大纲生成器
        
        Args:
            ai_config_name: AI配置名称
            generator_config: 生成器配置
        """
        self.ai_config_name = ai_config_name
        self.generator_config = generator_config or OutlineGeneratorConfig()
        self.config_manager = ConfigManager()
        self.ai_client = AIClient()
        
        # 初始化提示词管理器
        self.prompts_manager = PromptsManager()
        
        # 初始化缓存
        self.outline_cache = OutlineCache(self.generator_config)
        
        # 性能统计
        self.performance_stats = {
            'total_outlines_generated': 0,
            'total_generation_time': 0,
            'cache_hits': 0,
            'parallel_batches': 0,
            'abstracts_processed': 0,
            'ai_calls': 0,
            'errors': 0,
            'retries': 0
        }
        
        # 选择AI配置
        self.config = self._select_config()
        if self.config:
            self.adapter = self.ai_client.create_adapter(self.config)
            
            # 尝试使用意图分析器的缓存配置，确保完全一致
            cached_model = self._load_cached_model_config()
            if cached_model:
                self.model_id = cached_model['model_id']
                # 使用完全相同的参数，只调整stream为True以支持流式输出
                self.model_parameters = cached_model['parameters'].copy()
                self.model_parameters['stream'] = True  # 大纲生成使用流式输出
                print(f"[OK] 使用缓存模型配置: {self.model_id} (参数与意图分析器完全一致)")
            else:
                # 如果没有缓存，使用默认配置
                print("[WARN] 未找到模型配置缓存，使用默认配置")
                self.model_id = "gemini-2.5-pro"
                self.model_parameters = {
                    "temperature": 0.1,
                    "stream": True,
                    "max_tokens": None
                }
        else:
            raise RuntimeError("未找到可用的AI配置")
        
        print(f"并行处理: {'启用' if self.generator_config.enable_parallel else '禁用'}")
        print(f"缓存系统: {'启用' if self.generator_config.enable_caching else '禁用'}")
    
    def _load_cached_model_config(self) -> Optional[Dict]:
        """加载缓存的模型配置"""
        cache_file = "ai_model_cache.json"
        if os.path.exists(cache_file):
            try:
                import json
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载模型配置缓存失败: {e}")
        return None
    
    def _select_config(self):
        """选择AI配置"""
        configs = self.config_manager.list_configs()
        if not configs:
            return None
        if self.ai_config_name:
            return self.config_manager.get_config(self.ai_config_name)
        else:
            return self.config_manager.get_config(configs[0])
    
    def _get_default_model(self):
        """从端点获取模型并让用户选择"""
        try:
            models = self.adapter.get_available_models()
            if not models:
                print("[FAIL] 端点未返回可用模型")
                return None
            
            # 查找 gemini-2.5-pro 模型的索引
            preferred_index = None
            for i, model in enumerate(models):
                if "gemini-2.5-pro" in model.id.lower():
                    preferred_index = i + 1  # 显示的序号是从1开始的
                    break
            
            print(f"[FIND] 从端点获取到 {len(models)} 个可用模型:")
            for i, model in enumerate(models, 1):
                prefix = "🌟 " if preferred_index == i else "  "
                print(f"{prefix}{i}. {model.id}")
            
            # 设置默认选项提示
            default_choice = f"[{preferred_index}]" if preferred_index else "[1]"
            default_index = preferred_index - 1 if preferred_index else 0
            
            while True:
                try:
                    choice = input(f"\n请选择模型 (1-{len(models)}) {default_choice}: ").strip()
                    if not choice:
                        selected_index = default_index  # 默认选择
                    else:
                        selected_index = int(choice) - 1
                    
                    if 0 <= selected_index < len(models):
                        selected_model = models[selected_index]
                        print(f"[OK] 已选择模型: {selected_model.id}")
                        return selected_model.id
                    else:
                        print(f"请输入 1-{len(models)} 之间的数字")
                except (ValueError, EOFError):
                    # 如果是无输入环境或输入错误，使用默认选择
                    selected_model = models[default_index]
                    print(f"[OK] 自动选择默认模型: {selected_model.id}")
                    return selected_model.id
                    
        except Exception as e:
            print(f"[FAIL] 获取端点模型失败: {e}")
            return None
    
    def generate_outline_from_json(self, json_file_path: str, research_topic: str) -> str:
        """
        从JSON文件生成综述大纲
        
        Args:
            json_file_path: 文献JSON文件路径
            research_topic: 研究主题
            
        Returns:
            生成的大纲markdown文本
        """
        # 1. 读取JSON文献数据
        literature_data = self._load_literature_json(json_file_path)
        
        # 2. 提取摘要信息
        abstracts = self._extract_abstracts(literature_data)
        
        if not abstracts:
            print("警告: 未找到摘要信息，将基于标题生成大纲")
            abstracts = self._extract_titles(literature_data)
        
        # 3. 生成大纲
        outline = self._generate_outline_with_ai(abstracts, research_topic)
        
        return outline
    
    def generate_outline_from_data_optimized(self, literature_data: List[Dict], research_topic: str) -> str:
        """
        优化的从文献数据生成综述大纲方法
        
        Args:
            literature_data: 文献数据列表
            research_topic: 研究主题
            
        Returns:
            生成的大纲markdown文本
        """
        start_time = time.time()
        
        print(f"\n开始生成大纲，文献数量: {len(literature_data)}")
        print(f"并行处理: {'启用' if self.generator_config.enable_parallel else '禁用'}")
        
        # 并行提取文献信息
        abstracts, titles = self._extract_literature_info_parallel(literature_data)
        
        if not abstracts:
            print("警告: 未找到摘要信息，将基于标题生成大纲")
            abstracts = titles
        
        # 检查缓存
        cached_outline = self.outline_cache.get(abstracts, research_topic)
        if cached_outline:
            self.performance_stats['cache_hits'] += 1
            print("[OK] 命中缓存，直接返回大纲结果")
            return cached_outline
        
        # 生成大纲
        outline = self._generate_outline_with_ai_optimized(abstracts, research_topic)
        
        # 缓存结果
        if outline:
            self.outline_cache.put(abstracts, research_topic, outline)
        
        # 更新性能统计
        generation_time = time.time() - start_time
        self.performance_stats['total_generation_time'] += generation_time
        self.performance_stats['total_outlines_generated'] += 1
        self.performance_stats['abstracts_processed'] += len(abstracts)
        
        print(f"大纲生成完成，耗时: {generation_time:.2f}秒")
        
        return outline
    
    def _extract_literature_info_parallel(self, literature_data: List[Dict]) -> Tuple[List[str], List[str]]:
        """并行提取文献信息"""
        if self.generator_config.enable_parallel and len(literature_data) > self.generator_config.batch_size:
            # 并行处理
            return self._extract_info_parallel(literature_data)
        else:
            # 串行处理
            abstracts = self._extract_abstracts_optimized(literature_data)
            titles = self._extract_titles_optimized(literature_data)
            return abstracts, titles
    
    def _extract_info_parallel(self, literature_data: List[Dict]) -> Tuple[List[str], List[str]]:
        """并行提取摘要和标题"""
        batch_size = self.generator_config.batch_size
        batches = [literature_data[i:i + batch_size] for i in range(0, len(literature_data), batch_size)]
        
        all_abstracts = []
        all_titles = []
        
        with ThreadPoolExecutor(max_workers=self.generator_config.max_workers) as executor:
            # 提交所有批次任务
            future_to_batch = {
                executor.submit(self._process_literature_batch, batch): batch 
                for batch in batches
            }
            
            # 收集结果
            for future in as_completed(future_to_batch):
                try:
                    batch_abstracts, batch_titles = future.result()
                    all_abstracts.extend(batch_abstracts)
                    all_titles.extend(batch_titles)
                    self.performance_stats['parallel_batches'] += 1
                except Exception as e:
                    print(f"处理文献批次失败: {e}")
                    self.performance_stats['errors'] += 1
        
        return all_abstracts, all_titles
    
    def _process_literature_batch(self, batch: List[Dict]) -> Tuple[List[str], List[str]]:
        """处理一个批次的文献"""
        abstracts = self._extract_abstracts_optimized(batch)
        titles = self._extract_titles_optimized(batch)
        return abstracts, titles
    
    def generate_outline_from_data(self, literature_data: List[Dict], research_topic: str) -> str:
        """兼容性方法"""
        return self.generate_outline_from_data_optimized(literature_data, research_topic)
    
    def _load_literature_json(self, json_file_path: str) -> List[Dict]:
        """加载JSON文献数据"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 如果是智能文献检索系统导出的格式
            if isinstance(data, dict) and 'articles' in data:
                return data['articles']
            # 如果直接是文章列表
            elif isinstance(data, list):
                return data
            else:
                raise ValueError("不支持的JSON格式")
                
        except Exception as e:
            raise RuntimeError(f"读取JSON文件失败: {e}")
    
    def _extract_abstracts_optimized(self, literature_data: List[Dict]) -> List[str]:
        """优化的摘要提取方法"""
        abstracts = []
        
        # 可能的摘要字段名（按优先级排序）
        abstract_fields = ['摘要', 'abstract', 'Abstract', 'summary', 'Summary', 'description', 'Description']
        
        for article in literature_data:
            try:
                abstract = ''
                
                # 尝试不同的摘要字段名
                for field in abstract_fields:
                    if field in article:
                        abstract = article.get(field, '').strip()
                        if abstract and len(abstract) > 50:  # 找到有效摘要就跳出
                            break
                
                # 智能筛选：只保留有实际内容的摘要
                if abstract and len(abstract) > 50:
                    # 清理摘要文本
                    abstract = self._clean_abstract_text(abstract)
                    if abstract:
                        abstracts.append(abstract)
            except Exception as e:
                print(f"提取摘要失败: {e}")
                self.performance_stats['errors'] += 1
        
        # 智能选择：限制数量并优化质量
        return self._select_best_abstracts(abstracts)
    
    def _clean_abstract_text(self, abstract: str) -> str:
        """清理摘要文本"""
        try:
            # 移除多余的空白字符
            abstract = re.sub(r'\s+', ' ', abstract)
            # 移除特殊字符
            abstract = re.sub(r'[^\w\s\u4e00-\u9fff.,;:!?()-]', '', abstract)
            # 截断过长的摘要
            if len(abstract) > 2000:
                abstract = abstract[:2000] + "..."
            return abstract.strip()
        except Exception:
            return abstract
    
    def _select_best_abstracts(self, abstracts: List[str]) -> List[str]:
        """智能选择最佳摘要"""
        # 移除max_abstracts限制，处理所有摘要
        if not abstracts:
            return abstracts
        
        # 按长度和质量排序
        scored_abstracts = []
        for abstract in abstracts:
            score = self._score_abstract(abstract)
            scored_abstracts.append((score, abstract))
        
        # 选择得分最高的摘要（全部处理）
        scored_abstracts.sort(reverse=True)
        return [abstract for score, abstract in scored_abstracts]
    
    def _score_abstract(self, abstract: str) -> float:
        """为摘要评分"""
        score = 0.0
        
        # 长度评分
        length = len(abstract)
        if 100 <= length <= 800:
            score += 0.3
        elif 50 <= length <= 1500:
            score += 0.2
        
        # 内容质量评分
        # 检查是否包含关键词
        keywords = ['study', 'research', 'analysis', 'results', 'conclusion', 'findings', 
                   '研究', '分析', '结果', '结论', '发现']
        keyword_count = sum(1 for keyword in keywords if keyword.lower() in abstract.lower())
        score += min(keyword_count * 0.1, 0.3)
        
        # 结构评分
        if '.' in abstract and len(abstract.split('.')) > 3:
            score += 0.2
        
        return score
    
    def _extract_abstracts(self, literature_data: List[Dict]) -> List[str]:
        """兼容性方法"""
        return self._extract_abstracts_optimized(literature_data)
    
    def _extract_titles_optimized(self, literature_data: List[Dict]) -> List[str]:
        """优化的标题提取方法"""
        titles = []
        
        for article in literature_data:
            try:
                title = article.get('title', '').strip()
                if title:
                    # 清理标题文本
                    title = self._clean_title_text(title)
                    if title:
                        titles.append(title)
            except Exception as e:
                print(f"提取标题失败: {e}")
                self.performance_stats['errors'] += 1
        
        return titles
    
    def _clean_title_text(self, title: str) -> str:
        """清理标题文本"""
        try:
            # 移除多余的空白字符
            title = re.sub(r'\s+', ' ', title)
            # 移除特殊字符
            title = re.sub(r'[^\w\s\u4e00-\u9fff.,;:!?()-]', '', title)
            # 截断过长的标题
            if len(title) > 300:
                title = title[:300] + "..."
            return title.strip()
        except Exception:
            return title
    
    def _extract_titles(self, literature_data: List[Dict]) -> List[str]:
        """兼容性方法"""
        return self._extract_titles_optimized(literature_data)
    
    def _generate_outline_with_ai_optimized(self, abstracts: List[str], research_topic: str) -> str:
        """优化的AI大纲生成方法，支持重试机制"""
        
        # 构建提示词
        prompt = self._build_outline_prompt_optimized(abstracts, research_topic)
        
        # 构建消息
        messages = [ChatMessage(role="user", content=prompt)]
        
        # 重试机制
        last_error = None
        for attempt in range(self.generator_config.retry_attempts):
            try:
                self.performance_stats['ai_calls'] += 1
                
                # 调用AI生成大纲
                response = self.adapter.send_message(
                    messages,
                    self.model_id,
                    self.model_parameters
                )
                
                # 格式化响应
                outline = self.ai_client.format_response(response, self.adapter.config.api_type)
                
                # 验证大纲质量
                if self._validate_outline(outline):
                    return outline
                else:
                    print(f"大纲质量验证失败，尝试 {attempt + 1}/{self.generator_config.retry_attempts}")
                    last_error = "大纲质量验证失败"
                    
            except Exception as e:
                last_error = str(e)
                print(f"AI大纲生成失败 (尝试 {attempt + 1}/{self.generator_config.retry_attempts}): {e}")
                self.performance_stats['retries'] += 1
                
                # 指数退避
                if attempt < self.generator_config.retry_attempts - 1:
                    delay = min(2 ** attempt, 10)
                    time.sleep(delay)
        
        # 所有尝试都失败，返回基础大纲模板
        print(f"所有AI生成尝试失败，使用基础大纲模板")
        self.performance_stats['errors'] += 1
        return self._generate_basic_outline(research_topic)
    
    def _validate_outline(self, outline: str) -> bool:
        """验证大纲质量"""
        if not outline or len(outline.strip()) < 100:
            return False
        
        # 检查是否包含必要结构
        required_sections = ['引言', '结论', '总结']
        has_required = any(section in outline for section in required_sections)
        
        # 检查是否有层级结构
        has_hierarchy = '##' in outline or '###' in outline or '-' in outline
        
        # 检查是否有字数建议
        has_word_count = '字' in outline and '约' in outline
        
        return has_required and has_hierarchy and has_word_count
    
    def _build_outline_prompt_optimized(self, abstracts: List[str], research_topic: str) -> str:
        """优化的提示词构建方法"""
        
        # 处理所有传入的摘要，不设上限
        actual_total_count = len(abstracts)  # 实际总文献数
        processed_count = actual_total_count  # 处理所有文献
        
        abstracts_text = "\n\n".join([f"摘要{i+1}: {abstract}" for i, abstract in enumerate(abstracts)])
        
        # 动态调整提示词
        prompt = f"""
# 任务：生成医学文献综述写作大纲

## 1. 角色与目标
你将扮演一位 **医学文献结构化提炼与规划师**，你的核心目标是基于提供的{actual_total_count}篇医学文献摘要和原始检索主题，构建一份结构完整、逻辑清晰的中文综述写作大纲，并为每个部分规划合理的字数。

## 2. 背景与上下文
- **核心主题**: {research_topic}
- **文献数量**: {actual_total_count}篇
- **分析深度**: 基于摘要内容进行结构化分析

## 3. 关键步骤
1. **主题分析与提炼**: 深入分析文献摘要中的所有内容
2. **结构构建与排序**: 以核心主题为中心主线组织内容
3. **完整大纲规划**: 包含引言、主体、结论的完整框架
4. **字数权重分配**: 根据内容重要性分配合理字数

## 4. 输出要求
- **格式**: Markdown层级列表
- **风格**: 专业、学术、简洁
- **字数范围**: 建议总字数3000-8000字
- **结构要求**: 必须包含引言、核心主体、结论与展望
- **字数标注**: 每个部分后必须标注建议字数

## 5. 文献摘要内容
{abstracts_text}

请基于以上内容生成结构化的大纲。
"""
        return prompt
    
    def _generate_outline_with_ai(self, abstracts: List[str], research_topic: str) -> str:
        """兼容性方法"""
        return self._generate_outline_with_ai_optimized(abstracts, research_topic)
    
    def _build_outline_prompt(self, abstracts: List[str], research_topic: str) -> str:
        """构建AI提示词"""
        
        # 处理所有摘要，不设上限
        abstracts_text = "\n\n".join([f"摘要{i+1}: {abstract}" for i, abstract in enumerate(abstracts)])
        
        prompt = f"""
# 任务：生成医学文献综述写作大纲

## 1. 角色与目标
你将扮演一位 **医学文献结构化提炼与规划师**，你的核心目标是基于提供的{len(abstracts)}篇医学文献摘要和原始检索主题，构建一份结构完整、逻辑清晰的中文综述写作大纲，并为每个部分规划合理的字数。

## 2. 背景与上下文
你将收到两份关键信息：
1. **文献摘要**: {len(abstracts)}篇医学文献摘要的合并内容，这是你分析的核心材料。
2. **核心主题**: 用户的原始检索主题，这是综述需要围绕的核心主线。

## 3. 关键步骤
在你的创作过程中，请遵循以下内部步骤来构思和打磨作品：
1. **主题分析与提炼**: 深入分析文献摘要中的所有内容。识别并提炼出反复出现的核心议题、关键发现、研究方法或争议点。这些将构成综述的核心主体部分。
2. **结构构建与排序**: 以核心主题为中心主线，将上一步提炼出的核心议题组织成一个逻辑连贯的序列。设计出能够反映内容内在联系（如：从问题到解决方案，从基础到应用）的主体部分标题。
3. **完整大纲规划**: 在核心主体部分前后，分别加入标准的"引言"和"结论与展望"（或"总结"、"讨论与结论"等）部分，形成一个完整的综述框架。确保引言能概述背景和目的，结论能总结要点并提出未来方向。
4. **字数权重分配**: 评估大纲中每个部分（引言、各主体部分、结论）的内容承载量和重要性。根据其权重和综述的实际需要，为每个部分分配合理的建议字数，以指导后续的写作。

## 4. 输出要求
- **格式**: Markdown层级列表。
- **风格**: 专业、学术、简洁。
- **约束**:
    - 大纲必须包含引言、核心主体（可多部分）、结论与展望。
    - 核心主体的标题和结构必须直接源自对文献摘要的分析结果，并围绕核心主题展开。
    - 每个标题后必须紧跟括号，注明建议字数，格式为 `(建议约 XXX 字)`。
    - 根据主题的复杂程度和文献内容的丰富性，AI自主决定合适的总字数和各部分字数分配。
    - **最终输出**: 你的最终回复应仅包含生成的大纲本身。绝对禁止包含任何引导语、解释、理由、分析或其他非大纲内容。直接从"引言"开始输出。

## 5. 分析材料

**核心主题**: {research_topic}

**文献摘要内容**:
{abstracts_text}

请基于以上材料，生成结构化的综述大纲。
"""
        
        return prompt
    
    def _generate_basic_outline(self, research_topic: str) -> str:
        """生成基础大纲模板（AI失败时的后备方案）"""
        
        outline = f"""## 引言 (建议约 800 字)

## {research_topic}的研究现状 (建议约 1500 字)

## {research_topic}的主要方法与技术 (建议约 1500 字)

## {research_topic}的临床应用与效果 (建议约 1200 字)

## 结论与展望 (建议约 600 字)
"""
        
        return outline
    
    def save_outline(self, outline: str, output_file: str):
        """保存大纲到文件"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(outline)
            print(f"大纲已保存到: {output_file}")
        except Exception as e:
            print(f"保存大纲失败: {e}")
    
    def get_performance_report(self) -> Dict:
        """获取性能报告"""
        cache_stats = self.outline_cache.get_stats() if hasattr(self, 'outline_cache') else {}
        
        return {
            'total_outlines_generated': self.performance_stats['total_outlines_generated'],
            'total_generation_time': self.performance_stats['total_generation_time'],
            'average_generation_time': self.performance_stats['total_generation_time'] / max(self.performance_stats['total_outlines_generated'], 1),
            'cache_hits': self.performance_stats['cache_hits'],
            'parallel_batches': self.performance_stats['parallel_batches'],
            'abstracts_processed': self.performance_stats['abstracts_processed'],
            'ai_calls': self.performance_stats['ai_calls'],
            'errors': self.performance_stats['errors'],
            'retries': self.performance_stats['retries'],
            'cache_stats': cache_stats
        }
    
    def print_performance_report(self):
        """打印性能报告"""
        report = self.get_performance_report()
        
        print("\n=== 大纲生成器性能报告 ===")
        print(f"生成大纲总数: {report['total_outlines_generated']}")
        print(f"总生成时间: {report['total_generation_time']:.2f}秒")
        print(f"平均生成时间: {report['average_generation_time']:.2f}秒/个")
        print(f"缓存命中次数: {report['cache_hits']}")
        print(f"并行处理批次数: {report['parallel_batches']}")
        print(f"处理摘要总数: {report['abstracts_processed']}")
        print(f"AI调用次数: {report['ai_calls']}")
        print(f"错误次数: {report['errors']}")
        print(f"重试次数: {report['retries']}")
        
        if 'cache_stats' in report:
            cache_stats = report['cache_stats']
            print(f"缓存大小: {cache_stats['cache_size']}/{cache_stats['max_cache_size']}")
            print(f"缓存命中率: {cache_stats['hit_rate']:.2%}")
        
        print("=" * 30)
    
    def cleanup(self):
        """清理资源"""
        try:
            # 清理缓存
            if hasattr(self, 'outline_cache'):
                self.outline_cache.cache.clear()
                self.outline_cache.access_times.clear()
            
            # 打印性能报告
            if self.performance_stats['total_outlines_generated'] > 0:
                self.print_performance_report()
                
        except Exception as e:
            print(f"清理资源时出错: {e}")


def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='医学文献综述大纲生成器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python review_outline_generator.py -f literature.json -t "糖尿病治疗" -w 8000
  python review_outline_generator.py -f literature.json -t "COVID-19疫苗" -w 6000 -o outline.md
        """
    )
    
    parser.add_argument('-f', '--file', required=True, help='文献JSON文件路径')
    parser.add_argument('-t', '--topic', required=True, help='研究主题')
    parser.add_argument('-w', '--words', type=int, default=8000, help='目标总字数 (默认: 8000)')
    parser.add_argument('-o', '--output', help='输出文件路径 (默认: 自动生成)')
    parser.add_argument('--ai-config', help='指定AI配置名称')
    
    args = parser.parse_args()
    
    try:
        # 初始化生成器
        generator = ReviewOutlineGenerator(args.ai_config)
        
        # 生成大纲
        print(f"正在基于文献 '{args.file}' 生成主题为 '{args.topic}' 的综述大纲...")
        outline = generator.generate_outline_from_json(args.file, args.topic, args.words)
        
        # 输出结果
        if args.output:
            generator.save_outline(outline, args.output)
        else:
            # 生成默认文件名和路径
            import re
            import os
            from datetime import datetime
            safe_topic = re.sub(r'[^\w\s-]', '', args.topic).replace(' ', '_')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            outline_filename = f"综述大纲—{safe_topic}-{timestamp}.md"
            output_file = os.path.join("综述大纲", outline_filename)
            generator.save_outline(outline, output_file)
        
        print("\n生成的大纲:")
        print("=" * 60)
        print(outline)
        
    except Exception as e:
        print(f"大纲生成失败: {e}")


if __name__ == "__main__":
    main()