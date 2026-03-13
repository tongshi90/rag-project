"""
生成模块 (Generator)

负责根据检索到的 chunk 生成最终答案。

使用示例：
    from app.services.user_interaction.generator import generate_answer, generate_answer_stream

    # 普通模式
    answer = generate_answer("什么是RAG？", retrieved_chunks)

    # 流式模式
    for chunk in generate_answer_stream("什么是RAG？", retrieved_chunks):
        print(chunk, end='', flush=True)
"""

from .generator import (
    ContextBuilder,
    AnswerGenerator,
    generate_answer,
    generate_answer_stream,
    generate_answer_for_sub_questions,
)

__all__ = [
    'ContextBuilder',
    'AnswerGenerator',
    'generate_answer',
    'generate_answer_stream',
    'generate_answer_for_sub_questions',
]
