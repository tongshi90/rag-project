# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 提供项目指导。

---

## 项目概述

这是一个 **RAG（检索增强生成）问答系统**，采用 React TypeScript 前端 + Python Flask 后端架构。系统允许用户上传 PDF 文档，自动解析提取内容并构建向量索引，支持 AI 问答。

**核心特性**：
- 文档上传与解析（PDF）
- 向量化存储（ChromaDB）
- 语义检索与重排序
- 流式 AI 对话
- 技能卡片管理系统
- 开放 API 接口

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

# 测试 API
curl http://localhost:5000/health
curl http://localhost:5000/api/files
curl http://localhost:5000/api/chat/health
```

---

## 核心架构

### 后端分层架构

| 层次 | 目录 | 职责 | 关键文件 |
|------|------|------|----------|
| **路由层** | `api/` | HTTP 请求处理、参数验证 | `files.py`, `chat.py`, `skills.py`, `skill_files.py` |
| **模型层** | `models/` | 数据结构定义、SQLite CRUD | `file.py`, `skill_card.py` |
| **服务层** | `services/` | 业务逻辑、RAG 核心处理 | 见下方详细说明 |
| **配置层** | `config/` | 环境配置、模型配置、路径管理 | `model_config.py`, `paths.py` |

### 服务层模块化设计

```
services/
├── document_processing/          # 文档处理
│   ├── document_processor.py     # 流程编排主入口
│   ├── splitter/                 # PDF → Chunks
│   │   ├── text_splitter.py      # 文本分片
│   │   ├── form_splitter.py      # 表单分片
│   │   └── img_splitter.py       # 图片分片
│   ├── validator/                # 质量检测
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
└── user_interaction/             # 用户交互
    ├── question_splitter/        # 问题拆分
    ├── entity_recognizer/        # 实体识别
    ├── query_encoder/            # 问题向量化
    ├── retrieval/                # 检索 + 重排序
    ├── graph_retrieval/          # 图谱检索
    ├── context_enricher/         # 上下文增强
    ├── generator/                # LLM 生成
    └── conversation_processor.py # 对话处理主入口
```

---

## 关键设计模式

### 1. 文档处理流程

**入口**：`services/document_processing/document_processor.py`

```python
from app.services import parse_pdf

# 处理 PDF 文档
result = parse_pdf(file_path, doc_id)
# 返回: {"success": True, "steps": {...}, "total_elapsed": ...}
```

**异步执行**：文件上传后，`api/files.py` 在后台线程中调用处理流程，立即返回响应。

### 2. 对话处理流程

**入口**：`services/user_interaction/conversation_processor.py`

```python
from app.services.user_interaction import process_conversation

result = process_conversation(
    question="用户问题",
    conversation_history=None,
    top_k=5,
    retrieval_top_k=20
)
# 返回: {"success": True, "answer": "...", "total_elapsed": ...}
```

**流程**：
1. 问题拆分（LLM）
2. 问题向量化
3. 向量检索（ChromaDB）
4. 重排序（Rerank 模型）
5. 答案生成（LLM）

### 3. 配置管理模式

**单一配置源**：所有配置从 `.env.example` 读取（通过 `config/model_config.py`）

```python
from app.config.model_config import (
    get_chat_model,
    get_embedding_model,
    get_entity_extraction_model
)

