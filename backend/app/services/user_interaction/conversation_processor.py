"""
用户交互流程模块

整合用户交互的步骤：
1. 问题拆分 (Question Splitter) - 复杂问题 → 子问题列表
2. 问题向量化 (Query Encoder) - 子问题 → 向量表示
3. 检索和重排序 (Retrieval) - 向量检索 → Top K 分片
4. 答案生成 (Generator) - 问题 + 分片 → LLM 答案

使用方式：
    from app.services.user_interaction import process_conversation

    result = process_conversation(user_question, conversation_history)
"""

import time
import logging
from typing import Dict, Any, List, Optional

from .question_splitter import split_question
from .query_encoder import get_query_encoder
from .retrieval import RetrievalPipeline
from .generator import AnswerGenerator
from .intent_recognition import predict_knowledge_base
from app.config.model_config import get_chat_model

# 配置日志
logger = logging.getLogger(__name__)


def process_conversation(
    question: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    top_k: int = 5,
    retrieval_top_k: int = 20,
    kb_id: Optional[str] = None,
    show_progress: bool = True
) -> Dict[str, Any]:
    """
    完整的用户对话处理流程（主入口函数）

    处理流程：
        1. 问题拆分 → 2. 问题向量化 → 3. 检索和重排序 → 4. 答案生成

    Args:
        question: 用户问题
        conversation_history: 对话历史（可选），格式：[{"role": "user/assistant", "content": "..."}]
        top_k: 每个子问题最终返回的分片数量
        retrieval_top_k: 每个子问题初始检索的分片数量
        kb_id: 知识库 ID（可选），指定后仅从该知识库检索
        show_progress: 是否显示处理进度

    Returns:
        处理结果，包含：
            - success: 是否成功
            - answer: 生成的答案
            - sub_questions: 子问题列表
            - retrieved_chunks: 检索到的分片数据
            - total_elapsed: 总耗时
            - error: 错误信息（如果失败）
    """
    start_time = time.time()

    result = {
        "success": False,
        "answer": "",
        "sub_questions": [],
        "retrieved_chunks": [],
        "total_elapsed": 0,
        "error": None
    }

    try:
        # ============================================
        # 第一步：问题拆分
        # ============================================
        step_start = time.time()
        chat_model = get_chat_model()
        sub_questions = split_question(question, chat_model, temperature=0.1)
        step_elapsed = time.time() - step_start

        result['sub_questions'] = sub_questions

        # ============================================
        # 第二步：问题向量化
        # ============================================
        step_start = time.time()
        encoder = get_query_encoder()
        query_embeddings = encoder.encode_queries(sub_questions)
        step_elapsed = time.time() - step_start

        # ============================================
        # 第三步：检索和重排序
        # ============================================
        step_start = time.time()
        retrieval_pipeline = RetrievalPipeline(
            retrieval_top_k=retrieval_top_k,
            final_top_k=top_k,
            kb_id=kb_id  # 传递知识库 ID
        )
        all_retrieved_chunks = retrieval_pipeline.batch_retrieve(
            queries=sub_questions,
            query_embeddings=query_embeddings,
            encoder=encoder
        )
        step_elapsed = time.time() - step_start

        result['retrieved_chunks'] = all_retrieved_chunks

        # ============================================
        # 第四步：Chunk 过滤（低分过滤）
        # ============================================
        CHUNK_SCORE_THRESHOLD = 0.3  # chunk 分数阈值

        step_start = time.time()
        filtered_chunks = []
        filtered_count = 0

        for chunks in all_retrieved_chunks:
            filtered = [c for c in chunks if c.get('rerank_score', 0) >= CHUNK_SCORE_THRESHOLD]
            filtered_chunks.append(filtered)
            filtered_count += len(chunks) - len(filtered)

        step_elapsed = time.time() - step_start

        # 更新为过滤后的 chunks
        all_retrieved_chunks = filtered_chunks

        # ============================================
        # 第五步：答案生成
        # ============================================
        step_start = time.time()
        generator = AnswerGenerator()

        if len(sub_questions) == 1:
            # 单个问题，直接生成答案
            answer = generator.generate(
                query=sub_questions[0],
                retrieved_chunks=all_retrieved_chunks[0],
                conversation_history=conversation_history
            )
        else:
            # 多个问题，生成综合答案
            answer = generator.generate_for_sub_questions(
                sub_questions=sub_questions,
                all_retrieved_chunks=all_retrieved_chunks,
                original_query=question
            )

        step_elapsed = time.time() - step_start

        result['answer'] = answer

        # ============================================
        # 完成
        # ============================================
        result['success'] = True
        result['total_elapsed'] = time.time() - start_time

        logger.info(f"对话处理完成: 耗时: {result['total_elapsed']:.2f}s, 检索到 {sum(len(c) for c in all_retrieved_chunks)} 个 chunks")

        return result

    except Exception as e:
        result['error'] = str(e)
        result['total_elapsed'] = time.time() - start_time

        logger.error(f"[对话处理失败] 问题处理失败: {str(e)}, 耗时: {result['total_elapsed']:.2f}s", exc_info=True)

        raise


