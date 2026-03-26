"""
意图识别模块

使用 LLM 分析用户问题，预测最相关的知识库。

使用方式：
    from app.services.user_interaction.intent_recognition import predict_knowledge_base

    kb_id = predict_knowledge_base("如何报销差旅费？")
"""

import logging
import json
from typing import Optional, List, Dict, Any

from app.config.model_config import get_chat_model

logger = logging.getLogger(__name__)

# 意图识别阈值：LLM 返回的置信度低于此值时返回 None
CONFIDENCE_THRESHOLD = 0.6


def predict_knowledge_base(
    question: str,
    knowledge_bases: Optional[List[Dict[str, Any]]] = None
) -> Optional[str]:
    """
    使用 LLM 预测问题最相关的知识库

    Args:
        question: 用户问题
        knowledge_bases: 知识库列表，格式：[{"id": "kb_001", "name": "人力资源", "description": "..."}]
                      如果为 None，会自动从数据库获取

    Returns:
        预测的知识库 ID，如果无法确定则返回 None
    """
    # 如果没有提供知识库列表，从数据库获取
    if knowledge_bases is None:
        from app.models.knowledge_base import knowledge_base_db
        knowledge_bases = knowledge_base_db.get_all_knowledge_bases()

    # 如果没有知识库，返回 None
    if not knowledge_bases:
        logger.warning("[意图识别] 没有可用的知识库")
        return None

    # 如果只有一个知识库，直接返回
    if len(knowledge_bases) == 1:
        logger.debug(f"[意图识别] 只有一个知识库，直接返回: {knowledge_bases[0]['id']}")
        return knowledge_bases[0]['id']

    # 构建 LLM 提示词
    kb_list_str = "\n".join([
        f"- ID: {kb['id']}, 名称: {kb['name']}" +
        (f", 描述: {kb.get('description', '')}" if kb.get('description') else "")
        for kb in knowledge_bases
    ])

    prompt = f"""你是一个知识库分类助手。请分析用户问题，判断它最可能属于哪个知识库。

用户问题：{question}

可用的知识库：
{kb_list_str}

请严格按照以下 JSON 格式返回（不要包含任何其他文字）：
{{"kb_id": "知识库ID", "confidence": 0.9}}

说明：
- kb_id: 最相关的知识库ID（必须从上面的列表中选择）
- confidence: 你的置信度（0.0 到 1.0 之间的浮点数）
  - 如果问题与某个知识库高度相关，置信度设为 0.8 以上
  - 如果问题可能与多个知识库相关，选择最相关的一个，置信度设为 0.6-0.8
  - 如果问题无法判断或不属于任何知识库，返回 {{"kb_id": null, "confidence": 0.0}}

示例：
问题: "如何请假？"
回答: {{"kb_id": "kb_001", "confidence": 0.95}}

问题: "python 怎么写循环？"
回答: {{"kb_id": "kb_002", "confidence": 0.9}}

问题: "今天天气怎么样？"
回答: {{"kb_id": null, "confidence": 0.0}}
"""

    try:
        chat_model = get_chat_model()
        response = chat_model.chat([{"role": "user", "content": prompt}], temperature=0.1)

        logger.debug(f"[意图识别] LLM 原始响应: {response}")

        # 解析 LLM 响应
        result = _parse_llm_response(response)

        if result is None:
            logger.warning(f"[意图识别] 无法解析 LLM 响应: {response}")
            return None

        kb_id = result.get('kb_id')
        confidence = result.get('confidence', 0.0)

        # 检查置信度
        if confidence < CONFIDENCE_THRESHOLD:
            return None

        if kb_id:
            # 验证 kb_id 是否在列表中
            valid_kb_ids = {kb['id'] for kb in knowledge_bases}
            if kb_id not in valid_kb_ids:
                logger.warning(f"[意图识别] LLM 返回的 kb_id '{kb_id}' 不在有效列表中")
                return None

            return kb_id

        return None

    except Exception as e:
        logger.error(f"[意图识别] 处理异常: {e}", exc_info=True)
        return None


def _parse_llm_response(response: str) -> Optional[Dict[str, Any]]:
    """
    解析 LLM 返回的 JSON 响应

    Args:
        response: LLM 原始响应字符串

    Returns:
        解析后的字典，如果解析失败返回 None
    """
    if not response:
        return None

    # 尝试提取 JSON 部分（LLM 可能在 JSON 前后添加额外文字）
    response = response.strip()

    # 查找第一个 { 和最后一个 }
    start_idx = response.find('{')
    end_idx = response.rfind('}')

    if start_idx == -1 or end_idx == -1:
        return None

    json_str = response[start_idx:end_idx + 1]

    try:
        result = json.loads(json_str)
        return result
    except json.JSONDecodeError:
        # 尝试修复常见的 JSON 格式问题
        try:
            # 移除可能的多余字符
            cleaned = json_str.replace('\n', ' ').replace('\r', '')
            result = json.loads(cleaned)
            return result
        except:
            return None


# 便捷函数
def get_kb_id_by_name(kb_name: str) -> Optional[str]:
    """
    根据知识库名称获取知识库 ID

    Args:
        kb_name: 知识库名称

    Returns:
        知识库 ID，如果找不到返回 None
    """
    from app.models.knowledge_base import knowledge_base_db

    kbs = knowledge_base_db.get_all_knowledge_bases()

    # 完全匹配
    for kb in kbs:
        if kb.name == kb_name:
            return kb.id

    # 包含匹配
    for kb in kbs:
        if kb_name in kb.name or kb.name in kb_name:
            return kb.id

    return None
