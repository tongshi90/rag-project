# 用户提问到返回结果的业务流程

## 一、整体流程图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           用户交互阶段                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  用户提问 → API 接口 → 四步处理 → 流式返回结果                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、详细流程步骤

### 步骤 1：用户发送问题
**入口**：前端 `App.tsx` → `apiService.sendMessageStream()`

```typescript
// frontend/src/App.tsx
await apiService.sendMessageStream(content, (chunk) => {
  // 处理返回的数据片段
});
```

**调用 API**：`POST http://localhost:5000/api/chat/stream`

---

### 步骤 2：后端 API 接收请求
**文件**：`backend/app/api/chat.py`

**方法**：`chat_stream()`

**作用**：
- 接收用户的提问
- 获取对话历史（可选）
- 获取参数 `top_k`（重排序后的结果数，默认5）
- 获取参数 `retrieval_top_k`（初始检索数量，默认20）

```python
@api_bp.route('/chat/stream', methods=['POST'])
def chat_stream():
    data = request.get_json()
    user_message = data['message']
    conversation_history = data.get('conversation_history')
    top_k = data.get('top_k', 5)
    retrieval_top_k = data.get('retrieval_top_k', 20)

    return Response(
        stream_with_context(_stream_response(user_message, conversation_history, top_k, retrieval_top_k)),
        content_type='text/event-stream'
    )
```

---

### 步骤 3：问题拆分 (Question Splitter)
**文件**：`backend/app/api/chat.py` → `_stream_response()`

**调用方法**：`split_question()`

**来源**：`backend/app/services/user_interaction/question_splitter/question_splitter.py`

**作用**：
- 将用户的复杂问题拆分为多个子问题
- 当前使用基于规则的拆分（按标点符号：；、？和、还有、另外等）
- 例如：`"什么是RAG？它有哪些优势？"` → `["什么是RAG？", "它有哪些优势？"]`

```python
sub_questions = split_question(user_message, use_llm=False)
# 返回: ["子问题1", "子问题2"]
```

---

### 步骤 4：问题向量化 (Query Encoder)
**文件**：`backend/app/api/chat.py` → `_stream_response()`

**调用方法**：
1. `get_query_encoder()` - 获取编码器实例
2. `encoder.encode_queries(sub_questions)` - 批量向量化

**来源**：`backend/app/services/user_interaction/query_encoder/query_encoder.py`

**作用**：
- 将每个子问题转换为向量表示
- 使用 SiliconFlow 的 Qwen3-Embedding-4B 模型
- 向量维度：1536

```python
encoder = get_query_encoder()
query_embeddings = encoder.encode_queries(sub_questions)
# 返回: [[0.12, 0.34, ...], [0.56, 0.78, ...]]  # 每个子问题一个向量
```

---

### 步骤 5：检索和重排序 (Retrieval)
**文件**：`backend/app/api/chat.py` → `_stream_response()`

**调用方法**：
1. 创建 `RetrievalPipeline` 实例
2. 调用 `batch_retrieve()` 批量检索

**来源**：`backend/app/services/user_interaction/retrieval/retrieval.py`

**作用**：
- **向量检索**：根据问题向量从 ChromaDB 检索相似的分片
- **重排序**：对检索结果进行重新排序，提高相关性
- 返回每个子问题的 Top K 个分片

```python
retrieval_pipeline = RetrievalPipeline(
    retrieval_top_k=retrieval_top_k,  # 初始检索20个
    final_top_k=top_k                  # 最终返回5个
)
all_retrieved_chunks = retrieval_pipeline.batch_retrieve(
    queries=sub_questions,
    query_embeddings=query_embeddings,
    encoder=encoder
)
```

**子流程**：
1. `VectorSearcher.search()` - 向量相似度检索
2. `Reranker.rerank()` - 基于分数和关键词匹配重排序

---

### 步骤 6：LLM 生成答案 (Generator)
**文件**：`backend/app/api/chat.py` → `_stream_response()`

**调用方法**：`generate_answer_stream()`

**来源**：`backend/app/services/user_interaction/generator/generator.py`

**作用**：
- 将检索到的分片组织成上下文
- 调用 LLM（SiliconFlow Qwen2.5-72B）生成答案
- 以流式方式逐字返回结果

```python
# 单个问题直接流式生成
for chunk in generate_answer_stream(
    query=sub_questions[0],
    retrieved_chunks=all_retrieved_chunks[0],
    conversation_history=conversation_history
):
    yield f"data: {json.dumps({'content': chunk})}\n\n"
```

**子流程**：
1. `ContextBuilder.build_context()` - 构建上下文文本
2. `AnswerGenerator._build_prompt()` - 构建提示词
3. `SiliconFlowChat.chat_stream()` - LLM 流式调用

---

### 步骤 7：流式返回结果
**格式**：Server-Sent Events (SSE)

```
data: {"content": "您"}
data: {"content": "好"}
data: {"content": "！"}
...
data: [DONE]
```

**前端处理**：`frontend/src/services/api.ts` → `sendMessageStream()`

```typescript
const reader = response.body?.getReader();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  // 解析 SSE 数据并调用回调
  if (line.startsWith('data: ')) {
    const parsed = JSON.parse(data);
    onChunk(parsed.content);  // 更新 UI
  }
}
```

---

## 三、核心文件说明

### 流程编排文件
| 文件 | 作用 |
|------|------|
| `conversation_processor.py` | 主流程入口，整合四个步骤 |
| `chat.py` | API 路由，处理 HTTP 请求和 SSE 响应 |

### 四个子模块
| 模块 | 文件 | 作用 |
|------|------|------|
| 问题拆分 | `question_splitter.py` | 将复杂问题拆分为子问题 |
| 问题向量化 | `query_encoder.py` | 将问题转换为向量 |
| 检索重排序 | `retrieval.py` | 向量检索 + 重排序 |
| 答案生成 | `generator.py` | LLM 生成答案 |

### 配置文件
| 文件 | 作用 |
|------|------|
| `model_config.py` | 模型配置（Chat、Embedding） |
| `vector_store.py` | ChromaDB 向量存储封装 |

---

## 四、参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `retrieval_top_k` | 20 | 初始向量检索返回的分片数量 |
| `top_k` | 5 | 重排序后最终返回的分片数量 |
| `use_llm` | False | 是否使用 LLM 进行问题拆分 |

---

## 五、时序图

```
用户 → 前端 → API(chat_stream) → 问题拆分 → 向量化 → 检索重排序 → LLM生成 → 流式返回 → 前端 → 用户
```
