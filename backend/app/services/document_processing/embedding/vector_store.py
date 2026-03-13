"""
向量存储模块

基于 ChromaDB 的向量数据库封装，提供向量存储、检索和管理功能。

使用方式：
    from app.services.document_processing.embedding.vector_store import VectorStore, get_vector_store

    vector_store = get_vector_store()
    vector_store.add_chunks(chunks)
    results = vector_store.search("查询文本", top_k=5)
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Any
import chromadb
from chromadb.config import Settings

from app.config.paths import get_vector_db_path


class VectorStore:
    """
    向量数据库封装

    基于 ChromaDB 实现，支持：
    - 添加/删除 chunks
    - 向量相似度搜索
    - 按元数据过滤
    - 持久化存储
    """

    # 默认配置
    DEFAULT_COLLECTION_NAME = "rag_chunks"

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None
    ):
        """
        初始化向量存储

        Args:
            persist_directory: 持久化存储目录（可选）
            collection_name: 集合名称（可选）
        """
        # 优先使用环境变量，其次使用传入路径，最后使用默认路径
        env_vector_db_path = os.getenv('VECTOR_DB_PATH')

        if env_vector_db_path:
            # 环境变量优先级最高（Docker 部署时使用）
            self.persist_directory = env_vector_db_path
        elif persist_directory:
            # 使用传入的路径
            self.persist_directory = persist_directory
        else:
            # 使用默认路径（从 config.paths 获取）
            self.persist_directory = get_vector_db_path()

        self.collection_name = collection_name or self.DEFAULT_COLLECTION_NAME

        # 确保目录存在
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        # 初始化 ChromaDB 客户端
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # 获取或创建集合
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        """获取或创建集合"""
        try:
            # 尝试获取已存在的集合
            collection = self.client.get_collection(name=self.collection_name)
            print(f"加载现有向量集合: {self.collection_name}")
            return collection
        except Exception:
            # 集合不存在，创建新集合
            print(f"创建新向量集合: {self.collection_name}")
            return self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "RAG 系统文档 chunks 向量存储"}
            )

    def add_chunks(self, chunks: List[Dict]) -> int:
        """
        添加 chunks 到向量数据库

        Args:
            chunks: 分片列表，每个分片必须包含:
                - chunk_id: 唯一标识
                - embedding: 向量表示
                - text: 原始文本
                - doc_id: 所属文档 ID
                - order: 分片顺序
                - page: 所在页码
                - type: 分片类型
                - length: 字符数
                - bbox: 位置边界框（可选）

        Returns:
            成功添加的数量

        Raises:
            ValueError: 当数据格式错误或添加失败时
        """
        if not chunks:
            return 0

        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for chunk in chunks:
            # 验证必需字段
            chunk_id = chunk.get('chunk_id')
            embedding = chunk.get('embedding')
            text = chunk.get('text')
            doc_id = chunk.get('doc_id')

            if not chunk_id or not embedding or not text or not doc_id:
                raise ValueError(
                    f"chunk 缺少必需字段 (chunk_id, embedding, text, doc_id): {chunk}"
                )

            ids.append(chunk_id)
            embeddings.append(embedding)
            documents.append(text)

            # 构建元数据
            metadata = {
                'doc_id': str(doc_id),
                'order': int(chunk.get('order', 0)),
                'page': int(chunk.get('page', 0)),
                'type': str(chunk.get('type', 'text')),
                'length': int(chunk.get('length', 0))
            }

            # bbox 可选
            bbox = chunk.get('bbox')
            if bbox:
                metadata['bbox'] = str(bbox)

            metadatas.append(metadata)

        try:
            # 批量添加
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            return len(chunks)

        except Exception as e:
            raise ValueError(f"添加 chunks 到向量数据库失败: {str(e)}")

    def delete_by_doc_id(self, doc_id: str) -> int:
        """
        删除指定文档的所有 chunks

        Args:
            doc_id: 文档 ID

        Returns:
            删除的数量
        """
        try:
            # 查询该文档的所有 chunk ID
            results = self.collection.get(
                where={"doc_id": str(doc_id)}
            )

            if results and results['ids']:
                # 删除找到的 chunks
                self.collection.delete(ids=results['ids'])
                return len(results['ids'])

            return 0

        except Exception as e:
            raise ValueError(f"删除文档 {doc_id} 的 chunks 失败: {str(e)}")

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict]:
        """
        向量相似度搜索

        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量
            filter: 元数据过滤条件，例如 {"doc_id": "doc_001", "type": "text"}

        Returns:
            搜索结果列表，每个结果包含:
                - chunk_id: 分片 ID
                - text: 文本内容
                - score: 相似度分数
                - metadata: 元数据
        """
        try:
            # 构建查询参数
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": top_k
            }

            # 添加过滤条件(当前业务场景下还未使用)
            if filter:
                query_params["where"] = filter

            # 执行查询
            results = self.collection.query(**query_params)

            # 解析结果
            search_results = []

            if results and results['ids'] and results['ids'][0]:
                for i, chunk_id in enumerate(results['ids'][0]):
                    result = {
                        'chunk_id': chunk_id,
                        'text': results['documents'][0][i] if results['documents'] else '',
                        'score': 1 - results['distances'][0][i] if results['distances'] else 0,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {}
                    }
                    search_results.append(result)

            return search_results

        except Exception as e:
            raise ValueError(f"向量搜索失败: {str(e)}")

    def search_by_text(
        self,
        query_text: str,
        encoder,
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict]:
        """
        通过文本进行相似度搜索（自动编码查询文本）

        Args:
            query_text: 查询文本
            encoder: EmbeddingEncoder 实例
            top_k: 返回结果数量
            filter: 元数据过滤条件

        Returns:
            搜索结果列表
        """
        # 编码查询文本
        query_embedding = encoder.encode(query_text)
        return self.search(query_embedding, top_k, filter)

    def get_stats(self) -> Dict[str, Any]:
        """
        获取向量库统计信息

        Returns:
            统计信息，包含:
                - collection_name: 集合名称
                - total_count: 总 chunk 数量
                - persist_directory: 存储目录
                - doc_count: 文档数量
        """
        try:
            # 获取总数量
            count = self.collection.count()

            # 获取所有唯一的 doc_id
            all_data = self.collection.get()
            doc_ids = set()
            if all_data and all_data['metadatas']:
                for metadata in all_data['metadatas']:
                    if 'doc_id' in metadata:
                        doc_ids.add(metadata['doc_id'])

            return {
                'collection_name': self.collection_name,
                'total_count': count,
                'doc_count': len(doc_ids),
                'persist_directory': self.persist_directory
            }

        except Exception as e:
            return {
                'collection_name': self.collection_name,
                'total_count': 0,
                'doc_count': 0,
                'persist_directory': self.persist_directory,
                'error': str(e)
            }

    def clear_collection(self) -> bool:
        """
        清空集合（删除所有数据）

        Returns:
            是否成功
        """
        try:
            # 删除并重新创建集合
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "RAG 系统文档 chunks 向量存储"}
            )
            return True
        except Exception as e:
            print(f"清空集合失败: {str(e)}")
            return False

    def get_chunks_by_doc_id(self, doc_id: str) -> List[Dict]:
        """
        获取指定文档的所有 chunks

        Args:
            doc_id: 文档 ID

        Returns:
            chunk 列表
        """
        try:
            results = self.collection.get(
                where={"doc_id": str(doc_id)}
            )

            chunks = []
            if results and results['ids']:
                for i, chunk_id in enumerate(results['ids']):
                    chunk = {
                        'chunk_id': chunk_id,
                        'text': results['documents'][i] if results['documents'] else '',
                        'metadata': results['metadatas'][i] if results['metadatas'] else {}
                    }
                    chunks.append(chunk)

            # 按 order 排序
            chunks.sort(key=lambda x: x['metadata'].get('order', 0))

            return chunks

        except Exception as e:
            raise ValueError(f"获取文档 {doc_id} 的 chunks 失败: {str(e)}")

    def chunk_exists(self, chunk_id: str) -> bool:
        """
        检查 chunk 是否存在

        Args:
            chunk_id: 分片 ID

        Returns:
            是否存在
        """
        try:
            results = self.collection.get(ids=[chunk_id])
            return results and results['ids'] and len(results['ids']) > 0
        except Exception:
            return False


# ============================================
# 全局单例
# ============================================

_vector_store_instance: Optional[VectorStore] = None


def get_vector_store(
    persist_directory: Optional[str] = None,
    collection_name: Optional[str] = None
) -> VectorStore:
    """
    获取全局向量存储实例（单例模式）

    Args:
        persist_directory: 持久化目录（首次调用时设置）
        collection_name: 集合名称（首次调用时设置）

    Returns:
        VectorStore 实例
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore(
            persist_directory=persist_directory,
            collection_name=collection_name
        )
    return _vector_store_instance


def reset_vector_store():
    """重置向量存储实例（用于测试或重新初始化）"""
    global _vector_store_instance
    _vector_store_instance = None