chat = get_chat_model()                   # 工厂模式获取模型实例
embedding = get_embedding_model()
entity_llm = get_entity_extraction_model()
```

**抽象基类**：`OCRModel`, `ChatModel`, `EmbeddingModel`, `RerankModel` 定义统一接口。

### 4. 路径管理策略

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
    "keywords": ["RAG", "检索"],     # 关键字
    "embedding": [0.12, 0.34, ...]  # 向量表示
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

**Skill Cards 表**（SQLite）：
```sql
CREATE TABLE skill_cards (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    skill_code TEXT UNIQUE NOT NULL,
    published BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

---

## API 端点

### 文件管理

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/files` | GET | 获取文件列表 |
| `/api/files/upload` | POST | 上传文件 |
| `/api/files/<id>` | GET | 获取单个文件 |
| `/api/files/<id>` | DELETE | 删除文件 |
| `/api/files/all` | DELETE | 删除所有文件 |
| `/api/files/<id>/stats` | GET | 获取文件统计 |

### 对话接口

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/chat` | POST | 对话（非流式） |
| `/api/chat/stream` | POST | 流式对话（SSE） |
| `/api/chat/health` | GET | 健康检查 |

### 技能卡片管理

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/skills` | GET | 获取技能列表 |
| `/api/skills` | POST | 创建技能 |
| `/api/skills/<id>` | GET | 获取单个技能 |
| `/api/skills/<id>` | PUT | 更新技能 |
| `/api/skills/<id>` | DELETE | 删除技能 |
| `/api/skills/<id>/publish` | PUT | 发布技能 |
| `/api/skills/<id>/unpublish` | PUT | 取消发布 |

### 技能文件管理

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/skills/<id>/files` | GET | 列出技能文件 |
| `/api/skills/<id>/files/content` | GET | 获取文件内容 |
| `/api/skills/<id>/files` | POST | 创建文件 |
| `/api/skills/<id>/files` | PUT | 更新文件 |
| `/api/skills/<id>/files` | DELETE | 删除文件 |

### 开放 API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/ask` | POST | 开放问答接口 |

---

## 开发注意事项

### 后端
- **模型配置**：所有模型配置在 `.env.example` 中管理，不要硬编码
- **异步处理**：文件处理是异步的，通过状态字段（`parsing/completed/failed`）追踪进度
- **路径处理**：使用 `pathlib.Path` 而非字符串拼接，确保跨平台兼容
- **错误处理**：统一返回格式 `{"success": bool, "data": {...}, "error": str}`
- **CORS**：开发环境允许所有源访问

### 前端
- **API 基础 URL**：开发时 `http://127.0.0.1:5000`，生产环境需配置代理
- **类型定义**：所有 API 响应类型在 `types/index.ts` 中定义
- **状态管理**：使用 React Hooks（useState），暂无全局状态管理

### 调试技巧
- 后端启用 `FLASK_DEBUG=True` 可自动重载
- 查看 ChromaDB 存储：`data/vector_db/` 目录
- 查看知识图谱存储：`data/graph/` 目录
- 查看关键字索引：`data/keyword_index/` 目录
- 文件处理日志会打印到控制台（异步线程输出）

---

## 依赖包说明

### 后端依赖

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

# 图谱处理
networkx==3.2.1

# 关键字检索
jieba==0.42.1
rank-bm25==0.2.2

# API 调用
requests==2.32.3

# 其他
python-dotenv==1.0.0
tiktoken
numpy
tqdm==4.66.1
```

### 前端依赖

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-markdown": "^10.1.0",
    "remark-gfm": "^4.0.1"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.2.2",
    "vite": "^5.0.8"
  }
}
```

---

## 模型配置说明

系统使用 **SiliconFlow** 提供的模型服务：

| 功能 | 模型 | 用途 |
|------|------|------|
| OCR | Qwen/Qwen2-VL-72B-Instruct | 图片文字识别 |
| Chat | Qwen/Qwen2.5-72B-Instruct | 对话生成 |
| Embedding | Qwen/Qwen3-Embedding-4B | 文本向量化 |
| Rerank | Qwen/Qwen3-Reranker-0.6B | 检索结果重排序 |
| Text Splitter | Qwen/Qwen2.5-7B-Instruct | 分片优化/问题拆分 |
| Entity Extraction | Qwen/Qwen2.5-7B-Instruct | 实体抽取 |

配置文件：`backend/.env.example`

---

## 技能卡片系统

技能卡片是一个可发布、可管理的技能包系统：

### 技能生命周期

```
创建技能 → 编辑文件 → 发布技能 → [只读] → 取消发布 → [可编辑]
```

### 技能文件结构

```
data/skills/
├── skill_code_1/           # 技能目录
│   ├── config.yaml
│   ├── main.py
│   └── README.md
├── skill_code_2/
│   └── ...
└── _published/             # 发布的技能包（zip）
    ├── skill_code_1.zip
    └── skill_code_2.zip
```

### 发布状态

- **未发布**：可编辑技能信息和文件
- **已发布**：只读模式，生成 zip 包，不可修改或删除

---

## Docker 部署

项目支持 Docker 容器化部署：

### 构建镜像
```bash
docker build -t rag-app .
```

### 运行容器
```bash
docker run -p 3000:3000 -p 5000:5000 rag-app
```

### 环境变量
- `API_BASE_URL`：后端 API 地址（前端配置）

---

## 项目目录结构

```
rag_project/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── api/               # API 路由
│   │   ├── config/            # 配置模块
│   │   ├── models/            # 数据模型
│   │   └── services/          # 业务服务
│   ├── data/                  # 数据目录
│   │   ├── upload/            # 上传文件
│   │   ├── vector_db/         # 向量数据库
│   │   ├── graph/             # 知识图谱
│   │   ├── keyword_index/     # 关键字索引
│   │   └── rag.db             # SQLite 数据库
│   ├── requirements.txt
│   └── run.py
├── frontend/                   # 前端服务
│   ├── src/
│   │   ├── components/        # React 组件
│   │   ├── services/          # API 服务
│   │   ├── types/             # TypeScript 类型
│   │   └── config.ts          # 配置文件
│   └── package.json
└── CLAUDE.md                   # 本文件
```
