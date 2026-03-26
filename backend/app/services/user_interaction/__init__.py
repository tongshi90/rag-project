"""
用户交互阶段 (User Interaction)

本阶段是 RAG 系统的在线交互阶段，负责处理用户查询并生成答案。

包含的子模块：
-------------
- question_splitter: 问题拆分（将复杂问题拆分为子问题）
- query_encoder: 问题向量化
- retrieval: 向量检索 + 重排序
- generator: LLM 答案生成
- intent_recognition: 意图识别（预测问题最相关的知识库）

使用示例：
---------
```python
from app.services.user_interaction import process_conversation

# 普通检索（向量 + 重排序）
result = process_conversation("什么是RAG？它有哪些优势？")
print(result['answer'])
```
"""

# 完整对话处理流程
from .conversation_processor import (
    process_conversation,
    process_conversation_simple,
    chat,
    process_conversation_with_intent,  # 智能两阶段召回
)

# 单独使用各个步骤
from .question_splitter import split_question
from .query_encoder import encode_query, encode_queries
from .retrieval import retrieve, batch_retrieve
from .generator import generate_answer, generate_answer_for_sub_questions
from .intent_recognition import predict_knowledge_base, get_kb_id_by_name

__all__ = [
    # 完整流程
    'process_conversation',
    'process_conversation_simple',
    'chat',
    'process_conversation_with_intent',  # 智能两阶段召回

    # 单独步骤
    'split_question',
    'encode_query',
    'encode_queries',
    'retrieve',
    'batch_retrieve',
    'generate_answer',
    'generate_answer_for_sub_questions',

    # 意图识别
    'predict_knowledge_base',
    'get_kb_id_by_name',
]
