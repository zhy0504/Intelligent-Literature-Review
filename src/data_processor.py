#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期刊数据处理程序 - ABCE优化版本
处理中科院分区数据(zky.csv)和JCR数据(jcr.csv)，合并生成综合期刊数据表
"""

import pandas as pd
import numpy as np
import re
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime


class ProcessorConfig:
    """数据处理器配置"""
    def __init__(self):
        self.max_workers = 4
        self.enable_parallel = True
        self.enable_caching = True
        self.cache_size = 1000
        self.cache_ttl = 3600
        self.chunk_size = 10000  # 大数据集分块处理大小
        self.memory_limit_mb = 512  # 内存限制(MB)


class DataCache:
    """数据缓存系统"""
    def __init__(self, config: ProcessorConfig):
        self.config = config
        self.cache = {}
        self.access_times = {}
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        with self.lock:
            if key in self.cache:
                current_time = time.time()
                if current_time - self.access_times[key] < self.config.cache_ttl:
                    self.access_times[key] = current_time
                    self.hits += 1
                    return self.cache[key]
                else:
                    # 缓存过期
                    del self.cache[key]
                    del self.access_times[key]
            self.misses += 1
            return None
    
    def put(self, key: str, value: Any):
        """存储缓存数据"""
        with self.lock:
            # 检查缓存大小
            if len(self.cache) >= self.config.cache_size:
                # LRU淘汰
                oldest_key = min(self.access_times.keys(), key=self.access_times.get)
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
            
            self.cache[key] = value
            self.access_times[key] = time.time()
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        return {
            'current_size': len(self.cache),
            'max_size': self.config.cache_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate
        }


class JournalDataProcessor:
    """期刊数据处理器 - ABCE优化版本"""
    
    def __init__(self, data_dir: str = "data"):
        """
        初始化数据处理器 - ABCE优化版本
        
        Args:
            data_dir: 数据文件目录
        """
        # 初始化配置
        self.processor_config = ProcessorConfig()
        self.data_cache = DataCache(self.processor_config)
        
        # 性能统计
        self.performance_stats = {
            'total_processing_time': 0,
            'zky_processing_time': 0,
            'jcr_processing_time': 0,
            'merge_time': 0,
            'memory_usage_mb': 0,
            'records_processed': 0
        }
        
        self.data_dir = data_dir
        self.zky_file = os.path.join(data_dir, "zky.csv")
        self.jcr_file = os.path.join(data_dir, "jcr.csv")
        
        # 检查文件是否存在
        if not os.path.exists(self.zky_file):
            raise FileNotFoundError(f"找不到中科院分区数据文件: {self.zky_file}")
        if not os.path.exists(self.jcr_file):
            raise FileNotFoundError(f"找不到JCR数据文件: {self.jcr_file}")
        
        print(f"数据处理器初始化完成")
        print(f"并行处理: {'启用' if self.processor_config.enable_parallel else '禁用'}")
        print(f"缓存系统: {'启用' if self.processor_config.enable_caching else '禁用'}")
    
    def process_zky_data(self) -> pd.DataFrame:
        """
        处理中科院分区数据 - ABCE优化版本
        
        Returns:
            处理后的DataFrame，包含ISSN、EISSN、中科院分区列
        """
        start_time = time.time()
        print("处理中科院分区数据...")
        
        # 检查缓存
        cache_key = f"zky_data_{os.path.getmtime(self.zky_file)}"
        cached_result = self.data_cache.get(cache_key)
        if cached_result is not None:
            print(f"中科院数据缓存命中，共 {len(cached_result)} 条记录")
            self.performance_stats['zky_processing_time'] = time.time() - start_time
            return cached_result
        
        # 检查文件大小，决定是否分块处理
        file_size_mb = os.path.getsize(self.zky_file) / (1024 * 1024)
        if file_size_mb > 10:  # 大于10MB使用分块处理
            result_df = self._process_zky_data_chunked()
        else:
            result_df = self._process_zky_data_standard()
        
        # 缓存结果
        if self.processor_config.enable_caching:
            self.data_cache.put(cache_key, result_df)
        
        processing_time = time.time() - start_time
        self.performance_stats['zky_processing_time'] = processing_time
        print(f"中科院数据处理完成，共 {len(result_df)} 条记录，耗时 {processing_time:.2f}秒")
        return result_df
    
    def _process_zky_data_standard(self) -> pd.DataFrame:
        """标准中科院数据处理"""
        # 读取CSV文件
        df = pd.read_csv(self.zky_file, encoding='utf-8')
        
        # 提取需要的列
        df_processed = df[['ISSN/EISSN', '大类分区']].copy()
        
        # 处理ISSN/EISSN列，拆分为ISSN和EISSN
        issn_data = df_processed['ISSN/EISSN'].str.split('/', expand=True)
        df_processed['ISSN'] = issn_data[0].str.strip()
        df_processed['EISSN'] = issn_data[1].str.strip() if issn_data.shape[1] > 1 else ''
        
        # 处理相同ISSN和EISSN的情况
        df_processed.loc[df_processed['ISSN'] == df_processed['EISSN'], 'EISSN'] = ''
        
        # 提取大类分区数字（"["前面的数字）
        df_processed['中科院分区'] = df_processed['大类分区'].str.extract(r'(\d+)(?=\s*\[)')[0]
        df_processed['中科院分区'] = pd.to_numeric(df_processed['中科院分区'], errors='coerce')
        
        # 清理数据
        result_df = df_processed[['ISSN', 'EISSN', '中科院分区']].copy()
        
        # 移除ISSN和EISSN都为空的记录
        result_df = result_df[
            (result_df['ISSN'].notna() & (result_df['ISSN'] != '')) |
            (result_df['EISSN'].notna() & (result_df['EISSN'] != ''))
        ]
        
        return result_df
    
    def _process_zky_data_chunked(self) -> pd.DataFrame:
        """分块处理中科院数据"""
        print("使用分块处理模式处理中科院数据...")
        
        chunks = []
        for chunk in pd.read_csv(self.zky_file, encoding='utf-8', chunksize=self.processor_config.chunk_size):
            # 处理每个数据块
            df_processed = chunk[['ISSN/EISSN', '大类分区']].copy()
            
            # 处理ISSN/EISSN列
            issn_data = df_processed['ISSN/EISSN'].str.split('/', expand=True)
            df_processed['ISSN'] = issn_data[0].str.strip()
            df_processed['EISSN'] = issn_data[1].str.strip() if issn_data.shape[1] > 1 else ''
            
            # 处理相同ISSN和EISSN的情况
            df_processed.loc[df_processed['ISSN'] == df_processed['EISSN'], 'EISSN'] = ''
            
            # 提取大类分区数字
            df_processed['中科院分区'] = df_processed['大类分区'].str.extract(r'(\d+)(?=\s*\[)')[0]
            df_processed['中科院分区'] = pd.to_numeric(df_processed['中科院分区'], errors='coerce')
            
            # 清理数据
            result_chunk = df_processed[['ISSN', 'EISSN', '中科院分区']].copy()
            
            # 移除ISSN和EISSN都为空的记录
            result_chunk = result_chunk[
                (result_chunk['ISSN'].notna() & (result_chunk['ISSN'] != '')) |
                (result_chunk['EISSN'].notna() & (result_chunk['EISSN'] != ''))
            ]
            
            chunks.append(result_chunk)
        
        # 合并所有数据块
        result_df = pd.concat(chunks, ignore_index=True)
        return result_df
    
    def process_jcr_data(self) -> pd.DataFrame:
        """
        处理JCR数据 - ABCE优化版本
        
        Returns:
            处理后的DataFrame，包含ISSN、eISSN、影响因子、JCR分区列
        """
        start_time = time.time()
        print("处理JCR数据...")
        
        # 检查缓存
        cache_key = f"jcr_data_{os.path.getmtime(self.jcr_file)}"
        cached_result = self.data_cache.get(cache_key)
        if cached_result is not None:
            print(f"JCR数据缓存命中，共 {len(cached_result)} 条记录")
            self.performance_stats['jcr_processing_time'] = time.time() - start_time
            return cached_result
        
        # 检查文件大小，决定是否分块处理
        file_size_mb = os.path.getsize(self.jcr_file) / (1024 * 1024)
        if file_size_mb > 10:  # 大于10MB使用分块处理
            result_df = self._process_jcr_data_chunked()
        else:
            result_df = self._process_jcr_data_standard()
        
        # 缓存结果
        if self.processor_config.enable_caching:
            self.data_cache.put(cache_key, result_df)
        
        processing_time = time.time() - start_time
        self.performance_stats['jcr_processing_time'] = processing_time
        print(f"JCR数据处理完成，共 {len(result_df)} 条记录，耗时 {processing_time:.2f}秒")
        return result_df
    
    def _process_jcr_data_standard(self) -> pd.DataFrame:
        """标准JCR数据处理"""
        # 读取CSV文件
        df = pd.read_csv(self.jcr_file, encoding='utf-8')
        
        # 提取需要的列
        columns_needed = ['ISSN', 'eISSN', 'IF(2024)', 'IF Quartile(2024)']
        df_processed = df[columns_needed].copy()
        
        # 重命名列
        df_processed.rename(columns={
            'eISSN': 'EISSN',
            'IF(2024)': '影响因子',
            'IF Quartile(2024)': 'JCR分区'
        }, inplace=True)
        
        # 处理影响因子数据（转为数值型）
        df_processed['影响因子'] = pd.to_numeric(df_processed['影响因子'], errors='coerce')
        
        # 清理ISSN和EISSN数据
        df_processed['ISSN'] = df_processed['ISSN'].astype(str).str.strip()
        df_processed['EISSN'] = df_processed['EISSN'].astype(str).str.strip()
        
        # 处理NaN值
        df_processed['ISSN'] = df_processed['ISSN'].replace(['nan', 'NaN', ''], np.nan)
        df_processed['EISSN'] = df_processed['EISSN'].replace(['nan', 'NaN', ''], np.nan)
        
        # 移除ISSN和EISSN都为空的记录
        result_df = df_processed[
            (df_processed['ISSN'].notna()) |
            (df_processed['EISSN'].notna())
        ]
        
        return result_df
    
    def _process_jcr_data_chunked(self) -> pd.DataFrame:
        """分块处理JCR数据"""
        print("使用分块处理模式处理JCR数据...")
        
        chunks = []
        for chunk in pd.read_csv(self.jcr_file, encoding='utf-8', chunksize=self.processor_config.chunk_size):
            # 处理每个数据块
            columns_needed = ['ISSN', 'eISSN', 'IF(2024)', 'IF Quartile(2024)']
            df_processed = chunk[columns_needed].copy()
            
            # 重命名列
            df_processed.rename(columns={
                'eISSN': 'EISSN',
                'IF(2024)': '影响因子',
                'IF Quartile(2024)': 'JCR分区'
            }, inplace=True)
            
            # 处理影响因子数据
            df_processed['影响因子'] = pd.to_numeric(df_processed['影响因子'], errors='coerce')
            
            # 清理ISSN和EISSN数据
            df_processed['ISSN'] = df_processed['ISSN'].astype(str).str.strip()
            df_processed['EISSN'] = df_processed['EISSN'].astype(str).str.strip()
            
            # 处理NaN值
            df_processed['ISSN'] = df_processed['ISSN'].replace(['nan', 'NaN', ''], np.nan)
            df_processed['EISSN'] = df_processed['EISSN'].replace(['nan', 'NaN', ''], np.nan)
            
            # 移除ISSN和EISSN都为空的记录
            result_chunk = df_processed[
                (df_processed['ISSN'].notna()) |
                (df_processed['EISSN'].notna())
            ]
            
            chunks.append(result_chunk)
        
        # 合并所有数据块
        result_df = pd.concat(chunks, ignore_index=True)
        return result_df
    
    def merge_data(self, zky_df: pd.DataFrame, jcr_df: pd.DataFrame) -> pd.DataFrame:
        """
        合并中科院分区数据和JCR数据 - ABCE优化版本
        优先根据ISSN匹配，没有ISSN则根据EISSN匹配
        
        Args:
            zky_df: 处理后的中科院数据
            jcr_df: 处理后的JCR数据
            
        Returns:
            合并后的DataFrame
        """
        start_time = time.time()
        print("合并数据...")
        
        # 检查缓存
        cache_key = f"merge_data_{hash(str(zky_df.shape))}_{hash(str(jcr_df.shape))}"
        cached_result = self.data_cache.get(cache_key)
        if cached_result is not None:
            print(f"合并数据缓存命中，共 {len(cached_result)} 条记录")
            self.performance_stats['merge_time'] = time.time() - start_time
            return cached_result
        
        # 根据数据大小选择处理策略
        total_records = len(zky_df) + len(jcr_df)
        if self.processor_config.enable_parallel and total_records > 10000:
            result_df = self._merge_data_parallel(zky_df, jcr_df)
        else:
            result_df = self._merge_data_standard(zky_df, jcr_df)
        
        # 缓存结果
        if self.processor_config.enable_caching:
            self.data_cache.put(cache_key, result_df)
        
        merge_time = time.time() - start_time
        self.performance_stats['merge_time'] = merge_time
        print(f"数据合并完成，共 {len(result_df)} 条记录，耗时 {merge_time:.2f}秒")
        return result_df
    
    def _merge_data_standard(self, zky_df: pd.DataFrame, jcr_df: pd.DataFrame) -> pd.DataFrame:
        """标准数据合并方法"""
        # 准备最终结果DataFrame
        final_columns = ['ISSN', 'EISSN', '中科院分区', '影响因子', 'JCR分区']
        all_results = []
        
        # 创建用于匹配的数据副本
        zky_remaining = zky_df.copy()
        jcr_remaining = jcr_df.copy()
        
        # 第一步：基于ISSN匹配（ISSN不为空且相同）
        print("基于ISSN进行匹配...")
        zky_with_issn = zky_remaining[zky_remaining['ISSN'].notna() & (zky_remaining['ISSN'] != '')].copy()
        jcr_with_issn = jcr_remaining[jcr_remaining['ISSN'].notna() & (jcr_remaining['ISSN'] != '')].copy()
        
        if len(zky_with_issn) > 0 and len(jcr_with_issn) > 0:
            issn_merged = pd.merge(
                zky_with_issn, 
                jcr_with_issn, 
                on='ISSN', 
                how='inner',
                suffixes=('_zky', '_jcr')
            )
            
            if len(issn_merged) > 0:
                # 合并EISSN信息
                issn_merged['EISSN'] = issn_merged['EISSN_zky'].fillna(issn_merged['EISSN_jcr'])
                issn_result = issn_merged[final_columns].copy()
                all_results.append(issn_result)
                
                # 从剩余数据中移除已匹配的记录
                matched_issns = set(issn_merged['ISSN'].unique())
                zky_remaining = zky_remaining[~zky_remaining['ISSN'].isin(matched_issns)]
                jcr_remaining = jcr_remaining[~jcr_remaining['ISSN'].isin(matched_issns)]
                
                print(f"ISSN匹配找到 {len(issn_result)} 条记录")
        
        # 第二步：基于EISSN匹配（没有ISSN匹配的记录）
        print("基于EISSN进行匹配...")
        zky_with_eissn = zky_remaining[zky_remaining['EISSN'].notna() & (zky_remaining['EISSN'] != '')].copy()
        jcr_with_eissn = jcr_remaining[jcr_remaining['EISSN'].notna() & (jcr_remaining['EISSN'] != '')].copy()
        
        if len(zky_with_eissn) > 0 and len(jcr_with_eissn) > 0:
            eissn_merged = pd.merge(
                zky_with_eissn, 
                jcr_with_eissn, 
                on='EISSN', 
                how='inner',
                suffixes=('_zky', '_jcr')
            )
            
            if len(eissn_merged) > 0:
                # 合并ISSN信息
                eissn_merged['ISSN'] = eissn_merged['ISSN_zky'].fillna(eissn_merged['ISSN_jcr'])
                eissn_result = eissn_merged[final_columns].copy()
                all_results.append(eissn_result)
                
                # 从剩余数据中移除已匹配的记录
                matched_eissns = set(eissn_merged['EISSN'].unique())
                zky_remaining = zky_remaining[~zky_remaining['EISSN'].isin(matched_eissns)]
                jcr_remaining = jcr_remaining[~jcr_remaining['EISSN'].isin(matched_eissns)]
                
                print(f"EISSN匹配找到 {len(eissn_result)} 条记录")
        
        # 第三步：添加未匹配的中科院数据
        if len(zky_remaining) > 0:
            zky_unmatched = zky_remaining.copy()
            zky_unmatched['影响因子'] = np.nan
            zky_unmatched['JCR分区'] = np.nan
            zky_unmatched_result = zky_unmatched[final_columns].copy()
            all_results.append(zky_unmatched_result)
            print(f"未匹配的中科院数据: {len(zky_unmatched_result)} 条记录")
        
        # 第四步：添加未匹配的JCR数据
        if len(jcr_remaining) > 0:
            jcr_unmatched = jcr_remaining.copy()
            jcr_unmatched['中科院分区'] = np.nan
            jcr_unmatched_result = jcr_unmatched[final_columns].copy()
            all_results.append(jcr_unmatched_result)
            print(f"未匹配的JCR数据: {len(jcr_unmatched_result)} 条记录")
        
        # 合并所有结果
        if all_results:
            result_df = pd.concat(all_results, ignore_index=True)
            
            # 去重和排序
            result_df = result_df.drop_duplicates()
            result_df = result_df.sort_values(['ISSN', 'EISSN'], na_position='last')
            
            return result_df
        else:
            # 如果没有任何结果，返回空的DataFrame
            return pd.DataFrame(columns=final_columns)
    
    def _merge_data_parallel(self, zky_df: pd.DataFrame, jcr_df: pd.DataFrame) -> pd.DataFrame:
        """并行数据合并方法"""
        print("使用并行数据合并...")
        
        final_columns = ['ISSN', 'EISSN', '中科院分区', '影响因子', 'JCR分区']
        
        with ThreadPoolExecutor(max_workers=self.processor_config.max_workers) as executor:
            # 并行执行ISSN和EISSN匹配
            future_issn = executor.submit(self._match_by_issn, zky_df, jcr_df)
            future_eissn = executor.submit(self._match_by_eissn, zky_df, jcr_df)
            
            # 获取结果
            issn_result, zky_after_issn, jcr_after_issn = future_issn.result()
            eissn_result, zky_after_eissn, jcr_after_eissn = future_eissn.result()
            
            # 合并匹配结果
            all_results = []
            if issn_result is not None:
                all_results.append(issn_result)
            if eissn_result is not None:
                all_results.append(eissn_result)
            
            # 处理未匹配的数据
            if len(zky_after_eissn) > 0:
                zky_unmatched = zky_after_eissn.copy()
                zky_unmatched['影响因子'] = np.nan
                zky_unmatched['JCR分区'] = np.nan
                zky_unmatched_result = zky_unmatched[final_columns].copy()
                all_results.append(zky_unmatched_result)
                print(f"未匹配的中科院数据: {len(zky_unmatched_result)} 条记录")
            
            if len(jcr_after_eissn) > 0:
                jcr_unmatched = jcr_after_eissn.copy()
                jcr_unmatched['中科院分区'] = np.nan
                jcr_unmatched_result = jcr_unmatched[final_columns].copy()
                all_results.append(jcr_unmatched_result)
                print(f"未匹配的JCR数据: {len(jcr_unmatched_result)} 条记录")
        
        # 合并所有结果
        if all_results:
            result_df = pd.concat(all_results, ignore_index=True)
            result_df = result_df.drop_duplicates()
            result_df = result_df.sort_values(['ISSN', 'EISSN'], na_position='last')
            return result_df
        else:
            return pd.DataFrame(columns=final_columns)
    
    def _match_by_issn(self, zky_df: pd.DataFrame, jcr_df: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], pd.DataFrame, pd.DataFrame]:
        """基于ISSN匹配数据"""
        zky_with_issn = zky_df[zky_df['ISSN'].notna() & (zky_df['ISSN'] != '')].copy()
        jcr_with_issn = jcr_df[jcr_df['ISSN'].notna() & (jcr_df['ISSN'] != '')].copy()
        
        if len(zky_with_issn) > 0 and len(jcr_with_issn) > 0:
            issn_merged = pd.merge(
                zky_with_issn, 
                jcr_with_issn, 
                on='ISSN', 
                how='inner',
                suffixes=('_zky', '_jcr')
            )
            
            if len(issn_merged) > 0:
                issn_merged['EISSN'] = issn_merged['EISSN_zky'].fillna(issn_merged['EISSN_jcr'])
                final_columns = ['ISSN', 'EISSN', '中科院分区', '影响因子', 'JCR分区']
                result = issn_merged[final_columns].copy()
                
                # 从剩余数据中移除已匹配的记录
                matched_issns = set(issn_merged['ISSN'].unique())
                zky_remaining = zky_df[~zky_df['ISSN'].isin(matched_issns)]
                jcr_remaining = jcr_df[~jcr_df['ISSN'].isin(matched_issns)]
                
                print(f"ISSN匹配找到 {len(result)} 条记录")
                return result, zky_remaining, jcr_remaining
        
        return None, zky_df, jcr_df
    
    def _match_by_eissn(self, zky_df: pd.DataFrame, jcr_df: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], pd.DataFrame, pd.DataFrame]:
        """基于EISSN匹配数据"""
        zky_with_eissn = zky_df[zky_df['EISSN'].notna() & (zky_df['EISSN'] != '')].copy()
        jcr_with_eissn = jcr_df[jcr_df['EISSN'].notna() & (jcr_df['EISSN'] != '')].copy()
        
        if len(zky_with_eissn) > 0 and len(jcr_with_eissn) > 0:
            eissn_merged = pd.merge(
                zky_with_eissn, 
                jcr_with_eissn, 
                on='EISSN', 
                how='inner',
                suffixes=('_zky', '_jcr')
            )
            
            if len(eissn_merged) > 0:
                eissn_merged['ISSN'] = eissn_merged['ISSN_zky'].fillna(eissn_merged['ISSN_jcr'])
                final_columns = ['ISSN', 'EISSN', '中科院分区', '影响因子', 'JCR分区']
                result = eissn_merged[final_columns].copy()
                
                # 从剩余数据中移除已匹配的记录
                matched_eissns = set(eissn_merged['EISSN'].unique())
                zky_remaining = zky_df[~zky_df['EISSN'].isin(matched_eissns)]
                jcr_remaining = jcr_df[~jcr_df['EISSN'].isin(matched_eissns)]
                
                print(f"EISSN匹配找到 {len(result)} 条记录")
                return result, zky_remaining, jcr_remaining
        
        return None, zky_df, jcr_df
    
    def generate_statistics(self, df: pd.DataFrame):
        """
        生成数据统计信息
        
        Args:
            df: 合并后的数据表
        """
        print("\n=== 数据统计 ===")
        print(f"总记录数: {len(df)}")
        print(f"有ISSN的记录: {df['ISSN'].notna().sum()}")
        print(f"有EISSN的记录: {df['EISSN'].notna().sum()}")
        print(f"有中科院分区的记录: {df['中科院分区'].notna().sum()}")
        print(f"有影响因子的记录: {df['影响因子'].notna().sum()}")
        print(f"有JCR分区的记录: {df['JCR分区'].notna().sum()}")
        print(f"同时有中科院分区和JCR数据的记录: {(df['中科院分区'].notna() & df['影响因子'].notna()).sum()}")
        
        # 中科院分区分布
        if df['中科院分区'].notna().sum() > 0:
            print("\n中科院分区分布:")
            print(df['中科院分区'].value_counts().sort_index())
        
        # JCR分区分布
        if df['JCR分区'].notna().sum() > 0:
            print("\nJCR分区分布:")
            print(df['JCR分区'].value_counts())
    
    def save_result(self, df: pd.DataFrame, output_file: str = None, description: str = ""):
        """
        保存处理结果
        
        Args:
            df: 要保存的数据表
            output_file: 输出文件名，如果为None则生成带时间戳的文件名
            description: 文件描述，用于打印信息
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"processed_data_{timestamp}.csv"
        
        output_path = os.path.join(self.data_dir, output_file)
        
        # 如果文件已存在且被占用，生成新的文件名
        counter = 1
        original_path = output_path
        while True:
            try:
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
                print(f"\n{description}已保存到: {output_path}")
                break
            except PermissionError:
                # 文件被占用，尝试新文件名
                name, ext = os.path.splitext(original_path)
                output_path = f"{name}_{counter}{ext}"
                counter += 1
                if counter > 10:  # 避免无限循环
                    raise Exception("无法创建输出文件，请检查文件权限")
    
    def process_separate(self, zky_output: str = "processed_zky_data.csv", jcr_output: str = "processed_jcr_data.csv") -> tuple:
        """
        执行分离的数据处理流程，生成两个独立的数据表
        
        Args:
            zky_output: 中科院数据输出文件名
            jcr_output: JCR数据输出文件名
            
        Returns:
            tuple: (中科院处理后数据, JCR处理后数据)
        """
        print("开始分离式期刊数据处理...")
        
        try:
            # 处理中科院数据
            print("\n" + "="*50)
            zky_data = self.process_zky_data()
            
            # 生成中科院数据统计
            print("\n=== 中科院数据统计 ===")
            print(f"总记录数: {len(zky_data)}")
            print(f"有ISSN的记录: {zky_data['ISSN'].notna().sum()}")
            print(f"有EISSN的记录: {zky_data['EISSN'].notna().sum()}")
            print(f"有中科院分区的记录: {zky_data['中科院分区'].notna().sum()}")
            
            if zky_data['中科院分区'].notna().sum() > 0:
                print("\n中科院分区分布:")
                print(zky_data['中科院分区'].value_counts().sort_index())
            
            # 保存中科院数据
            self.save_result(zky_data, zky_output, "中科院处理数据")
            
            print("\n=== 中科院数据预览（前10行）===")
            print(zky_data.head(10).to_string(index=False))
            
            # 处理JCR数据
            print("\n" + "="*50)
            jcr_data = self.process_jcr_data()
            
            # 生成JCR数据统计
            print("\n=== JCR数据统计 ===")
            print(f"总记录数: {len(jcr_data)}")
            print(f"有ISSN的记录: {jcr_data['ISSN'].notna().sum()}")
            print(f"有EISSN的记录: {jcr_data['EISSN'].notna().sum()}")
            print(f"有影响因子的记录: {jcr_data['影响因子'].notna().sum()}")
            print(f"有JCR分区的记录: {jcr_data['JCR分区'].notna().sum()}")
            
            if jcr_data['JCR分区'].notna().sum() > 0:
                print("\nJCR分区分布:")
                print(jcr_data['JCR分区'].value_counts())
            
            if jcr_data['影响因子'].notna().sum() > 0:
                print(f"\n影响因子统计:")
                print(f"最小值: {jcr_data['影响因子'].min():.3f}")
                print(f"最大值: {jcr_data['影响因子'].max():.3f}")
                print(f"平均值: {jcr_data['影响因子'].mean():.3f}")
                print(f"中位数: {jcr_data['影响因子'].median():.3f}")
            
            # 保存JCR数据
            self.save_result(jcr_data, jcr_output, "JCR处理数据")
            
            print("\n=== JCR数据预览（前10行）===")
            print(jcr_data.head(10).to_string(index=False))
            
            print("\n" + "="*60)
            print("分离式数据处理完成！")
            print(f"中科院数据文件：data/{zky_output}")
            print(f"JCR数据文件：data/{jcr_output}")
            print("="*60)
            
            return zky_data, jcr_data
            
        except Exception as e:
            print(f"数据处理过程中出现错误: {e}")
            raise
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        stats = self.performance_stats.copy()
        
        # 添加缓存统计
        if hasattr(self, 'data_cache'):
            stats['cache_stats'] = self.data_cache.get_stats()
        
        # 添加配置信息
        stats['config'] = {
            'parallel_enabled': self.processor_config.enable_parallel,
            'caching_enabled': self.processor_config.enable_caching,
            'max_workers': self.processor_config.max_workers,
            'cache_size': self.processor_config.cache_size,
            'chunk_size': self.processor_config.chunk_size
        }
        
        return stats
    
    def print_performance_summary(self):
        """打印性能摘要"""
        stats = self.get_performance_stats()
        
        print("\nData Processor 性能摘要:")
        print(f"   总处理时间: {stats.get('total_processing_time', 0):.2f}秒")
        print(f"   中科院数据处理时间: {stats.get('zky_processing_time', 0):.2f}秒")
        print(f"   JCR数据处理时间: {stats.get('jcr_processing_time', 0):.2f}秒")
        print(f"   数据合并时间: {stats.get('merge_time', 0):.2f}秒")
        print(f"   处理记录数: {stats.get('records_processed', 0)}")
        print(f"   并行处理: {'启用' if stats['config']['parallel_enabled'] else '禁用'}")
        print(f"   缓存系统: {'启用' if stats['config']['caching_enabled'] else '禁用'}")
        
        if 'cache_stats' in stats:
            cache_stats = stats['cache_stats']
            print(f"   缓存命中率: {cache_stats.get('hit_rate', 0):.1%}")
            print(f"   缓存使用: {cache_stats.get('current_size', 0)}/{cache_stats.get('max_size', 0)}")
    
    def cleanup(self):
        """清理资源"""
        print("清理 Data Processor 资源...")
        
        # 清理缓存
        if hasattr(self, 'data_cache'):
            self.data_cache.clear()
        
        # 重置性能统计
        self.performance_stats = {
            'total_processing_time': 0,
            'zky_processing_time': 0,
            'jcr_processing_time': 0,
            'merge_time': 0,
            'memory_usage_mb': 0,
            'records_processed': 0
        }
        
        print("Data Processor 资源清理完成")


def main():
    """主函数 - ABCE优化版本"""
    start_time = time.time()
    try:
        processor = JournalDataProcessor()
        
        # 使用分离处理方法
        zky_data, jcr_data = processor.process_separate()
        
        # 更新总处理时间
        total_time = time.time() - start_time
        processor.performance_stats['total_processing_time'] = total_time
        processor.performance_stats['records_processed'] = len(zky_data) + len(jcr_data)
        
        # 显示性能摘要
        processor.print_performance_summary()
        
    except Exception as e:
        print(f"程序执行失败: {e}")
    finally:
        # 清理资源
        if 'processor' in locals():
            processor.cleanup()


if __name__ == "__main__":
    main()