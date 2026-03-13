"""
用户交互阶段 (User Interaction)

本阶段是 RAG 系统的在线交互阶段，负责处理用户查询并生成答案。

包含的子模块：
-------------
- question_splitter: 问题拆分（将复杂问题拆分为子问题）
- entity_recognizer: 问题实体识别
- query_encoder: 问题向量化
- retrieval: 向量检索 + 重排序 + 混合检索
- graph_retrieval: 图谱检索
- context_enricher: 上下文增强
- generator: LLM 答案生成

使用示例：
---------
```python
from app.services.user_interaction import process_conversation, process_conversation_hybrid

# 普通检索（向量 + 重排序）
result = process_conversation("什么是RAG？它有哪些优势？")
print(result['answer'])

# 混合检索（向量 + 关键字 + 图谱）
result = process_conversation_hybrid("什么是RAG？", doc_id="xxx")
print(result['answer'])
```
"""

# 完整对话处理流程
from .conversation_processor import (
    process_conversation,
    process_conversation_simple,
    chat,
    process_conversation_hybrid,  # 新增
)

# 单独使用各个步骤
from .question_splitter import split_question
from .query_encoder import encode_query, encode_queries
from .retrieval import retrieve, batch_retrieve, HybridRetrievalPipeline  # 新增
from .generator import generate_answer, generate_answer_for_sub_questions
from .entity_recognizer import QueryEntityRecognizer, recognize_query_entities  # 新增
from .graph_retrieval import GraphRetriever, get_graph_retriever  # 新增
from .context_enricher import ContextEnricher  # 新增

__all__ = [
    # 完整流程
    'process_conversation',
    'process_conversation_simple',
    'chat',
    'process_conversation_hybrid',  # 新增

    # 单独步骤
    'split_question',
    'encode_query',
    'encode_queries',
    'retrieve',
    'batch_retrieve',
    'generate_answer',
    'generate_answer_for_sub_questions',

    # 新增模块
    'HybridRetrievalPipeline',
    'QueryEntityRecognizer',
    'recognize_query_entities',
    'GraphRetriever',
    'get_graph_retriever',
    'ContextEnricher',
]
