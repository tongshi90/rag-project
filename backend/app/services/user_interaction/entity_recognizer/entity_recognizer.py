"""
问题实体识别器

从用户问题中识别实体，用于增强检索
"""
import json
import re
from typing import List, Dict, Any, Optional, Set

from app.config.model_config import get_text_splitter_llm
from app.services.document_processing.graph_builder import get_graph_builder


class QueryEntityRecognizer:
    """
    问题实体识别器

    从用户问题中识别实体，并与知识图谱中的实体匹配
    """

    def __init__(self, chat_model=None, graph_builder=None):
        """
        初始化问题实体识别器

        Args:
            chat_model: LLM 模型实例
            graph_builder: 知识图谱构建器实例
        """
        self.chat_model = chat_model or get_text_splitter_llm()
        self.graph_builder = graph_builder or get_graph_builder()
        self.cached_entities: Set[str] = set()
        self.current_doc_id: Optional[str] = None

    def _load_graph_entities(self, doc_id: str) -> Set[str]:
        """
        加载知识图谱中的所有实体

        Args:
            doc_id: 文档 ID

        Returns:
            实体文本集合
        """
        if self.current_doc_id == doc_id and self.cached_entities:
            return self.cached_entities

        # 加载图谱
        if not self.graph_builder.load_graph(doc_id):
            return set()

        # 收集所有实体文本
        entities = set()
        for node_data in self.graph_builder.graph.nodes.values():
            entity_text = node_data.get("text", "")
            if entity_text:
                entities.add(entity_text)

        self.cached_entities = entities
        self.current_doc_id = doc_id

        return entities

    def _build_recognition_prompt(
        self,
        query: str,
        known_entities: Optional[Set[str]] = None
    ) -> str:
        """
        构建实体识别的提示词

        Args:
            query: 用户问题
            known_entities: 已知实体集合（用于匹配）

        Returns:
            提示词字符串
        """
        prompt = f"""请从以下问题中识别实体。

【问题】
{query}

【实体类型】
- 人物: 人名、角色
- 地点: 地理位置、场所
- 组织机构: 公司、机构、部门
- 时间: 日期、时间段
- 数量: 数值、统计数据
- 产品: 产品名称、服务
- 技术概念: 技术术语、概念
- 事件: 事件、活动

【识别规则】
1. 只识别明确提及的实体
2. 实体应该是问题中的关键概念或专有名词
3. 通用词汇（如"什么"、"如何"等）不算实体
"""

        if known_entities:
            known_list = sorted(list(known_entities))[:50]  # 限制数量
            prompt += f"\n【已知实体列表（参考）】\n"
            prompt += "、".join(known_list[:20])
            if len(known_list) > 20:
                prompt += f" ... 等 {len(known_list)} 个实体"
            prompt += "\n\n如果问题中的实体与已知实体匹配，请优先使用已知实体的确切文本。"

        prompt += """
\n【输出格式】
请以JSON格式输出，格式如下：
```json
{
  "entities": [
    {
      "text": "实体文本",
      "type": "实体类型"
    }
  ]
}
```

注意：
- 如果没有找到实体，返回 {"entities": []}
- 确保输出有效的 JSON 格式
"""
        return prompt

    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """
        解析 LLM 返回的实体识别结果

        Args:
            response: LLM 返回的文本

        Returns:
            实体列表
        """
        try:
            # 尝试提取 JSON 内容
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response.strip()

            data = json.loads(json_str)
            entities = data.get("entities", [])

            # 验证实体格式
            valid_entities = []
            for entity in entities:
                if isinstance(entity, dict) and "text" in entity and "type" in entity:
                    valid_entities.append({
                        "text": entity["text"],
                        "type": entity["type"]
                    })

            return valid_entities

        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}")
            return []
        except Exception as e:
            print(f"解析实体响应失败: {e}")
            return []

    def recognize_entities(
        self,
        query: str,
        doc_id: Optional[str] = None,
        use_graph: bool = True
    ) -> List[Dict[str, Any]]:
        """
        从问题中识别实体

        Args:
            query: 用户问题
            doc_id: 文档 ID（用于加载知识图谱）
            use_graph: 是否使用知识图谱匹配

        Returns:
            识别的实体列表
        """
        # 加载知识图谱实体
        known_entities = set()
        if use_graph and doc_id:
            known_entities = self._load_graph_entities(doc_id)

        # 构建提示词
        prompt = self._build_recognition_prompt(query, known_entities if known_entities else None)

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.chat_model.chat(messages, temperature=0)

            # 解析结果
            entities = self._parse_llm_response(response)

            # 匹配知识图谱中的实体
            if known_entities:
                for entity in entities:
                    entity_text = entity["text"]
                    # 精确匹配
                    if entity_text in known_entities:
                        entity["matched"] = True
                        entity["match_type"] = "exact"
                    else:
                        # 模糊匹配
                        for known_entity in known_entities:
                            if entity_text in known_entity or known_entity in entity_text:
                                entity["matched"] = True
                                entity["match_type"] = "fuzzy"
                                entity["matched_text"] = known_entity
                                break
                        else:
                            entity["matched"] = False

            return entities

        except Exception as e:
            print(f"实体识别失败: {e}")
            return []

    def get_entity_ids(
        self,
        entities: List[Dict[str, Any]],
        doc_id: str
    ) -> List[str]:
        """
        将实体文本转换为实体 ID

        Args:
            entities: 实体列表
            doc_id: 文档 ID

        Returns:
            实体 ID 列表
        """
        if not entities:
            return []

        # 确保图谱已加载
        self._load_graph_entities(doc_id)

        entity_ids = []
        for entity in entities:
            entity_text = entity.get("matched_text", entity.get("text", ""))

            # 在图谱中查找匹配的节点
            for node_id, node_data in self.graph_builder.graph.nodes.items():
                if node_data.get("text") == entity_text:
                    entity_ids.append(node_id)
                    break

        return entity_ids


def recognize_query_entities(
    query: str,
    doc_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    识别问题实体的便捷函数

    Args:
        query: 用户问题
        doc_id: 文档 ID

    Returns:
        实体列表
    """
    recognizer = QueryEntityRecognizer()
    return recognizer.recognize_entities(query, doc_id)
