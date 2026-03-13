"""
关系抽取器

使用 LLM 从实体和文档内容中抽取关系
"""
import json
import re
from typing import List, Dict, Any, Optional

from app.config.model_config import get_text_splitter_llm


class RelationExtractor:
    """
    关系抽取器

    使用 LLM 从实体和文档内容中抽取实体间的关系
    """

    # 常见的关系类型
    RELATION_TYPES = [
        "包含关系",      # A 包含 B（如：公司包含部门）
        "从属关系",      # A 属于 B（如：员工属于公司）
        "合作关系",      # A 与 B 合作
        "竞争关系",      # A 与 B 竞争
        "因果关系",      # A 导致 B
        "时序关系",      # A 发生在 B 之前/之后
        "位置关系",      # A 位于 B
        "相似关系",      # A 与 B 相似
        "对比关系",      # A 与 B 对比
    ]

    def __init__(self, chat_model=None):
        """
        初始化关系抽取器

        Args:
            chat_model: LLM 模型实例
        """
        self.chat_model = chat_model or get_text_splitter_llm()
        self.batch_size = 3  # 每次处理的关系数量

    def _build_extraction_prompt(
        self,
        entities: List[Dict[str, Any]],
        text_chunks: List[str]
    ) -> str:
        """
        构建关系抽取的提示词

        Args:
            entities: 实体列表
            text_chunks: 相关文本块

        Returns:
            提示词字符串
        """
        relation_types_str = "\n".join([f"- {rt}" for rt in self.RELATION_TYPES])

        # 构建实体列表
        entities_summary = ""
        entity_map = {}
        for idx, entity in enumerate(entities):
            entity_id = f"E{idx}"
            entity_map[entity["text"]] = entity_id
            entities_summary += f"{entity_id}: {entity['text']} ({entity['type']})\n"

        prompt = f"""请从以下文档内容中抽取实体之间的关系。

【已知实体】
{entities_summary}

【关系类型】
{relation_types_str}
- 其他关系（如有必要）

【抽取规则】
1. 只抽取明确存在的关系，避免过度推断
2. 关系应该在文档中有明确表述
3. 双向关系（如A与B合作）只需要抽取一次
4. 优先抽取有意义的关系，避免过于泛泛的关系

【文档内容】
"""

        for idx, chunk in enumerate(text_chunks, 1):
            chunk_text = chunk[:800] if len(chunk) > 800 else chunk
            prompt += f"\n[片段{idx}]\n{chunk_text}\n"

        prompt += """
\n【输出格式】
请以JSON格式输出，格式如下：
```json
{
  "relations": [
    {
      "source": "源实体文本",
      "target": "目标实体文本",
      "relation_type": "关系类型",
      "description": "关系描述",
      "chunk_index": 所在片段索引
    }
  ]
}
```

注意：
- source 和 target 必须是上述已知实体中的文本
- chunk_index 从 0 开始计数
- 如果没有找到关系，返回 {"relations": []}
- 确保输出有效的 JSON 格式
"""
        return prompt

    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """
        解析 LLM 返回的关系抽取结果

        Args:
            response: LLM 返回的文本

        Returns:
            关系列表
        """
        try:
            # 尝试提取 JSON 内容
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response.strip()

            data = json.loads(json_str)
            relations = data.get("relations", [])

            # 验证关系格式
            valid_relations = []
            for relation in relations:
                if isinstance(relation, dict) and all(k in relation for k in ["source", "target", "relation_type"]):
                    valid_relations.append({
                        "source": relation["source"],
                        "target": relation["target"],
                        "relation_type": relation["relation_type"],
                        "description": relation.get("description", ""),
                        "chunk_index": relation.get("chunk_index", 0)
                    })

            return valid_relations

        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}")
            return []
        except Exception as e:
            print(f"解析关系响应失败: {e}")
            return []

    def extract_relations(
        self,
        entities: List[Dict[str, Any]],
        chunks: List[Dict[str, Any]],
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        从实体和 chunks 中抽取关系

        Args:
            entities: 实体列表
            chunks: 文档 chunks
            show_progress: 是否显示进度

        Returns:
            抽取结果
        """
        if show_progress:
            print(f"\n{'='*60}")
            print(f"关系抽取开始")
            print(f"{'='*60}")

        if not entities:
            if show_progress:
                print("没有实体，跳过关系抽取")
            return {"success": True, "relations": [], "statistics": {}}

        all_relations = []
        chunk_texts = [chunk.get("text", "") for chunk in chunks]

        # 构建实体文本到实体的映射
        entity_text_map = {e["text"]: e for e in entities}

        # 分批处理（每次处理部分实体）
        for i in range(0, len(entities), self.batch_size):
            batch_entities = entities[i:i + self.batch_size]

            # 只使用包含这些实体的 chunks
            relevant_chunks = []
            for chunk in chunks:
                chunk_text = chunk.get("text", "")
                for entity in batch_entities:
                    if entity["text"] in chunk_text:
                        relevant_chunks.append(chunk_text)
                        break

            if not relevant_chunks:
                continue

            # 构建提示词
            prompt = self._build_extraction_prompt(batch_entities, relevant_chunks[:3])

            try:
                messages = [{"role": "user", "content": prompt}]
                response = self.chat_model.chat(messages, temperature=0.3)

                # 解析结果
                relations = self._parse_llm_response(response)

                # 添加实体 ID
                for relation in relations:
                    source_entity = entity_text_map.get(relation["source"])
                    target_entity = entity_text_map.get(relation["target"])

                    if source_entity and target_entity:
                        relation["source_id"] = source_entity.get("entity_id", "")
                        relation["target_id"] = target_entity.get("entity_id", "")
                        relation["doc_id"] = source_entity.get("doc_id", "")
                        all_relations.append(relation)

                print(f"批次 {i//self.batch_size + 1}: 抽取到 {len(relations)} 个关系")

            except Exception as e:
                print(f"关系抽取失败 (批次 {i//self.batch_size + 1}): {e}")
                continue

        # 去重（相同的 source-target-relation_type 组合）
        unique_relations = []
        seen = set()
        for relation in all_relations:
            key = (relation["source"], relation["target"], relation["relation_type"])
            if key not in seen:
                seen.add(key)
                unique_relations.append(relation)

        # 生成唯一 ID
        for idx, relation in enumerate(unique_relations):
            relation["relation_id"] = f"{relation.get('doc_id', 'unknown')}_R{idx}"

        # 按类型统计
        type_counts = {}
        for relation in unique_relations:
            rt = relation["relation_type"]
            type_counts[rt] = type_counts.get(rt, 0) + 1

        statistics = {
            "total_count": len(unique_relations),
            "type_counts": type_counts
        }

        if show_progress:
            print(f"关系抽取完成: 共 {len(unique_relations)} 个关系")
            for rel_type, count in type_counts.items():
                print(f"  - {rel_type}: {count}")
            print(f"{'='*60}\n")

        return {
            "success": True,
            "relations": unique_relations,
            "statistics": statistics
        }


def extract_relations(
    entities: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    抽取关系的便捷函数

    Args:
        entities: 实体列表
        chunks: 文档 chunks

    Returns:
        关系列表
    """
    extractor = RelationExtractor()
    result = extractor.extract_relations(entities, chunks)
    return result.get("relations", [])
