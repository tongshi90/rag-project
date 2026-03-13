# RAG 系统后端

## 项目概述

这是一个**检索增强生成(RAG)系统**的后端服务，采用 Python Flask 框架，负责处理 PDF 文档的上传、解析、拆分和向量化存储，为前端的 AI 问答功能提供支持。

系统采用**离线索引 + 在线检索**的两阶段架构：
- **离线阶段**：文档拆分 → 质量检测 → LLM 优化 → 向量化存储
- **在线阶段**：问题向量化 → 相似度检索 → 答案生成

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端框架 | Flask 3.0.0 + Flask-CORS |
| PDF 解析 | pdfplumber, PyMuPDF (fitz) |
| 数据库 | SQLite |
| 向量数据库 | ChromaDB (>=0.5.0) |
| 向量计算 | numpy |
| Token 计算 | tiktoken |
| LLM 服务 | SiliconFlow API |
| 进度显示 | tqdm |

## 项目结构

```
backend/
├── app/
│   ├── __init__.py              # Flask 应用工厂
│   ├── config/                  # 配置管理
│   │   ├── __init__.py
│   │   ├── model_config.py      # LLM/Embedding/OCR 模型配置
│   │   └── paths.py             # 路径统一管理（跨平台兼容）
│   ├── models/                  # 数据模型（SQLite）
│   │   ├── __init__.py
│   │   └── file.py              # File 模型 + 数据库 CRUD 操作
│   ├── api/                     # API 路由层（蓝本模式）
│   │   ├── __init__.py          # 蓝本注册
│   │   ├── files.py             # 文件管理 API
│   │   └── chat.py              # 聊天 API（待实现完整 RAG）
│   └── services/                # 业务逻辑层
│       ├── __init__.py
│       ├── document_processing/ # 文档处理阶段（离线）
│       │   ├── __init__.py
│       │   ├── document_processor.py  # 完整流程编排（主入口）
│       │   ├── splitter/        # PDF → Chunks
│       │   │   ├── __init__.py
│       │   │   ├── text_splitter.py   # 文本智能分片（8步流程）
│       │   │   ├── img_splitter.py    # 图片提取与分片
│       │   │   └── form_splitter.py   # 表格提取与分片
│       │   ├── validator/       # Chunk 质量检测
│       │   │   ├── __init__.py
│       │   │   └── validate.py  # 异常检测 + 风险评分
│       │   ├── optimizer/       # Chunk 优化
│       │   │   ├── __init__.py
│       │   │   └── chunk_optimizer.py  # LLM 分析 + 合并/拆分
│       │   └── embedding/       # 向量化（已实现）
│       │       ├── __init__.py
│       │       ├── encoder.py         # Embedding 编码器封装
│       │       ├── vector_store.py    # ChromaDB 向量存储封装
│       │       └── batch_processor.py # 批量处理器
│       └── user_interaction/    # 用户交互阶段（在线）
│           ├── __init__.py
│           ├── question_splitter/  # 问题拆分（待实现）
│           ├── query_encoder/     # 问题向量化（待实现）
│           ├── retrieval/         # 检索 + 重排序（待实现）
│           └── generator/         # LLM 生成（待实现）
├── data/                       # 数据目录（自动创建）
│   ├── rag.db                  # SQLite 数据库
│   ├── vector_db/              # ChromaDB 向量存储
│   └── upload/                 # 上传的 PDF 文件存储
├── run.py                      # 应用入口
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量示例
└── README.md                   # 本文档
```

## 核心流程

### 阶段一：文档处理（Document Processing）

文档处理采用**四步流水线**架构，由 `document_processor.py` 统一编排：

```python
from app.services.document_processing import parse_pdf

result = parse_pdf(pdf_path, file_id)
# 返回: {
#   "success": True,
#   "doc_id": "xxx",
#   "steps": {"split": {...}, "validate": {...}, "optimize": {...}, "embed": {...}},
#   "total_elapsed": 123.45
# }
```

#### 1. Splitter - 文档拆分

**功能**：将 PDF 文档解析并拆分为多个语义完整的 chunk

**入口函数**：`split_pdf_to_chunks(pdf_path, file_id)`

**完整拆分步骤**：

