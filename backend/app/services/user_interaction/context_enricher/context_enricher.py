"""
上下文增强器

使用图谱和实体信息增强检索上下文
"""
from typing import List, Dict, Any, Optional

from app.services.user_interaction.graph_retrieval import get_graph_retriever


class ContextEnricher:
    """
    上下文增强器

    使用知识图谱增强检索的上下文信息
    """

    def __init__(self, graph_retriever=None):
        """
        初始化上下文增强器

        Args:
            graph_retriever: 图谱检索器实例
        """
        self.graph_retriever = graph_retriever or get_graph_retriever()

    def enrich_chunks_with_entity_info(
        self,
        chunks: List[Dict[str, Any]],
        entities: List[Dict[str, Any]],
        doc_id: str
    ) -> List[Dict[str, Any]]:
        """
        为 chunks 添加实体信息

        Args:
            chunks: chunk 列表
            entities: 实体列表
            doc_id: 文档 ID

        Returns:
            增强后的 chunk 列表
        """
        # 获取实体 ID
        entity_ids = []
        entity_map = {}
        for entity in entities:
            entity_id = entity.get("entity_id") or entity.get("matched_text")
            if entity_id:
                entity_ids.append(entity_id)
                entity_map[entity.get("text", "")] = entity

        if not entity_ids:
            return chunks

        # 获取相关 chunks
        related_chunks = self.graph_retriever.get_related_chunks(
            entity_ids, doc_id, hop_depth=1
        )

        # 构建映射
        related_map = {rc["chunk_id"]: rc for rc in related_chunks}

        # 增强原始 chunks
        enriched = []
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id")
            enriched_chunk = chunk.copy()

            if chunk_id in related_map:
                related = related_map[chunk_id]
                enriched_chunk["graph_enriched"] = True
                enriched_chunk["related_entities"] = related.get("related_entities", [])
                enriched_chunk["graph_score"] = related.get("score", 0.0)
            else:
                enriched_chunk["graph_enriched"] = False
                enriched_chunk["related_entities"] = []
                enriched_chunk["graph_score"] = 0.0

            enriched.append(enriched_chunk)

        return enriched

    def build_entity_context(
        self,
        entities: List[Dict[str, Any]],
        doc_id: str,
        max_context: int = 200
    ) -> str:
        """
        构建实体的上下文描述

        Args:
            entities: 实体列表
            doc_id: 文档 ID
            max_context: 最大上下文长度

        Returns:
            上下文描述字符串
        """
        if not entities:
            return ""

        context_parts = []

        for entity in entities[:5]:  # 限制实体数量
            entity_text = entity.get("text", "")
            entity_type = entity.get("type", "")

            # 查找相关实体
            related = self.graph_retriever.retrieve_by_entity(
                entity.get("entity_id", entity_text),
                doc_id,
                hop_depth=1,
                max_neighbors=5
            )

            if related:
                related_texts = [r.get("text", "") for r in related if r.get("text")]
                context_part = f"[{entity_type}] {entity_text}: 相关实体包括 {', '.join(related_texts[:3])}"
                context_parts.append(context_part)

        context = " | ".join(context_parts)

        # 限制长度
        if len(context) > max_context:
            context = context[:max_context] + "..."

        return context

    def merge_and_deduplicate(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        graph_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        合并并去重不同检索源的结果

        Args:
            vector_results: 向量检索结果
            keyword_results: 关键字检索结果
            graph_results: 图谱检索结果

        Returns:
            合并去重后的结果
        """
        merged = {}
        seen_ids = set()

        # 处理向量检索结果
        for result in vector_results:
            chunk_id = result.get("chunk_id") or result.get("id")
            if chunk_id and chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                merged[chunk_id] = {
                    "chunk_id": chunk_id,
                    "doc_id": result.get("doc_id"),
                    "text": result.get("text", ""),
                    "vector_score": result.get("score", result.get("distance", 0.0)),
                    "keyword_score": 0.0,
                    "graph_score": 0.0,
                    "metadata": result.get("metadata", {})
                }

        # 处理关键字检索结果
        for result in keyword_results:
            chunk_id = result.get("chunk_id")
            if chunk_id:
                if chunk_id in merged:
                    merged[chunk_id]["keyword_score"] = result.get("score", 0.0)
                elif chunk_id not in seen_ids:
                    seen_ids.add(chunk_id)
                    merged[chunk_id] = {
                        "chunk_id": chunk_id,
                        "doc_id": result.get("doc_id"),
                        "text": "",
                        "vector_score": 0.0,
                        "keyword_score": result.get("score", 0.0),
                        "graph_score": 0.0,
                        "metadata": {}
                    }

        # 处理图谱检索结果
        for result in graph_results:
            chunk_id = result.get("chunk_id")
            if chunk_id:
                if chunk_id in merged:
                    merged[chunk_id]["graph_score"] = result.get("score", 0.0)
                    if "related_entities" in result:
                        merged[chunk_id]["related_entities"] = result["related_entities"]
                elif chunk_id not in seen_ids:
                    seen_ids.add(chunk_id)
                    merged[chunk_id] = {
                        "chunk_id": chunk_id,
                        "doc_id": result.get("doc_id"),
                        "text": "",
                        "vector_score": 0.0,
                        "keyword_score": 0.0,
                        "graph_score": result.get("score", 0.0),
                        "metadata": {}
                    }
                    if "related_entities" in result:
                        merged[chunk_id]["related_entities"] = result["related_entities"]

        return list(merged.values())
