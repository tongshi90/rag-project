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

## Docker 部署

#### 后端

```bash
# 进入后端目录
cd backend

# 构建镜像
docker build -t rag-backend:latest .

# 运行容器
docker run -d \
  --name rag-backend \
  -p 5000:5000 \
  -v /home/p40/ts/rag_project/data:/app/data \
  -v /home/p40/ts/rag_project/skills:/app/skills \
  rag-backend:latest

# 查看日志
docker logs -f rag-backend

# 停止容器
docker stop rag-backend
docker rm rag-backend
```

#### 前端

```bash
# 进入前端目录
cd frontend

# 构建镜像
docker build -t rag-frontend:latest .

# 运行容器（使用 -e 参数配置后端地址）
docker run -d \
  --name rag-frontend \
  -p 8085:80 \
  -e API_BASE_URL=http://192.168.18.77:5000 \
  rag-frontend:latest

# 查看日志
docker logs -f rag-frontend

# 停止容器
docker stop rag-frontend
docker rm rag-frontend
```

**环境变量说明：**
- `API_BASE_URL`: 后端 API 地址，前端会通过此地址访问后端
- 当容器使用 `--network host` 时，可以使用 `localhost:5000`
- 当容器独立网络时，需要使用宿主机 IP 或容器名称

### 构建脚本

将以下脚本保存为 `build.sh`（Linux/Mac）或 `build.bat`（Windows）：

**build.sh**
```bash
#!/bin/bash
echo "Building RAG System Docker images..."

# 构建后端镜像
echo "Building backend image..."
cd backend
docker build -t rag-backend:latest .
cd ..

# 构建前端镜像
echo "Building frontend image..."
cd frontend
docker build -t rag-frontend:latest .
cd ..

echo "Build complete!"
```

**build.bat**
```batch
@echo off
echo Building RAG System Docker images...

REM 构建后端镜像
echo Building backend image...
cd backend
docker build -t rag-backend:latest .
cd ..

REM 构建前端镜像
echo Building frontend image...
cd frontend
docker build -t rag-frontend:latest .
cd ..

echo Build complete!
pause
```

### 启动脚本

将以下脚本保存为 `start.sh`（Linux/Mac）或 `start.bat`（Windows）：

**start.sh**
```bash
#!/bin/bash
echo "Starting RAG System..."

# 获取本机 IP（Linux）
LOCAL_IP=$(hostname -I | awk '{print $1}')
# 如果获取失败，使用 Docker 网关 IP
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="172.17.0.1"
fi

# 启动后端
docker run -d \
  --name rag-backend \
  --restart unless-stopped \
  -p 5000:5000 \
  -v /home/p40/ts/rag_project/data:/app/data \
  -v /home/p40/ts/rag_project/skills:/app/skills \
  --env-file backend/.env \
  rag-backend:latest

# 启动前端（配置后端地址）
docker run -d \
  --name rag-frontend \
  --restart unless-stopped \
  -p 80:80 \
  -e API_BASE_URL=http://${LOCAL_IP}:5000 \
  --link rag-backend:rag-backend \
  rag-frontend:latest

echo "Services started!"
echo "Frontend: http://localhost"
echo "Backend: http://localhost:5000"
echo "Frontend API URL: http://${LOCAL_IP}:5000"
echo "Data mounted: /home/p40/ts/rag_project/data -> /app/data"
echo "Skills mounted: /home/p40/ts/rag_project/skills -> /app/skills"
```

**start.bat**
```batch
@echo off
echo Starting RAG System...

REM 获取本机 IP（Windows - 使用默认网关）
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do set LOCAL_IP=%%a
set LOCAL_IP=%LOCAL_IP: =%
if "%LOCAL_IP%"=="" set LOCAL_IP=172.17.0.1

REM 启动后端
docker run -d ^
  --name rag-backend ^
  --restart unless-stopped ^
  -p 5000:5000 ^
  -v /home/p40/ts/rag_project/data:/app/data ^
  -v /home/p40/ts/rag_project/skills:/app/skills ^
  --env-file backend\.env ^
  rag-backend:latest

REM 启动前端（配置后端地址）
docker run -d ^
  --name rag-frontend ^
  --restart unless-stopped ^
  -p 80:80 ^
  -e API_BASE_URL=http://%LOCAL_IP%:5000 ^
  --link rag-backend:rag-backend ^
  rag-frontend:latest

echo Services started!
echo Frontend: http://localhost
echo Backend: http://localhost:5000
echo Frontend API URL: http://%LOCAL_IP%:5000
echo Data mounted: /home/p40/ts/rag_project/data -^> /app/data
echo Skills mounted: /home/p40/ts/rag_project/skills -^> /app/skills
pause
```

### 停止脚本

**stop.sh**
```bash
#!/bin/bash
echo "Stopping RAG System..."
docker stop rag-backend rag-frontend
docker rm rag-backend rag-frontend
echo "Services stopped!"
```

**stop.bat**
```batch
@echo off
echo Stopping RAG System...
docker stop rag-backend rag-frontend
docker rm rag-backend rag-frontend
echo Services stopped!
pause
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