| 步骤 | 函数 | 说明 |
|------|------|------|
| 1 | `extract_pages` | 提取页面文本，排除表格区域 |
| 2 | `remove_repeated_headers_footers` | 去除重复的页眉页脚（阈值 70%） |
| 3 | `remove_page_numbers` | 去除页码（支持"第X页"/"X页"/纯数字格式） |
| 4 | `refine_title_patterns` | 动态修正标题规则（过滤误判率高的规则） |
| 5 | `split_chunks` | 按标题层级构建分片 |
| 6 | `merge_title_only_chunks` | 合并仅含标题的分片 |
| 7 | `dedup_same_format_titles` | 去重相同格式的标题 |
| 8 | `post_process_chunks` | 重新调整 order 和 chunk_id |

**标题识别规则**：

| 层级 | 格式类型 | 正则表达式 | 优先级 |
|------|----------|------------|--------|
| level1 | 第X章 | `^第[一二三四五六七八九十百]+章\s+.+` | 最高 |
| level2 | 第X节 | `^第[一二三四五六七八九十百]+节\s+.+` | 高 |
| level2 | 中文数字顿号 | `^[一二三四五六七八九十百]+、\s*.+` | 高 |
| level2 | 阿拉伯数字点 | `^\d+(\.\d+)*\s+.+` | 高 |
| level3 | 括号中文数字 | `^[（(][一二三四五六七八九十百]+[）)]\s*.+` | 低 |

**Chunk 数据结构**：

```json
{
    "chunk_id": "1738756800123_1",      // {file_id}_{order}
    "order": 1,                          // 排序序号
    "doc_id": "1738756800123",          // 所属文档ID
    "title_path": ["第一章 概述", "一、背景"],  // 多级标题路径
    "text": "完整文本内容（包含标题和正文）",
    "page": 1,                          // 所在页码
    "type": "text",                     // 分片类型
    "bbox": [],                         // 位置边界框
    "length": 62                        // 字符数
}
```

#### 2. Validator - Chunk 质量检测

**功能**：检测拆分后的 chunk 是否存在质量问题，计算风险分数并标记异常

**入口函数**：`validate_chunks(chunks, title_patterns)`

**完整校验步骤**：

| 步骤 | 函数 | 说明 | handling_mode |
|------|------|------|---------------|
| 0 | `calculate_pre_validation_metrics` | 计算前置统计指标（总token数、中位长度、标题占比等） | - |
| 1 | `validate_chunk_too_short` | 分片过短验证（<80 tokens 或 <中位值*0.4） | merge |
| 2 | `validate_chunk_too_long` | 分片过长验证（>1000 tokens 或 >中位值*2.5） | split |
| 3 | `validate_content_existence` | 正文存在性验证（检测纯标题分片） | merge |
| 4 | `validate_parameter_mixing` | 参数混杂检测（参数类与描述类内容混合） | split |
| 5 | `validate_title_structure` | 标题结构验证（检查标题层级是否符合规则） | split |
| 6 | `validate_title_proportion` | 标题占比验证（标题占比过高异常） | merge |
| 7 | `validate_long_chunk_multi_topic` | 长chunk内部多主题检测（相邻窗口相似度过低） | split |
| 8 | `validate_continuous_short_chunk_same_topic` | 连续短chunk同一知识点检测（相邻chunk相似度过高） | merge |

**风险评分规则**：

| 检测项 | 风险分数 | 说明 |
|--------|----------|------|
| 分片过短异常 | 5~15 | 根据偏离程度分档（15分最高） |
| 分片过长异常 | 5~15 | 根据偏离程度分档（15分最高） |
| 无正文 | 10~20 | 正文长度不足，20分最高 |
| 参数混杂 | 10~25 | 参数类与描述类混合程度，25分最高 |
| 标题结构错误 | 20 | 标题层级不符合规则 |
| 标题占比过高 | 5~15 | 标题占比 >40%，15分最高 |
| 长chunk多主题 | 20~60 | 内部相似度过低，60分最高（强制异常） |
| 连续短chunk重复 | 15~60 | 相邻chunk相似度过高，60分最高（强制异常） |

**handling_mode 说明**：

| 值 | 说明 | LLM 处理方式 |
|----|------|-------------|
| `merge` | 需要合并分片 | 将当前分片与相邻分片一起交给 LLM 处理 |
| `split` | 需要拆分分片 | 仅将当前分片交给 LLM 处理 |

