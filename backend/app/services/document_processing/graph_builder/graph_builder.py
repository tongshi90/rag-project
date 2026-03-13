"""
知识图谱构建器

使用 NetworkX 构建和管理知识图谱
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple

try:
    import networkx as nx
except ImportError:
    nx = None
    print("警告: networkx 未安装，请运行: pip install networkx")


from app.config.paths import GRAPH_DB_PATH


class KnowledgeGraphBuilder:
    """
    知识图谱构建器

    使用 NetworkX MultiDiGraph 构建知识图谱
    """

    def __init__(self, storage_type: str = "memory"):
        """
        初始化知识图谱构建器

        Args:
            storage_type: 存储类型 ("memory" 或 "file")
        """
        if nx is None:
            raise ImportError("networkx 未安装，请运行: pip install networkx")

        self.graph = nx.MultiDiGraph()
        self.storage_type = storage_type
        self.current_doc_id = None

    def build_graph(
        self,
        entities: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
        doc_id: str
    ) -> Dict[str, Any]:
        """
        构建知识图谱

        Args:
            entities: 实体列表
            relations: 关系列表
            doc_id: 文档 ID

        Returns:
            构建结果统计
        """
        self.current_doc_id = doc_id

        # 添加实体节点
        entity_counts = {"total": 0, "by_type": {}}
        for entity in entities:
            node_id = entity.get("entity_id", entity.get("text", ""))
            self.graph.add_node(
                node_id,
                text=entity.get("text", ""),
                type=entity.get("type", ""),
                description=entity.get("description", ""),
                doc_id=doc_id,
                chunk_id=entity.get("chunk_id", "")
            )
            entity_counts["total"] += 1
            etype = entity.get("type", "unknown")
            entity_counts["by_type"][etype] = entity_counts["by_type"].get(etype, 0) + 1

        # 添加关系边
        relation_counts = {"total": 0, "by_type": {}}
        for relation in relations:
            source_id = relation.get("source_id", "")
            target_id = relation.get("target_id", "")

            if source_id and target_id:
                edge_key = relation.get("relation_id", f"{source_id}-{target_id}")
                self.graph.add_edge(
                    source_id,
                    target_id,
                    key=edge_key,
                    relation_type=relation.get("relation_type", ""),
                    description=relation.get("description", ""),
                    doc_id=doc_id
                )
                relation_counts["total"] += 1
                rtype = relation.get("relation_type", "unknown")
                relation_counts["by_type"][rtype] = relation_counts["by_type"].get(rtype, 0) + 1

        return {
            "success": True,
            "entity_counts": entity_counts,
            "relation_counts": relation_counts,
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges()
        }

    def get_neighbors(
        self,
        entity_id: str,
        hop_depth: int = 1,
        max_neighbors: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取实体的邻域节点

        Args:
            entity_id: 实体 ID
            hop_depth: 跳数（1=直接邻居，2=二跳邻居）
            max_neighbors: 最大邻居数量

        Returns:
            邻居节点列表
        """
        if entity_id not in self.graph:
            return []

        neighbors = []
        visited: Set[str] = set()
        current_level = {entity_id}

        for hop in range(hop_depth):
            next_level = set()
            for node in current_level:
                # 获取出边邻居
                for successor in self.graph.successors(node):
                    if successor not in visited and successor != entity_id:
                        edge_data = self.graph.get_edge_data(node, successor)
                        if edge_data:
                            for key, data in edge_data.items():
                                neighbors.append({
                                    "entity_id": successor,
                                    "hop": hop + 1,
                                    "direction": "outgoing",
                                    "relation_type": data.get("relation_type", ""),
                                    "relation_description": data.get("description", ""),
                                    **self.graph.nodes[successor]
                                })
                                next_level.add(successor)
                                visited.add(successor)
                                if len(neighbors) >= max_neighbors:
                                    return neighbors

                # 获取入边邻居
                for predecessor in self.graph.predecessors(node):
                    if predecessor not in visited and predecessor != entity_id:
                        edge_data = self.graph.get_edge_data(predecessor, node)
                        if edge_data:
                            for key, data in edge_data.items():
                                neighbors.append({
                                    "entity_id": predecessor,
                                    "hop": hop + 1,
                                    "direction": "incoming",
                                    "relation_type": data.get("relation_type", ""),
                                    "relation_description": data.get("description", ""),
                                    **self.graph.nodes[predecessor]
                                })
                                next_level.add(predecessor)
                                visited.add(predecessor)
                                if len(neighbors) >= max_neighbors:
                                    return neighbors

            current_level = next_level

        return neighbors

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_length: int = 3
    ) -> List[List[Dict[str, Any]]]:
        """
        查找两个实体之间的路径

        Args:
            source_id: 源实体 ID
            target_id: 目标实体 ID
            max_length: 最大路径长度

        Returns:
            路径列表，每条路径是节点和边的序列
        """
        if source_id not in self.graph or target_id not in self.graph:
            return []

        try:
            # 使用最短路径算法
            paths = list(nx.all_simple_paths(
                self.graph,
                source_id,
                target_id,
                cutoff=max_length
            ))

            result = []
            for path in paths:
                path_data = []
                for i in range(len(path) - 1):
                    edge_data = self.graph.get_edge_data(path[i], path[i + 1])
                    path_data.append({
                        "from": path[i],
                        "to": path[i + 1],
                        "from_data": self.graph.nodes[path[i]],
                        "to_data": self.graph.nodes[path[i + 1]],
                        "edge_data": edge_data
                    })
                result.append(path_data)

            return result

        except (nx.NodeNotFound, nx.NetworkXNoPath):
            return []

    def search_entities_by_type(
        self,
        entity_type: str,
        doc_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        按类型搜索实体

        Args:
            entity_type: 实体类型
            doc_id: 文档 ID（可选）

        Returns:
            匹配的实体列表
        """
        results = []
        for node_id, node_data in self.graph.nodes(data=True):
            if node_data.get("type") == entity_type:
                if doc_id is None or node_data.get("doc_id") == doc_id:
                    results.append({
                        "entity_id": node_id,
                        **node_data
                    })
        return results

    def search_entities_by_text(
        self,
        keyword: str,
        doc_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        按关键词搜索实体

        Args:
            keyword: 关键词
            doc_id: 文档 ID（可选）

        Returns:
            匹配的实体列表
        """
        results = []
        keyword_lower = keyword.lower()
        for node_id, node_data in self.graph.nodes(data=True):
            text = node_data.get("text", "")
            if keyword_lower in text.lower():
                if doc_id is None or node_data.get("doc_id") == doc_id:
                    results.append({
                        "entity_id": node_id,
                        **node_data
                    })
        return results

    def get_graph_stats(self) -> Dict[str, Any]:
        """
        获取图谱统计信息

        Returns:
            统计信息
        """
        entity_types = {}
        for node_data in self.graph.nodes.values():
            etype = node_data.get("type", "unknown")
            entity_types[etype] = entity_types.get(etype, 0) + 1

        relation_types = {}
        for _, _, edge_data in self.graph.edges(data=True):
            # MultiDiGraph 的 edge_data 是单条边的数据
            rtype = edge_data.get("relation_type", "unknown")
            relation_types[rtype] = relation_types.get(rtype, 0) + 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "entity_types": entity_types,
            "relation_types": relation_types
        }

    def save_graph(self, doc_id: str) -> str:
        """
        保存图谱到文件

        Args:
            doc_id: 文档 ID

        Returns:
            保存路径
        """
        GRAPH_DB_PATH.mkdir(parents=True, exist_ok=True)
        file_path = GRAPH_DB_PATH / f"{doc_id}.json"

        # 转换为可序列化的格式
        graph_data = {
            "nodes": [],
            "edges": []
        }

        for node_id, node_data in self.graph.nodes(data=True):
            graph_data["nodes"].append({
                "id": node_id,
                **node_data
            })

        for source, target, edge_data in self.graph.edges(data=True):
            graph_data["edges"].append({
                "source": source,
                "target": target,
                **edge_data
            })

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)

        return str(file_path)

    def load_graph(self, doc_id: str) -> bool:
        """
        从文件加载图谱

        Args:
            doc_id: 文档 ID

        Returns:
            是否加载成功
        """
        file_path = GRAPH_DB_PATH / f"{doc_id}.json"

        if not file_path.exists():
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                graph_data = json.load(f)

            self.graph.clear()
            self.current_doc_id = doc_id

            for node in graph_data.get("nodes", []):
                node_id = node.pop("id")
                self.graph.add_node(node_id, **node)

            for edge in graph_data.get("edges", []):
                source = edge.pop("source")
                target = edge.pop("target")
                edge_key = edge.pop("key", edge.pop("relation_id", None))
                self.graph.add_edge(source, target, key=edge_key, **edge)

            return True

        except Exception as e:
            print(f"加载图谱失败: {e}")
            return False

    def delete_graph(self, doc_id: str) -> bool:
        """
        删除图谱文件

        Args:
            doc_id: 文档 ID

        Returns:
            是否删除成功
        """
        file_path = GRAPH_DB_PATH / f"{doc_id}.json"

        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def clear(self):
        """清空图谱"""
        self.graph.clear()
        self.current_doc_id = None


# 全局图谱构建器实例
_graph_builder_instance = None


def get_graph_builder() -> KnowledgeGraphBuilder:
    """
    获取全局图谱构建器实例

    Returns:
        KnowledgeGraphBuilder 实例
    """
    global _graph_builder_instance
    if _graph_builder_instance is None:
        _graph_builder_instance = KnowledgeGraphBuilder()
    return _graph_builder_instance
