"""
问题拆分模块 (Question Splitter)

负责将用户的复杂问题拆分为多个子问题，以便分别进行检索和回答。
只支持使用 LLM 模型进行智能拆分，并进行语义补充。

使用示例：
    from app.services.user_interaction.question_splitter import split_question
    from app.config.model_config import get_chat_model

    chat_model = get_chat_model()
    sub_questions = split_question("什么是RAG？它有哪些优势", chat_model)
    # 返回: ["什么是RAG？", "RAG有哪些优势"]
"""

from .question_splitter import (
    QuestionSplitter,
    LLMBasedSplitter,
    get_question_splitter,
    split_question,
)

__all__ = [
    'QuestionSplitter',
    'LLMBasedSplitter',
    'get_question_splitter',
    'split_question',
]
