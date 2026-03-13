"""
向量化模块

负责将 chunk 转换为向量并存储到向量数据库。
这是文档处理流程的第四步。

使用方式：
    from app.services.document_processing.embedding import (
        embed_and_store_chunks,
        get_encoder,
        get_vector_store
    )

    # 完整向量化流程
    result = embed_and_store_chunks(chunks, doc_id)

    # 单独使用编码器
    encoder = get_encoder()
    vector = encoder.encode("文本")

    # 单独使用向量存储
    vector_store = get_vector_store()
    results = vector_store.search_by_text("查询文本", encoder, top_k=5)
"""

# 批量处理（主入口）
from .batch_processor import (
    embed_and_store_chunks,
    BatchProcessor
)

# 编码器
from .encoder import (
    EmbeddingEncoder,
    get_encoder
)

# 向量存储
from .vector_store import (
    VectorStore,
    get_vector_store,
    reset_vector_store
)

__all__ = [
    # 主入口函数
    'embed_and_store_chunks',

    # 批量处理器
    'BatchProcessor',

    # 编码器
    'EmbeddingEncoder',
    'get_encoder',

    # 向量存储
    'VectorStore',
    'get_vector_store',
    'reset_vector_store',
]
