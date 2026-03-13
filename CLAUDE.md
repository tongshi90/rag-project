# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 项目概述

这是一个**混合增强检索生成（Hybrid RAG）系统**，采用 React TypeScript 前端 + Python Flask 后端架构。系统允许用户上传 PDF 文档，自动解析提取文本/表格/图片，构建向量索引、关键字索引和知识图谱，支持 AI 问答。

**系统架构特点**：采用**离线索引 + 在线混合检索**的两阶段架构设计。

```
离线阶段（文档处理）：PDF → 拆分 → 验证 → 优化 → 实体抽取 → 关系抽取 → 图谱构建 → 关键字索引 → 向量化 → 存储
在线阶段（用户交互）：查询 → 实体识别 → 混合检索(向量+关键字+图谱) → RRF融合 → 重排序 → LLM生成 → 答案
```

---

## 常用命令

### 前端开发
```bash
cd frontend
npm install              # 首次：安装依赖
npm run dev              # 启动开发服务器（http://localhost:3000）
npm run build            # 构建生产版本
npm run lint             # ESLint 代码检查
```

### 后端开发
```bash
cd backend
pip install -r requirements.txt    # 首次：安装依赖
python run.py                       # 启动 Flask 服务器（http://0.0.0.0:5000）
```

### 调试与测试
```bash
# 查看数据库内容
sqlite3 backend/data/rag.db

# 查看向量库统计
cd backend && python -c "from app.services.document_processing.embedding import get_vector_store; print(get_vector_store().get_stats())"

# 查看知识图谱统计
cd backend && python -c "from app.services.document_processing.graph_builder import get_graph_builder; gb = get_graph_builder(); gb.load_graph('doc_id'); print(gb.get_graph_stats())"

# 测试 API
curl http://localhost:5000/health
curl http://localhost:5000/api/files
curl http://localhost:5000/api/graph/stats/<doc_id>
```

---

## 核心架构

### 两阶段数据流

```
┌────────────────────────────────────────────────────────────────────────┐
│ 阶段一：文档处理（Document Processing）- 离线、异步                      │
├────────────────────────────────────────────────────────────────────────┤
│  用户上传 PDF                                                          │
│      ↓                                                                 │
│  [1] Splitter: PDF → Chunks（text_splitter.py）                        │
│      ↓                                                                 │
│  [2] Validator: 质量检测（validate.py）                                 │
│      ↓                                                                 │
│  [3] Optimizer: LLM 优化（chunk_optimizer.py）                         │
│      ↓                                                                 │
│  [4] Entity Extraction: 实体抽取（entity_extractor.py）                 │
│      ↓                                                                 │
│  [5] Relation Extraction: 关系抽取（relation_extractor.py）             │
│      ↓                                                                 │
│  [6] Graph Builder: 知识图谱构建（graph_builder.py）                    │
│      ↓                                                                 │
│  [7] Keyword Index: 关键字索引（keyword_indexer.py）                    │
│      ↓                                                                 │
│  [8] Embedding: 向量化存储（encoder.py + vector_store.py）              │
│      ↓                                                                 │
│  ChromaDB + Graph + Keyword Index                                      │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│ 阶段二：用户交互（User Interaction）- 在线、实时                         │
├────────────────────────────────────────────────────────────────────────┤
│  用户提问                                                               │
│      ↓                                                                 │
│  [1] Question Splitter: 复杂问题拆分（question_splitter.py）            │
│      ↓                                                                 │
│  [2] Entity Recognizer: 实体识别（entity_recognizer.py）               │
│      ↓                                                                 │
│  [3] Query Encoder: 问题向量化（query_encoder.py）                      │
│      ↓                                                                 │
│  [4] Hybrid Retrieval: 混合检索（retrieval.py）                         │
│      ├─ Vector Search: 向量检索                                         │
│      ├─ Keyword Search: BM25 关键字检索                                │
│      └─ Graph Search: 图谱邻域检索                                     │
│      ↓                                                                 │
│  [5] RRF Fusion: 结果融合（Reciprocal Rank Fusion）                     │
│      ↓                                                                 │
│  [6] Reranker: 重排序（Cross-Encoder）                                  │
│      ↓                                                                 │
│  [7] Generator: LLM 答案生成（generator.py）                            │
│      ↓                                                                 │
│  返回答案                                                               │
└────────────────────────────────────────────────────────────────────────┘
```

### 后端分层架构

| 层次 | 目录 | 职责 | 关键文件 |
|------|------|------|----------|
| **路由层** | `api/` | HTTP 请求处理、参数验证 | `files.py`, `chat.py`, `graph.py` |
| **模型层** | `models/` | 数据结构定义、SQLite CRUD | `file.py` |
| **服务层** | `services/` | 业务逻辑、RAG 核心处理 | 见下方详细说明 |
| **配置层** | `config/` | 环境配置、模型配置、路径管理 | `model_config.py`, `paths.py` |

### 服务层模块化设计

