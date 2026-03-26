"""
完整文档处理流程模块

整合文档处理的步骤：
1. 文档拆分 (Splitter) - PDF/Word → Chunks
2. 异常检测 (Validator) - Chunk 质量检测
3. Chunk 优化 (Optimizer) - LLM 辅助合并/拆分
4. 向量化存储 (Embedding) - 向量数据库存储

使用方式：
    from app.services.document_processing import process_document

    result = process_document(file_path, file_id)

支持格式：
- PDF (.pdf)
- Word (.docx)
"""

import time
import logging
from pathlib import Path
from typing import Dict, Any

from .embedding import embed_and_store_chunks, get_vector_store
from .optimizer.chunk_optimizer import optimize_chunks
# 导入各个步骤的模块
from .splitter import split_pdf_to_chunks, split_word_to_chunks, is_word_file
from .validator.validate import validate_chunks, get_validation_summary, merge_short_chunks

# 配置日志
logger = logging.getLogger(__name__)


def process_document(
    file_path: str,
    doc_id: str,
    kb_id: str = None,
    show_progress: bool = True,
    embedding_batch_size: int = 10
) -> Dict[str, Any]:
    """
    完整的文档处理流程（主入口函数）

    处理流程：
        1. 文档拆分 → 2. 异常检测 → 3. Chunk 优化 → 4. 向量化存储

    Args:
        file_path: 文件路径（支持 PDF 和 Word）
        doc_id: 文档 ID
        kb_id: 知识库 ID（可选），用于标记向量数据
        show_progress: 是否显示处理进度
        embedding_batch_size: 向量化批处理大小

    Returns:
        处理结果，包含：
            - success: 是否成功
            - doc_id: 文档 ID
            - file_type: 文件类型（pdf/word）
            - steps: 各步骤的执行结果
                - split: 拆分结果
                - validate: 验证结果
                - optimize: 优化结果
                - embed: 向量化结果
            - total_elapsed: 总耗时
            - error: 错误信息（如果失败）

    Raises:
        Exception: 当处理失败时抛出异常
    """
    start_time = time.time()

    # 判断文件类型
    file_type = "word" if is_word_file(file_path) else "pdf"

    result = {
        "success": False,
        "doc_id": doc_id,
        "steps": {},
        "total_elapsed": 0,
        "error": None
    }

    try:
        # ============================================
        # 第一步：文档拆分
        # ============================================
        step_start = time.time()
        # 根据文件类型选择解析器，传递 kb_id
        # 注意：新的返回格式是 (chunks, result_info)，其中 result_info 包含 title_tree, toc_info, title_patterns
        if file_type == "word":
            chunks, result_info = split_word_to_chunks(file_path, doc_id, kb_id)
        else:
            chunks, result_info = split_pdf_to_chunks(file_path, doc_id, kb_id)

        # 从 result_info 中提取 title_patterns（向后兼容）
        title_patterns = result_info.get("title_patterns", [])
        title_tree = result_info.get("title_tree", [])
        toc_info = result_info.get("toc_info")

        step_elapsed = time.time() - step_start

        result['steps']['split'] = {
            "success": True,
            "file_type": file_type,
            "chunk_count": len(chunks),
            "title_pattern_count": len(title_patterns) if title_patterns else 0,
            "elapsed": step_elapsed
        }

        # ============================================
        # 短 Chunk 合并处理
        # ============================================
        step_start = time.time()
        chunks_before_merge = len(chunks)
        chunks = merge_short_chunks(chunks, min_content_tokens=20)
        step_elapsed = time.time() - step_start

        result['steps']['merge_short_chunks'] = {
            "success": True,
            "original_count": chunks_before_merge,
            "merged_count": len(chunks),
            "change": len(chunks) - chunks_before_merge,
            "elapsed": step_elapsed
        }

        """
        # ============================================
        # 第二步：异常检测
        # ============================================
        logger.info(f"[质量检测] 开始检测 {len(chunks)} 个 chunks 的质量")
        if show_progress:
            print(f"\n{'='*60}")
            print(f"第二步: Chunk 质量检测")
            print(f"{'='*60}")

        step_start = time.time()
        validated_chunks = validate_chunks(chunks, title_patterns)
        validation_summary = get_validation_summary(validated_chunks)
        step_elapsed = time.time() - step_start

        result['steps']['validate'] = {
            "success": True,
            "total_chunks": validation_summary.get('total_chunks', 0),
            "chunks_with_errors": validation_summary.get('chunks_with_errors', 0),
            "chunks_with_hard_violation": validation_summary.get('chunks_with_hard_violation', 0),
            "total_risk_score": validation_summary.get('total_risk_score', 0),
            "high_risk_count": len(validation_summary.get('high_risk_chunks', [])),
            "elapsed": step_elapsed
        }

        logger.info(f"[质量检测] 完成: 异常 {validation_summary.get('chunks_with_errors', 0)} 个, "
                   f"高风险 {len(validation_summary.get('high_risk_chunks', []))} 个, "
                   f"风险分数 {validation_summary.get('total_risk_score', 0)}, 耗时: {step_elapsed:.2f}s")
        if show_progress:
            print(f"检测完成: {validation_summary.get('chunks_with_errors', 0)} 个异常 chunks")
            print(f"高风险 chunks: {len(validation_summary.get('high_risk_chunks', []))}")
            print(f"总风险分数: {validation_summary.get('total_risk_score', 0)}")
            print(f"耗时: {step_elapsed:.2f} 秒")

        # ============================================
        # 第三步：Chunk 优化
        # ============================================
        logger.info(f"[Chunk优化] 开始优化 {len(validated_chunks)} 个 chunks (最小风险分数: 60)")
        if show_progress:
            print(f"\n{'='*60}")
            print(f"第三步: Chunk 优化 (LLM)")
            print(f"{'='*60}")

        step_start = time.time()
        optimized_chunks = optimize_chunks(
            validated_chunks,
            min_risk_score=40,
            show_content=False  # 不显示详细内容预览
        )
        step_elapsed = time.time() - step_start

        result['steps']['optimize'] = {
            "success": True,
            "original_count": len(validated_chunks),
            "optimized_count": len(optimized_chunks),
            "change": len(optimized_chunks) - len(validated_chunks),
            "elapsed": step_elapsed
        }

        logger.info(f"[Chunk优化] 完成: {len(validated_chunks)} → {len(optimized_chunks)} chunks "
                   f"(变化: {len(optimized_chunks) - len(validated_chunks):+d}), 耗时: {step_elapsed:.2f}s")
        if show_progress:
            print(f"优化完成: {len(validated_chunks)} → {len(optimized_chunks)} chunks")
            print(f"变化: {len(optimized_chunks) - len(validated_chunks):+d}")
            print(f"耗时: {step_elapsed:.2f} 秒")
        """

        # ============================================
        # 第四步：向量化存储
        # ============================================
        step_start = time.time()
        embed_result = embed_and_store_chunks(
            chunks=chunks,
            doc_id=doc_id,
            batch_size=embedding_batch_size,
            show_progress=False
        )
        step_elapsed = time.time() - step_start

        result['steps']['embed'] = {
            "success": True,
            "total_chunks": embed_result.get('total_chunks', 0),
            "success_count": embed_result.get('success_count', 0),
            "failed_count": embed_result.get('failed_count', 0),
            "vector_store_stats": embed_result.get('vector_store_stats', {}),
            "elapsed": step_elapsed
        }

        # ============================================
        # 完成
        # ============================================
        result['success'] = True
        result['total_elapsed'] = time.time() - start_time

        logger.info(f"文档 {doc_id} 处理成功! 共 {len(chunks)} 个 chunks, 耗时: {result['total_elapsed']:.2f}s")

        return result

    except Exception as e:
        result['error'] = str(e)
        result['total_elapsed'] = time.time() - start_time

        logger.error(f"文档 {doc_id} 处理失败: {str(e)}, 耗时: {result['total_elapsed']:.2f}s", exc_info=True)

        raise


