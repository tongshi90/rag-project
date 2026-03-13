"""
生成模块

负责根据检索到的 chunk 生成最终答案。
"""

from typing import List, Dict, Any, Optional, Generator
from app.config.model_config import get_chat_model, ChatModel


class ContextBuilder:
    """
    上下文构建器

    将检索到的 chunks 组织成连贯的上下文
    """

    def __init__(self, max_context_length: int = 3000):
        """
        初始化上下文构建器

        Args:
            max_context_length: 最大上下文长度（字符数）
        """
        self.max_context_length = max_context_length

    def build_context(
        self,
        chunks: List[Dict[str, Any]],
        query: Optional[str] = None
    ) -> str:
        """
        构建上下文文本

        Args:
            chunks: 检索到的 chunk 列表
            query: 原始问题（可选）

        Returns:
            构建的上下文文本
        """
        if not chunks:
            return "抱歉，根据当前知识库内容，我无法回答这个问题。您可以尝试重新描述问题或上传相关文档。"

        context_parts = []

        # 按文档分组
        doc_groups = self._group_by_document(chunks)

        for doc_id, doc_chunks in doc_groups.items():
            # 按顺序排列 chunks
            doc_chunks.sort(key=lambda x: x.get('metadata', {}).get('order', 0))

            # 构建文档上下文
            doc_context = self._build_document_context(doc_chunks)
            context_parts.append(doc_context)

        # 合并所有上下文
        full_context = "\n\n".join(context_parts)

        # 截断到最大长度
        if len(full_context) > self.max_context_length:
            full_context = full_context[:self.max_context_length] + "\n...(内容截断)"

        return full_context

    def _group_by_document(
        self,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """按文档 ID 分组 chunks"""
        groups = {}
        for chunk in chunks:
            doc_id = chunk.get('metadata', {}).get('doc_id', 'unknown')
            if doc_id not in groups:
                groups[doc_id] = []
            groups[doc_id].append(chunk)
        return groups

    def _build_document_context(
        self,
        chunks: List[Dict[str, Any]]
    ) -> str:
        """构建单个文档的上下文"""
        parts = []
        for i, chunk in enumerate(chunks, 1):
            text = chunk.get('text', '').strip()
            parts.append(text)
        return "\n\n".join(parts)


class AnswerGenerator:
    """
    答案生成器

    使用 LLM 根据问题和上下文生成答案
    """

    def __init__(
        self,
        chat_model: Optional[ChatModel] = None,
        context_builder: Optional[ContextBuilder] = None
    ):
        """
        初始化答案生成器

        Args:
            chat_model: 聊天模型实例
            context_builder: 上下文构建器
        """
        self.chat_model = chat_model or get_chat_model()
        self.context_builder = context_builder or ContextBuilder()

    def generate(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        生成答案

        Args:
            query: 用户问题
            retrieved_chunks: 检索到的相关 chunks
            conversation_history: 对话历史（可选）

        Returns:
            生成的答案
        """
        # 构建上下文
        context = self.context_builder.build_context(retrieved_chunks, query)

        # 构建提示词
        prompt = self._build_prompt(query, context, conversation_history)

        # 构建消息列表
        messages = self._build_messages(prompt, conversation_history)

        # 调用 LLM
        try:
            response = self.chat_model.chat(messages)
            return self._clean_response(response)
        except Exception as e:
            return f"生成答案时出错: {str(e)}"

    def generate_stream(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Generator[str, None, None]:
        """
        流式生成答案

        Args:
            query: 用户问题
            retrieved_chunks: 检索到的相关 chunks
            conversation_history: 对话历史（可选）

        Yields:
            生成的答案片段
        """
        # 构建上下文
        context = self.context_builder.build_context(retrieved_chunks, query)

        # 构建提示词
        prompt = self._build_prompt(query, context, conversation_history)

        # 构建消息列表
        messages = self._build_messages(prompt, conversation_history)

        # 调用 LLM 流式生成
        try:
            # 直接调用流式方法（SiliconFlowChat 支持）
            for chunk in self.chat_model.chat_stream(messages):
                yield chunk
        except Exception as e:
            print(f"Stream error: {e}, falling back to normal mode")
            try:
                # 如果流式失败，回退到普通模式
                response = self.chat_model.chat(messages)
                # 模拟流式输出，按字符分块
                chunk_size = 10
                for i in range(0, len(response), chunk_size):
                    yield response[i:i + chunk_size]
            except Exception as e2:
                yield f"生成答案时出错: {str(e2)}"

    def generate_for_sub_questions(
        self,
        sub_questions: List[str],
        all_retrieved_chunks: List[List[Dict[str, Any]]],
        original_query: str
    ) -> str:
        """
        为多个子问题生成综合答案

        Args:
            sub_questions: 子问题列表
            all_retrieved_chunks: 每个子问题对应的检索结果
            original_query: 原始问题

        Returns:
            综合答案
        """
        # 为每个子问题生成答案
        sub_answers = []

        for sub_q, chunks in zip(sub_questions, all_retrieved_chunks):
            if not chunks:
                sub_answers.append(f"关于「{sub_q}」，抱歉，知识库中没有相关内容可以回答这个问题。")
                continue

            context = self.context_builder.build_context(chunks, sub_q)
            prompt = self._build_single_question_prompt(sub_q, context)

            messages = [{"role": "user", "content": prompt}]

            try:
                response = self.chat_model.chat(messages)
                cleaned = self._clean_response(response)
                sub_answers.append(f"{sub_q}\n{cleaned}")
            except Exception as e:
                sub_answers.append(f"{sub_q}\n生成答案时出错: {str(e)}")

        # 如果只有一个子问题，直接返回
        if len(sub_answers) == 1:
            return sub_answers[0]

        # 多个子问题，综合成一个答案
        final_prompt = self._build_synthesis_prompt(original_query, sub_answers)
        messages = [{"role": "user", "content": final_prompt}]

        try:
            response = self.chat_model.chat(messages)
            return self._clean_response(response)
        except Exception as e:
            # 如果综合失败，返回所有子答案
            return "\n\n".join(sub_answers)

    def _build_prompt(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """构建提示词"""
        prompt = f"""根据以下参考内容回答用户问题。除非用户明确要求解释原因，否则直接给出答案即可。

参考内容：
{context}

问题：{query}

要求：
1. 答案必须严格基于参考内容，不要编造信息
2. 如果参考内容中没有相关信息来回答用户的问题，请友好地说明："抱歉，根据当前知识库内容，我无法回答这个问题。您可以尝试重新描述问题或上传相关文档。"
3. 不要说"参考内容中没有"等生硬的话，使用自然的友好表达
4. 只返回问题答案本身，不要添加"希望这些信息能帮到您"、"如有其他问题请随时提问"等客套话或结语

回答：
"""
        return prompt

    def _build_single_question_prompt(self, question: str, context: str) -> str:
        """为单个问题构建提示词"""
        return f"""根据参考内容回答问题。除非问题要求解释原因，否则直接给出答案。

参考内容：
{context}

问题：{question}

要求：
1. 如果参考内容中没有相关信息，请说明"抱歉，知识库中没有相关内容可以回答这个问题。"
2. 只返回问题答案本身，不要添加"希望这些信息能帮到您"、"如有其他问题请随时提问"等客套话或结语

回答：
"""

    def _build_synthesis_prompt(self, original_query: str, sub_answers: List[str]) -> str:
        """构建综合答案的提示词"""
        answers_text = "\n\n".join(sub_answers)
        return f"""将以下子答案整合成简洁的完整回答，不要添加额外信息。

问题：{original_query}

子答案：
{answers_text}

要求：
1. 整合后的回答要简洁连贯
2. 只返回整合后的答案本身，不要添加"希望这些信息能帮到您"、"如有其他问题请随时提问"等客套话或结语

综合回答：
"""

    def _build_messages(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """构建消息列表"""
        messages = []

        # 添加对话历史
        if conversation_history:
            # 限制历史长度，避免超出模型限制
            recent_history = conversation_history[-6:]  # 保留最近3轮对话
            messages.extend(recent_history)

        # 添加当前问题
        messages.append({"role": "user", "content": prompt})

        return messages

    def _clean_response(self, response: str) -> str:
        """清理响应内容"""
        if not response:
            return "抱歉，无法生成答案。"

        response = response.strip()

        # 移除可能的思考过程标记
        if "思考：" in response or "思考:" in response:
            lines = response.split('\n')
            cleaned_lines = []
            skip_thinking = False
            for line in lines:
                if line.startswith('思考：') or line.startswith('思考:'):
                    skip_thinking = True
                    continue
                if skip_thinking and line.startswith('答案：'):
                    skip_thinking = False
                    cleaned_lines.append(line[3:])
                    continue
                if not skip_thinking:
                    cleaned_lines.append(line)
            response = '\n'.join(cleaned_lines).strip()

        return response


# 便捷函数
def generate_answer(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    生成答案的便捷函数

    Args:
        query: 用户问题
        retrieved_chunks: 检索到的相关 chunks
        conversation_history: 对话历史

    Returns:
        生成的答案
    """
    generator = AnswerGenerator()
    return generator.generate(query, retrieved_chunks, conversation_history)


def generate_answer_stream(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Generator[str, None, None]:
    """
    流式生成答案的便捷函数

    Args:
        query: 用户问题
        retrieved_chunks: 检索到的相关 chunks
        conversation_history: 对话历史

    Yields:
        生成的答案片段
    """
    generator = AnswerGenerator()
    yield from generator.generate_stream(query, retrieved_chunks, conversation_history)


def generate_answer_for_sub_questions(
    sub_questions: List[str],
    all_retrieved_chunks: List[List[Dict[str, Any]]],
    original_query: str
) -> str:
    """
    为子问题生成综合答案的便捷函数

    Args:
        sub_questions: 子问题列表
        all_retrieved_chunks: 每个子问题对应的检索结果
        original_query: 原始问题

    Returns:
        综合答案
    """
    generator = AnswerGenerator()
    return generator.generate_for_sub_questions(
        sub_questions, all_retrieved_chunks, original_query
    )
