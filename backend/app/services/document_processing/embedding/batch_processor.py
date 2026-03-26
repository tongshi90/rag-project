"""
批量处理器模块

负责大规模 chunks 的批量向量化处理，支持进度跟踪和错误处理。

使用方式：
    from app.services.document_processing.embedding.batch_processor import BatchProcessor

    processor = BatchProcessor(batch_size=10)
    result = processor.process_and_store(chunks, vector_store, encoder)
"""

import time
import logging
from typing import List, Dict, Optional, Any
from .encoder import EmbeddingEncoder
from .vector_store import VectorStore

# 配置日志
logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    批量处理器

    处理大规模 chunk 的向量化流程：
    1. 数据预处理
    2. 批量编码
    3. 向量数据库存储
    4. 结果统计
    """

    def __init__(
        self,
        batch_size: int = 10,
        show_progress: bool = True,
        fail_fast: bool = True
    ):
        """
        初始化批量处理器

        Args:
            batch_size: 每批处理的 chunk 数量
            show_progress: 是否显示进度信息
            fail_fast: 遇到错误时是否立即终止（True 则终止，False 则记录并继续）
        """
        self.batch_size = batch_size
        self.show_progress = show_progress
        self.fail_fast = fail_fast

    def process_and_store(
        self,
        chunks: List[Dict],
        vector_store: VectorStore,
        encoder: EmbeddingEncoder,
        doc_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        批量处理 chunks 并存储到向量数据库

        Args:
            chunks: 优化后的分片列表（第三步输出）
            vector_store: 向量存储实例
            encoder: 编码器实例
            doc_id: 文档 ID（可选，用于验证）

        Returns:
            处理结果，包含:
                - total_chunks: 总分片数
                - success_count: 成功数量
                - failed_count: 失败数量
                - failed_chunk_ids: 失败的分片 ID 列表
                - vector_store_stats: 向量库统计信息
                - elapsed_time: 处理耗时（秒）

        Raises:
            ValueError: 当处理失败时抛出异常
        """
        start_time = time.time()
        actual_doc_id = doc_id or (chunks[0].get('doc_id') if chunks else 'unknown')

        # 预处理：验证和清理数据
        valid_chunks = self._preprocess_chunks(chunks, doc_id)

        if not valid_chunks:
            logger.error(f"[批量向量化] 没有有效的 chunks 可供处理 (输入: {len(chunks)})")
            raise ValueError("没有有效的 chunks 可供处理")

        total_count = len(valid_chunks)

        # 批量编码
        encoded_chunks = self._encode_chunks(valid_chunks, encoder)

        # 存储到向量数据库
        self._store_to_vector_db(encoded_chunks, vector_store)

        # 获取统计信息
        elapsed = time.time() - start_time
        stats = vector_store.get_stats()

        result = {
            "total_chunks": total_count,
            "success_count": len(encoded_chunks),
            "failed_count": 0,
            "failed_chunk_ids": [],
            "vector_store_stats": stats,
            "elapsed_time": elapsed
        }

        # 只打印最终结果
        logger.info(f"向量化完成: 文档 {actual_doc_id}, 成功 {result['success_count']}/{result['total_chunks']} 个 chunks, "
                   f"向量库总量: {stats.get('total_count', 0)}, 耗时: {elapsed:.2f}s")

        return result

    def _preprocess_chunks(
        self,
        chunks: List[Dict],
        doc_id: Optional[str] = None
    ) -> List[Dict]:
        """
        预处理 chunks：验证必需字段，过滤无效数据

        TODO: 当前只处理 type='text' 的 chunks，表格(type='table')和图片(type='image')未处理
        TODO: 表格和图片需要有对应的向量化策略（如OCR文本向量化、多模态embedding等）

        Args:
            chunks: 原始分片列表
            doc_id: 文档 ID（可选，用于验证）

        Returns:
            有效的分片列表

        Raises:
            ValueError: 当发现无效数据时
        """
        valid_chunks = []
        invalid_chunks = []

        for idx, chunk in enumerate(chunks):
            # 检查必需字段
            chunk_id = chunk.get('chunk_id')
            text = chunk.get('text')
            chunk_doc_id = chunk.get('doc_id')

            # 验证
            if not chunk_id:
                invalid_chunks.append({"index": idx, "reason": "缺少 chunk_id"})
                continue

            if not text or not text.strip():
                invalid_chunks.append({"index": idx, "chunk_id": chunk_id, "reason": "文本为空"})
                continue

            if not chunk_doc_id:
                invalid_chunks.append({"index": idx, "chunk_id": chunk_id, "reason": "缺少 doc_id"})
                continue

            # 验证 doc_id 是否匹配（如果提供）
            if doc_id and chunk_doc_id != doc_id:
                invalid_chunks.append({
                    "index": idx,
                    "chunk_id": chunk_id,
                    "reason": f"doc_id 不匹配: 期望 {doc_id}, 实际 {chunk_doc_id}"
                })
                continue

            # 确保有必需的元数据字段
            chunk.setdefault('order', 0)
            chunk.setdefault('page', 0)
            chunk.setdefault('type', 'text')
            chunk.setdefault('length', len(text))
            chunk.setdefault('bbox', [])

            valid_chunks.append(chunk)

        # 报告无效 chunks
        if invalid_chunks:
            logger.warning(f"[批量向量化] 发现 {len(invalid_chunks)} 个无效 chunks")

        return valid_chunks

    def _encode_chunks(
        self,
        chunks: List[Dict],
        encoder: EmbeddingEncoder
    ) -> List[Dict]:
        """
        批量编码 chunks

        Args:
            chunks: 有效分片列表
            encoder: 编码器实例

        Returns:
            添加了 embedding 字段的分片列表

        Raises:
            ValueError: 当编码失败时
        """
        # 提取文本
        texts = [chunk['text'] for chunk in chunks]

        try:
            # 批量编码
            embeddings = encoder.encode_batch(
                texts,
                batch_size=self.batch_size,
                show_progress=self.show_progress
            )

            # 将 embedding 添加到 chunk
            for i, chunk in enumerate(chunks):
                chunk['embedding'] = embeddings[i]

            return chunks

        except ValueError as e:
            # 编码失败，抛出异常
            raise ValueError(f"向量化编码失败: {str(e)}")

        except Exception as e:
            raise ValueError(f"向量化编码异常: {str(e)}")

    def _store_to_vector_db(
        self,
        chunks: List[Dict],
        vector_store: VectorStore
    ) -> None:
        """
        存储 chunks 到向量数据库

        Args:
            chunks: 已编码的分片列表
            vector_store: 向量存储实例

        Raises:
            ValueError: 当存储失败时
        """
        try:
            count = vector_store.add_chunks(chunks)
            logger.debug(f"[批量向量化] 成功存储 {count} 个 chunks")

        except ValueError as e:
            # 存储失败，抛出异常
            raise ValueError(f"向量数据库存储失败: {str(e)}")

        except Exception as e:
            raise ValueError(f"向量数据库存储异常: {str(e)}")