def delete_document_vectors(doc_id: str, show_progress: bool = True) -> Dict[str, Any]:
    """
    删除文档的向量数据

    Args:
        doc_id: 文档 ID
        show_progress: 是否显示进度

    Returns:
        删除结果
    """
    result = {
        "success": True,
        "doc_id": doc_id,
        "deleted": {
            "vectors": 0
        },
        "error": None
    }

    try:
        # 删除向量数据
        vector_store = get_vector_store()
        count = vector_store.delete_by_doc_id(doc_id)
        result["deleted"]["vectors"] = count

    except Exception as e:
        result["success"] = False
        result["error"] = f"删除向量数据失败: {str(e)}"

    return result


def get_document_stats(doc_id: str) -> Dict[str, Any]:
    """
    获取文档的向量存储统计信息

    Args:
        doc_id: 文档 ID

    Returns:
        统计信息
    """
    try:
        vector_store = get_vector_store()
        chunks = vector_store.get_chunks_by_doc_id(doc_id)

        return {
            "success": True,
            "doc_id": doc_id,
            "chunk_count": len(chunks),
            "chunks": chunks
        }

    except Exception as e:
        return {
            "success": False,
            "doc_id": doc_id,
            "error": str(e),
            "chunk_count": 0
        }


# 向后兼容：保持原有的 parse_pdf 函数名
def parse_pdf(file_path: str, doc_id: str, kb_id: str = None) -> Dict[str, Any]:
    """
    向后兼容的 parse_pdf 函数

    内部调用完整的 process_document 流程
    注意：函数名虽然叫 parse_pdf，但实际支持 PDF 和 Word 文档

    Args:
        file_path: 文件路径（支持 PDF 和 Word）
        doc_id: 文档 ID
        kb_id: 知识库 ID（可选）

    Returns:
        处理结果字典
    """
    return process_document(file_path, doc_id, kb_id=kb_id, show_progress=True)
