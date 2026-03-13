"""
图谱检索器

基于知识图谱的邻域和路径检索
"""
from typing import List, Dict, Any, Optional, Set

from app.config.paths import GRAPH_DB_PATH
from app.services.document_processing.graph_builder import get_graph_builder


class GraphRetriever:
    """
    图谱检索器

    基于知识图谱进行邻域检索和路径检索
    """

    def __init__(self, graph_builder=None):
        """
        初始化图谱检索器

        Args:
            graph_builder: 知识图谱构建器实例
        """
        self.graph_builder = graph_builder or get_graph_builder()
        self.loaded_docs: Set[str] = set()

    def _ensure_graph_loaded(self, doc_id: str) -> bool:
        """
        确保指定文档的图谱已加载

        Args:
            doc_id: 文档 ID

        Returns:
            是否加载成功
        """
        if doc_id in self.loaded_docs:
            return True

        success = self.graph_builder.load_graph(doc_id)
        if success:
            self.loaded_docs.add(doc_id)
        return success

    def retrieve_by_entity(
        self,
        entity_id: str,
        doc_id: str,
        hop_depth: int = 2,
        max_neighbors: int = 20
    ) -> List[Dict[str, Any]]:
        """
        基于实体进行邻域检索

        Args:
            entity_id: 实体 ID
            doc_id: 文档 ID
            hop_depth: 跳数
            max_neighbors: 最大邻居数量

        Returns:
            邻居节点列表
        """
        if not self._ensure_graph_loaded(doc_id):
            return []

        neighbors = self.graph_builder.get_neighbors(
            entity_id,
            hop_depth=hop_depth,
            max_neighbors=max_neighbors
        )

        return neighbors

    def retrieve_by_entities(
        self,
        entity_ids: List[str],
        doc_id: str,
        hop_depth: int = 2,
        max_neighbors: int = 20
    ) -> List[Dict[str, Any]]:
        """
        基于多个实体进行邻域检索

        Args:
            entity_ids: 实体 ID 列表
            doc_id: 文档 ID
            hop_depth: 跳数
            max_neighbors: 每个实体的最大邻居数量

        Returns:
            合并后的邻居节点列表
        """
        all_neighbors = []
        seen_ids = set()

        for entity_id in entity_ids:
            neighbors = self.retrieve_by_entity(
                entity_id, doc_id, hop_depth, max_neighbors
            )

            for neighbor in neighbors:
                neighbor_id = neighbor.get("entity_id")
                if neighbor_id and neighbor_id not in seen_ids:
                    seen_ids.add(neighbor_id)
                    all_neighbors.append(neighbor)

        return all_neighbors

    def retrieve_by_path(
        self,
        source_id: str,
        target_id: str,
        doc_id: str,
        max_length: int = 3
    ) -> List[Dict[str, Any]]:
        """
        基于路径进行检索

        Args:
            source_id: 源实体 ID
            target_id: 目标实体 ID
            doc_id: 文档 ID
            max_length: 最大路径长度

        Returns:
            路径列表
        """
        if not self._ensure_graph_loaded(doc_id):
            return []

        paths = self.graph_builder.find_path(
            source_id,
            target_id,
            max_length=max_length
        )

        # 将路径转换为 chunk 相关的结果
        results = []
        for path in paths:
            # 收集路径上所有节点的 chunk_id
            chunk_ids = set()
            for step in path:
                from_data = step.get("from_data", {})
                to_data = step.get("to_data", {})
                if from_data.get("chunk_id"):
                    chunk_ids.add(from_data["chunk_id"])
                if to_data.get("chunk_id"):
                    chunk_ids.add(to_data["chunk_id"])

            # 转换为结果格式
            for chunk_id in chunk_ids:
                results.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "retrieval_method": "graph_path",
                    "score": 1.0  # 路径检索结果给最高分
                })

        return results

    def search_entities(
        self,
        keyword: str,
        doc_id: str,
        entity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        在图谱中搜索实体

        Args:
            keyword: 关键词
            doc_id: 文档 ID
            entity_type: 实体类型（可选）

        Returns:
            匹配的实体列表
        """
        if not self._ensure_graph_loaded(doc_id):
            return []

        if entity_type:
            entities = self.graph_builder.search_entities_by_type(entity_type, doc_id)
        else:
            entities = self.graph_builder.search_entities_by_text(keyword, doc_id)

        return entities

    def get_related_chunks(
        self,
        entity_ids: List[str],
        doc_id: str,
        hop_depth: int = 1
    ) -> List[Dict[str, Any]]:
        """
        获取实体相关的 chunk 列表

        Args:
            entity_ids: 实体 ID 列表
            doc_id: 文档 ID
            hop_depth: 跳数

        Returns:
            相关 chunk 列表
        """
        if not entity_ids:
            return []

        neighbors = self.retrieve_by_entities(
            entity_ids,
            doc_id,
            hop_depth=hop_depth
        )

        # 提取唯一的 chunk_id
        chunk_map = {}
        for neighbor in neighbors:
            chunk_id = neighbor.get("chunk_id")
            if chunk_id and chunk_id not in chunk_map:
                chunk_map[chunk_id] = {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "retrieval_method": "graph_neighbor",
                    "score": 0.8 - (neighbor.get("hop", 1) * 0.1),  # 跳数越多分数越低
                    "related_entities": []
                }
            if chunk_id in chunk_map:
                chunk_map[chunk_id]["related_entities"].append({
                    "entity_id": neighbor.get("entity_id"),
                    "entity_text": neighbor.get("text"),
                    "hop": neighbor.get("hop", 1)
                })

        return list(chunk_map.values())


# 全局图谱检索器实例
_graph_retriever_instance = None


def get_graph_retriever() -> GraphRetriever:
    """
    获取全局图谱检索器实例

    Returns:
        GraphRetriever 实例
    """
    global _graph_retriever_instance
    if _graph_retriever_instance is None:
        _graph_retriever_instance = GraphRetriever()
    return _graph_retriever_instance
