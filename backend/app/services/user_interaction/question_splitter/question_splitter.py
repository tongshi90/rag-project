"""
问题拆分模块

负责将用户的复杂问题拆分为多个子问题，以便分别进行检索和回答。
只支持使用 LLM 模型进行智能拆分和语义补充。
"""

import json
from abc import ABC, abstractmethod
from typing import List, Optional


class QuestionSplitter(ABC):
    """问题拆分器抽象基类"""

    @abstractmethod
    def split(self, question: str) -> List[str]:
        """将问题拆分为子问题列表"""
        pass


class LLMBasedSplitter(QuestionSplitter):
    """
    基于 LLM 的问题拆分器

    功能：
    1. 使用 LLM 分析问题是否包含多个独立的子问题
    2. 如果有多个子问题，进行拆分
    3. 分析每个子问题是否包含代词（如"它"、"这个"、"那个"等）
    4. 如果需要，从原问题中提取实体并替换代词，使子问题语义完整
    """

    def __init__(self, chat_model=None):
        """
        初始化基于 LLM 的拆分器

        Args:
            chat_model: 聊天模型实例
        """
        self.chat_model = chat_model

    def split(self, question: str, temperature: float = 0.1) -> List[str]:
        """
        使用 LLM 将问题拆分为子问题列表，并进行语义补充

        Args:
            question: 用户输入的问题
            temperature: 温度参数，控制拆分结果的随机性，默认0.1

        Returns:
            语义完整的子问题列表
        """
        if not question or not question.strip():
            return [question]

        # 如果没有提供模型，直接返回原问题
        if not self.chat_model:
            return [question]

        # 使用 LLM 一次性完成拆分和语义补充
        prompt = f"""请分析以下用户问题，判断是否包含多个独立的子问题。

用户问题：{question}

处理要求：
1. 如果问题包含多个独立的子问题，请将其拆分。
2. 分析每个子问题是否包含代词（如"它"、"这个"、"那个"、"它们"等）。
3. 如果子问题中的代词指代原问题中提到的某个具体事物，请将该代词替换为具体的事物名称，使子问题语义完整。
4. 每个子问题应该是一个完整的、可以独立回答的问题。

请以 JSON 格式返回，格式如下：
{{"sub_questions": ["子问题1", "子问题2", ...]}}

如果问题不需要拆分，请返回只包含原始问题的数组。

示例：
- 输入："什么是RAG？它有哪些优势？"
- 输出：{{"sub_questions": ["什么是RAG？", "RAG有哪些优势？"]}}

- 输入："深度学习和机器学习有什么区别？"
- 输出：{{"sub_questions": ["深度学习和机器学习有什么区别？"]}}

- 输入："Python和Java分别有什么特点？"
- 输出：{{"sub_questions": ["Python有什么特点？", "Java有什么特点？"]}}
"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.chat_model.chat(messages, temperature=temperature)

            # 解析 LLM 响应 - 提取 JSON 部分
            result = _extract_json(response)
            if result is None:
                print(f"LLM 返回格式错误: 无法解析 JSON，返回原问题")
                return [question]

            sub_questions = result.get("sub_questions", [question])

            # 验证返回结果
            if not sub_questions or not isinstance(sub_questions, list):
                return [question]

            # 确保每个子问题都不为空
            cleaned_questions = [sq.strip() for sq in sub_questions if sq and sq.strip()]

            return cleaned_questions if cleaned_questions else [question]

        except Exception as e:
            print(f"LLM 拆分失败: {e}，返回原问题")
            return [question]


def _extract_json(response: str):
    """
    从 LLM 响应中提取 JSON 对象

    Args:
        response: LLM 原始响应字符串

    Returns:
        解析后的字典，如果解析失败返回 None
    """
    if not response:
        return None

    # 查找第一个 { 和最后一个 }
    response = response.strip()
    start_idx = response.find('{')
    end_idx = response.rfind('}')

    if start_idx == -1 or end_idx == -1:
        return None

    json_str = response[start_idx:end_idx + 1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # 尝试修复常见的 JSON 格式问题
        try:
            cleaned = json_str.replace('\n', ' ').replace('\r', '')
            return json.loads(cleaned)
        except:
            return None


def get_question_splitter(chat_model=None) -> LLMBasedSplitter:
    """
    获取问题拆分器实例

    Args:
        chat_model: 聊天模型实例（必须提供）

    Returns:
        LLMBasedSplitter 实例
    """
    if not chat_model:
        raise ValueError("LLM 问题拆分必须提供 chat_model 参数")
    return LLMBasedSplitter(chat_model)


# 便捷函数
def split_question(question: str, chat_model, temperature: float = 0.1) -> List[str]:
    """
    拆分问题的便捷函数（只支持 LLM 模式）

    Args:
        question: 用户问题
        chat_model: 聊天模型实例（必须提供）
        temperature: 温度参数，控制拆分结果的随机性，默认0.1

    Returns:
        语义完整的子问题列表

    示例:
        输入: "什么是RAG？它有哪些优势"
        输出: ["什么是RAG？", "RAG有哪些优势"]
    """
    splitter = get_question_splitter(chat_model)
    return splitter.split(question, temperature=temperature)
