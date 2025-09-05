#!/usr/bin/env python3
"""
PubMed文献搜索和导出工具 v2.0
支持搜索PubMed数据库并导出为多种格式（CSV、JSON、TXT、BibTeX）
优化特性：异步请求、智能缓存、增强错误处理、性能监控
"""

import requests
import json
import csv
import asyncio
import aiohttp
import lxml.etree as lxml_etree
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
import time
import argparse
import sys
import os
import hashlib
import threading
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict


@dataclass
class SearchConfig:
    """搜索配置类"""
    email: str = "user@example.com"
    tool: str = "pubmed_searcher"
    max_results: int = 100
    sort_by: str = "relevance"
    batch_size: int = 200
    request_delay: float = 5.0
    max_retries: int = 3
    enable_cache: bool = True
    cache_ttl: int = 3600
    cache_max_size: int = 1000
    enable_async: bool = True
    max_concurrent: int = 5


class SearchResultCache:
    """搜索结果缓存管理器"""
    
    def __init__(self, cache_dir: str = "pubmed_cache", max_size: int = 1000, ttl: int = 3600):
        self.cache_dir = cache_dir
        self.max_size = max_size
        self.ttl = ttl
        self.lock = threading.Lock()
        self.stats = {'hits': 0, 'misses': 0, 'evictions': 0}
        
        # 创建缓存目录
        os.makedirs(cache_dir, exist_ok=True)
    
    def _generate_cache_key(self, query: str, max_results: int, sort_by: str) -> str:
        """生成缓存键"""
        content = f"{query}:{max_results}:{sort_by}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _get_cache_file_path(self, cache_key: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def get(self, query: str, max_results: int, sort_by: str) -> Optional[List[str]]:
        """获取缓存的PMID列表"""
        cache_key = self._generate_cache_key(query, max_results, sort_by)
        cache_file = self._get_cache_file_path(cache_key)
        
        with self.lock:
            if os.path.exists(cache_file):
                try:
                    file_stat = os.stat(cache_file)
                    if time.time() - file_stat.st_mtime < self.ttl:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            self.stats['hits'] += 1
                            return data.get('pmids', [])
                    else:
                        # 清除过期缓存
                        os.remove(cache_file)
                        self.stats['evictions'] += 1
                except Exception:
                    # 缓存文件损坏，删除
                    if os.path.exists(cache_file):
                        os.remove(cache_file)
        
        self.stats['misses'] += 1
        return None
    
    def put(self, query: str, max_results: int, sort_by: str, pmids: List[str]):
        """缓存PMID列表"""
        cache_key = self._generate_cache_key(query, max_results, sort_by)
        cache_file = self._get_cache_file_path(cache_key)
        
        with self.lock:
            # LRU缓存清理
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
            if len(cache_files) >= self.max_size:
                # 删除最老的缓存文件
                cache_files.sort(key=lambda f: os.path.getmtime(os.path.join(self.cache_dir, f)))
                oldest_file = cache_files[0]
                os.remove(os.path.join(self.cache_dir, oldest_file))
                self.stats['evictions'] += 1
            
            # 保存缓存
            cache_data = {
                'query': query,
                'max_results': max_results,
                'sort_by': sort_by,
                'pmids': pmids,
                'timestamp': time.time()
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
    
    def clear(self):
        """清除所有缓存"""
        with self.lock:
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
            for cache_file in cache_files:
                os.remove(os.path.join(self.cache_dir, cache_file))
            self.stats = {'hits': 0, 'misses': 0, 'evictions': 0}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                'cache_size': len([f for f in os.listdir(self.cache_dir) if f.endswith('.json')]),
                'max_cache_size': self.max_size,
                'hit_rate': hit_rate,
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'evictions': self.stats['evictions']
            }


