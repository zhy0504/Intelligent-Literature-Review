"""
医学文献智能检索系统核心模块

包含以下功能模块:
- ai_client: AI客户端和配置管理
- data_processor: 期刊数据处理
- intent_analyzer: 用户意图分析
- literature_filter: 文献过滤和导出
- pubmed_search: PubMed检索
- review_outline_generator: 综述大纲生成
- smart_literature_search: 智能文献检索主系统
- start: 系统启动脚本
"""

__version__ = "1.0.0"
__author__ = "Medical Literature Search System"

# 主要模块的快捷导入
from .smart_literature_search import SmartLiteratureSearchSystem
from .intent_analyzer import IntentAnalyzer
from .intent_analyzer import SearchCriteria
from .pubmed_search import PubMedSearcher
from .literature_filter import LiteratureFilter
from .review_outline_generator import ReviewOutlineGenerator
from .ai_client import AIClient, ConfigManager
from .data_processor import JournalDataProcessor

__all__ = [
    'SmartLiteratureSearchSystem',
    'IntentAnalyzer', 
    'SearchCriteria',
    'PubMedSearcher',
    'LiteratureFilter', 
    'ReviewOutlineGenerator',
    'AIClient',
    'ConfigManager',
    'JournalDataProcessor'
]