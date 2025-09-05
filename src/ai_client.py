#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI接口交互程序 v2.0
支持OpenAI和Gemini两种接口，自定义端点URL，动态获取模型和参数
优化特性：增强连接管理、智能缓存系统、重试机制、性能监控
"""

import requests
import json
import os
import sys
import time
import asyncio
import aiohttp
import hashlib
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import argparse
import yaml
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from urllib.parse import urljoin

# 设置标准输出编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Windows控制台编码设置
if os.name == 'nt':  # Windows
    try:
        # 设置控制台代码页为UTF-8
        os.system('chcp 65001 >nul')
    except:
        pass


def safe_print(text: str, end: str = '\n', flush: bool = False):
    """安全的打印函数，处理编码问题"""
    try:
        print(text, end=end, flush=flush)
    except UnicodeEncodeError:
        # 如果编码失败，替换无法显示的字符
        try:
            safe_text = text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            print(safe_text, end=end, flush=flush)
        except:
            # 最后的备选方案，只输出ASCII字符
            ascii_text = text.encode('ascii', errors='replace').decode('ascii')
            print(ascii_text, end=end, flush=flush)


class AICacheManager:
    """AI响应缓存管理器"""
    def __init__(self, cache_size: int = 1000, ttl: int = 3600):
        self.cache_size = cache_size
        self.ttl = ttl
        self.cache = {}
        self.access_times = {}
        self.lock = threading.Lock()
    
    def _generate_cache_key(self, messages: List['ChatMessage'], model_id: str, parameters: Dict = None) -> str:
        """生成缓存键"""
        content = f"{model_id}:" + "|".join([f"{msg.role}:{msg.content}" for msg in messages])
        if parameters:
            content += ":" + json.dumps(parameters, sort_keys=True)
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get_cached_response(self, messages: List['ChatMessage'], model_id: str, parameters: Dict = None) -> Optional[str]:
        """获取缓存的响应"""
        cache_key = self._generate_cache_key(messages, model_id, parameters)
        
        with self.lock:
            if cache_key in self.cache:
                cache_data = self.cache[cache_key]
                if time.time() - cache_data['timestamp'] < self.ttl:
                    self.access_times[cache_key] = time.time()
                    return cache_data['response']
                else:
                    # 清除过期缓存
                    del self.cache[cache_key]
                    if cache_key in self.access_times:
                        del self.access_times[cache_key]
        return None
    
    def cache_response(self, messages: List['ChatMessage'], model_id: str, response: str, parameters: Dict = None):
        """缓存响应"""
        cache_key = self._generate_cache_key(messages, model_id, parameters)
        
        with self.lock:
            # LRU缓存清理
            if len(self.cache) >= self.cache_size:
                oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
            
            self.cache[cache_key] = {
                'response': response,
                'timestamp': time.time(),
                'model_id': model_id,
                'parameters': parameters
            }
            self.access_times[cache_key] = time.time()
    
    def clear_cache(self):
        """清除所有缓存"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            return {
                'cache_size': len(self.cache),
                'max_cache_size': self.cache_size,
                'hit_rate': len([v for v in self.cache.values() if time.time() - v['timestamp'] < self.ttl]) / max(len(self.cache), 1)
            }


class EnhancedConnectionManager:
    """增强的连接管理器"""
    def __init__(self, max_connections: int = 100, timeout: int = 60):
        self.max_connections = max_connections
        self.timeout = timeout
        self.session = None
        self.connector = None
        self.rate_limiter = asyncio.Semaphore(10) if hasattr(asyncio, 'Semaphore') else None
        self.connection_pool = []
        self.lock = threading.Lock()
        self.request_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_latency': 0.0
        }
    
    def _create_session(self) -> requests.Session:
        """创建HTTP会话"""
        session = requests.Session()
        
        # 配置连接池
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=self.max_connections,
            pool_maxsize=self.max_connections,
            max_retries=3
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        return session
    
    def get_session(self) -> requests.Session:
        """获取HTTP会话"""
        if self.session is None:
            with self.lock:
                if self.session is None:
                    self.session = self._create_session()
        return self.session
    
    def make_request_with_retry(self, method: str, url: str, headers: Dict = None, 
                               json_data: Dict = None, max_retries: int = 3) -> Dict:
        """带重试机制的请求"""
        session = self.get_session()
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                response = session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json_data,
                    timeout=self.timeout
                )
                
                latency = time.time() - start_time
                
                # 更新统计信息
                with self.lock:
                    self.request_stats['total_requests'] += 1
                    self.request_stats['total_latency'] += latency
                    
                    if response.status_code == 200:
                        self.request_stats['successful_requests'] += 1
                    else:
                        self.request_stats['failed_requests'] += 1
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in [429, 500, 502, 503, 504]:
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 10)  # 指数退避，最多等待10秒
                        time.sleep(wait_time)
                        continue
                else:
                    response.raise_for_status()
                    
            except requests.exceptions.RequestException as e:
                with self.lock:
                    self.request_stats['total_requests'] += 1
                    self.request_stats['failed_requests'] += 1
                
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 10)
                    time.sleep(wait_time)
                    continue
                else:
                    raise ConnectionError(f"请求失败，已重试{max_retries}次: {e}")
        
        raise Exception("请求失败")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        with self.lock:
            total_requests = self.request_stats['total_requests']
            if total_requests == 0:
                return self.request_stats.copy()
            
            return {
                'total_requests': total_requests,
                'successful_requests': self.request_stats['successful_requests'],
                'failed_requests': self.request_stats['failed_requests'],
                'success_rate': self.request_stats['successful_requests'] / total_requests,
                'average_latency': self.request_stats['total_latency'] / total_requests
            }
    
    def close(self):
        """关闭连接"""
        if self.session:
            self.session.close()
            self.session = None


@dataclass
class AIConfig:
    """AI配置类"""
    name: str
    api_type: str  # 'openai' 或 'gemini'
    base_url: str
    api_key: str
    default_model: str = ""
    timeout: int = 60


@dataclass  
class ModelInfo:
    """模型信息类"""
    id: str
    name: str
    description: str = ""
    context_length: int = 0
    supports_streaming: bool = True


@dataclass
class ChatMessage:
    """聊天消息类"""
    role: str  # 'user', 'assistant', 'system'
    content: str