class PubMedSearcher:
    """PubMed搜索和数据处理类 v2.0"""
    
    def __init__(self, config: SearchConfig = None):
        """
        初始化PubMed搜索器
        
        Args:
            config: 搜索配置
        """
        self.config = config or SearchConfig()
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.esearch_url = f"{self.base_url}esearch.fcgi"
        self.efetch_url = f"{self.base_url}efetch.fcgi"
        
        # 初始化缓存
        self.cache = SearchResultCache(
            max_size=self.config.cache_max_size,
            ttl=self.config.cache_ttl
        ) if self.config.enable_cache else None
        
        # 性能统计
        self.performance_stats = {
            'total_searches': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'total_articles': 0,
            'total_latency': 0.0,
            'errors': 0,
            'retries': 0,
            'parse_time': 0.0,
            'articles_parsed': 0
        }
        
        # 请求会话
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': f'{self.config.tool}/{self.config.email}'
        })
        
        # 异步会话
        self.async_session = None
        self.thread_pool = ThreadPoolExecutor(max_workers=4) if self.config.enable_async else None
        
    def search_articles(self, query: str, max_results: int = None, 
                       sort_by: str = None) -> List[str]:
        """
        搜索PubMed文章并返回PMID列表 - 优化版
        
        Args:
            query: 搜索关键词
            max_results: 最大结果数量
            sort_by: 排序方式 (relevance, date, author, journal)
        
        Returns:
            PMID列表
        """
        start_time = time.time()
        max_results = max_results or self.config.max_results
        sort_by = sort_by or self.config.sort_by
        
        self.performance_stats['total_searches'] += 1
        print(f"正在搜索关键词: '{query}'...")
        
        # 检查缓存
        if self.cache:
            cached_pmids = self.cache.get(query, max_results, sort_by)
            if cached_pmids:
                self.performance_stats['cache_hits'] += 1
                print(f"缓存命中: 找到 {len(cached_pmids)} 篇文章")
                return cached_pmids
        
        # 构建请求参数
        params = {
            'db': 'pubmed',
            'term': query,
            'retmax': str(max_results),
            'sort': sort_by,
            'email': self.config.email,
            'tool': self.config.tool,
            'retmode': 'json'
        }
        
        # 执行请求（带重试机制）
        pmids = self._execute_request_with_retry(
            self.esearch_url, params, "搜索"
        )
        
        if pmids:
            # 缓存结果
            if self.cache:
                self.cache.put(query, max_results, sort_by, pmids)
            
            # 更新统计
            latency = time.time() - start_time
            self.performance_stats['total_latency'] += latency
            print(f"找到 {len(pmids)} 篇文章，耗时: {latency:.2f}秒")
        else:
            print("搜索失败")
            self.performance_stats['errors'] += 1
        
        return pmids
    
    def _execute_request_with_retry(self, url: str, params: Dict, operation: str) -> List[str]:
        """执行请求并带有重试机制"""
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                self.performance_stats['api_calls'] += 1
                
                # 智能延迟
                if attempt > 0:
                    delay = min(self.config.request_delay * (2 ** attempt), 10.0)
                    print(f"{operation}重试 {attempt + 1}/{self.config.max_retries}，等待 {delay:.1f}秒...")
                    time.sleep(delay)
                
                response = self.session.get(url, params=params, timeout=30)
                
                # 检查API限制
                if response.status_code == 429:
                    retry_after = int(response.headers.get('retry-after', 60))
                    print(f"API限制，等待 {retry_after} 秒...")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                
                # 解析响应
                data = response.json()
                pmids = data.get('esearchresult', {}).get('idlist', [])
                
                if pmids:
                    count = int(data.get('esearchresult', {}).get('count', 0))
                    print(f"{operation}成功: 总计 {count} 篇文章，获取 {len(pmids)} 篇")
                    return pmids
                else:
                    print(f"{operation}未找到结果")
                    return []
                    
            except requests.RequestException as e:
                last_error = e
                self.performance_stats['retries'] += 1
                print(f"{operation}请求失败 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                
                if attempt == self.config.max_retries - 1:
                    break
                    
            except (json.JSONDecodeError, KeyError) as e:
                last_error = e
                print(f"{operation}解析失败 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                
                if attempt == self.config.max_retries - 1:
                    break
        
        self.performance_stats['errors'] += 1
        print(f"{operation}最终失败: {last_error}")
        return []
    
    def fetch_article_details(self, pmids: List[str]) -> List[Dict]:
        """
        获取文章详细信息 - 优化版
        
        Args:
            pmids: PMID列表
        
        Returns:
            文章详细信息列表
        """
        if not pmids:
            return []
        
        print(f"正在获取 {len(pmids)} 篇文章的详细信息...")
        
        # 动态批处理大小
        batch_size = self._calculate_optimal_batch_size(len(pmids))
        all_articles = []
        
        # 同步批处理
        for i in range(0, len(pmids), batch_size):
            batch_pmids = pmids[i:i + batch_size]
            current_batch = i//batch_size + 1
            total_batches = (len(pmids) + batch_size - 1) // batch_size
            print(f"处理第 {current_batch}/{total_batches} 批 ({len(batch_pmids)} 篇)...")
            
            articles = self._fetch_batch_with_retry(batch_pmids)
            all_articles.extend(articles)
            
            # 批次间延迟
            if i + batch_size < len(pmids):  # 不是最后一批
                print(f"等待 {self.config.request_delay} 秒后处理下一批...")
                time.sleep(self.config.request_delay)
        
        print(f"成功获取 {len(all_articles)} 篇文章信息")
        self.performance_stats['total_articles'] += len(all_articles)
        return all_articles
    
    def fetch_article_issn_only(self, pmids: List[str]) -> List[Dict]:
        """
        只获取文章的ISSN和EISSN信息用于筛选
        
        Args:
            pmids: PMID列表
        
        Returns:
            包含PMID、ISSN、EISSN的信息列表
        """
        if not pmids:
            return []
        
        print(f"正在获取 {len(pmids)} 篇文章的ISSN/EISSN信息...")
        
        # 动态批处理大小
        batch_size = self._calculate_optimal_batch_size(len(pmids))
        all_articles = []
        
        # 同步批处理
        for i in range(0, len(pmids), batch_size):
            batch_pmids = pmids[i:i + batch_size]
            current_batch = i//batch_size + 1
            total_batches = (len(pmids) + batch_size - 1) // batch_size
            print(f"处理第 {current_batch}/{total_batches} 批 ({len(batch_pmids)} 篇)...")
            
            articles = self._fetch_batch_issn_only_with_retry(batch_pmids)
            all_articles.extend(articles)
            
            # 批次间延迟
            if i + batch_size < len(pmids):  # 不是最后一批
                print(f"等待 {self.config.request_delay} 秒后处理下一批...")
                time.sleep(self.config.request_delay)
        
        print(f"成功获取 {len(all_articles)} 篇文章的ISSN/EISSN信息")
        return all_articles
    
    async def fetch_article_details_async(self, pmids: List[str]) -> List[Dict]:
        """
        异步获取文章详细信息
        
        Args:
            pmids: PMID列表
        
        Returns:
            文章详细信息列表
        """
        if not pmids:
            return []
        
        if not self.config.enable_async:
            return self.fetch_article_details(pmids)
        
        print(f"异步获取 {len(pmids)} 篇文章的详细信息...")
        
        # 创建异步会话
        if not self.async_session:
            self.async_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60),
                headers={
                    'User-Agent': f'{self.config.tool}/{self.config.email}'
                }
            )
        
        # 动态批处理
        batch_size = self._calculate_optimal_batch_size(len(pmids))
        all_articles = []
        
        # 创建异步任务
        tasks = []
        for i in range(0, len(pmids), batch_size):
            batch_pmids = pmids[i:i + batch_size]
            task = self._fetch_batch_async(batch_pmids)
            tasks.append(task)
        
        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"第 {i + 1} 批异步获取失败: {result}")
                self.performance_stats['errors'] += 1
            else:
                all_articles.extend(result)
        
        # 关闭异步会话
        await self.async_session.close()
        self.async_session = None
        
        print(f"异步成功获取 {len(all_articles)} 篇文章信息")
        self.performance_stats['total_articles'] += len(all_articles)
        return all_articles
    
    def _calculate_optimal_batch_size(self, total_pmids: int) -> int:
        """计算最优批处理大小"""
        # 使用配置的固定批次大小，但不超过总数量
        return min(self.config.batch_size, total_pmids)
    
    def _fetch_batch_with_retry(self, batch_pmids: List[str]) -> List[Dict]:
        """获取一批文章详细信息（带重试）"""
        params = {
            'db': 'pubmed',
            'id': ','.join(batch_pmids),
            'retmode': 'xml',
            'email': self.config.email,
            'tool': self.config.tool
        }
        
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(self.efetch_url, params=params, timeout=60)
                
                # 检查API限制
                if response.status_code == 429:
                    retry_after = int(response.headers.get('retry-after', 60))
                    print(f"API限制，等待 {retry_after} 秒...")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                
                articles = self._parse_xml_response_optimized(response.text)
                return articles
                
            except requests.RequestException as e:
                self.performance_stats['retries'] += 1
                if attempt == self.config.max_retries - 1:
                    print(f"获取批次失败: {e}")
                    self.performance_stats['errors'] += 1
                    return []
                
                delay = min(self.config.request_delay * (2 ** attempt), 10.0)
                time.sleep(delay)
        
        return []
    
    def _fetch_batch_issn_only_with_retry(self, batch_pmids: List[str]) -> List[Dict]:
        """获取一批文章的ISSN信息（带重试）"""
        params = {
            'db': 'pubmed',
            'id': ','.join(batch_pmids),
            'retmode': 'xml',
            'email': self.config.email,
            'tool': self.config.tool
        }
        
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(self.efetch_url, params=params, timeout=60)
                
                # 检查API限制
                if response.status_code == 429:
                    retry_after = int(response.headers.get('retry-after', 60))
                    print(f"API限制，等待 {retry_after} 秒...")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                
                articles = self._parse_xml_response_issn_only(response.text)
                return articles
                
            except requests.RequestException as e:
                self.performance_stats['retries'] += 1
                if attempt == self.config.max_retries - 1:
                    print(f"获取批次ISSN/EISSN信息失败: {e}")
                    self.performance_stats['errors'] += 1
                    return []
                
                delay = min(self.config.request_delay * (2 ** attempt), 10.0)
                time.sleep(delay)
        
        return []
    
    async def _fetch_batch_async(self, batch_pmids: List[str]) -> List[Dict]:
        """异步获取一批文章详细信息"""
        params = {
            'db': 'pubmed',
            'id': ','.join(batch_pmids),
            'retmode': 'xml',
            'email': self.config.email,
            'tool': self.config.tool
        }
        
        for attempt in range(self.config.max_retries):
            try:
                async with self.async_session.get(self.efetch_url, params=params) as response:
                    if response.status == 429:
                        retry_after = int(response.headers.get('retry-after', 60))
                        print(f"API限制，等待 {retry_after} 秒...")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    response.raise_for_status()
                    xml_content = await response.text()
                    articles = self._parse_xml_response_optimized(xml_content)
                    return articles
                    
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    print(f"异步获取批次失败: {e}")
                    self.performance_stats['errors'] += 1
                    return []
                
                delay = min(self.config.request_delay * (2 ** attempt), 10.0)
                await asyncio.sleep(delay)
        
        return []
    
    def _parse_xml_response_optimized(self, xml_content: str) -> List[Dict]:
        """
        优化的XML响应解析方法，使用lxml提高解析速度
        
        Args:
            xml_content: XML内容
        
        Returns:
            文章信息列表
        """
        start_time = time.time()
        articles = []
        
        try:
            # 使用lxml进行更快的XML解析
            root = lxml_etree.fromstring(xml_content.encode('utf-8'))
            
            # 使用XPath优化查找性能
            article_elements = root.xpath('.//PubmedArticle')
            
            # 并行处理文章解析
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_article = {
                    executor.submit(self._extract_article_info, article): article 
                    for article in article_elements
                }
                
                for future in future_to_article:
                    try:
                        article_info = future.result(timeout=30)
                        if article_info:
                            articles.append(article_info)
                    except Exception as e:
                        print(f"文章解析失败: {e}")
                        self.performance_stats['errors'] += 1
            
            # 更新性能统计
            parse_time = time.time() - start_time
            self.performance_stats['parse_time'] += parse_time
            self.performance_stats['articles_parsed'] += len(articles)
            
            return articles
            
        except Exception as e:
            print(f"XML解析错误: {e}")
            self.performance_stats['errors'] += 1
            return []
    
    def _parse_xml_response_issn_only(self, xml_content: str) -> List[Dict]:
        """
        只解析ISSN和EISSN信息的XML响应
        
        Args:
            xml_content: XML内容
        
        Returns:
            只包含PMID、ISSN、EISSN的文章信息列表
        """
        start_time = time.time()
        articles = []
        
        try:
            # 使用lxml进行更快的XML解析
            root = lxml_etree.fromstring(xml_content.encode('utf-8'))
            
            # 使用XPath优化查找性能
            article_elements = root.xpath('.//PubmedArticle')
            
            for article_element in article_elements:
                article_info = self._extract_issn_info(article_element)
                if article_info:
                    articles.append(article_info)
            
            # 更新性能统计
            parse_time = time.time() - start_time
            self.performance_stats['parse_time'] += parse_time
            self.performance_stats['articles_parsed'] += len(articles)
            
            return articles
            
        except Exception as e:
            print(f"ISSN/EISSN信息XML解析错误: {e}")
            self.performance_stats['errors'] += 1
            return []
    
    def _extract_issn_info(self, article_element) -> Optional[Dict]:
        """
        从XML元素中提取ISSN和EISSN信息
        
        Args:
            article_element: XML文章元素
        
        Returns:
            包含PMID、ISSN、EISSN的文章信息字典
        """
        try:
            # 基本信息
            pmid_elem = article_element.find('.//PMID')
            pmid = pmid_elem.text if pmid_elem is not None else ""
            
            # ISSN和eISSN
            issn, eissn = self._extract_issn(article_element)
            
            return {
                'pmid': pmid,
                'issn': issn,
                'eissn': eissn,
            }
            
        except Exception as e:
            print(f"提取ISSN/EISSN信息失败: {e}")
            return None
    
    def _extract_article_info(self, article_element) -> Optional[Dict]:
        """
        从XML元素中提取文章信息
        
        Args:
            article_element: XML文章元素
        
        Returns:
            文章信息字典
        """
        try:
            # 基本信息
            pmid_elem = article_element.find('.//PMID')
            pmid = pmid_elem.text if pmid_elem is not None else ""
            
            title_elem = article_element.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else ""
            
            # 作者信息
            authors = []
            for author in article_element.findall('.//Author'):
                last_name = author.find('LastName')
                fore_name = author.find('ForeName')
                if last_name is not None and fore_name is not None:
                    authors.append(f"{last_name.text}, {fore_name.text}")
                elif last_name is not None:
                    authors.append(last_name.text)
            
            # 期刊信息
            journal_elem = article_element.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else ""
            
            # 期刊卷期页码信息
            volume, issue, pages = self._extract_journal_info(article_element)
            
            # 发表日期
            pub_date = self._extract_publication_date(article_element)
            
            # 摘要 - 支持多段落完整摘要
            abstract = self._extract_complete_abstract(article_element)
            
            # ISSN和eISSN
            issn, eissn = self._extract_issn(article_element)
            
            # DOI
            doi = ""
            for article_id in article_element.findall('.//ArticleId'):
                id_type = article_id.get('IdType')
                if id_type == 'doi':
                    doi = article_id.text
                    break
            
            # 关键词
            keywords = []
            for keyword in article_element.findall('.//Keyword'):
                if keyword.text:
                    keywords.append(keyword.text)
            
            return {
                'pmid': pmid,
                'title': title,
                'authors': authors,
                'journal': journal,
                'volume': volume,
                'issue': issue,
                'pages': pages,
                'publication_date': pub_date,
                'abstract': abstract,
                'doi': doi,
                'issn': issn,
                'eissn': eissn,
                'keywords': keywords,
                'authors_str': '; '.join(authors),
                'keywords_str': '; '.join(keywords),
                'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}" if pmid else ""  # 构建PubMed URL
            }
            
        except Exception as e:
            print(f"提取文章信息失败: {e}")
            return None
    
    def _extract_journal_info(self, article_element) -> tuple:
        """
        提取期刊卷号、期号和页码信息
        
        Args:
            article_element: XML文章元素
        
        Returns:
            (volume, issue, pages) 元组
        """
        volume = ""
        issue = ""
        pages = ""
        
        try:
            # 查找JournalIssue下的Volume
            volume_elem = article_element.find('.//JournalIssue/Volume')
            if volume_elem is not None:
                volume = volume_elem.text or ""
            
            # 查找JournalIssue下的Issue
            issue_elem = article_element.find('.//JournalIssue/Issue')
            if issue_elem is not None:
                issue = issue_elem.text or ""
            
            # 查找Pagination下的MedlinePgn
            pages_elem = article_element.find('.//Pagination/MedlinePgn')
            if pages_elem is not None:
                pages = pages_elem.text or ""
            
            # 备用方案：查找StartPage和EndPage
            if not pages:
                start_page = article_element.find('.//Pagination/StartPage')
                end_page = article_element.find('.//Pagination/EndPage')
                
                if start_page is not None and end_page is not None:
                    pages = f"{start_page.text}-{end_page.text}"
                elif start_page is not None:
                    pages = start_page.text or ""
                    
        except Exception as e:
            # 静默处理异常
            pass
            
        return volume, issue, pages
    
    def _extract_publication_date(self, article_element) -> str:
        """提取发表日期"""
        try:
            # 尝试获取完整日期
            date_elem = article_element.find('.//PubDate')
            if date_elem is not None:
                year = date_elem.find('Year')
                month = date_elem.find('Month')
                day = date_elem.find('Day')
                
                date_parts = []
                if year is not None:
                    date_parts.append(year.text)
                if month is not None:
                    date_parts.append(month.text)
                if day is not None:
                    date_parts.append(day.text)
                
                return '-'.join(date_parts) if date_parts else ""
            
            return ""
            
        except Exception:
            return ""
    
    def _extract_issn(self, article_element) -> tuple:
        """
        提取ISSN和eISSN
        
        Args:
            article_element: XML文章元素
        
        Returns:
            (issn, eissn) 元组
        """
        issn = ""
        eissn = ""
        
        try:
            # 查找Journal下的ISSN信息
            for issn_elem in article_element.findall('.//Journal/ISSN'):
                issn_type = issn_elem.get('IssnType')
                if issn_type == 'Print' and not issn:
                    issn = issn_elem.text or ""
                elif issn_type == 'Electronic' and not eissn:
                    eissn = issn_elem.text or ""
            
            # 如果没有找到Print ISSN，尝试获取任意ISSN作为备用
            if not issn:
                issn_elem = article_element.find('.//Journal/ISSN')
                if issn_elem is not None:
                    issn = issn_elem.text or ""
                    
        except Exception as e:
            pass
            
        return issn, eissn
    
    def _extract_complete_abstract(self, article_element) -> str:
        """
        提取完整摘要，支持多段落和结构化摘要
        
        Args:
            article_element: XML文章元素
        
        Returns:
            完整的摘要文本
        """
        try:
            abstract_parts = []
            
            # 查找所有AbstractText元素
            abstract_texts = article_element.findall('.//AbstractText')
            
            if abstract_texts:
                for abstract_elem in abstract_texts:
                    # 获取标签（如Background, Methods, Results等）
                    label = abstract_elem.get('Label')
                    text = abstract_elem.text or ""
                    
                    if text.strip():
                        if label:
                            abstract_parts.append(f"{label}: {text.strip()}")
                        else:
                            abstract_parts.append(text.strip())
                
                # 合并所有段落
                if abstract_parts:
                    return " ".join(abstract_parts)
            
            # 备用方案：查找Abstract元素
            abstract_elem = article_element.find('.//Abstract')
            if abstract_elem is not None:
                # 获取所有文本内容
                abstract_text = "".join(abstract_elem.itertext()).strip()
                if abstract_text:
                    return abstract_text
                    
            return ""
            
        except Exception as e:
            # 备用方案：使用简单方式提取
            try:
                abstract_elem = article_element.find('.//AbstractText')
                return abstract_elem.text if abstract_elem is not None else ""
            except:
                return ""