# ============================================
# 便捷函数
# ============================================

def embed_and_store_chunks(
    chunks: List[Dict],
    doc_id: str,
    batch_size: int = 10,
    show_progress: bool = True
) -> Dict[str, Any]:
    """
    将 chunks 向量化并存储到向量数据库（主入口函数）

    这是文档处理流程第四步的主入口函数，集成编码器和向量存储。

    Args:
        chunks: 第三步 optimizer 返回的优化后分片列表
        doc_id: 文档 ID
        batch_size: 批处理大小
        show_progress: 是否显示进度

    Returns:
        处理结果，包含:
            - total_chunks: 总分片数
            - success_count: 成功数量
            - failed_count: 失败数量
            - failed_chunk_ids: 失败的分片 ID 列表
            - vector_store_stats: 向量库统计信息
            - elapsed_time: 处理耗时（秒）

    Raises:
        ValueError: 当处理失败时抛出异常

    使用示例:
        >>> from app.services.document_processing.embedding import embed_and_store_chunks
        >>> result = embed_and_store_chunks(optimized_chunks, doc_id="doc_001")
        >>> print(f"成功: {result['success_count']}/{result['total_chunks']}")
    """
    from .encoder import get_encoder
    from .vector_store import get_vector_store

    # 获取编码器实例
    encoder = get_encoder()

    # 获取向量存储实例
    vector_store = get_vector_store()

    # 创建批量处理器
    processor = BatchProcessor(
        batch_size=batch_size,
        show_progress=show_progress,
        fail_fast=True  # 遇到错误立即终止
    )

    # 执行处理
    return processor.process_and_store(chunks, vector_store, encoder, doc_id)
