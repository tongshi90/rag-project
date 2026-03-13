"""
Embedding 编码器模块

负责将文本转换为向量表示，封装 SiliconFlow Embedding 模型。

使用方式：
    from app.services.document_processing.embedding.encoder import EmbeddingEncoder

    encoder = EmbeddingEncoder()
    vector = encoder.encode("这是一段文本")
    vectors = encoder.encode_batch(["文本1", "文本2", ...])
"""

import time
from typing import List, Optional, Dict, Any
from app.config.model_config import get_embedding_model


class EmbeddingEncoder:
    """
    Embedding 编码器

    封装 SiliconFlow Qwen3-Embedding-4B 模型，提供文本向量化功能。
    支持单个文本编码和批量文本编码。
    """

    def __init__(self, timeout: int = 90):
        """
        初始化编码器

        Args:
            timeout: API 调用超时时间（秒）
        """
        self.model = get_embedding_model()
        self.timeout = timeout
        self._vector_dim: Optional[int] = None

    def encode(self, text: str) -> List[float]:
        """
        对单个文本进行编码

        Args:
            text: 待编码的文本

        Returns:
            向量表示（浮点数列表）

        Raises:
            ValueError: 当文本为空或编码失败时
        """
        if not text or not text.strip():
            raise ValueError("文本内容不能为空")

        try:
            start_time = time.time()
            embedding = self.model.embed(text)
            elapsed = time.time() - start_time

            # 缓存向量维度
            if self._vector_dim is None and embedding:
                self._vector_dim = len(embedding)

            if not embedding:
                raise ValueError("编码返回空向量")

            return embedding

        except Exception as e:
            raise ValueError(f"文本编码失败: {str(e)}")

    def encode_batch(
        self,
        texts: List[str],
        batch_size: int = 10,
        show_progress: bool = True
    ) -> List[List[float]]:
        """
        批量编码文本

        Args:
            texts: 待编码的文本列表
            batch_size: 每批处理的文本数量
            show_progress: 是否显示进度

        Returns:
            向量列表（与输入文本顺序一致）

        Raises:
            ValueError: 当编码失败时抛出异常，包含错误详情
        """
        if not texts:
            return []

        # 过滤空文本
        valid_texts = []
        valid_indices = []
        for idx, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(idx)
            else:
                if show_progress:
                    print(f"警告: 索引 {idx} 的文本为空，跳过")

        if not valid_texts:
            raise ValueError("没有有效的文本可供编码")

        all_embeddings: List[List[float]] = [None] * len(texts)
        failed_batches: List[Dict[str, Any]] = []

        # 分批处理
        total_batches = (len(valid_texts) + batch_size - 1) // batch_size

        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(valid_texts))
            batch_texts = valid_texts[start_idx:end_idx]

            try:
                # 调用模型批量编码
                start_time = time.time()
                batch_embeddings = self.model.embed_batch(batch_texts)
                elapsed = time.time() - start_time

                # 检查返回结果
                if not batch_embeddings or len(batch_embeddings) != len(batch_texts):
                    raise ValueError(
                        f"编码返回数量不匹配: 期望 {len(batch_texts)}, "
                        f"实际 {len(batch_embeddings) if batch_embeddings else 0}"
                    )

                # 缓存向量维度
                if self._vector_dim is None and batch_embeddings[0]:
                    self._vector_dim = len(batch_embeddings[0])

                # 将结果放入对应位置
                for i, embedding in enumerate(batch_embeddings):
                    original_idx = valid_indices[start_idx + i]
                    all_embeddings[original_idx] = embedding

                if show_progress:
                    print(
                        f"批次 {batch_idx + 1}/{total_batches} 完成 "
                        f"({len(batch_texts)} 条, 耗时 {elapsed:.2f}s)"
                    )

            except Exception as e:
                # 记录失败的批次信息
                batch_info = {
                    "batch_index": batch_idx,
                    "range": f"{start_idx}-{end_idx}",
                    "count": len(batch_texts),
                    "error": str(e)
                }
                failed_batches.append(batch_info)

                # 终止处理并抛出异常
                error_msg = (
                    f"批量编码失败（批次 {batch_idx + 1}/{total_batches}）: {str(e)}\n"
                    f"批次范围: 索引 {start_idx}-{end_idx}\n"
                    f"失败数量: {len(batch_texts)} 条"
                )
                raise ValueError(error_msg)

        # 检查是否有空结果（防御性检查）
        for idx, embedding in enumerate(all_embeddings):
            if embedding is None:
                raise ValueError(f"索引 {idx} 的编码结果为空")

        return all_embeddings

    @property
    def vector_dim(self) -> Optional[int]:
        """
        获取向量维度

        Returns:
            向量维度，如果尚未编码则返回 None
        """
        return self._vector_dim

    def get_vector_dim(self) -> int:
        """
        获取向量维度（主动获取）

        通过编码一个测试文本来获取向量维度

        Returns:
            向量维度

        Raises:
            ValueError: 当无法获取向量维度时
        """
        if self._vector_dim is not None:
            return self._vector_dim

        try:
            test_vector = self.encode("测试")
            self._vector_dim = len(test_vector)
            return self._vector_dim
        except Exception as e:
            raise ValueError(f"无法获取向量维度: {str(e)}")


# ============================================
# 全局单例
# ============================================

_encoder_instance: Optional[EmbeddingEncoder] = None


def get_encoder() -> EmbeddingEncoder:
    """
    获取全局编码器实例（单例模式）

    Returns:
        EmbeddingEncoder 实例
    """
    global _encoder_instance
    if _encoder_instance is None:
        _encoder_instance = EmbeddingEncoder()
    return _encoder_instance