class DataExporter:
    """数据导出类"""
    
    @staticmethod
    def export_to_csv(articles: List[Dict], filename: str) -> bool:
        """导出为CSV格式"""
        if not articles:
            print("没有文章数据可导出")
            return False
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'pmid', 'title', 'authors_str', 'journal', 'volume', 'issue', 'pages',
                    'publication_date', 'abstract', 'doi', 'issn', 'eissn', 'keywords_str'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for article in articles:
                    # 只写入指定字段
                    row = {field: article.get(field, '') for field in fieldnames}
                    writer.writerow(row)
            
            print(f"已导出CSV文件: {filename}")
            return True
            
        except Exception as e:
            print(f"导出CSV失败: {e}")
            return False
    
    @staticmethod
    def export_to_json(articles: List[Dict], filename: str) -> bool:
        """导出为JSON格式"""
        if not articles:
            print("没有文章数据可导出")
            return False
        
        try:
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump({
                    'search_date': datetime.now().isoformat(),
                    'total_articles': len(articles),
                    'articles': articles
                }, jsonfile, ensure_ascii=False, indent=2)
            
            print(f"已导出JSON文件: {filename}")
            return True
            
        except Exception as e:
            print(f"导出JSON失败: {e}")
            return False
    
    @staticmethod
    def export_to_txt(articles: List[Dict], filename: str) -> bool:
        """导出为TXT格式"""
        if not articles:
            print("没有文章数据可导出")
            return False
        
        try:
            with open(filename, 'w', encoding='utf-8') as txtfile:
                txtfile.write(f"PubMed搜索结果\n")
                txtfile.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                txtfile.write(f"文章数量: {len(articles)}\n")
                txtfile.write("=" * 80 + "\n\n")
                
                for i, article in enumerate(articles, 1):
                    txtfile.write(f"[{i}] PMID: {article.get('pmid', '')}\n")
                    txtfile.write(f"标题: {article.get('title', '')}\n")
                    txtfile.write(f"作者: {article.get('authors_str', '')}\n")
                    txtfile.write(f"期刊: {article.get('journal', '')}\n")
                    if article.get('volume'):
                        txtfile.write(f"卷: {article.get('volume', '')}\n")
                    if article.get('issue'):
                        txtfile.write(f"期: {article.get('issue', '')}\n")
                    if article.get('pages'):
                        txtfile.write(f"页码: {article.get('pages', '')}\n")
                    txtfile.write(f"发表日期: {article.get('publication_date', '')}\n")
                    txtfile.write(f"DOI: {article.get('doi', '')}\n")
                    txtfile.write(f"ISSN: {article.get('issn', '')}\n")
                    txtfile.write(f"eISSN: {article.get('eissn', '')}\n")
                    txtfile.write(f"关键词: {article.get('keywords_str', '')}\n")
                    
                    if article.get('abstract'):
                        txtfile.write(f"摘要: {article['abstract']}\n")
                    
                    txtfile.write("-" * 80 + "\n\n")
            
            print(f"已导出TXT文件: {filename}")
            return True
            
        except Exception as e:
            print(f"导出TXT失败: {e}")
            return False
    
    @staticmethod
    def export_to_bibtex(articles: List[Dict], filename: str) -> bool:
        """导出为BibTeX格式"""
        if not articles:
            print("没有文章数据可导出")
            return False
        
        try:
            with open(filename, 'w', encoding='utf-8') as bibfile:
                for article in articles:
                    pmid = article.get('pmid', '')
                    title = article.get('title', '').replace('{', '').replace('}', '')
                    authors = ' and '.join(article.get('authors', []))
                    journal = article.get('journal', '')
                    year = article.get('publication_date', '').split('-')[0] if article.get('publication_date') else ''
                    volume = article.get('volume', '')
                    issue = article.get('issue', '') 
                    pages = article.get('pages', '')
                    doi = article.get('doi', '')
                    
                    bibfile.write(f"@article{{pmid{pmid},\n")
                    bibfile.write(f"  title={{{title}}},\n")
                    if authors:
                        bibfile.write(f"  author={{{authors}}},\n")
                    if journal:
                        bibfile.write(f"  journal={{{journal}}},\n")
                    if volume:
                        bibfile.write(f"  volume={{{volume}}},\n")
                    if issue:
                        bibfile.write(f"  number={{{issue}}},\n")
                    if pages:
                        bibfile.write(f"  pages={{{pages}}},\n")
                    if year:
                        bibfile.write(f"  year={{{year}}},\n")
                    if doi:
                        bibfile.write(f"  doi={{{doi}}},\n")
                    
                    issn = article.get('issn', '')
                    if issn:
                        bibfile.write(f"  issn={{{issn}}},\n")
                    
                    eissn = article.get('eissn', '')
                    if eissn:
                        bibfile.write(f"  eissn={{{eissn}}},\n")
                    
                    bibfile.write(f"  pmid={{{pmid}}}\n")
                    bibfile.write("}\n\n")
            
            print(f"已导出BibTeX文件: {filename}")
            return True
            
        except Exception as e:
            print(f"导出BibTeX失败: {e}")
            return False


