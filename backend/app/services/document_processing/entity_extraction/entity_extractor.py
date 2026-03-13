"""
实体抽取器

使用 LLM 从文档 chunks 中抽取实体
"""
import json
import re
from typing import List, Dict, Any, Optional
from collections import defaultdict

from app.config.model_config import get_text_splitter_llm


class EntityExtractor:
    """
    实体抽取器

    使用 LLM 从文档中抽取结构化实体信息
    """

    # 支持的实体类型
    ENTITY_TYPES = [
        "人物",      # 人名、角色
        "地点",      # 地理位置、场所
        "组织机构",   # 公司、机构、部门
        "时间",      # 日期、时间段
        "数量",      # 数值、统计数据
        "产品",      # 产品名称、服务
        "技术概念",   # 技术术语、概念
        "事件",      # 事件、活动
    ]

    def __init__(self, chat_model=None):
        """
        初始化实体抽取器

        Args:
            chat_model: LLM 模型实例，默认使用 get_text_splitter_llm()
        """
        self.chat_model = chat_model or get_text_splitter_llm()
        self.batch_size = 5  # 每次处理的 chunk 数量

    def _build_extraction_prompt(self, text_chunks: List[str]) -> str:
        """
        构建实体抽取的提示词

        Args:
            text_chunks: 文本块列表

        Returns:
            提示词字符串
        """
        entity_types_str = "、".join(self.ENTITY_TYPES)

        prompt = f"""请从以下文档内容中抽取实体信息。

【实体类型】
{entity_types_str}

【抽取规则】
1. 只抽取明确提及的实体，避免过度推断
2. 实体应该是文档中的重要概念或专有名词
3. 同一实体多次出现只抽取一次，合并到第一次出现的位置
4. 时间实体包含：日期（如"2024年1月1日"）、时间段（如"去年"、"第三季度"）
5. 数量实体包含：具体数值（如"100万元"、"50%"）、统计数据

【文档内容】
"""

        for idx, chunk in enumerate(text_chunks, 1):
            # 限制每个 chunk 的长度
            chunk_text = chunk[:800] if len(chunk) > 800 else chunk
            prompt += f"\n[片段{idx}]\n{chunk_text}\n"

        prompt += """
\n【输出格式】
请以JSON格式输出，格式如下：
```json
{
  "entities": [
    {
      "text": "实体文本",
      "type": "实体类型",
      "chunk_index": 所在片段索引,
      "description": "简短描述（可选）"
    }
  ]
}
```

注意：
- chunk_index 从 0 开始计数
- 如果没有找到实体，返回 {"entities": []}
- 确保输出有效的 JSON 格式
"""
        return prompt

    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """
        解析 LLM 返回的实体抽取结果

        Args:
            response: LLM 返回的文本

        Returns:
            实体列表
        """
        try:
            # 尝试提取 JSON 内容
            # 查找 ```json ``` 代码块
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析整个响应
                json_str = response.strip()

            data = json.loads(json_str)
            entities = data.get("entities", [])

            # 验证实体格式
            valid_entities = []
            for entity in entities:
                if isinstance(entity, dict) and "text" in entity and "type" in entity:
                    valid_entities.append({
                        "text": entity["text"],
                        "type": entity["type"],
                        "chunk_index": entity.get("chunk_index", 0),
                        "description": entity.get("description", "")
                    })

            return valid_entities

        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}")
            print(f"原始响应: {response}")
            return []
        except Exception as e:
            print(f"解析实体响应失败: {e}")
            return []

    def _merge_duplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        合并重复实体（相同文本和类型）

        Args:
            entities: 实体列表

        Returns:
            去重后的实体列表
        """
        seen = {}
        merged = []

        for entity in entities:
            key = (entity["text"], entity["type"])
            if key not in seen:
                seen[key] = len(merged)
                merged.append(entity)
            else:
                # 更新已有实体的 chunk_index（保留第一次出现的）
                existing_idx = seen[key]
                if entity["chunk_index"] < merged[existing_idx]["chunk_index"]:
                    merged[existing_idx]["chunk_index"] = entity["chunk_index"]

        return merged

    def extract_from_chunks(
        self,
        chunks: List[Dict[str, Any]],
        batch_size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        从 chunks 中抽取实体

        Args:
            chunks: chunk 列表，每个包含 text 字段
            batch_size: 每批处理的 chunk 数量

        Returns:
            抽取的实体列表
        """
        if not chunks:
            return []

        batch_size = batch_size or self.batch_size
        all_entities = []

        # 分批处理
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_texts = [chunk.get("text", "") for chunk in batch_chunks]

            # 构建提示词
            prompt = self._build_extraction_prompt(batch_texts)

            # 调用 LLM
            try:
                messages = [{"role": "user", "content": prompt}]
                response = self.chat_model.chat(messages, temperature=0.3)

                # 解析结果
                entities = self._parse_llm_response(response)

                # 调整 chunk_index（相对于整个文档）
                for entity in entities:
                    entity["chunk_index"] += i
                    entity["chunk_id"] = batch_chunks[entity["chunk_index"]].get("chunk_id", "")
                    entity["doc_id"] = batch_chunks[0].get("doc_id", "")

                all_entities.extend(entities)

                print(f"批次 {i//batch_size + 1}: 抽取到 {len(entities)} 个实体")

            except Exception as e:
                print(f"实体抽取失败 (批次 {i//batch_size + 1}): {e}")
                continue

        # 合并重复实体
        all_entities = self._merge_duplicate_entities(all_entities)

        # 生成唯一 ID
        for idx, entity in enumerate(all_entities):
            entity["entity_id"] = f"{entity.get('doc_id', 'unknown')}_{idx}"

        return all_entities

    def extract_from_document(
        self,
        chunks: List[Dict[str, Any]],
        doc_id: str,
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        从文档中抽取实体（主入口）

        Args:
            chunks: 文档的所有 chunks
            doc_id: 文档 ID
            show_progress: 是否显示进度

        Returns:
            抽取结果，包含：
                - success: 是否成功
                - entities: 实体列表
                - statistics: 统计信息
        """
        if show_progress:
            print(f"\n{'='*60}")
            print(f"实体抽取开始")
            print(f"{'='*60}")

        try:
            entities = self.extract_from_chunks(chunks)

            # 按类型统计
            type_counts = defaultdict(int)
            for entity in entities:
                type_counts[entity["type"]] += 1

            statistics = {
                "total_count": len(entities),
                "type_counts": dict(type_counts)
            }

            if show_progress:
                print(f"实体抽取完成: 共 {len(entities)} 个实体")
                for entity_type, count in type_counts.items():
                    print(f"  - {entity_type}: {count}")
                print(f"{'='*60}\n")

            return {
                "success": True,
                "entities": entities,
                "statistics": statistics
            }

        except Exception as e:
            if show_progress:
                print(f"实体抽取失败: {e}")
            return {
                "success": False,
                "entities": [],
                "statistics": {},
                "error": str(e)
            }


def extract_entities_from_document(
    chunks: List[Dict[str, Any]],
    doc_id: str
) -> List[Dict[str, Any]]:
    """
    从文档中抽取实体的便捷函数

    Args:
        chunks: 文档 chunks
        doc_id: 文档 ID

    Returns:
        实体列表
    """
    extractor = EntityExtractor()
    result = extractor.extract_from_document(chunks, doc_id)
    return result.get("entities", [])
