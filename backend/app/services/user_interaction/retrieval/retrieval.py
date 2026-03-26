"""
检索和重排序模块

负责根据问题向量检索相关 chunk，并进行重排序。
支持混合检索：向量检索 + 关键字检索 + 图谱检索
使用 Cross-Encoder 模型进行深度语义重排序。
"""

import time
import logging
from typing import List, Dict, Any, Optional

from app.services.document_processing.embedding.vector_store import VectorStore, get_vector_store
from app.services.document_processing.keyword_index import get_keyword_indexer
from app.services.user_interaction.graph_retrieval import get_graph_retriever
from app.services.user_interaction.context_enricher import ContextEnricher
from app.config.model_config import get_reranker_model

# 配置日志
logger = logging.getLogger(__name__)


class VectorSearcher:
    """
    向量检索器

    根据问题向量从向量数据库中检索相关 chunks
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        default_top_k: int = 10
    ):
        """
        初始化向量检索器

        Args:
            vector_store: 向量存储实例
            default_top_k: 默认检索数量
        """
        self.vector_store = vector_store or get_vector_store()
        self.default_top_k = default_top_k

    def search(
        self,
        query_embedding: List[float],
        top_k: Optional[int] = None,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        向量相似度检索

        Args:
            query_embedding: 问题向量
            top_k: 返回结果数量
            filter: 元数据过滤条件

        Returns:
            检索结果列表
        """
        top_k = top_k or self.default_top_k

        try:
            results = self.vector_store.search(query_embedding, top_k=top_k, filter=filter)
            return results
        except Exception as e:
            logger.error(f"[向量检索] 向量检索失败: {e}")
            return []

    def search_by_text(
        self,
        query_text: str,
        encoder,
        top_k: Optional[int] = None,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        通过文本进行检索（自动编码）

        Args:
            query_text: 问题文本
            encoder: 编码器实例
            top_k: 返回结果数量
            filter: 元数据过滤条件

        Returns:
            检索结果列表
        """
        # 编码查询文本
        query_embedding = encoder.encode(query_text)
        return self.search(query_embedding, top_k, filter)

    def batch_search(
        self,
        query_embeddings: List[List[float]],
        top_k: Optional[int] = None,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[List[Dict[str, Any]]]:
        """
        批量向量检索

        Args:
            query_embeddings: 问题向量列表
            top_k: 每个查询返回结果数量
            filter: 元数据过滤条件

        Returns:
            检索结果列表的列表
        """
        top_k = top_k or self.default_top_k
        results_list = []

        for embedding in query_embeddings:
            results = self.search(embedding, top_k, filter)
            results_list.append(results)

        return results_list


class Reranker:
    """
    重排序器

    使用 Cross-Encoder 模型对检索结果进行深度语义重排序
    """

    def __init__(self):
        """初始化重排序器"""
        self.reranker_model = get_reranker_model()

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        对检索结果进行重排序

        Args:
            query: 原始问题
            candidates: 候选结果列表
            top_k: 返回结果数量

        Returns:
            重排序后的结果列表
        """
        if not candidates:
            return []

        top_k = top_k or len(candidates)

        # 提取文档文本
        documents = [c.get('text', '') for c in candidates]

        try:
            # 调用模型 API 进行重排序
            reranked_results = self.reranker_model.rerank(query, documents, top_n=top_k)

            # 根据模型返回的结果重新排序
            reranked_candidates = []

            for result in reranked_results:
                original_idx = result.get("index")
                relevance_score = result.get("relevance_score", 0.0)

                if original_idx < len(candidates):
                    candidate = candidates[original_idx].copy()
                    candidate['rerank_score'] = relevance_score
                    reranked_candidates.append(candidate)

            # 如果模型返回的结果数量不足，补充剩余的候选
            if len(reranked_candidates) < len(candidates):
                processed_indices = {r.get('text', '') for r in reranked_candidates}
                for candidate in candidates:
                    if candidate.get('text', '') not in processed_indices:
                        reranked_candidates.append(candidate)

            return reranked_candidates[:top_k]

        except Exception as e:
            logger.error(f"[重排序] 模型重排序失败: {e}，返回原始顺序")
            return candidates[:top_k]


class RetrievalPipeline:
    """
    检索流水线

    整合向量检索和重排序的完整流程
    """

    def __init__(
        self,
        searcher: Optional[VectorSearcher] = None,
        reranker: Optional[Reranker] = None,
        retrieval_top_k: int = 20,
        final_top_k: int = 5,
        kb_id: Optional[str] = None
    ):
        """
        初始化检索流水线

        Args:
            searcher: 向量检索器
            reranker: 重排序器
            retrieval_top_k: 初始检索数量
            final_top_k: 最终返回数量
            kb_id: 知识库 ID，用于过滤检索结果（可选）
        """
        self.searcher = searcher or VectorSearcher()
        self.reranker = reranker or Reranker()
        self.retrieval_top_k = retrieval_top_k
        self.final_top_k = final_top_k
        self.kb_id = kb_id

    def retrieve(
        self,
        query: str,
        query_embedding: List[float],
        encoder=None
    ) -> List[Dict[str, Any]]:
        """
        执行完整的检索流程

        Args:
            query: 原始问题文本
            query_embedding: 问题向量
            encoder: 编码器（可选，用于文本检索）

        Returns:
            检索结果列表
        """
        start_time = time.time()

        # 构建过滤条件
        filter条件 = None
        if self.kb_id:
            filter条件 = {"kb_id": self.kb_id}

        # 第一步：向量检索（获取更多候选）
        if query_embedding:
            candidates = self.searcher.search(query_embedding, top_k=self.retrieval_top_k, filter=filter条件)
        elif encoder:
            candidates = self.searcher.search_by_text(query, encoder, top_k=self.retrieval_top_k, filter=filter条件)
        else:
            logger.error("[检索流程] 必须提供 query_embedding 或 encoder")
            raise ValueError("必须提供 query_embedding 或 encoder")

        elapsed_retrieval = time.time() - start_time

        # 第二步：模型重排序
        final_results = self.reranker.rerank(query, candidates, top_k=self.final_top_k)
        elapsed_rerank = time.time() - start_time - elapsed_retrieval

        return final_results

    def batch_retrieve(
        self,
        queries: List[str],
        query_embeddings: List[List[float]],
        encoder=None
    ) -> List[List[Dict[str, Any]]]:
        """
        批量执行检索流程

        Args:
            queries: 问题列表
            query_embeddings: 问题向量列表
            encoder: 编码器（可选）

        Returns:
            检索结果列表的列表
        """
        results = []

        for query, embedding in zip(queries, query_embeddings):
            result = self.retrieve(query, embedding, encoder)
            results.append(result)

        return results


class HybridRetrievalPipeline(RetrievalPipeline):
    """
    混合检索流水线

    整合向量检索、关键字检索和图谱检索，使用 RRF 算法融合结果
    """

    def __init__(
        self,
        searcher: Optional[VectorSearcher] = None,
        reranker: Optional[Reranker] = None,
        keyword_indexer=None,
        graph_retriever=None,
        context_enricher=None,
        retrieval_top_k: int = 20,
        final_top_k: int = 5,
        weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化混合检索流水线

        Args:
            searcher: 向量检索器
            reranker: 重排序器
            keyword_indexer: 关键字索引器
            graph_retriever: 图谱检索器
            context_enricher: 上下文增强器
            retrieval_top_k: 初始检索数量
            final_top_k: 最终返回数量
            weights: 各检索方法的权重配置
        """
        super().__init__(searcher, reranker, retrieval_top_k, final_top_k)
        self.keyword_indexer = keyword_indexer or get_keyword_indexer()
        self.graph_retriever = graph_retriever or get_graph_retriever()
        self.context_enricher = context_enricher or ContextEnricher()

        # 默认权重配置
        self.weights = weights or {
            'vector': 0.5,
            'keyword': 0.3,
            'graph': 0.2
        }

    def _vector_retrieve(
        self,
        query_embedding: List[float],
        doc_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        向量检索

        Args:
            query_embedding: 问题向量
            doc_id: 文档 ID（用于过滤）

        Returns:
            检索结果
        """
        filter_dict = {"doc_id": doc_id} if doc_id else None
        return self.searcher.search(query_embedding, top_k=self.retrieval_top_k, filter=filter_dict)

    def _keyword_retrieve(
        self,
        query: str,
        doc_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        关键字检索

        Args:
            query: 问题文本
            doc_id: 文档 ID（用于过滤）

        Returns:
            检索结果
        """
        # 加载文档索引
        if doc_id and self.keyword_indexer.current_doc_id != doc_id:
            self.keyword_indexer.load_index(doc_id)

        results = self.keyword_indexer.search(query, top_k=self.retrieval_top_k, doc_id=doc_id)

        # 标准化格式
        formatted = [{
            "chunk_id": r["chunk_id"],
            "score": r["score"],
            "doc_id": r.get("doc_id", doc_id)
        } for r in results]

        return formatted

    def _graph_retrieve(
        self,
        entity_ids: List[str],
        doc_id: str
    ) -> List[Dict[str, Any]]:
        """
        图谱检索

        Args:
            entity_ids: 实体 ID 列表
            doc_id: 文档 ID

        Returns:
            检索结果
        """
        if not entity_ids:
            return []

        results = self.graph_retriever.get_related_chunks(
            entity_ids,
            doc_id,
            hop_depth=1
        )

        return results

    def _rrf_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        graph_results: List[Dict[str, Any]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        使用 Reciprocal Rank Fusion (RRF) 算法融合多路检索结果

        Args:
            vector_results: 向量检索结果
            keyword_results: 关键字检索结果
            graph_results: 图谱检索结果
            k: RRF 参数（默认 60）

        Returns:
            融合后的结果
        """
        fused_scores = {}
        score_breakdown = {}  # 记录每个chunk的得分来源

        # 向量检索结果
        for rank, result in enumerate(vector_results):
            chunk_id = result.get("chunk_id") or result.get("id")
            if chunk_id:
                score = self.weights.get('vector', 0.5) / (k + rank + 1)
                fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + score
                if chunk_id not in score_breakdown:
                    score_breakdown[chunk_id] = {'vector': 0, 'keyword': 0, 'graph': 0}
                score_breakdown[chunk_id]['vector'] = score

        # 关键字检索结果
        for rank, result in enumerate(keyword_results):
            chunk_id = result.get("chunk_id")
            if chunk_id:
                score = self.weights.get('keyword', 0.3) / (k + rank + 1)
                fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + score
                if chunk_id not in score_breakdown:
                    score_breakdown[chunk_id] = {'vector': 0, 'keyword': 0, 'graph': 0}
                score_breakdown[chunk_id]['keyword'] = score

        # 图谱检索结果
        for rank, result in enumerate(graph_results):
            chunk_id = result.get("chunk_id")
            if chunk_id:
                score = self.weights.get('graph', 0.2) / (k + rank + 1)
                fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + score
                if chunk_id not in score_breakdown:
                    score_breakdown[chunk_id] = {'vector': 0, 'keyword': 0, 'graph': 0}
                score_breakdown[chunk_id]['graph'] = score

        # 排序
        sorted_results = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)

        # 构建结果列表
        merged = self.context_enricher.merge_and_deduplicate(
            vector_results, keyword_results, graph_results
        )
        merged_map = {m["chunk_id"]: m for m in merged}

        final_results = []
        for chunk_id, fused_score in sorted_results:
            if chunk_id in merged_map:
                result = merged_map[chunk_id].copy()
                result["fused_score"] = fused_score
                result["score_breakdown"] = score_breakdown.get(chunk_id, {})
                final_results.append(result)

        return final_results

    def retrieve(
        self,
        query: str,
        query_embedding: List[float],
        doc_id: Optional[str] = None,
        entities: Optional[List[str]] = None,
        entity_ids: Optional[List[str]] = None,
        encoder=None,
        enable_vector: bool = True,
        enable_keyword: bool = True,
        enable_graph: bool = True
    ) -> List[Dict[str, Any]]:
        """
        执行混合检索流程

        Args:
            query: 原始问题文本
            query_embedding: 问题向量
            doc_id: 文档 ID
            entities: 识别的实体列表（用于图谱检索）
            entity_ids: 实体 ID 列表（用于图谱检索）
            encoder: 编码器（可选，用于文本检索）
            enable_vector: 是否启用向量检索
            enable_keyword: 是否启用关键字检索
            enable_graph: 是否启用图谱检索

        Returns:
            检索结果列表
        """
        start_time = time.time()

        vector_results = []
        keyword_results = []
        graph_results = []

        # 1. 向量检索
        if enable_vector:
            if query_embedding:
                vector_results = self._vector_retrieve(query_embedding, doc_id)
            elif encoder:
                vector_results = self.searcher.search_by_text(
                    query, encoder, top_k=self.retrieval_top_k,
                    filter={"doc_id": doc_id} if doc_id else None
                )

        # 2. 关键字检索
        if enable_keyword:
            keyword_results = self._keyword_retrieve(query, doc_id)

        # 3. 图谱检索
        if enable_graph and doc_id and entity_ids:
            graph_results = self._graph_retrieve(entity_ids, doc_id)

        # 4. RRF 融合
        fused_results = self._rrf_fusion(vector_results, keyword_results, graph_results)

        # 5. 重排序（取前 N 个候选）
        candidates = fused_results[:self.retrieval_top_k]
        final_results = self.reranker.rerank(query, candidates, top_k=self.final_top_k)

        return final_results

    def batch_retrieve(
        self,
        queries: List[str],
        query_embeddings: List[List[float]],
        doc_id: Optional[str] = None,
        entities_list: Optional[List[List[str]]] = None,
        encoder=None
    ) -> List[List[Dict[str, Any]]]:
        """
        批量执行混合检索流程

        Args:
            queries: 问题列表
            query_embeddings: 问题向量列表
            doc_id: 文档 ID
            entities_list: 实体列表的列表（每个问题对应的实体）
            encoder: 编码器（可选）

        Returns:
            检索结果列表的列表
        """
        results = []

        for idx, (query, embedding) in enumerate(zip(queries, query_embeddings)):
            entities = entities_list[idx] if entities_list else None
            entity_ids = None  # TODO: 转换实体为 ID

            result = self.retrieve(
                query, embedding, doc_id,
                entities=entities,
                entity_ids=entity_ids,
                encoder=encoder
            )
            results.append(result)

        return results


# 便捷函数
def retrieve(
    query: str,
    query_embedding: List[float],
    top_k: int = 5,
    retrieval_top_k: int = 20
) -> List[Dict[str, Any]]:
    """
    检索的便捷函数

    Args:
        query: 问题文本
        query_embedding: 问题向量
        top_k: 最终返回数量
        retrieval_top_k: 初始检索数量

    Returns:
        检索结果列表
    """
    pipeline = RetrievalPipeline(retrieval_top_k=retrieval_top_k, final_top_k=top_k)
    return pipeline.retrieve(query, query_embedding)


def batch_retrieve(
    queries: List[str],
    query_embeddings: List[List[float]],
    top_k: int = 5,
    retrieval_top_k: int = 20
) -> List[List[Dict[str, Any]]]:
    """
    批量检索的便捷函数

    Args:
        queries: 问题列表
        query_embeddings: 问题向量列表
        top_k: 最终返回数量
        retrieval_top_k: 初始检索数量

    Returns:
        检索结果列表的列表
    """
    pipeline = RetrievalPipeline(retrieval_top_k=retrieval_top_k, final_top_k=top_k)
    return pipeline.batch_retrieve(queries, query_embeddings)
