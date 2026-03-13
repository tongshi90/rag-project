# 混合增强 RAG 智能问答系统

基于 React + Python Flask 的检索增强生成（RAG）系统，支持 PDF 文档上传、自动解析、向量化存储和 AI 问答。

**核心特性**：向量检索 + 关键字检索(BM25) + 知识图谱检索的混合增强架构。

## 系统架构

```
离线阶段（文档处理）：
PDF → 拆分 → 验证 → 优化 → 实体抽取 → 关系抽取 → 知识图谱构建 → 关键字索引 → 向量化 → 存储

在线阶段（用户交互）：
查询 → 实体识别 → 混合检索(向量+关键字+图谱) → RRF融合 → 重排序 → LLM生成 → 答案
```

## 技术栈

### 前端
- React 18 + TypeScript
- Vite 构建工具
- ReactMarkdown（Markdown 渲染）

### 后端
- Python 3.10+
- Flask Web 框架
- ChromaDB 向量数据库
- SiliconFlow API（LLM + Embedding）
- pdfplumber（PDF 解析）
- NetworkX（知识图谱）
- jieba（中文分词）
- rank-bm25（BM25 检索）

## 快速开始

### 前端开发

```bash
cd frontend
npm install
npm run dev    # http://localhost:3000
```

### 后端开发

```bash
cd backend
pip install -r requirements.txt
python run.py   # http://0.0.0.0:5000
```

### 配置环境

复制 `backend/.env.example` 为 `backend/.env`，填入你的 API 密钥：

```env
SILICONFLOW_API_KEY=your_api_key_here
```

## 项目结构

```
rag_project/
├── frontend/              # React 前端
│   ├── src/
│   │   ├── components/   # 组件
│   │   ├── types/        # 类型定义
│   │   └── index.css     # 全局样式
│   └── package.json
│
├── backend/              # Flask 后端
│   ├── app/
│   │   ├── api/         # API 路由
│   │   │   ├── files.py      # 文件管理
│   │   │   ├── chat.py       # 对话接口
│   │   │   └── graph.py      # 知识图谱接口
│   │   ├── config/      # 配置管理
│   │   ├── models/      # 数据模型
│   │   └── services/    # 业务逻辑
│   │       ├── document_processing/   # 离线文档处理
│   │       │   ├── splitter/           # 文档拆分
│   │       │   ├── validator/          # 质量检测
│   │       │   ├── optimizer/          # LLM 优化
│   │       │   ├── entity_extraction/  # 实体抽取
│   │       │   ├── relation_extraction/# 关系抽取
│   │       │   ├── graph_builder/      # 知识图谱
│   │       │   ├── keyword_index/      # 关键字索引
│   │       │   └── embedding/          # 向量化
│   │       └── user_interaction/       # 在线用户交互
│   │           ├── question_splitter/   # 问题拆分
│   │           ├── entity_recognizer/   # 实体识别
│   │           ├── query_encoder/       # 问题向量化
│   │           ├── retrieval/           # 混合检索
│   │           ├── graph_retrieval/     # 图谱检索
│   │           ├── context_enricher/    # 上下文增强
│   │           └── generator/           # 答案生成
│   ├── data/            # 数据存储
│   │   ├── rag.db       # SQLite 数据库
│   │   ├── vector_db/   # ChromaDB 向量库
│   │   ├── graph/       # 知识图谱存储
│   │   └── keyword_index/  # BM25 索引
│   └── requirements.txt
│
├── CLAUDE.md             # Claude Code 开发指南
└── 生产级别RAG.md        # RAG 系统设计文档
```

## 核心功能

### 文档处理
- [x] PDF 文档上传与解析
- [x] 文本智能分块（基于标题层级）
- [x] 质量检测（8种验证规则）
- [x] LLM 辅助分块优化
- [x] **实体抽取**（8种类型：人物/地点/组织/时间/数量/产品/技术概念/事件）
- [x] **关系抽取**（实体间关系识别）
- [x] **知识图谱构建**（NetworkX）
- [x] **关键字索引**（jieba + BM25）
- [x] 向量化存储（ChromaDB）

### 检索增强
- [x] 问题智能拆分
- [x] **问题实体识别**
- [x] 向量检索
- [x] **关键字检索**（BM25）
- [x] **图谱邻域检索**
- [x] **RRF 结果融合**
- [x] Cross-Encoder 重排序
- [x] LLM 流式回答生成

### 管理功能
- [x] 文件管理（上传/删除/列表）
- [x] **知识图谱查询**
- [x] **实体搜索**
- [x] **关系路径查询**

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
| `/api/chat/stream` | POST | 流式对话 |
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

## 混合检索配置

在 `.env` 中配置检索权重：

```env
# 检索权重配置
VECTOR_WEIGHT=0.5      # 向量检索权重
KEYWORD_WEIGHT=0.3    # 关键字检索权重
GRAPH_WEIGHT=0.2      # 图谱检索权重

# 图谱检索配置
GRAPH_HOP_DEPTH=2     # 邻域跳数
GRAPH_MAX_NEIGHBORS=20 # 最大邻居数
```

## 开发文档

- **CLAUDE.md** - Claude Code AI 助手开发指南
- **生产级别RAG.md** - 完整的 RAG 系统设计文档

## 使用示例

### 基础对话（向量检索）

```python
from app.services.user_interaction import process_conversation

result = process_conversation("什么是RAG？")
print(result['answer'])
```

### 混合检索对话（向量+关键字+图谱）

```python
from app.services.user_interaction import process_conversation_hybrid

result = process_conversation_hybrid(
    question="什么是RAG？",
    doc_id="xxx",
    enable_vector=True,
    enable_keyword=True,
    enable_graph=True
)
print(result['answer'])
print(result['recognized_entities'])  # 识别的实体
```

### 查询知识图谱

```python
from app.services.document_processing.graph_builder import get_graph_builder

graph = get_graph_builder()
graph.load_graph("doc_id")

# 获取实体邻居
neighbors = graph.get_neighbors("entity_id", hop_depth=2)

# 查找实体路径
paths = graph.find_path("entity_1", "entity_2", max_length=3)
```

## 性能特点

- **混合检索**：结合向量、关键字、图谱三种检索方式，提升召回率和准确率
- **智能融合**：使用 RRF 算法融合多路检索结果
- **实体增强**：通过知识图谱提供实体上下文，增强答案相关性
- **中文优化**：使用 jieba 分词和 BM25 算法，优化中文检索效果

## 许可证

MIT
