# 智能文献检索与综述生成系统

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com)

一个基于AI的智能文献检索与医学综述自动生成系统，支持PubMed搜索、智能筛选、大纲生成和专业综述文章撰写。

## ✨ 核心功能

### 🔍 智能文献检索
- **PubMed API集成**：直接连接PubMed数据库，支持复杂的布尔查询
- **MeSH词表智能映射**：自动将中文查询转换为标准MeSH术语
- **意图分析**：基于AI的自然语言理解，精确解析用户查询意图
- **多格式导出**：支持CSV、JSON、BibTeX、TXT等多种格式

### 📊 智能文献筛选
- **期刊影响因子过滤**：基于JCR数据自动筛选高质量期刊
- **智能相关性评分**：使用AI评估文献与研究主题的相关度
- **多维度筛选**：年份、期刊类型、研究类型等多重过滤条件
- **去重与优化**：自动识别并去除重复文献

### 📋 大纲智能生成
- **结构化大纲**：根据文献内容自动生成逻辑清晰的综述大纲
- **专业医学结构**：遵循标准医学综述写作规范
- **可定制模板**：支持不同类型综述的大纲模板

### 📝 综述文章生成
- **AI驱动写作**：基于检索到的文献自动生成高质量综述文章
- **多AI服务支持**：支持OpenAI、Gemini、本地AI等多种服务
- **专业格式输出**：自动生成符合学术规范的文章格式
- **DOCX导出**：通过Pandoc支持Word文档导出

## 🚀 快速开始

### 系统要求
- **操作系统**：Windows 10/11、Linux、macOS
- **Python版本**：3.7 或更高版本
- **内存**：建议 4GB 以上
- **磁盘空间**：至少 1GB 可用空间

### 安装步骤

#### Windows 用户（推荐）
1. **下载项目**
   ```bash
   git clone https://github.com/your-repo/Intelligent-Literature-Review.git
   cd Intelligent-Literature-Review
   ```

2. **运行启动脚本**
   ```bash
   # 双击运行
   start.bat
   
   ```

#### Linux/macOS 用户
1. **下载项目**
   ```bash
   git clone https://github.com/your-repo/Intelligent-Literature-Review.git
   cd Intelligent-Literature-Review
   ```

2. **运行启动脚本**
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

#### 手动安装（不推荐）
```bash
# 1. 创建虚拟环境
python -m venv venv

# 2. 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动系统
python src/start.py
```

### AI服务配置

1. **复制配置模板**
   ```bash
   copy ai_config_example.yaml ai_config.yaml  # Windows
   cp ai_config_example.yaml ai_config.yaml    # Linux/macOS
   ```

2. **编辑配置文件**
   ```yaml
   ai_services:
     openai_official:
       name: "openai_official"
       api_type: "openai"
       base_url: "https://api.openai.com/"
       api_key: "sk-your_openai_api_key_here"  # 填入你的API密钥
       default_model: "gpt-4"
       status: "active"  # 改为active启用
   ```

3. **支持的AI服务**
   - **OpenAI**：ChatGPT、GPT-4 系列
   - **Gemini**：Google Gemini Pro
   - **国产AI**：DeepSeek、月之暗面Kimi、通义千问等
   - **本地AI**：Ollama、LocalAI等

## 📖 使用指南

### 基础使用流程

1. **启动系统**
   - 运行启动脚本，系统会自动检查环境并安装依赖

2. **配置AI服务**
   - 首次使用需要配置AI API密钥
   - 系统会自动检测可用服务并进行连接测试

3. **开始文献检索**
   - 输入研究主题，如："糖尿病的最新治疗方法"
   - 系统自动分析意图并生成PubMed查询

4. **智能筛选**
   - 系统根据配置自动筛选高质量文献
   - 支持手动调整筛选条件

5. **生成综述**
   - 基于筛选后的文献自动生成大纲
   - 生成完整的综述文章
   - 导出为Word文档

### 高级功能

#### 自定义搜索策略
```python
# 支持复杂的PubMed查询语法
query = '("Diabetes Mellitus"[MeSH Terms] OR "diabetes"[tiab]) AND "treatment"[tiab] AND ("2020"[PDAT] : "2024"[PDAT])'
```

#### 期刊筛选配置
- **影响因子阈值**：自动过滤低影响因子期刊
- **期刊白名单**：指定高质量期刊列表
- **研究类型**：临床试验、系统性综述、Meta分析等