```
services/
├── document_processing/          # 离线文档处理
│   ├── document_processor.py     # ★流程编排主入口
│   ├── splitter/                 # PDF → Chunks
│   │   └── text_splitter.py      # 关键字提取
│   ├── validator/                # 质量检测（8种验证规则）
│   ├── optimizer/                # LLM 辅助优化
│   ├── entity_extraction/        # 实体抽取
│   ├── relation_extraction/      # 关系抽取
│   ├── graph_builder/            # 知识图谱构建（NetworkX）
│   ├── keyword_index/            # BM25 关键字索引
│   └── embedding/                # 向量化
│       ├── encoder.py            # SiliconFlow Embedding 封装
│       ├── vector_store.py       # ChromaDB 封装
│       └── batch_processor.py    # 批量处理器
│
└── user_interaction/             # 在线用户交互
    ├── question_splitter/        # 问题拆分
    ├── entity_recognizer/        # 实体识别
    ├── query_encoder/            # 问题向量化
    ├── retrieval/                # 混合检索 + 重排序
    │   └── retrieval.py          # HybridRetrievalPipeline
    ├── graph_retrieval/          # 图谱检索
    ├── context_enricher/         # 上下文增强
    └── generator/                # LLM 生成
```

---

## 关键设计模式

### 1. 文档处理流程编排

**入口**：`services/document_processing/document_processor.py`

```python
from app.services.document_processing import process_document

# 完整八步流程
result = process_document(pdf_path, doc_id)
# 返回: {"success": True, "steps": {...}, "total_elapsed": ...}
```

**异步执行**：文件上传后，`api/files.py` 在后台线程中调用处理流程，立即返回响应。

### 2. 混合检索管道

**入口**：`services/user_interaction/retrieval/retrieval.py`

```python
from app.services.user_interaction.retrieval import HybridRetrievalPipeline

pipeline = HybridRetrievalPipeline(
    weights={'vector': 0.5, 'keyword': 0.3, 'graph': 0.2}
)

results = pipeline.retrieve(
    query="用户问题",
    query_embedding=embedding,
    doc_id="文档ID",
    entity_ids=["实体ID列表"],
    enable_vector=True,
    enable_keyword=True,
    enable_graph=True
)
```

**RRF 融合算法**：
```
score(chunk) = w1/(k+rank_vector) + w2/(k+rank_keyword) + w3/(k+rank_graph)
```

### 3. 知识图谱操作

**NetworkX 集成**：`services/document_processing/graph_builder/graph_builder.py`

```python
from app.services.document_processing.graph_builder import get_graph_builder

graph = get_graph_builder()

# 构建图谱
graph.build_graph(entities, relations, doc_id)
graph.save_graph(doc_id)

# 邻域检索
neighbors = graph.get_neighbors("entity_id", hop_depth=2)

# 路径查找
paths = graph.find_path("entity_1", "entity_2", max_length=3)
```

### 4. 配置管理模式

**单一配置源**：所有配置从 `.env.example` 读取（通过 `config/model_config.py`）

```python
from app.config.model_config import (
    get_chat_model,
    get_embedding_model,
    get_entity_extraction_model
)

chat = get_chat_model()                   # 工厂模式获取模型实例
embedding = get_embedding_model()
entity_llm = get_entity_extraction_model() # 实体抽取专用模型
```

**抽象基类**：`OCRModel`, `ChatModel`, `EmbeddingModel`, `RerankModel` 定义统一接口。

### 5. 路径管理策略

**跨平台兼容**：`config/paths.py` 统一管理所有路径

```python
from app.config.paths import (
    DATA_DIR, DB_PATH, VECTOR_DB_PATH,
    UPLOAD_PATH, GRAPH_DB_PATH, KEYWORD_INDEX_PATH
)
```

---

## 数据结构

### Chunk 标准格式

所有文档分片遵循统一格式：

```python
{
    "chunk_id": "doc_001_1",        # {file_id}_{order}
    "order": 1,                     # 排序序号
    "doc_id": "doc_001",            # 所属文档
    "title_path": ["第一章 概述"],  # 标题层级路径
    "text": "完整文本内容...",       # 分片正文
    "page": 12,                     # 所在页码
    "type": "text",                 # text/table/image
    "length": 62,                   # 字符数
    "keywords": ["RAG", "检索"],     # 关键字（新增）
    "embedding": [0.12, 0.34, ...]  # 向量表示（1536维）
}
```

### 实体格式

```python
{
    "entity_id": "doc_001_0",       # {doc_id}_{index}
    "text": "RAG",                  # 实体文本
    "type": "技术概念",              # 实体类型
    "chunk_id": "doc_001_1",        # 所在分片
    "doc_id": "doc_001",            # 所属文档
    "description": ""               # 描述（可选）
}
```

### 关系格式

