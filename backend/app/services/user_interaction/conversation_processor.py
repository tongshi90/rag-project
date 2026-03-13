"""
用户交互流程模块

整合用户交互的步骤：
1. 问题拆分 (Question Splitter) - 复杂问题 → 子问题列表
2. 实体识别 (Entity Recognizer) - 识别问题中的实体
3. 问题向量化 (Query Encoder) - 子问题 → 向量表示
4. 检索和重排序 (Retrieval) - 混合检索（向量+关键字+图谱）→ Top K 分片
5. 答案生成 (Generator) - 问题 + 分片 → LLM 答案

使用方式：
    from app.services.user_interaction import process_conversation

    result = process_conversation(user_question, conversation_history)
    result = process_conversation_hybrid(user_question, conversation_history, doc_id="xxx")
"""

import time
from typing import Dict, Any, List, Optional

from .question_splitter import split_question
from .query_encoder import get_query_encoder
from .retrieval import RetrievalPipeline, HybridRetrievalPipeline
from .generator import AnswerGenerator
from .entity_recognizer import QueryEntityRecognizer
from app.config.model_config import get_chat_model


def process_conversation(
    question: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    top_k: int = 5,
    retrieval_top_k: int = 20,
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
        if show_progress:
            print(f"\n{'#'*60}")
            print(f"# 开始处理用户问题")
            print(f"# 问题: {question[:50]}{'...' if len(question) > 50 else ''}")
            print(f"{'#'*60}\n")

        # ============================================
        # 第一步：问题拆分
        # ============================================
        if show_progress:
            print(f"\n{'='*60}")
            print(f"第一步: 问题拆分")
            print(f"{'='*60}")

        step_start = time.time()
        chat_model = get_chat_model()
        sub_questions = split_question(question, chat_model, temperature=0.1)
        step_elapsed = time.time() - step_start

        if show_progress:
            print(f"拆分完成: {len(sub_questions)} 个子问题")
            for i, sq in enumerate(sub_questions, 1):
                print(f"  - 子问题 {i}: {sq}")
            print(f"耗时: {step_elapsed:.2f} 秒")

        result['sub_questions'] = sub_questions

        # ============================================
        # 第二步：问题向量化
        # ============================================
        if show_progress:
            print(f"\n{'='*60}")
            print(f"第二步: 问题向量化")
            print(f"{'='*60}")

        step_start = time.time()
        encoder = get_query_encoder()
        query_embeddings = encoder.encode_queries(sub_questions)
        step_elapsed = time.time() - step_start

        if show_progress:
            print(f"向量化完成: {len(query_embeddings)} 个向量")
            print(f"向量维度: {len(query_embeddings[0]) if query_embeddings else 'N/A'}")
            print(f"耗时: {step_elapsed:.2f} 秒")

        # ============================================
        # 第三步：检索和重排序
        # ============================================
        if show_progress:
            print(f"\n{'='*60}")
            print(f"第三步: 检索和重排序")
            print(f"{'='*60}")

        step_start = time.time()
        retrieval_pipeline = RetrievalPipeline(
            retrieval_top_k=retrieval_top_k,
            final_top_k=top_k
        )
        all_retrieved_chunks = retrieval_pipeline.batch_retrieve(
            queries=sub_questions,
            query_embeddings=query_embeddings,
            encoder=encoder
        )
        step_elapsed = time.time() - step_start

        # 统计检索结果
        total_chunks = sum(len(chunks) for chunks in all_retrieved_chunks)

        if show_progress:
            print(f"检索完成: 共 {total_chunks} 个分片")
            for i, chunks in enumerate(all_retrieved_chunks, 1):
                print(f"  - 子问题 {i}: {len(chunks)} 个分片")
            print(f"耗时: {step_elapsed:.2f} 秒")

        result['retrieved_chunks'] = all_retrieved_chunks

        # ============================================
        # 第四步：答案生成
        # ============================================
        if show_progress:
            print(f"\n{'='*60}")
            print(f"第四步: 答案生成 (LLM)")
            print(f"{'='*60}")

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

        if show_progress:
            print(f"答案生成完成")
            print(f"耗时: {step_elapsed:.2f} 秒")

        result['answer'] = answer

        # ============================================
        # 完成
        # ============================================
        result['success'] = True
        result['total_elapsed'] = time.time() - start_time

        if show_progress:
            print(f"\n{'#'*60}")
            print(f"# 用户问题处理完成！")
            print(f"# 总耗时: {result['total_elapsed']:.2f} 秒")
            print(f"{'#'*60}\n")

        return result

    except Exception as e:
        result['error'] = str(e)
        result['total_elapsed'] = time.time() - start_time

        if show_progress:
            print(f"\n{'!'*60}")
            print(f"! 问题处理失败: {str(e)}")
            print(f"{'!'*60}\n")

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


def process_conversation_hybrid(
    question: str,
    doc_id: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    top_k: int = 5,
    retrieval_top_k: int = 20,
    show_progress: bool = True,
    enable_vector: bool = True,
    enable_keyword: bool = True,
    enable_graph: bool = True,
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    使用混合检索的完整对话处理流程

    处理流程：
        1. 问题拆分 → 2. 实体识别 → 3. 问题向量化 → 4. 混合检索 → 5. 答案生成

    Args:
        question: 用户问题
        doc_id: 文档 ID（用于加载图谱和索引）
        conversation_history: 对话历史（可选）
        top_k: 最终返回的分片数量
        retrieval_top_k: 初始检索的分片数量
        show_progress: 是否显示处理进度
        enable_vector: 是否启用向量检索
        enable_keyword: 是否启用关键字检索
        enable_graph: 是否启用图谱检索
        weights: 各检索方法的权重配置

    Returns:
        处理结果，包含：
            - success: 是否成功
            - answer: 生成的答案
            - sub_questions: 子问题列表
            - recognized_entities: 识别的实体
            - retrieved_chunks: 检索到的分片数据
            - total_elapsed: 总耗时
    """
    start_time = time.time()

    result = {
        "success": False,
        "answer": "",
        "sub_questions": [],
        "recognized_entities": [],
        "retrieved_chunks": [],
        "total_elapsed": 0,
        "error": None
    }

    try:
        if show_progress:
            print(f"\n{'#'*60}")
            print(f"# 开始处理用户问题（混合检索）")
            print(f"# 问题: {question[:50]}{'...' if len(question) > 50 else ''}")
            print(f"# 文档 ID: {doc_id}")
            print(f"{'#'*60}\n")

        # ============================================
        # 第一步：问题拆分
        # ============================================
        if show_progress:
            print(f"\n{'='*60}")
            print(f"第一步: 问题拆分")
            print(f"{'='*60}")

        step_start = time.time()
        chat_model = get_chat_model()
        sub_questions = split_question(question, chat_model, temperature=0.1)
        step_elapsed = time.time() - step_start

        if show_progress:
            print(f"拆分完成: {len(sub_questions)} 个子问题")
            for i, sq in enumerate(sub_questions, 1):
                print(f"  - 子问题 {i}: {sq}")
            print(f"耗时: {step_elapsed:.2f} 秒")

        result['sub_questions'] = sub_questions

        # ============================================
        # 第二步：实体识别
        # ============================================
        if show_progress:
            print(f"\n{'='*60}")
            print(f"第二步: 实体识别")
            print(f"{'='*60}")

        step_start = time.time()
        entity_recognizer = QueryEntityRecognizer()
        entities = entity_recognizer.recognize_entities(question, doc_id, use_graph=enable_graph)

        # 转换实体为 ID
        entity_ids = entity_recognizer.get_entity_ids(entities, doc_id) if enable_graph else []
        step_elapsed = time.time() - step_start

        if show_progress:
            print(f"实体识别完成: {len(entities)} 个实体")
            for entity in entities[:5]:
                print(f"  - {entity['text']} ({entity['type']})")
            if len(entities) > 5:
                print(f"  ... 等 {len(entities)} 个实体")
            print(f"匹配到 {len(entity_ids)} 个图谱实体")
            print(f"耗时: {step_elapsed:.2f} 秒")

        result['recognized_entities'] = entities

        # ============================================
        # 第三步：问题向量化
        # ============================================
        if show_progress:
            print(f"\n{'='*60}")
            print(f"第三步: 问题向量化")
            print(f"{'='*60}")

        step_start = time.time()
        encoder = get_query_encoder()
        query_embeddings = encoder.encode_queries(sub_questions)
        step_elapsed = time.time() - step_start

        if show_progress:
            print(f"向量化完成: {len(query_embeddings)} 个向量")
            print(f"向量维度: {len(query_embeddings[0]) if query_embeddings else 'N/A'}")
            print(f"耗时: {step_elapsed:.2f} 秒")

        # ============================================
        # 第四步：混合检索
        # ============================================
        if show_progress:
            print(f"\n{'='*60}")
            print(f"第四步: 混合检索 (向量+关键字+图谱)")
            print(f"{'='*60}")

        step_start = time.time()
        hybrid_pipeline = HybridRetrievalPipeline(
            retrieval_top_k=retrieval_top_k,
            final_top_k=top_k,
            weights=weights
        )

        all_retrieved_chunks = []
        for i, (sub_q, embedding) in enumerate(zip(sub_questions, query_embeddings)):
            chunks = hybrid_pipeline.retrieve(
                query=sub_q,
                query_embedding=embedding,
                doc_id=doc_id,
                entity_ids=entity_ids,
                encoder=encoder,
                enable_vector=enable_vector,
                enable_keyword=enable_keyword,
                enable_graph=enable_graph
            )
            all_retrieved_chunks.append(chunks)

        step_elapsed = time.time() - step_start

        total_chunks = sum(len(chunks) for chunks in all_retrieved_chunks)

        if show_progress:
            print(f"检索完成: 共 {total_chunks} 个分片")
            for i, chunks in enumerate(all_retrieved_chunks, 1):
                print(f"  - 子问题 {i}: {len(chunks)} 个分片")
            print(f"耗时: {step_elapsed:.2f} 秒")

        result['retrieved_chunks'] = all_retrieved_chunks

        # ============================================
        # 第五步：答案生成
        # ============================================
        if show_progress:
            print(f"\n{'='*60}")
            print(f"第五步: 答案生成 (LLM)")
            print(f"{'='*60}")

        step_start = time.time()
        generator = AnswerGenerator()

        if len(sub_questions) == 1:
            answer = generator.generate(
                query=sub_questions[0],
                retrieved_chunks=all_retrieved_chunks[0],
                conversation_history=conversation_history
            )
        else:
            answer = generator.generate_for_sub_questions(
                sub_questions=sub_questions,
                all_retrieved_chunks=all_retrieved_chunks,
                original_query=question
            )

        step_elapsed = time.time() - step_start

        if show_progress:
            print(f"答案生成完成")
            print(f"耗时: {step_elapsed:.2f} 秒")

        result['answer'] = answer

        # ============================================
        # 完成
        # ============================================
        result['success'] = True
        result['total_elapsed'] = time.time() - start_time

        if show_progress:
            print(f"\n{'#'*60}")
            print(f"# 用户问题处理完成！（混合检索）")
            print(f"# 总耗时: {result['total_elapsed']:.2f} 秒")
            print(f"{'#'*60}\n")

        return result

    except Exception as e:
        result['error'] = str(e)
        result['total_elapsed'] = time.time() - start_time

        if show_progress:
            print(f"\n{'!'*60}")
            print(f"! 问题处理失败: {str(e)}")
            print(f"{'!'*60}\n")

        raise
