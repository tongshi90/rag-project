"""
问题向量化模块

负责将用户问题转换为向量，用于后续检索。
复用文档处理阶段的 EmbeddingEncoder。
"""

from typing import List, Dict, Any, Optional
from app.services.document_processing.embedding.encoder import EmbeddingEncoder, get_encoder


class QueryEncoder:
    """
    问题编码器

    封装 EmbeddingEncoder，提供问题向量化功能。
    支持单个问题和批量问题的编码。
    """

    def __init__(self, encoder: Optional[EmbeddingEncoder] = None):
        """
        初始化问题编码器

        Args:
            encoder: EmbeddingEncoder 实例（可选，默认使用全局实例）
        """
        self.encoder = encoder or get_encoder()

    def encode_query(self, query: str) -> List[float]:
        """
        对单个问题进行编码

        Args:
            query: 用户问题

        Returns:
            问题向量表示
        """
        return self.encoder.encode(query)

    def encode_queries(self, queries: List[str]) -> List[List[float]]:
        """
        批量编码问题

        Args:
            queries: 问题列表

        Returns:
            问题向量列表
        """
        return self.encoder.encode_batch(queries, batch_size=10, show_progress=False)

    def encode_sub_questions(
        self,
        sub_questions: List[str],
        show_progress: bool = False
    ) -> Dict[str, List[float]]:
        """
        编码子问题列表，返回映射字典

        Args:
            sub_questions: 子问题列表
            show_progress: 是否显示进度

        Returns:
            问题到向量的映射字典
        """
        if not sub_questions:
            return {}

        embeddings = self.encoder.encode_batch(
            sub_questions,
            batch_size=10,
            show_progress=show_progress
        )

        return {
            question: embedding
            for question, embedding in zip(sub_questions, embeddings)
        }


# 全局单例
_query_encoder_instance: Optional[QueryEncoder] = None


def get_query_encoder() -> QueryEncoder:
    """
    获取全局问题编码器实例（单例模式）

    Returns:
        QueryEncoder 实例
    """
    global _query_encoder_instance
    if _query_encoder_instance is None:
        _query_encoder_instance = QueryEncoder()
    return _query_encoder_instance


# 便捷函数
def encode_query(query: str) -> List[float]:
    """编码单个问题的便捷函数"""
    encoder = get_query_encoder()
    return encoder.encode_query(query)


def encode_queries(queries: List[str]) -> List[List[float]]:
    """批量编码问题的便捷函数"""
    encoder = get_query_encoder()
    return encoder.encode_queries(queries)