#### 大纲模板定制
- 支持不同医学领域的专业大纲模板
- 可自定义章节结构和内容重点

## 🏗️ 项目架构

```
Intelligent-Literature-Review/
├── src/                          # 核心源码目录
│   ├── intelligent_literature_system.py  # 主系统入口
│   ├── intent_analyzer.py        # 意图分析模块
│   ├── pubmed_search.py          # PubMed搜索引擎
│   ├── literature_filter.py     # 文献筛选器
│   ├── review_outline_generator.py # 大纲生成器
│   ├── medical_review_generator.py # 综述生成器
│   ├── ai_client.py              # AI服务客户端
│   ├── data_processor.py         # 数据处理器
│   └── prompts_manager.py        # 提示词管理器
├── data/                         # 数据目录
│   ├── jcr.csv                   # JCR期刊影响因子数据
│   ├── processed_jcr_data.csv    # 处理后的JCR数据
│   └── zky.csv                   # 中科院期刊分区数据
├── prompts/                      # AI提示词配置
│   └── prompts_config.yaml       # 提示词配置文件
├── start.bat                     # Windows启动脚本
├── start.ps1                     # PowerShell启动脚本
├── start.sh                      # Linux/macOS启动脚本
├── requirements.txt              # Python依赖包
├── ai_config_example.yaml        # AI配置模板
└── README.md                     # 项目文档
```

## 🛠️ 核心模块

### 意图分析器 (IntentAnalyzer)
- **自然语言理解**：解析用户的查询意图
- **MeSH词表映射**：将中文转换为标准医学术语
- **查询优化**：生成精确的PubMed检索策略

### PubMed搜索器 (PubMedSearcher)
- **异步并发搜索**：支持高效的批量文献检索
- **智能缓存**：避免重复请求，提高响应速度
- **多格式导出**：支持多种文献格式的导出

### 文献筛选器 (LiteratureFilter)
- **多维度评分**：影响因子、相关性、时效性综合评分
- **智能去重**：基于DOI、标题等多重去重策略
- **质量控制**：确保筛选出的文献质量

### 综述生成器 (MedicalReviewGenerator)
- **结构化写作**：按照标准学术规范生成文章
- **参考文献管理**：自动处理引用格式
- **多格式输出**：支持Markdown、DOCX等格式

## ⚙️ 配置说明

### 环境配置
- 系统会自动检测Python环境和依赖包
- 支持虚拟环境自动创建和管理
- 跨平台兼容，支持Windows、Linux、macOS

### AI服务配置
```yaml
ai_services:
  openai_official:
    name: "openai_official"
    api_type: "openai"
    base_url: "https://api.openai.com/"
    api_key: "your-api-key"
    default_model: "gpt-4"
    timeout: 300
    status: "active"
```

### 搜索配置
- **默认结果数量**：每次搜索的文献数量
- **时间范围**：文献发表时间限制
- **语言过滤**：支持多语言文献筛选

## 🔧 故障排除

### 常见问题

#### 1. PowerShell执行策略问题
**问题**：Windows系统提示"无法执行脚本"
**解决方案**：
```bash
# 方法1：使用批处理文件（推荐）
start.bat

# 方法2：临时绕过执行策略
powershell -ExecutionPolicy Bypass -File start.ps1

# 方法3：设置执行策略
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 2. 依赖安装失败
**问题**：pip安装包失败或速度慢（脚本启动已经能自动切换到国内镜像下载）
**解决方案**：
```bash
# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 3. AI服务连接失败
**问题**：API密钥无效或网络连接问题
**解决方案**：
- 检查API密钥是否正确
- 验证网络连接和防火墙设置
- 尝试使用不同的AI服务提供商

#### 4. 虚拟环境创建失败
**问题**：Python venv模块不可用
**解决方案**：
```bash
# Ubuntu/Debian
sudo apt install python3-venv

# CentOS/RHEL
sudo yum install python3-venv

# 或重新安装Python，确保包含venv模块
```

### 系统日志
- 详细的错误日志会保存在 `venv_creation_error.log`
- 包含系统环境信息和具体错误原因
- 提供针对性的解决建议

## 📊 性能优化

### 搜索优化
- **并发请求**：使用异步方式提高搜索效率
- **智能缓存**：避免重复的API调用
- **批量处理**：支持大规模文献处理

### 内存管理
- **流式处理**：大文件分块处理，避免内存溢出
- **缓存控制**：智能缓存管理，平衡性能和内存使用
- **垃圾回收**：及时清理临时文件和缓存