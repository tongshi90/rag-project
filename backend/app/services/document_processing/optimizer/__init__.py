"""
Chunk 优化模块

负责使用 LLM 分析异常 chunk 并给出合并/拆分建议。
"""

from app.services.document_processing.optimizer.chunk_optimizer import optimize_chunks

__all__ = [
    'optimize_chunks',
]