**校验结果数据结构**：

```json
{
    "chunk_id": "1738756800123_1",
    "order": 1,
    "title_path": ["第一章 概述"],
    "text": "完整文本内容...",
    "error_info": [
        {"risk_score": 15, "type": "validate_chunk_too_short", "handling_mode": "merge"},
        {"risk_score": 20, "type": "validate_title_structure", "handling_mode": "split"}
    ],
    "total_risk_score": 35,
    "hard_violation": false
}
```

**辅助函数**：

| 函数 | 说明 |
|------|------|
| `get_validation_summary(chunks)` | 获取校验摘要（总分片数、异常数、总风险分数等） |
| `get_risk_chunk_ids(chunks, min_risk_score=60)` | 获取高风险分片信息列表，返回格式：`[{'chunk_id': 'xxx', 'handling_mode': 'merge'}, ...]` |

**handling_mode 判定规则**：
- 只要有一条异常的 `handling_mode` 是 `merge`，则该分片的处理类型为 `merge`
- 只有所有异常的 `handling_mode` 都是 `split` 时，处理类型才为 `split`

#### 3. Optimizer - Chunk 优化

**功能**：使用 LLM 分析异常 chunk 并给出合并/拆分建议

**入口函数**：`optimize_chunks(chunks, min_risk_score=60, show_content=True)`

**处理逻辑**：

```
获取高风险分片（total_risk_score >= 60）
    ↓
按 handling_mode 分类
    ↓
    ├── [merge 处理]
    │   ├── 获取相邻分片作为上下文
    │   ├── 按连续性分组
    │   ├── 调用 LLM 分析是否需要切分
    │   └── 执行合并或拆分操作
    │
    └── [split 处理]
        ├── 获取当前分片
        ├── 调用 LLM 分析拆分位置
        └── 执行拆分操作
```

**LLM Prompt**：

- **MERGE_ANALYSIS_PROMPT**：分析多个分片是否属于同一知识点，返回切分点标记
- **SPLIT_ANALYSIS_PROMPT**：分析单个分片是否包含多个知识点，返回切分点标记

**输出结果**：

```python
optimized_chunks = optimize_chunks(validated_chunks)
# 返回优化后的分片列表（新的列表，不影响原始数据）
```

#### 4. Embedding - 向量化（已实现）

**功能**：将 chunk 转换为向量并存储到 ChromaDB

**入口函数**：`embed_and_store_chunks(chunks, doc_id, batch_size=10)`

**核心组件**：

| 组件 | 文件 | 功能 |
|------|------|------|
| **EmbeddingEncoder** | `encoder.py` | 封装 SiliconFlow/Qwen3-Embedding-4B 模型，支持单个/批量编码 |
| **VectorStore** | `vector_store.py` | ChromaDB 向量存储封装，提供增删查改功能 |
| **BatchProcessor** | `batch_processor.py` | 批量处理器，进度跟踪 + 错误处理 |

**向量存储功能**：

```python
from app.services.document_processing.embedding import get_vector_store, get_encoder

# 获取向量存储实例
vector_store = get_vector_store()
encoder = get_encoder()

# 搜索相关 chunks
results = vector_store.search_by_text(
    query_text="查询问题",
    encoder=encoder,
    top_k=5,
    filter={"doc_id": "doc_001"}  # 可选：元数据过滤
)

# 获取文档的所有 chunks
chunks = vector_store.get_chunks_by_doc_id("doc_001")

# 获取统计信息
stats = vector_store.get_stats()
# {"collection_name": "rag_chunks", "total_count": 1234, "doc_count": 5}
```

**数据存储结构**：

```
ChromaDB Collection: "rag_chunks"
├── ids: chunk_id (唯一标识)
├── embeddings: 向量表示 (Qwen3-Embedding-4B: 1536维)
├── documents: 原始文本
└── metadatas: {doc_id, order, page, type, length, bbox}
```

---

### 阶段二：用户交互（User Interaction）

#### 1. Question Splitter - 问题拆分（待实现）

**功能**：将复杂的用户问题拆分为多个子问题

**实现内容**：
- 判断是否需要拆分
- 执行问题拆分
- 处理子问题之间的关联关系

#### 2. Query Encoder - 问题向量化（待实现）