def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description='PubMed文献搜索和导出工具')
    parser.add_argument('query', help='搜索关键词')
    parser.add_argument('-n', '--max-results', type=int, default=50, 
                       help='最大结果数量 (默认: 50)')
    parser.add_argument('-f', '--format', choices=['csv', 'json', 'txt', 'bibtex', 'all'],
                       default='csv', help='导出格式 (默认: csv)')
    parser.add_argument('-o', '--output', help='输出文件前缀 (默认: pubmed_search)')
    parser.add_argument('-e', '--email', default='user@example.com',
                       help='邮箱地址 (用于API请求)')
    parser.add_argument('--sort', choices=['relevance', 'date', 'author', 'journal'],
                       default='relevance', help='排序方式 (默认: relevance)')
    
    args = parser.parse_args()
    
    # 创建搜索器
    searcher = PubMedSearcher(email=args.email)
    
    # 搜索文章
    pmids = searcher.search_articles(
        query=args.query,
        max_results=args.max_results,
        sort_by=args.sort
    )
    
    if not pmids:
        print("未找到任何文章")
        sys.exit(1)
    
    # 获取文章详细信息
    articles = searcher.fetch_article_details(pmids)
    
    if not articles:
        print("无法获取文章详细信息")
        sys.exit(1)
    
    # 生成输出文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_prefix = args.output or f"pubmed_search_{timestamp}"
    
    # 导出数据
    exporter = DataExporter()
    success = False
    
    if args.format == 'all':
        formats = ['csv', 'json', 'txt', 'bibtex']
    else:
        formats = [args.format]
    
    for fmt in formats:
        filename = f"{output_prefix}.{fmt}"
        
        if fmt == 'csv':
            success = exporter.export_to_csv(articles, filename) or success
        elif fmt == 'json':
            success = exporter.export_to_json(articles, filename) or success
        elif fmt == 'txt':
            success = exporter.export_to_txt(articles, filename) or success
        elif fmt == 'bibtex':
            success = exporter.export_to_bibtex(articles, filename) or success
    
    if success:
        print(f"\n搜索完成! 共处理 {len(articles)} 篇文章")
    else:
        print("导出失败")
        sys.exit(1)


    def get_performance_report(self) -> Dict:
        """获取性能报告"""
        return {
            'total_searches': self.performance_stats['total_searches'],
            'cache_hits': self.performance_stats['cache_hits'],
            'cache_hit_rate': self.performance_stats['cache_hits'] / max(self.performance_stats['total_searches'], 1),
            'api_calls': self.performance_stats['api_calls'],
            'retries': self.performance_stats['retries'],
            'errors': self.performance_stats['errors'],
            'total_latency': self.performance_stats['total_latency'],
            'average_latency': self.performance_stats['total_latency'] / max(self.performance_stats['total_searches'], 1),
            'parse_time': self.performance_stats['parse_time'],
            'articles_parsed': self.performance_stats['articles_parsed'],
            'average_parse_time': self.performance_stats['parse_time'] / max(self.performance_stats['articles_parsed'], 1) if self.performance_stats['articles_parsed'] > 0 else 0
        }
    
    def print_performance_report(self):
        """打印性能报告"""
        report = self.get_performance_report()
        print("\n=== PubMed检索器性能报告 ===")
        print(f"总搜索次数: {report['total_searches']}")
        print(f"缓存命中率: {report['cache_hit_rate']:.2%}")
        print(f"API调用次数: {report['api_calls']}")
        print(f"重试次数: {report['retries']}")
        print(f"错误次数: {report['errors']}")
        print(f"平均延迟: {report['average_latency']:.2f}秒")
        print(f"平均解析时间: {report['average_parse_time']:.4f}秒")
        print(f"解析文章总数: {report['articles_parsed']}")
        print("=" * 30)
    
    def cleanup(self):
        """清理资源"""
        try:
            # 清理会话
            if hasattr(self, 'session'):
                self.session.close()
            
            # 清理缓存
            if hasattr(self, 'cache'):
                self.cache.cleanup()
            
            # 打印性能报告
            if self.performance_stats['total_searches'] > 0:
                self.print_performance_report()
                
        except Exception as e:
            print(f"清理资源时出错: {e}")


if __name__ == "__main__":
    main()