class BaseAIAdapter:
    """AI适配器基类 v2.0"""
    
    def __init__(self, config: AIConfig, enable_cache: bool = True, enable_retry: bool = True):
        self.config = config
        self.enable_cache = enable_cache
        self.enable_retry = enable_retry
        
        # 增强的连接管理
        self.connection_manager = EnhancedConnectionManager(
            max_connections=50,
            timeout=config.timeout
        )
        
        # 智能缓存系统
        self.cache_manager = AICacheManager(cache_size=500, ttl=1800) if enable_cache else None
        
        # 基础会话配置
        self.session = self.connection_manager.get_session()
        self.session.headers.update({
            'Authorization': f'Bearer {config.api_key}',
            'Content-Type': 'application/json'
        })
        
        # 性能统计
        self.performance_stats = {
            'total_calls': 0,
            'cache_hits': 0,
            'total_tokens': 0,
            'total_latency': 0.0
        }
    
    def _check_cache(self, messages: List[ChatMessage], model_id: str, parameters: Dict = None) -> Optional[str]:
        """检查缓存"""
        if not self.cache_manager:
            return None
        
        cached_response = self.cache_manager.get_cached_response(messages, model_id, parameters)
        if cached_response:
            self.performance_stats['cache_hits'] += 1
            return cached_response
        return None
    
    def _cache_response(self, messages: List[ChatMessage], model_id: str, response: str, parameters: Dict = None):
        """缓存响应"""
        if self.cache_manager:
            self.cache_manager.cache_response(messages, model_id, response, parameters)
    
    def _update_performance_stats(self, start_time: float, tokens: int = 0, cache_hit: bool = False):
        """更新性能统计"""
        latency = time.time() - start_time
        self.performance_stats['total_calls'] += 1
        self.performance_stats['total_latency'] += latency
        if tokens > 0:
            self.performance_stats['total_tokens'] += tokens
    
    def test_connection(self) -> Dict[str, Any]:
        """测试API连接"""
        raise NotImplementedError
    
    def get_available_models(self) -> List[ModelInfo]:
        """获取可用模型列表"""
        raise NotImplementedError
    
    def get_model_parameters(self, model_id: str) -> Dict[str, Any]:
        """获取模型可调节参数"""
        raise NotImplementedError
    
    def send_message(self, messages: List[ChatMessage], model_id: str, 
                    parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """发送消息并获取响应"""
        raise NotImplementedError
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取适配器性能报告"""
        return {
            "performance_stats": self.performance_stats.copy(),
            "cache_enabled": self.cache_manager is not None,
            "retry_enabled": self.enable_retry
        }


class OpenAIAdapter(BaseAIAdapter):
    """OpenAI API适配器 v2.0"""
    
    def __init__(self, config: AIConfig, enable_cache: bool = True, enable_retry: bool = True):
        super().__init__(config, enable_cache, enable_retry)
        if not self.config.base_url.endswith('/'):
            self.config.base_url += '/'
        
        # 模型信息缓存
        self._models_cache = None
        self._models_cache_time = 0
        self._models_cache_ttl = 3600  # 1小时
    
    def test_connection(self) -> Dict[str, Any]:
        """测试OpenAI API连接"""
        try:
            # 确保认证头已设置
            if 'Authorization' not in self.session.headers:
                self.session.headers.update({
                    'Authorization': f'Bearer {self.config.api_key}',
                    'Content-Type': 'application/json'
                })
            
            if self.enable_retry:
                response = self.connection_manager.make_request_with_retry(
                    'GET',
                    f"{self.config.base_url}v1/models",
                    max_retries=2
                )
            else:
                response = self.session.get(
                    f"{self.config.base_url}v1/models",
                    timeout=10
                )
                response.raise_for_status()
                response = response.json()
            
            return {"status": "success", "message": "API连接正常"}
                
        except requests.ConnectionError as e:
            return {"status": "error", "message": f"连接失败: {e}"}
        except requests.Timeout as e:
            return {"status": "error", "message": f"连接超时: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"连接测试失败: {e}"}
    
    def get_available_models(self) -> List[ModelInfo]:
        """获取OpenAI可用模型"""
        # 检查缓存
        current_time = time.time()
        if (self._models_cache and 
            current_time - self._models_cache_time < self._models_cache_ttl):
            return self._models_cache
        
        try:
            if self.enable_retry:
                response_data = self.connection_manager.make_request_with_retry(
                    'GET',
                    f"{self.config.base_url}v1/models",
                    max_retries=2
                )
            else:
                response = self.session.get(
                    f"{self.config.base_url}v1/models",
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                response_data = response.json()
            
            # 检查响应内容
            if not response_data or 'data' not in response_data:
                models = self._get_default_models()
            else:
                models = []
                for model_data in response_data['data']:
                    model_info = ModelInfo(
                        id=model_data.get('id', ''),
                        name=model_data.get('id', ''),
                        description=f"OpenAI模型: {model_data.get('id', '')}",
                        context_length=model_data.get('context_length', 4096),
                        supports_streaming=True
                    )
                    models.append(model_info)
            
            # 缓存结果
            self._models_cache = models
            self._models_cache_time = current_time
            
            return models
            try:
                models_data = response.json()
            except json.JSONDecodeError:
                return self._get_default_models()
            
            models = []
            
            for model in models_data.get('data', []):
                model_info = ModelInfo(
                    id=model['id'],
                    name=model.get('name', model['id']),
                    description=f"Created: {model.get('created', 'Unknown')}",
                    context_length=model.get('context_length', 4096),
                    supports_streaming=True
                )
                models.append(model_info)
            
            # 按名称排序
            models.sort(key=lambda x: x.name)
            return models if models else self._get_default_models()
            
        except Exception as e:
            print(f"获取OpenAI模型列表失败: {e}")
            return self._get_default_models()
    
    def _get_default_models(self) -> List[ModelInfo]:
        """返回默认模型列表"""
        return [
            ModelInfo("gpt-4", "GPT-4", "GPT-4模型", 8192),
            ModelInfo("gpt-3.5-turbo", "GPT-3.5 Turbo", "GPT-3.5 Turbo模型", 4096),
            ModelInfo("gpt-4-turbo-preview", "GPT-4 Turbo", "GPT-4 Turbo预览版", 128000)
        ]
    
    def get_model_parameters(self, model_id: str) -> Dict[str, Any]:
        """获取OpenAI模型参数配置"""
        return {
            "temperature": {
                "type": "float", 
                "min": 0.0, 
                "max": 2.0, 
                "default": 0.1, 
                "description": "控制输出随机性，0最确定，2最随机"
            },
            "top_p": {
                "type": "float",
                "min": 0.0,
                "max": 1.0, 
                "default": 1.0,
                "description": "核采样参数，控制候选词概率累积阈值"
            },
            "max_tokens": {
                "type": "int",
                "min": 1,
                "max": 32768,
                "default": None,
                "description": "最大输出token数，None表示不限制（使用模型最大值）"
            },
            "frequency_penalty": {
                "type": "float",
                "min": -2.0,
                "max": 2.0,
                "default": 0.0,
                "description": "频率惩罚，降低重复内容"
            },
            "presence_penalty": {
                "type": "float", 
                "min": -2.0,
                "max": 2.0,
                "default": 0.0,
                "description": "存在惩罚，鼓励谈论新话题"
            },
            "stream": {
                "type": "bool",
                "default": False,
                "description": "是否流式返回结果"
            }
        }
    
    def send_message(self, messages: List[ChatMessage], model_id: str, 
                    parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """发送OpenAI消息"""
        start_time = time.time()
        
        if parameters is None:
            parameters = {}
        
        # 检查缓存
        cache_hit = False
        cached_response = self._check_cache(messages, model_id, parameters)
        if cached_response:
            cache_hit = True
            # 构造缓存的响应格式
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": cached_response
                    }
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                },
                "cached": True
            }
        
        # 过滤None值的参数，特别是max_tokens=None时不发送该参数
        filtered_params = {k: v for k, v in parameters.items() if v is not None}
        
        # 构建请求数据
        request_data = {
            "model": model_id,
            "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
            **filtered_params
        }
        
        # 检查是否使用流式输出
        if parameters.get("stream", True):
            response = self._send_stream_message(request_data)
        else:
            response = self._send_regular_message(request_data)
        
        # 缓存成功的响应
        if not response.get('error') and 'choices' in response:
            content = response['choices'][0]['message']['content']
            self._cache_response(messages, model_id, content, parameters)
        
        # 更新性能统计
        tokens = response.get('usage', {}).get('total_tokens', 0)
        self._update_performance_stats(start_time, tokens, cache_hit)
        
        return response
    
    def _send_regular_message(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """发送常规非流式消息"""
        try:
            if self.enable_retry:
                response = self.connection_manager.make_request_with_retry(
                    'POST',
                    f"{self.config.base_url}v1/chat/completions",
                    json_data=request_data,
                    max_retries=3
                )
            else:
                response = self.session.post(
                    f"{self.config.base_url}v1/chat/completions",
                    json=request_data,
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                response = response.json()
            
            if not response:
                return {"error": "服务器返回空响应"}
            
            return response
            
        except requests.RequestException as e:
            return {"error": f"OpenAI请求失败: {e}"}
    
    def _send_stream_message(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """发送流式消息"""
        try:
            response = self.session.post(
                f"{self.config.base_url}v1/chat/completions",
                json=request_data,
                stream=True,
                timeout=self.config.timeout
            )
            
            response.raise_for_status()
            
            # 收集流式响应
            content_parts = []
            
            # 设置响应编码
            response.encoding = 'utf-8'
            
            for line in response.iter_lines(decode_unicode=False):
                if line:
                    try:
                        # 手动解码为UTF-8
                        line_str = line.decode('utf-8', errors='ignore').strip()
                        
                        if line_str.startswith('data: '):
                            data = line_str[6:].strip()
                            
                            if data == '[DONE]':
                                break
                            
                            try:
                                chunk = json.loads(data)
                                choices = chunk.get('choices', [])
                                if choices:
                                    delta = choices[0].get('delta', {})
                                    if 'content' in delta:
                                        content = delta['content']
                                        if content:  # 确保内容不为空
                                            content_parts.append(content)
                                            # 使用安全打印函数实时输出
                                            safe_print(content, end='', flush=True)
                            
                            except json.JSONDecodeError:
                                continue
                    except UnicodeDecodeError:
                        continue
            
            # 返回完整响应格式
            full_content = ''.join(content_parts)
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": full_content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {"stream": True}
            }
            
        except requests.RequestException as e:
            return {"error": f"OpenAI流式请求失败: {e}"}
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取OpenAI适配器性能报告"""
        base_report = super().get_performance_report()
        openai_report = {
            "adapter_type": "OpenAI",
            "model": self.config.default_model,
            "base_url": self.config.base_url,
            "connection_stats": self.connection_manager.get_performance_stats(),
            "cache_stats": self.cache_manager.get_cache_stats() if self.cache_manager else {}
        }
        return {**base_report, **openai_report}


class GeminiAdapter(BaseAIAdapter):
    """Google Gemini API适配器 - A/B优化版"""
    
    def __init__(self, config: AIConfig, enable_cache: bool = True, enable_retry: bool = True):
        super().__init__(config, enable_cache, enable_retry)
        # Gemini API使用查询参数认证，不在头部中包含API key
        self.session.headers.pop('Authorization', None)
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
        if not self.config.base_url.endswith('/'):
            self.config.base_url += '/'
            
        # 模型信息缓存
        self._models_cache = None
        self._models_cache_time = 0
        self._models_cache_ttl = 3600  # 1小时
    
    def test_connection(self) -> Dict[str, Any]:
        """测试Gemini API连接 - 增强连接管理"""
        try:
            # Gemini API使用查询参数认证
            import urllib.parse
            api_url = f"{self.config.base_url}v1beta/models?key={urllib.parse.quote(self.config.api_key)}"
            
            if self.enable_retry:
                response_data = self.connection_manager.make_request_with_retry(
                    'GET',
                    api_url,
                    max_retries=2
                )
            else:
                response = self.session.get(
                    api_url,
                    timeout=10
                )
                response.raise_for_status()
                response_data = response.json()
            
            return {"status": "success", "message": "Gemini API连接正常"}
                
        except requests.ConnectionError as e:
            return {"status": "error", "message": f"连接失败: {e}"}
        except requests.Timeout as e:
            return {"status": "error", "message": f"连接超时: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"连接测试失败: {e}"}
    
    def get_available_models(self) -> List[ModelInfo]:
        """获取Gemini可用模型 - 集成缓存管理"""
        # 检查缓存
        current_time = time.time()
        if (self._models_cache and 
            current_time - self._models_cache_time < self._models_cache_ttl):
            return self._models_cache
        
        try:
            # 使用增强连接管理
            if self.enable_retry:
                models_data = self.connection_manager.make_request_with_retry(
                    'GET',
                    f"{self.config.base_url}v1beta/models",
                    max_retries=2
                )
            else:
                response = self.session.get(
                    f"{self.config.base_url}v1beta/models",
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                models_data = response.json()
            
            models = []
            
            for model in models_data.get('models', []):
                # 只获取生成模型
                if 'generateContent' in model.get('supportedGenerationMethods', []):
                    model_info = ModelInfo(
                        id=model['name'].split('/')[-1],  # 提取模型名
                        name=model.get('displayName', model['name']),
                        description=model.get('description', ''),
                        context_length=model.get('inputTokenLimit', 0),
                        supports_streaming=True
                    )
                    models.append(model_info)
            
            # 缓存结果
            self._models_cache = models
            self._models_cache_time = current_time
            
            return models
            
        except Exception as e:
            print(f"获取Gemini模型列表失败: {e}")
            # 返回常见的Gemini模型作为备选
            return [
                ModelInfo("gemini-2.5-pro", "Gemini 2.5 Pro", "Gemini 2.5 Pro模型", 30720),
                ModelInfo("gemini-2.5-flash", "Gemini 2.5 Flash", "Gemini 2.5 Flash模型", 16384),
                ModelInfo("gemini-pro", "Gemini Pro", "Gemini Pro模型", 30720),
                ModelInfo("gemini-pro-vision", "Gemini Pro Vision", "支持图像的Gemini模型", 16384)
            ]
    
    def get_model_parameters(self, model_id: str) -> Dict[str, Any]:
        """获取Gemini模型参数配置"""
        return {
            "temperature": {
                "type": "float",
                "min": 0.0,
                "max": 2.0, 
                "default": 0.1,
                "description": "控制输出随机性，0最确定，2最随机"
            },
            "topK": {
                "type": "int",
                "min": 1,
                "max": 40,
                "default": None,
                "description": "Top-K采样参数，抽样时要考虑的令牌数量上限"
            },
            "topP": {
                "type": "float",
                "min": 0.0,
                "max": 1.0,
                "default": 0.95, 
                "description": "Top-P核采样参数"
            },
            "maxOutputTokens": {
                "type": "int",
                "min": 1,
                "max": 8192,
                "default": None,
                "description": "最大输出token数，None表示不限制"
            },
            "candidateCount": {
                "type": "int",
                "min": 1,
                "max": 8,
                "default": 1,
                "description": "要返回的生成响应数量"
            },
            "stopSequences": {
                "type": "list",
                "default": [],
                "description": "停止生成的字符序列集（最多5个）"
            },
            "seed": {
                "type": "int",
                "min": 0,
                "max": 2147483647,
                "default": None,
                "description": "解码中使用的种子，用于可重现性"
            },
            "responseMimeType": {
                "type": "str",
                "default": "text/plain",
                "description": "生成的候选文本的MIME类型（text/plain, application/json, text/x.enum）"
            }
        }
    
    def send_message(self, messages: List[ChatMessage], model_id: str,
                    parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """发送Gemini消息 - 集成缓存和连接管理"""
        start_time = time.time()
        
        if parameters is None:
            parameters = {}
        
        # 检查缓存
        cache_hit = False
        cached_response = self._check_cache(messages, model_id, parameters)
        if cached_response:
            cache_hit = True
            # 构造Gemini格式的缓存响应
            return {
                "candidates": [{
                    "content": {
                        "parts": [{"text": cached_response}],
                        "role": "model"
                    },
                    "finishReason": "STOP",
                    "index": 0
                }],
                "cached": True
            }
        
        # 过滤None值的参数，同时转换OpenAI参数到Gemini参数
        filtered_params = {}
        
        for k, v in parameters.items():
            if v is None:
                continue
                
            # 跳过stream参数，单独处理
            if k == "stream":
                continue
                
            # 转换OpenAI参数名到Gemini参数名
            if k == "max_tokens":
                filtered_params["maxOutputTokens"] = v
            elif k == "top_p":
                filtered_params["topP"] = v
            elif k == "top_k":
                filtered_params["topK"] = v
            elif k == "stop":
                # OpenAI的stop参数对应Gemini的stopSequences
                if isinstance(v, str):
                    filtered_params["stopSequences"] = [v]
                elif isinstance(v, list):
                    filtered_params["stopSequences"] = v[:5]  # 最多5个
            elif k == "frequency_penalty":
                # 尝试使用Gemini的frequencyPenalty参数
                filtered_params["frequencyPenalty"] = v
            elif k == "presence_penalty":
                # 尝试使用Gemini的presencePenalty参数  
                filtered_params["presencePenalty"] = v
            else:
                # 其他参数直接使用
                filtered_params[k] = v
        
        # 转换消息格式 - 使用标准Gemini API格式（无role字段）
        contents = []
        
        # 合并所有用户消息内容
        combined_content = ""
        for msg in messages:
            if msg.role == "system":
                # Gemini没有system role，添加到内容开头
                combined_content += f"System: {msg.content}\n\n"
            elif msg.role == "user":
                combined_content += msg.content
            elif msg.role == "assistant":
                # 如果有助手消息，需要构建对话历史格式
                # 但对于单轮对话，暂时跳过
                pass
        
        # 构建标准Gemini格式
        contents = [
            {
                "parts": [
                    {"text": combined_content.strip()}
                ]
            }
        ]
        
        # 构建请求数据
        request_data = {
            "contents": contents
        }
        
        # 添加生成配置（如果有参数）
        if filtered_params:
            request_data["generationConfig"] = filtered_params
        
        # 检查是否使用流式输出
        if parameters.get("stream", False):
            response = self._send_stream_message(request_data, model_id)
        else:
            response = self._send_regular_message(request_data, model_id)
        
        # 缓存成功的响应
        if not response.get('error') and 'candidates' in response:
            content = response['candidates'][0]['content']['parts'][0]['text']
            self._cache_response(messages, model_id, content, parameters)
        
        # 更新性能统计
        self._update_performance_stats(start_time, 0, cache_hit)
        
        return response
    
    def _send_regular_message(self, request_data: Dict[str, Any], model_id: str) -> Dict[str, Any]:
        """发送常规非流式消息 - 增强连接管理"""
        try:
            # 使用官方Gemini API格式，添加查询参数
            import urllib.parse
            api_url = f"{self.config.base_url}v1beta/models/{model_id}:generateContent?key={urllib.parse.quote(self.config.api_key)}"
            
            if self.enable_retry:
                response = self.connection_manager.make_request_with_retry(
                    'POST',
                    api_url,
                    json_data=request_data,
                    max_retries=3
                )
            else:
                response = self.session.post(
                    api_url,
                    json=request_data,
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                response = response.json()
            
            if not response:
                return {"error": "服务器返回空响应"}
            
            return response
            
        except requests.RequestException as e:
            return {"error": f"Gemini请求失败: {e}"}
    
    def _send_stream_message(self, request_data: Dict[str, Any], model_id: str) -> Dict[str, Any]:
        """发送流式消息"""
        try:
            # 使用官方Gemini API格式，添加查询参数
            import urllib.parse
            api_url = f"{self.config.base_url}v1beta/models/{model_id}:streamGenerateContent?alt=sse&key={urllib.parse.quote(self.config.api_key)}"
            
            response = self.session.post(
                api_url,
                json=request_data,
                stream=True,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            # 收集流式响应
            content_parts = []
            
            # 设置响应编码
            response.encoding = 'utf-8'
            
            for line in response.iter_lines(decode_unicode=False):
                if line:
                    try:
                        # 手动解码为UTF-8
                        line_str = line.decode('utf-8', errors='ignore').strip()
                        
                        # 官方Gemini API返回直接的JSON，没有data:前缀
                        if line_str:
                            try:
                                chunk = json.loads(line_str)
                                
                                # 提取内容
                                candidates = chunk.get('candidates', [])
                                if candidates:
                                    content = candidates[0].get('content', {})
                                    parts = content.get('parts', [])
                                    if parts and 'text' in parts[0]:
                                        text = parts[0]['text']
                                        if text:  # 确保内容不为空
                                            content_parts.append(text)
                                            # 使用安全打印函数实时输出
                                            safe_print(text, end='', flush=True)
                            
                            except json.JSONDecodeError:
                                continue
                    except UnicodeDecodeError:
                        continue
            
            # 返回完整响应格式（模拟非流式响应格式）
            full_content = ''.join(content_parts)
            return {
                "candidates": [{
                    "content": {
                        "parts": [{"text": full_content}],
                        "role": "model"
                    },
                    "finishReason": "STOP",
                    "index": 0
                }]
            }
            
        except requests.RequestException as e:
            return {"error": f"Gemini流式请求失败: {e}"}
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取Gemini适配器性能报告"""
        base_report = super().get_performance_report()
        gemini_report = {
            "adapter_type": "Gemini",
            "model": self.config.default_model,
            "client_initialized": self.session is not None,
            "connection_stats": self.connection_manager.get_performance_stats(),
            "cache_stats": self.cache_manager.get_cache_stats() if self.cache_manager else {}
        }
        return {**base_report, **gemini_report}


class ConfigManager:
    """配置管理器 - 支持新的多服务配置格式"""
    
    _services_displayed = False  # 全局标志，防止重复显示服务列表
    
    def __init__(self, config_file: str = "ai_config.yaml"):
        self.config_file = config_file
        self.configs = {}
        self.default_service = None
        self.settings = {}
        self.load_config()
        
        # 只在主线程中第一次初始化时显示服务列表
        if not ConfigManager._services_displayed and threading.current_thread() is threading.main_thread():
            self._show_loaded_services()
            ConfigManager._services_displayed = True
    
    def load_config(self):
        """加载配置文件 - 支持新格式和兼容旧格式"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                
                # 检查是否为新的多服务配置格式
                if 'ai_services' in data:
                    # 新格式：多服务配置
                    self._load_multi_service_config(data)
                else:
                    # 兼容旧格式：直接服务配置
                    self._load_legacy_config(data)
                    
            except Exception as e:
                print(f"加载配置文件失败: {e}")
    
    def _load_multi_service_config(self, data):
        """加载新的多服务配置格式"""
        services = data.get('ai_services', {})
        self.default_service = data.get('default_service', 'ai_wave')
        self.settings = data.get('settings', {
            'auto_retry': True,
            'max_retries': 3,
            'show_service_status': True,
            'allow_service_switch': True
        })
        
        # 加载所有服务配置
        for service_id, service_data in services.items():
            try:
                # 只加载状态为active或testing的服务
                status = service_data.get('status', 'inactive')
                if status in ['active', 'testing']:
                    # 创建AIConfig对象，使用service_id作为name
                    config = AIConfig(
                        name=service_data.get('name', service_id),
                        api_type=service_data.get('api_type', 'openai'),
                        base_url=service_data.get('base_url', ''),
                        api_key=service_data.get('api_key', ''),
                        default_model=service_data.get('default_model', ''),
                        timeout=service_data.get('timeout', 60)
                    )
                    self.configs[service_id] = config
                    
                    # 如果是默认服务或第一个激活的服务，设置为当前默认
                    if service_id == self.default_service or not hasattr(self, '_default_set'):
                        self.default_service = service_id
                        self._default_set = True
                        
            except Exception as e:
                print(f"加载服务配置 '{service_id}' 失败: {e}")
        
        # 已在__init__中统一显示服务状态，此处移除重复显示
        pass
    
    def _load_legacy_config(self, data):
        """加载旧格式配置（向后兼容）"""
        print("检测到旧格式配置文件，建议升级到新的多服务格式")
        
        for name, config_data in data.items():
            try:
                self.configs[name] = AIConfig(**config_data)
                if not self.default_service:
                    self.default_service = name
            except Exception as e:
                print(f"加载配置 '{name}' 失败: {e}")
    
    def _show_loaded_services(self):
        """显示已加载的服务状态"""
        print("\n[OK] 已加载的AI服务:")
        for service_id, config in self.configs.items():
            status_indicator = "[TARGET]" if service_id == self.default_service else "[ ]"
            print(f"  {status_indicator} {config.name} ({config.api_type}) - {config.base_url}")
        
        if self.default_service:
            default_config = self.configs.get(self.default_service)
            if default_config:
                print(f"\n[TARGET] 默认服务: {default_config.name}")
    
    def get_default_config(self) -> Optional[AIConfig]:
        """获取默认配置"""
        if self.default_service and self.default_service in self.configs:
            return self.configs[self.default_service]
        
        # 如果没有默认配置，返回第一个可用配置
        if self.configs:
            return next(iter(self.configs.values()))
        
        return None
    
    def get_active_configs(self) -> Dict[str, AIConfig]:
        """获取所有激活的配置"""
        return self.configs.copy()
    
    def switch_default_service(self, service_id: str) -> bool:
        """切换默认服务"""
        if service_id in self.configs:
            self.default_service = service_id
            print(f"默认服务已切换到: {self.configs[service_id].name}")
            return True
        else:
            print(f"服务 '{service_id}' 不存在或未激活")
            return False
    
    def auto_retry_enabled(self) -> bool:
        """检查是否启用自动重试"""
        return self.settings.get('auto_retry', True)
    
    def get_max_retries(self) -> int:
        """获取最大重试次数"""
        return self.settings.get('max_retries', 3)
    
    def get_fallback_configs(self) -> List[AIConfig]:
        """获取备用配置列表（除了当前默认服务外的其他服务）"""
        fallback_configs = []
        for service_id, config in self.configs.items():
            if service_id != self.default_service:
                fallback_configs.append(config)
        return fallback_configs
    
    def save_config(self):
        """保存配置文件"""
        try:
            data = {name: asdict(config) for name, config in self.configs.items()}
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
                
            print(f"配置已保存到 {self.config_file}")
            
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def add_config(self, config: AIConfig):
        """添加配置"""
        self.configs[config.name] = config
        self.save_config()
    
    def get_config(self, name: str) -> Optional[AIConfig]:
        """获取配置"""
        return self.configs.get(name)
    
    def list_configs(self) -> List[str]:
        """列出所有配置名称"""
        return list(self.configs.keys())


class AIClient:
    """AI客户端主类 v2.0 - 支持多配置和自动重试"""
    
    def __init__(self, enable_cache: bool = True, enable_retry: bool = True):
        self.config_manager = ConfigManager()
        self.current_adapter = None
        self.conversation_history = []
        self.enable_cache = enable_cache
        self.enable_retry = enable_retry
        
        # 性能统计
        self.session_stats = {
            'total_sessions': 0,
            'total_messages': 0,
            'cache_hits': 0,
            'start_time': time.time()
        }
    
    def create_adapter(self, config: AIConfig) -> BaseAIAdapter:
        """创建AI适配器"""
        if config.api_type.lower() == 'openai':
            adapter = OpenAIAdapter(config, self.enable_cache, self.enable_retry)
            self.current_adapter = adapter
            return adapter
        elif config.api_type.lower() == 'gemini':
            adapter = GeminiAdapter(config, self.enable_cache, self.enable_retry)
            self.current_adapter = adapter
            return adapter
        else:
            raise ValueError(f"不支持的AI类型: {config.api_type}")
    
    def setup_new_config(self):
        """交互式设置新配置"""
        print("\n=== 设置新的AI配置 ===")
        
        name = input("配置名称: ").strip()
        if not name:
            print("配置名称不能为空")
            return
        
        print("支持的AI类型: openai, gemini")
        api_type = input("AI类型: ").strip().lower()
        if api_type not in ['openai', 'gemini']:
            print("不支持的AI类型")
            return
        
        base_url = input("API端点URL: ").strip()
        if not base_url:
            print("API端点URL不能为空")
            return
        
        api_key = input("API密钥: ").strip()
        if not api_key:
            print("API密钥不能为空")
            return
        
        timeout = input("超时时间(秒) [60]: ").strip()
        timeout = int(timeout) if timeout.isdigit() else 60
        
        config = AIConfig(
            name=name,
            api_type=api_type,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout
        )
        
        self.config_manager.add_config(config)
        print(f"配置 '{name}' 已保存")
    
    def select_config(self) -> Optional[AIConfig]:
        """选择AI配置 - 支持多配置选择"""
        # 首先尝试使用默认配置
        default_config = self.config_manager.get_default_config()
        if default_config:
            print(f"\n[TARGET] 使用默认AI服务: {default_config.name}")
            return default_config
        
        # 如果没有默认配置，显示选择菜单
        configs = self.config_manager.get_active_configs()
        
        if not configs:
            print("未找到任何激活的配置，请先配置AI服务")
            return None
        
        if len(configs) == 1:
            # 只有一个配置，直接使用
            config = next(iter(configs.values()))
            print(f"使用唯一可用配置: {config.name}")
            return config
        
        # 多个配置，让用户选择
        print("\n可用配置:")
        config_list = list(configs.items())
        for i, (service_id, config) in enumerate(config_list, 1):
            print(f"{i}. {config.name} ({config.api_type}) - {config.base_url}")
        
        try:
            choice = int(input("\n选择配置 (序号): ").strip())
            if 1 <= choice <= len(config_list):
                return config_list[choice - 1][1]
        except ValueError:
            pass
        
        print("无效选择")
        return None
    
    def send_message_with_retry(self, messages: List[ChatMessage], model_id: str, 
                               parameters: Dict[str, Any] = None, 
                               adapter: BaseAIAdapter = None) -> Dict[str, Any]:
        """发送消息并支持自动重试功能"""
        self.session_stats['total_messages'] += 1
        
        if not self.config_manager.auto_retry_enabled() or not adapter:
            # 如果未启用自动重试或没有适配器，直接发送
            return adapter.send_message(messages, model_id, parameters) if adapter else {"error": "No adapter"}
        
        # 首先尝试当前适配器
        response = adapter.send_message(messages, model_id, parameters)
        
        # 如果成功，直接返回
        if 'error' not in response:
            # 检查是否是缓存命中
            if response.get('cached'):
                self.session_stats['cache_hits'] += 1
            return response
        
        print(f"\n当前服务出现错误: {response.get('error', 'Unknown error')}")
        
        # 尝试备用配置
        fallback_configs = self.config_manager.get_fallback_configs()
        max_retries = self.config_manager.get_max_retries()
        
        for i, fallback_config in enumerate(fallback_configs[:max_retries], 1):
            print(f"尝试备用服务 ({i}/{min(len(fallback_configs), max_retries)}): {fallback_config.name}")
            
            try:
                fallback_adapter = self.create_adapter(fallback_config)
                
                # 测试连接
                test_result = fallback_adapter.test_connection()
                if test_result["status"] != "success":
                    print(f"备用服务连接失败: {test_result['message']}")
                    continue
                
                # 尝试发送消息
                fallback_response = fallback_adapter.send_message(messages, model_id, parameters)
                
                if 'error' not in fallback_response:
                    print(f"备用服务响应成功: {fallback_config.name}")
                    # 可选：切换默认服务
                    if self.config_manager.settings.get('allow_service_switch', True):
                        service_id = None
                        for sid, config in self.config_manager.configs.items():
                            if config == fallback_config:
                                service_id = sid
                                break
                        if service_id:
                            self.config_manager.switch_default_service(service_id)
                    
                    return fallback_response
                else:
                    print(f"备用服务也出现错误: {fallback_response.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"备用服务创建失败: {e}")
                continue
        
        # 所有服务都失败
        print(f"\n所有AI服务都不可用，请检查网络连接和配置")
        return {"error": "所有AI服务都不可用"}
    
    def select_model(self, adapter: BaseAIAdapter) -> Optional[str]:
        """选择模型"""
        print("\n正在获取可用模型...")
        models = adapter.get_available_models()
        
        if not models:
            print("未找到可用模型")
            return None
        
        # 如果配置中有默认模型，优先使用
        if hasattr(adapter.config, 'default_model') and adapter.config.default_model:
            for model in models:
                if model.id == adapter.config.default_model:
                    print(f"[TARGET] 使用默认模型: {model.name} ({model.id})")
                    return model.id
        
        print("\n可用模型:")
        for i, model in enumerate(models, 1):
            print(f"{i}. {model.name} ({model.id})")
            if model.description:
                print(f"   {model.description}")
            if model.context_length:
                print(f"   上下文长度: {model.context_length}")
        
        try:
            choice = int(input("\n选择模型 (序号): ").strip())
            if 1 <= choice <= len(models):
                return models[choice - 1].id
        except ValueError:
            pass
        
        print("无效选择")
        return None
    
    def configure_parameters(self, adapter: BaseAIAdapter, model_id: str) -> Dict[str, Any]:
        """配置模型参数"""
        parameters = adapter.get_model_parameters(model_id)
        config = {
            "stream": True,  # 默认启用流式输出
            "max_tokens": None  # 默认不限制token数量
        }
        
        print(f"\n=== 配置 {model_id} 参数 ===")
        print("直接回车使用默认值")
        
        for param_name, param_info in parameters.items():
            description = param_info.get('description', '')
            default_value = param_info.get('default')
            param_type = param_info.get('type', 'str')
            
            # 对于stream参数，强制设为True，不询问用户
            if param_name == 'stream':
                config[param_name] = True
                print(f"\n{param_name}: {description}")
                print(f"固定值: True (强制启用流式输出)")
                continue
            
            print(f"\n{param_name}: {description}")
            print(f"默认值: {default_value}")
            
            if param_type in ['int', 'float']:
                min_val = param_info.get('min')
                max_val = param_info.get('max')
                if min_val is not None or max_val is not None:
                    range_info = f"范围: {min_val} - {max_val}"
                    print(range_info)
            
            user_input = input(f"设置 {param_name}: ").strip()
            
            if not user_input:
                if default_value is not None:
                    config[param_name] = default_value
                # 对于max_tokens，空输入保持为None（不限制）
                elif param_name == 'max_tokens':
                    config[param_name] = None
            else:
                try:
                    if param_type == 'int':
                        if user_input.lower() in ['none', 'null', '无限制', 'unlimited']:
                            config[param_name] = None
                        else:
                            config[param_name] = int(user_input)
                    elif param_type == 'float':
                        config[param_name] = float(user_input)
                    elif param_type == 'bool':
                        config[param_name] = user_input.lower() in ['true', '1', 'yes', 'y']
                    else:
                        config[param_name] = user_input
                except ValueError:
                    print(f"无效值，使用默认值: {default_value}")
                    if default_value is not None:
                        config[param_name] = default_value
                    elif param_name == 'max_tokens':
                        config[param_name] = None
        
        return config
    
    def format_response(self, response: Dict[str, Any], api_type: str) -> str:
        """格式化AI响应"""
        if 'error' in response:
            return f"错误: {response['error']}"
        
        try:
            if api_type.lower() == 'openai':
                choices = response.get('choices', [])
                if choices:
                    content = choices[0].get('message', {}).get('content', '')
                    return content.strip()
            
            elif api_type.lower() == 'gemini':
                candidates = response.get('candidates', [])
                if candidates:
                    content = candidates[0].get('content', {})
                    parts = content.get('parts', [])
                    if parts:
                        return parts[0].get('text', '').strip()
            
        except (KeyError, IndexError, TypeError) as e:
            return f"解析响应失败: {e}\n\n原始响应:\n{json.dumps(response, indent=2, ensure_ascii=False)}"
        
        return f"未知响应格式:\n{json.dumps(response, indent=2, ensure_ascii=False)}"
    
    def chat_session(self, adapter: BaseAIAdapter, model_id: str, parameters: Dict[str, Any]):
        """聊天会话 - 支持自动重试"""
        print(f"\n=== 开始与 {model_id} 对话 ===")
        print("输入 '/quit' 退出，'/clear' 清空历史，'/history' 查看历史")
        print("输入 '/system <内容>' 添加系统提示词")
        if parameters.get("stream", True):
            print("✨ 流式输出模式已启用")
        if self.config_manager.auto_retry_enabled():
            print("[RELOAD] 自动重试功能已启用")
        print("-" * 50)
        
        while True:
            user_input = input("\n你: ").strip()
            
            if not user_input:
                continue
            
            if user_input == '/quit':
                break
            elif user_input == '/clear':
                self.conversation_history.clear()
                print("对话历史已清空")
                continue
            elif user_input == '/history':
                self.print_history()
                continue
            elif user_input.startswith('/system '):
                system_content = user_input[8:].strip()
                if system_content:
                    system_msg = ChatMessage(role='system', content=system_content)
                    self.conversation_history.insert(0, system_msg)
                    print("系统提示词已添加")
                continue
            
            # 添加用户消息
            user_msg = ChatMessage(role='user', content=user_input)
            current_messages = self.conversation_history + [user_msg]
            
            # 显示AI开始回答的提示
            if parameters.get("stream", True):
                print("\nAI: ", end='', flush=True)
            else:
                print("\nAI: 思考中...")
            
            # 发送消息 - 使用自动重试功能
            response = self.send_message_with_retry(current_messages, model_id, parameters, adapter)
            ai_response = self.format_response(response, adapter.config.api_type)
            
            # 如果是流式输出，AI响应已经实时显示了，只需要换行
            if parameters.get("stream", True):
                print()  # 换行
            else:
                print(f"\nAI: {ai_response}")
            
            # 更新对话历史
            self.conversation_history.append(user_msg)
            if not response.get('error'):
                assistant_msg = ChatMessage(role='assistant', content=ai_response)
                self.conversation_history.append(assistant_msg)
    
    def print_history(self):
        """打印对话历史"""
        if not self.conversation_history:
            print("暂无对话历史")
            return
        
        print("\n=== 对话历史 ===")
        for msg in self.conversation_history:
            role_name = {"user": "你", "assistant": "AI", "system": "系统"}.get(msg.role, msg.role)
            print(f"{role_name}: {msg.content}")
        print("=" * 20)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        session_duration = time.time() - self.session_stats['start_time']
        
        report = {
            'session_stats': self.session_stats.copy(),
            'session_duration': session_duration,
            'cache_hit_rate': 0,
            'messages_per_minute': 0
        }
        
        # 计算缓存命中率
        if self.session_stats['total_messages'] > 0:
            report['cache_hit_rate'] = (self.session_stats['cache_hits'] / self.session_stats['total_messages']) * 100
        
        # 计算每分钟消息数
        if session_duration > 0:
            report['messages_per_minute'] = (self.session_stats['total_messages'] / session_duration) * 60
        
        # 添加适配器性能统计
        if self.current_adapter and hasattr(self.current_adapter, 'cache_manager'):
            if self.current_adapter.cache_manager:
                report['adapter_cache_stats'] = self.current_adapter.cache_manager.get_cache_stats()
        
        if self.current_adapter and hasattr(self.current_adapter, 'connection_manager'):
            report['connection_stats'] = self.current_adapter.connection_manager.get_performance_stats()
        
        return report
    
    def print_performance_report(self):
        """打印性能报告"""
        report = self.get_performance_report()
        
        print("\n=== 性能报告 ===")
        session_stats = report['session_stats']
        
        print(f"会话时长: {report['session_duration']:.1f}秒")
        print(f"总消息数: {session_stats['total_messages']}")
        print(f"缓存命中: {session_stats['cache_hits']}")
        print(f"缓存命中率: {report['cache_hit_rate']:.1f}%")
        print(f"每分钟消息数: {report['messages_per_minute']:.1f}")
        
        if 'adapter_cache_stats' in report:
            cache_stats = report['adapter_cache_stats']
            print(f"适配器缓存大小: {cache_stats['cache_size']}/{cache_stats['max_cache_size']}")
            print(f"适配器缓存命中率: {cache_stats['hit_rate']*100:.1f}%")
        
        if 'connection_stats' in report:
            conn_stats = report['connection_stats']
            print(f"连接成功率: {conn_stats['success_rate']*100:.1f}%")
            print(f"平均延迟: {conn_stats['average_latency']:.2f}秒")
    
    def run(self):
        """运行主程序"""
        print("欢迎使用AI接口交互程序 v2.0!")
        self.session_stats['total_sessions'] += 1
        
        while True:
            print("\n=== 主菜单 ===")
            print("1. 开始对话")
            print("2. 添加配置")
            print("3. 查看配置")
            print("4. 测试连接")
            print("5. 性能报告")
            print("6. 退出")
            
            choice = input("\n请选择: ").strip()
            
            if choice == '1':
                # 选择配置
                config = self.select_config()
                if not config:
                    continue
                
                try:
                    # 创建适配器
                    adapter = self.create_adapter(config)
                    
                    # 测试连接
                    test_result = adapter.test_connection()
                    if test_result["status"] != "success":
                        print(f"连接测试失败: {test_result['message']}")
                        continue
                    
                    # 选择模型
                    model_id = self.select_model(adapter)
                    if not model_id:
                        continue
                    
                    # 配置参数
                    parameters = self.configure_parameters(adapter, model_id)
                    
                    # 开始对话
                    self.chat_session(adapter, model_id, parameters)
                    
                except Exception as e:
                    print(f"创建AI适配器失败: {e}")
            
            elif choice == '2':
                self.setup_new_config()
            
            elif choice == '3':
                configs = self.config_manager.list_configs()
                if configs:
                    print("\n当前配置:")
                    for name in configs:
                        config = self.config_manager.get_config(name)
                        print(f"- {name}: {config.api_type} ({config.base_url})")
                else:
                    print("暂无配置")
            
            elif choice == '4':
                # 测试连接
                config = self.select_config()
                if config:
                    try:
                        adapter = self.create_adapter(config)
                        print("\n正在测试连接...")
                        test_result = adapter.test_connection()
                        
                        if test_result["status"] == "success":
                            print(f"[OK] {test_result['message']}")
                        else:
                            print(f"[FAIL] {test_result['message']}")
                    except Exception as e:
                        print(f"测试连接时出错: {e}")
            
            elif choice == '5':
                print("再见!")
                break
            
            else:
                print("无效选择，请重试")


def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description='AI接口交互程序')
    parser.add_argument('--config', help='配置文件路径', default='ai_config.yaml')
    
    args = parser.parse_args()
    
    try:
        # 设置配置文件路径
        if args.config != 'ai_config.yaml':
            ConfigManager.config_file = args.config
        
        client = AIClient()
        client.run()
        
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"程序运行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()