**功能**：将用户问题转换为向量

**实现内容**：
- 问题预处理
- 向量转换
- 查询扩展（可选）

#### 3. Retrieval - 检索（待实现）

**功能**：根据问题向量检索相关 chunk 并重排序

**实现内容**：
- 向量搜索器（相似度计算）
- 重排序器（Cross-Encoder）
- 混合检索（向量 + 关键词）

#### 4. Generator - 答案生成（待实现）

**功能**：根据检索到的 chunk 生成最终答案

**实现内容**：
- 上下文构建器（拼接 chunk，控制 token 数量）
- LLM 客户端（封装 API 调用）
- 来源标注

---

## 安装和运行

### 环境要求

- Python 3.8+
- pip

### 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 配置环境变量

1. 复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，配置必需的 API 密钥：

```env
# ============================================
# API 密钥（必填）
# ============================================
SILICONFLOW_API_KEY=your_api_key_here

# ============================================
# 服务配置
# ============================================
PORT=5000
FLASK_DEBUG=True

# ============================================
# 路径配置（可选，Docker 部署时使用）
# ============================================
# DATABASE_PATH=/app/data/rag.db
# VECTOR_DB_PATH=/app/data/vector_db
# UPLOAD_FOLDER=/app/data/upload
```

**完整配置说明请参考 `.env.example` 文件**

### 启动服务

```bash
python run.py
```

服务将运行在 `http://0.0.0.0:5000`

### 目录初始化

首次运行时，系统会自动创建以下目录结构：

```
backend/
└── data/                # 数据目录（自动创建）
    ├── rag.db          # SQLite 数据库
    ├── vector_db/      # ChromaDB 向量存储
    └── upload/         # PDF 文件存储
```

---

## API 接口

### 文件管理

| 方法 | 路径 | 说明 | 响应格式 |
|------|------|------|----------|
| GET | `/api/files` | 获取所有文件列表 | `{"success": true, "data": {"files": [...], "total": N}}` |
| POST | `/api/files/upload` | 上传 PDF 文件（异步处理） | `{"success": true, "data": {...}}` |
| GET | `/api/files/<id>` | 获取单个文件详情 | `{"success": true, "data": {...}}` |
| DELETE | `/api/files/<id>` | 删除指定文件（含向量数据） | `{"success": true}` |
| DELETE | `/api/files/all` | 删除所有文件（含向量库） | `{"success": true}` |
| GET | `/api/files/<id>/stats` | 获取文件处理统计 | `{"success": true, "data": {"file": {...}, "vector_stats": {...}}}` |

**文件状态值**：
- `parsing` - 正在解析文档
- `completed` - 处理完成
- `failed` - 处理失败

### 聊天（待实现）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | 处理用户查询 |

### 健康检查

| 方法 | 路径 | 说明 | 响应 |
|------|------|------|------|
| GET | `/health` | 服务状态 | `{"status": "healthy"}` |

---

## 模型配置

系统通过 `.env.example` 文件集中管理所有模型配置，由 `config/model_config.py` 统一读取。

### 支持的模型类型

| 类型 | 默认模型 | 用途 |
|------|----------|------|
| OCR | Qwen/Qwen2-VL-72B-Instruct | 图片文字识别 |
| Chat | Qwen/Qwen2.5-72B-Instruct | 对话生成、chunk 优化 |
| Embedding | Qwen/Qwen3-Embedding-4B | 文本向量化 |
| Text Splitter | Qwen/Qwen2.5-72B-Instruct | 文本分割专用 |

### 模型抽象接口

所有模型均基于统一的抽象基类：

```python
# OCR 模型
class OCRModel(ABC):
    @abstractmethod
    def recognize(self, image_bytes: bytes, prompt: Optional[str] = None) -> str:
        """识别图片中的文字内容"""
        pass

# 聊天模型
class ChatModel(ABC):
    @abstractmethod
    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """生成聊天回复"""
        pass

# 嵌入模型
class EmbeddingModel(ABC):
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """生成文本的嵌入向量"""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成文本的嵌入向量"""
        pass
```

### 使用方式