```python
{
    "relation_id": "doc_001_R0",    # {doc_id}_R{index}
    "source": "RAG",                 # 源实体文本
    "target": "检索增强生成",         # 目标实体文本
    "source_id": "doc_001_0",        # 源实体ID
    "target_id": "doc_001_1",        # 目标实体ID
    "relation_type": "包含关系",     # 关系类型
    "description": "",               # 关系描述
    "doc_id": "doc_001"
}
```

### 数据库表结构

**Files 表**（SQLite, `data/rag.db`）：
```sql
CREATE TABLE files (
    id TEXT PRIMARY KEY,          -- 文件 ID（毫秒时间戳）
    name TEXT NOT NULL,           -- 原始文件名
    size INTEGER NOT NULL,        -- 文件大小（字节）
    file_type TEXT NOT NULL,      -- application/pdf
    upload_time TEXT NOT NULL,    -- 上传时间
    status TEXT NOT NULL,         -- parsing/completed/failed
    file_path TEXT NOT NULL,      -- 相对路径
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

---

## API 端点

### 文件管理

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/files` | GET | 获取文件列表 |
| `/api/files` | POST | 上传文件 |
| `/api/files/<id>` | DELETE | 删除文件 |

### 对话接口

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/chat` | POST | 对话（非流式） |
| `/api/chat/stream` | POST | 流式对话（SSE） |
| `/api/chat/health` | GET | 健康检查 |

### 知识图谱接口

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/graph/stats/<doc_id>` | GET | 获取图谱统计 |
| `/api/graph/entities/<doc_id>` | GET | 获取文档实体 |
| `/api/graph/neighbors` | POST | 获取实体邻居 |
| `/api/graph/search` | POST | 搜索实体 |
| `/api/graph/recognize` | POST | 识别问题实体 |
| `/api/graph/path` | POST | 查找实体路径 |

---

## 混合检索使用示例

### 基础向量检索

```python
from app.services.user_interaction import process_conversation

result = process_conversation("什么是RAG？")
print(result['answer'])
```

### 混合检索（推荐）

```python
from app.services.user_interaction import process_conversation_hybrid

result = process_conversation_hybrid(
    question="RAG系统中包含哪些组件？",
    doc_id="doc_xxx",
    enable_vector=True,
    enable_keyword=True,
    enable_graph=True,
    weights={'vector': 0.5, 'keyword': 0.3, 'graph': 0.2}
)

# 查看识别的实体
for entity in result['recognized_entities']:
    print(f"{entity['text']} ({entity['type']})")
```

### 直接使用检索管道

```python
from app.services.user_interaction.retrieval import HybridRetrievalPipeline
from app.services.user_interaction.entity_recognizer import QueryEntityRecognizer

pipeline = HybridRetrievalPipeline()
recognizer = QueryEntityRecognizer()

# 识别实体
entities = recognizer.recognize_entities(query, doc_id)
entity_ids = recognizer.get_entity_ids(entities, doc_id)

# 混合检索
results = pipeline.retrieve(
    query=query,
    query_embedding=embedding,
    doc_id=doc_id,
    entity_ids=entity_ids
)
```

---

## 开发注意事项

### 后端
- **模型配置**：所有模型配置在 `.env.example` 中管理，不要硬编码
- **异步处理**：文件处理是异步的，通过状态字段（`parsing/completed/failed`）追踪进度
- **路径处理**：使用 `pathlib.Path` 而非字符串拼接，确保跨平台兼容
- **错误处理**：统一返回格式 `{"success": bool, "data": {...}, "error": str}`
- **向后兼容**：图谱/索引加载失败时，自动回退到纯向量检索

### 前端
- **API 基础 URL**：开发时 `http://localhost:5000`，生产环境需配置代理
- **类型定义**：所有 API 响应类型在 `types/index.ts` 中定义
- **状态管理**：使用 React Hooks（useState），暂无全局状态管理

### 调试技巧
- 后端启用 `FLASK_DEBUG=True` 可自动重载
- 查看 ChromaDB 存储：`data/vector_db/` 目录
- 查看知识图谱存储：`data/graph/` 目录
- 查看关键字索引：`data/keyword_index/` 目录
- 文件处理日志会打印到控制台（异步线程输出）

### 性能优化
- **实体抽取**：使用批量处理减少 API 调用（默认 batch_size=5）
- **图谱检索**：限制邻域跳数和最大邻居数避免性能问题
- **RRF 融合**：使用常数 k=60 平衡各路检索结果
- **缓存策略**：图谱和索引按需加载，避免频繁 I/O

---

## 依赖包说明

### 新增依赖（混合检索）

```txt
# 图谱处理
networkx==3.2.1

# 关键字检索
jieba==0.42.1
rank-bm25==0.2.2
```

### 现有依赖

```txt
# Web 框架
Flask==3.0.0
Flask-CORS==4.0.0

# PDF 处理
pdfplumber==0.11.4
PyMuPDF==1.24.10
Pillow==11.0.0

# 向量数据库
chromadb>=0.5.0

# API 调用
requests==2.32.3

# 其他
python-dotenv==1.0.0
tiktoken
numpy
tqdm==4.66.1
```
