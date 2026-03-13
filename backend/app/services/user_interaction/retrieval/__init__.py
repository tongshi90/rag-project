"""
检索模块 (Retrieval)

负责根据问题向量检索相关 chunk，并进行重排序。
支持混合检索：向量检索 + 关键字检索 + 图谱检索

使用示例：
    from app.services.user_interaction.retrieval import retrieve, batch_retrieve

    results = retrieve("什么是RAG？", query_embedding, top_k=5)

    # 使用混合检索
    from app.services.user_interaction.retrieval import HybridRetrievalPipeline
    pipeline = HybridRetrievalPipeline()
    results = pipeline.retrieve("什么是RAG？", query_embedding, doc_id="xxx")
"""

from .retrieval import (
    VectorSearcher,
    Reranker,
    RetrievalPipeline,
    HybridRetrievalPipeline,
    retrieve,
    batch_retrieve,
)

__all__ = [
    'VectorSearcher',
    'Reranker',
    'RetrievalPipeline',
    'HybridRetrievalPipeline',
    'retrieve',
    'batch_retrieve',
]