```python
from app.config.model_config import (
    get_chat_model,
    get_embedding_model,
    get_ocr_model,
    get_text_splitter_llm
)

# 获取聊天模型实例
chat_model = get_chat_model()
response = chat_model.chat([{"role": "user", "content": "你好"}])

# 获取嵌入模型实例
embedding_model = get_embedding_model()
vector = embedding_model.embed("这是一段文本")
vectors = embedding_model.embed_batch(["文本1", "文本2"])

# 获取 OCR 模型实例
ocr_model = get_ocr_model()
text = ocr_model.recognize(image_bytes)

# 获取文本分割专用 LLM
splitter_llm = get_text_splitter_llm()
```

---

## 文件路径管理

为确保跨平台兼容性（Windows/Linux/Docker），系统采用统一路径管理策略。

### 路径配置模块 (`config/paths.py`)

```python
from app.config.paths import (
    PROJECT_ROOT,    # 项目根目录
    DATA_DIR,        # 数据目录
    DB_PATH,         # 数据库路径
    VECTOR_DB_PATH,  # 向量库路径
    UPLOAD_PATH,     # 上传目录
    ensure_data_dirs # 确保目录存在
)
```

### 跨平台兼容策略

| 操作 | 说明 |
|------|------|
| **存储** | 数据库存储相对路径（如 `data/upload/file.pdf`） |
| **读取** | 自动转换为系统对应的绝对路径 |
| **路径分隔符** | 使用 `pathlib.Path` 自动处理 `\` 和 `/` |
| **环境变量覆盖** | Docker 部署时支持通过环境变量覆盖默认路径 |

### 支持的环境变量

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `DATABASE_PATH` | SQLite 数据库路径 | `data/rag.db` |
| `VECTOR_DB_PATH` | 向量数据库路径 | `data/vector_db` |
| `UPLOAD_FOLDER` | 文件上传目录 | `data/upload` |

---

## 待实现功能

### 用户交互阶段（在线）

| 模块 | 状态 | 描述 |
|------|------|------|
| **问题拆分** | 待实现 | 识别复杂问题中的多个意图，拆分为子问题 |
| **问题向量化** | 待实现 | 将用户问题转换为向量表示 |
| **向量检索** | 待实现 | 基于相似度检索相关 chunks（VectorStore 已提供基础能力） |
| **重排序** | 待实现 | 使用 Cross-Encoder 对检索结果进行细粒度排序 |
| **答案生成** | 待实现 | 基于检索结果构建上下文，调用 LLM 生成答案 |
| **混合检索** | 待实现 | 向量检索 + 关键词匹配（BM25） |

### 监控系统

| 指标 | 状态 | 描述 |
|------|------|------|
| **chunk 命中率** | 待实现 | 统计各 chunk 被检索的频率 |
| **无结果率** | 待实现 | 监控查询无结果的比例 |
| **幻觉率** | 待实现 | 检测生成答案与检索内容的一致性 |
| **响应时间** | 待实现 | 各阶段耗时统计 |

---

## 开发指南

### 添加新的 API 端点

1. 在 `app/api/` 下创建或编辑路由文件
2. 使用 `@api_bp.route()` 装饰器定义端点
3. 在 `app/api/__init__.py` 中导入蓝本（如果是新文件）

### 调试技巧

```bash
# 启用调试模式（自动重载）
FLASK_DEBUG=True python run.py

# 查看数据库
sqlite3 backend/data/rag.db

# 查看向量库统计
python -c "from app.services.document_processing.embedding import get_vector_store; print(get_vector_store().get_stats())"
```

### 测试 API

```bash
# 健康检查
curl http://localhost:5000/health

# 获取文件列表
curl http://localhost:5000/api/files

# 上传文件
curl -X POST -F "file=@document.pdf" http://localhost:5000/api/files/upload
```

---

## 常见问题

**Q: 为什么上传文件后 status 一直是 parsing？**

A: 文档处理在后台线程中异步执行，查看控制台输出确认处理进度。如果失败，status 会变为 failed。

**Q: 如何重置向量数据库？**

A: 删除 `data/vector_db` 文件夹或调用 DELETE `/api/files/all`。

**Q: 支持哪些 PDF 格式？**

A: 支持标准 PDF 文档，包括文本、图片和表格。扫描版 PDF 需要 OCR 支持。

**Q: 如何更换 Embedding 模型？**

A: 修改 `.env.example` 中的 `SILICONFLOW_EMBEDDING_MODEL` 配置项。
