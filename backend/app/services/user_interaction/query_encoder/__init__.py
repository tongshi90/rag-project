"""
问题向量化模块 (Query Encoder)

负责将用户问题转换为向量，用于后续检索。

使用示例：
    from app.services.user_interaction.query_encoder import encode_query, encode_queries

    vector = encode_query("什么是RAG？")
    vectors = encode_queries(["问题1", "问题2"])
"""

from .query_encoder import (
    QueryEncoder,
    get_query_encoder,
    encode_query,
    encode_queries,
)

__all__ = [
    'QueryEncoder',
    'get_query_encoder',
    'encode_query',
    'encode_queries',
]
