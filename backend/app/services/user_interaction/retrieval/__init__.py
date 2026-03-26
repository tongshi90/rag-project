"""
检索模块 (Retrieval)

负责根据问题向量检索相关 chunk，并进行重排序。

使用示例：
    from app.services.user_interaction.retrieval import retrieve, batch_retrieve

    results = retrieve("什么是RAG？", query_embedding, top_k=5)
"""

from .retrieval import (
    VectorSearcher,
    Reranker,
    RetrievalPipeline,
    retrieve,
    batch_retrieve,
)

__all__ = [
    'VectorSearcher',
    'Reranker',
    'RetrievalPipeline',
    'retrieve',
    'batch_retrieve',
]