def process_conversation_simple(
    question: str,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    简化版对话处理（只返回答案）

    Args:
        question: 用户问题
        conversation_history: 对话历史（可选）

    Returns:
        生成的答案
    """
    result = process_conversation(question, conversation_history, show_progress=False)
    return result['answer']


# 向后兼容
def chat(question: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """
    向后兼容的 chat 函数

    内部调用完整的 process_conversation 流程

    Args:
        question: 用户问题
        conversation_history: 对话历史

    Returns:
        处理结果字典
    """
    return process_conversation(question, conversation_history, show_progress=True)


# ============================================
# 智能两阶段召回
# ============================================

RERANK_SCORE_THRESHOLD = 0.6  # rerank 分数阈值


def process_conversation_with_intent(
    question: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    top_k: int = 5,
    retrieval_top_k: int = 20,
    kb_id: Optional[str] = None,
    show_progress: bool = True
) -> Dict[str, Any]:
    """
    智能两阶段召回的对话处理流程

    流程：
    1. 如果用户指定了 kb_id，直接查询
    2. 如果用户未指定 kb_id：
       a. 使用 LLM 进行意图识别，预测最相关的知识库
       b. 进行第一次定向召回
       c. 检查最高 rerank_score：
          - 如果 >= 0.6：使用当前结果生成答案
          - 如果 < 0.6：进行第二次全局召回

    Args:
        question: 用户问题
        conversation_history: 对话历史（可选）
        top_k: 每个子问题最终返回的分片数量
        retrieval_top_k: 每个子问题初始检索的分片数量
        kb_id: 知识库 ID（可选），如果指定则跳过意图识别
        show_progress: 是否显示处理进度

    Returns:
        处理结果，包含：
            - success: 是否成功
            - answer: 生成的答案
            - kb_id: 最终使用的知识库 ID（可能为 None 表示全库）
            - retrieved_chunks: 检索到的分片数据
            - total_elapsed: 总耗时
            - stages: 召回阶段信息
    """
    start_time = time.time()

    result = {
        "success": False,
        "answer": "",
        "kb_id": kb_id,
        "retrieved_chunks": [],
        "total_elapsed": 0,
        "stages": {
            "intent_recognition": None,
            "first_retrieval": None,
            "second_retrieval": None
        },
        "error": None
    }

    try:
        # ============================================
        # 阶段0：意图识别（仅当未指定 kb_id 时）
        # ============================================
        predicted_kb_id = kb_id
        if kb_id is None:
            step_start = time.time()
            predicted_kb_id = predict_knowledge_base(question)
            step_elapsed = time.time() - step_start

            result['stages']['intent_recognition'] = {
                'predicted_kb_id': predicted_kb_id,
                'elapsed': step_elapsed
            }

            # 使用预测的 kb_id（可能为 None）
            result['kb_id'] = predicted_kb_id

        # ============================================
        # 阶段1：第一次召回（定向或全局）
        # ============================================
        step_start = time.time()
        first_result = _do_retrieval(
            question, conversation_history, top_k, retrieval_top_k,
            predicted_kb_id, show_progress=False
        )
        step_elapsed = time.time() - step_start

        # 获取最高 rerank_score
        max_score = _get_max_rerank_score(first_result.get('retrieved_chunks', []))

        result['stages']['first_retrieval'] = {
            'kb_id': predicted_kb_id,
            'max_score': max_score,
            'elapsed': step_elapsed
        }

        # ============================================
        # 阶段2：判断是否需要第二次召回
        # ============================================
        need_second_retrieval = (
            max_score < RERANK_SCORE_THRESHOLD and
            predicted_kb_id is not None  # 只有定向召回才需要第二阶段
        )

        if need_second_retrieval:
            step_start = time.time()
            second_result = _do_retrieval(
                question, conversation_history, top_k, retrieval_top_k,
                None,  # 全局召回
                show_progress=False
            )
            step_elapsed = time.time() - step_start

            # 获取第二次召回的最高分
            second_max_score = _get_max_rerank_score(second_result.get('retrieved_chunks', []))

            result['stages']['second_retrieval'] = {
                'kb_id': None,
                'max_score': second_max_score,
                'elapsed': step_elapsed
            }

            # 使用第二次召回的结果
            result['retrieved_chunks'] = second_result['retrieved_chunks']
            result['kb_id'] = None  # 标记为全局检索
            result['answer'] = second_result['answer']
        else:
            # 使用第一次召回的结果
            result['retrieved_chunks'] = first_result['retrieved_chunks']
            result['answer'] = first_result['answer']

        # ============================================
        # 完成
        # ============================================
        result['success'] = True
        result['total_elapsed'] = time.time() - start_time

        return result

    except Exception as e:
        result['error'] = str(e)
        result['total_elapsed'] = time.time() - start_time

        logger.error(f"[智能召回失败] 处理失败: {str(e)}, 耗时: {result['total_elapsed']:.2f}s", exc_info=True)

        raise


def _do_retrieval(
    question: str,
    conversation_history: Optional[List[Dict[str, str]]],
    top_k: int,
    retrieval_top_k: int,
    kb_id: Optional[str],
    show_progress: bool
) -> Dict[str, Any]:
    """
    执行单次检索流程

    Args:
        question: 用户问题
        conversation_history: 对话历史
        top_k: 最终返回数量
        retrieval_top_k: 初始检索数量
        kb_id: 知识库 ID（None 表示全局检索）
        show_progress: 是否显示进度

    Returns:
        检索结果
    """
    return process_conversation(
        question=question,
        conversation_history=conversation_history,
        top_k=top_k,
        retrieval_top_k=retrieval_top_k,
        kb_id=kb_id,
        show_progress=show_progress
    )


def _get_max_rerank_score(chunks_list: List[List[Dict[str, Any]]]) -> float:
    """
    获取所有 chunks 中的最高 rerank_score

    Args:
        chunks_list: chunks 列表的列表

    Returns:
        最高分数，如果没有 chunks 返回 0.0
    """
    max_score = 0.0

    for chunks in chunks_list:
        for chunk in chunks:
            score = chunk.get('rerank_score', 0)
            if score > max_score:
                max_score = score

    return max_score

