"""
完整文档处理流程模块

整合文档处理的步骤：
1. 文档拆分 (Splitter) - PDF → Chunks
2. 异常检测 (Validator) - Chunk 质量检测
3. Chunk 优化 (Optimizer) - LLM 辅助合并/拆分
4. 实体抽取 (Entity Extraction) - 抽取文档实体
5. 关系抽取 (Relation Extraction) - 抽取实体关系
6. 知识图谱构建 (Graph Builder) - 构建知识图谱
7. 关键字索引 (Keyword Index) - 构建 BM25 索引
8. 向量化存储 (Embedding) - 向量数据库存储

使用方式：
    from app.services.document_processing import process_document

    result = process_document(pdf_path, file_id)
"""

import time
from pathlib import Path
from typing import Dict, Any

from .embedding import embed_and_store_chunks, get_vector_store
from .optimizer.chunk_optimizer import optimize_chunks
# 导入各个步骤的模块
from .splitter.text_splitter import split_pdf_to_chunks
from .validator.validate import validate_chunks, get_validation_summary
# 新增模块
from .entity_extraction import EntityExtractor
from .relation_extraction import RelationExtractor
from .graph_builder import KnowledgeGraphBuilder
from .keyword_index import KeywordIndexer


def process_document(
    pdf_path: str,
    doc_id: str,
    show_progress: bool = True,
    embedding_batch_size: int = 10
) -> Dict[str, Any]:
    """
    完整的文档处理流程（主入口函数）

    处理流程：
        1. 文档拆分 → 2. 异常检测 → 3. Chunk 优化
        4. 实体抽取 → 5. 关系抽取 → 6. 知识图谱构建
        7. 关键字索引 → 8. 向量化存储

    Args:
        pdf_path: PDF 文件路径
        doc_id: 文档 ID
        show_progress: 是否显示处理进度
        embedding_batch_size: 向量化批处理大小

    Returns:
        处理结果，包含：
            - success: 是否成功
            - doc_id: 文档 ID
            - steps: 各步骤的执行结果
                - split: 拆分结果
                - validate: 验证结果
                - optimize: 优化结果
                - entity_extract: 实体抽取结果
                - relation_extract: 关系抽取结果
                - graph_build: 知识图谱构建结果
                - keyword_index: 关键字索引结果
                - embed: 向量化结果
            - total_elapsed: 总耗时
            - error: 错误信息（如果失败）

    Raises:
        Exception: 当处理失败时抛出异常
    """
    start_time = time.time()

    if show_progress:
        print(f"\n{'#'*60}")
        print(f"# 开始处理文档: {Path(pdf_path).name}")
        print(f"# 文档 ID: {doc_id}")
        print(f"{'#'*60}\n")

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
        # TODO: 当前只处理文本内容，表格和图片数据未包含在内
        # TODO: 需要集成 form_splitter.py 和 img_splitter.py 的处理结果
        if show_progress:
            print(f"\n{'='*60}")
            print(f"第一步: 文档拆分")
            print(f"{'='*60}")

        step_start = time.time()
        chunks, title_patterns = split_pdf_to_chunks(pdf_path, doc_id)
        step_elapsed = time.time() - step_start

        result['steps']['split'] = {
            "success": True,
            "chunk_count": len(chunks),
            "title_pattern_count": len(title_patterns) if title_patterns else 0,
            "elapsed": step_elapsed
        }

        if show_progress:
            print(f"拆分完成: {len(chunks)} 个 chunks")
            print(f"标题规则数: {len(title_patterns) if title_patterns else 0}")
            print(f"耗时: {step_elapsed:.2f} 秒")

        # ============================================
        # 第二步：异常检测
        # ============================================
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

        if show_progress:
            print(f"检测完成: {validation_summary.get('chunks_with_errors', 0)} 个异常 chunks")
            print(f"高风险 chunks: {len(validation_summary.get('high_risk_chunks', []))}")
            print(f"总风险分数: {validation_summary.get('total_risk_score', 0)}")
            print(f"耗时: {step_elapsed:.2f} 秒")

        # ============================================
        # 第三步：Chunk 优化
        # ============================================
        if show_progress:
            print(f"\n{'='*60}")
            print(f"第三步: Chunk 优化 (LLM)")
            print(f"{'='*60}")

        step_start = time.time()
        optimized_chunks = optimize_chunks(
            validated_chunks,
            min_risk_score=60,
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

        if show_progress:
            print(f"优化完成: {len(validated_chunks)} → {len(optimized_chunks)} chunks")
            print(f"变化: {len(optimized_chunks) - len(validated_chunks):+d}")
            print(f"耗时: {step_elapsed:.2f} 秒")

        print("\n切分效果:")
        print(f"分片数量: {len(optimized_chunks)}")
        print(f"{'='*60}")
        for i, chunk in enumerate(optimized_chunks, 1):
            title = chunk.get('metadata', {}).get('title', '')
            title_path = chunk.get('metadata', {}).get('title_path', [])
            text = chunk.get('text', '')

            # 构建标题信息
            if title_path:
                title_info = ' > '.join(title_path)
            elif title:
                title_info = title
            else:
                title_info = '(无标题)'

            print(f"\n[Chunk {i}]")
            print(f"  标题: {title_info}")
            print(f"  text: {text}")
        print(f"{'='*60}\n")

        # ============================================
        # 第四步：实体抽取
        # ============================================
        if show_progress:
            print(f"\n{'='*60}")
            print(f"第四步: 实体抽取 (LLM)")
            print(f"{'='*60}")

        step_start = time.time()
        entity_extractor = EntityExtractor()
        entity_result = entity_extractor.extract_from_document(
            optimized_chunks, doc_id, show_progress=False
        )
        entities = entity_result.get("entities", [])
        entity_stats = entity_result.get("statistics", {})
        step_elapsed = time.time() - step_start

        result['steps']['entity_extract'] = {
            "success": entity_result.get("success", False),
            "total_entities": entity_stats.get("total_count", 0),
            "type_counts": entity_stats.get("type_counts", {}),
            "elapsed": step_elapsed
        }

        if show_progress:
            print(f"实体抽取完成: {entity_stats.get('total_count', 0)} 个实体")
            for etype, count in entity_stats.get("type_counts", {}).items():
                print(f"  - {etype}: {count}")
            print(f"耗时: {step_elapsed:.2f} 秒")

        # ============================================
        # 第五步：关系抽取
        # ============================================
        if show_progress:
            print(f"\n{'='*60}")
            print(f"第五步: 关系抽取 (LLM)")
            print(f"{'='*60}")

        step_start = time.time()
        relation_extractor = RelationExtractor()
        relation_result = relation_extractor.extract_relations(
            entities, optimized_chunks, show_progress=False
        )
        relations = relation_result.get("relations", [])
        relation_stats = relation_result.get("statistics", {})
        step_elapsed = time.time() - step_start

        result['steps']['relation_extract'] = {
            "success": relation_result.get("success", False),
            "total_relations": relation_stats.get("total_count", 0),
            "type_counts": relation_stats.get("type_counts", {}),
            "elapsed": step_elapsed
        }

        if show_progress:
            print(f"关系抽取完成: {relation_stats.get('total_count', 0)} 个关系")
            for rtype, count in relation_stats.get("type_counts", {}).items():
                print(f"  - {rtype}: {count}")
            print(f"耗时: {step_elapsed:.2f} 秒")

        # ============================================
        # 第六步：知识图谱构建
        # ============================================
        if show_progress:
            print(f"\n{'='*60}")
            print(f"第六步: 知识图谱构建")
            print(f"{'='*60}")

        step_start = time.time()
        graph_builder = KnowledgeGraphBuilder()
        graph_result = graph_builder.build_graph(entities, relations, doc_id)
        graph_builder.save_graph(doc_id)
        graph_stats = graph_builder.get_graph_stats()
        step_elapsed = time.time() - step_start

        result['steps']['graph_build'] = {
            "success": graph_result.get("success", False),
            "total_nodes": graph_result.get("total_nodes", 0),
            "total_edges": graph_result.get("total_edges", 0),
            "entity_types": graph_stats.get("entity_types", {}),
            "relation_types": graph_stats.get("relation_types", {}),
            "elapsed": step_elapsed
        }

        if show_progress:
            print(f"图谱构建完成: {graph_result.get('total_nodes', 0)} 节点, {graph_result.get('total_edges', 0)} 边")
            print(f"耗时: {step_elapsed:.2f} 秒")

        # ============================================
        # 第七步：关键字索引
        # ============================================
        if show_progress:
            print(f"\n{'='*60}")
            print(f"第七步: 关键字索引 (BM25)")
            print(f"{'='*60}")

        step_start = time.time()
        keyword_indexer = KeywordIndexer()
        keyword_result = keyword_indexer.build_index(optimized_chunks, doc_id)
        keyword_indexer.save_index(doc_id)
        step_elapsed = time.time() - step_start

        result['steps']['keyword_index'] = {
            "success": keyword_result.get("success", False),
            "total_chunks": keyword_result.get("total_chunks", 0),
            "elapsed": step_elapsed
        }

        if show_progress:
            print(f"关键字索引完成: {keyword_result.get('total_chunks', 0)} chunks")
            print(f"耗时: {step_elapsed:.2f} 秒")

        # ============================================
        # 第八步：向量化存储
        # ============================================
        if show_progress:
            print(f"\n{'='*60}")
            print(f"第四步: 向量化存储")
            print(f"{'='*60}")

        step_start = time.time()
        embed_result = embed_and_store_chunks(
            chunks=optimized_chunks,
            doc_id=doc_id,
            batch_size=embedding_batch_size,
            show_progress=show_progress
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

        if show_progress:
            print(f"向量化完成: {embed_result.get('success_count', 0)}/{embed_result.get('total_chunks', 0)}")
            print(f"向量库总量: {embed_result.get('vector_store_stats', {}).get('total_count', 0)}")
            print(f"耗时: {step_elapsed:.2f} 秒")

        # ============================================
        # 完成
        # ============================================
        result['success'] = True
        result['total_elapsed'] = time.time() - start_time

        if show_progress:
            print(f"\n{'#'*60}")
            print(f"# 文档处理完成！")
            print(f"# 总耗时: {result['total_elapsed']:.2f} 秒")
            print(f"# 最终 chunks: {len(optimized_chunks)}")
            print(f"{'#'*60}\n")

        return result

    except Exception as e:
        result['error'] = str(e)
        result['total_elapsed'] = time.time() - start_time

        if show_progress:
            print(f"\n{'!'*60}")
            print(f"! 文档处理失败: {str(e)}")
            print(f"{'!'*60}\n")

        raise


def delete_document_vectors(doc_id: str, show_progress: bool = True) -> Dict[str, Any]:
    """
    删除文档的所有数据（向量、图谱、关键字索引）

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
            "vectors": 0,
            "graph": False,
            "keyword_index": False
        },
        "error": None
    }

    try:
        # 删除向量数据
        vector_store = get_vector_store()
        count = vector_store.delete_by_doc_id(doc_id)
        result["deleted"]["vectors"] = count

        if show_progress:
            print(f"已删除文档 {doc_id} 的 {count} 个向量数据")

    except Exception as e:
        result["success"] = False
        result["error"] = f"删除向量数据失败: {str(e)}"

    try:
        # 删除知识图谱
        graph_builder = KnowledgeGraphBuilder()
        graph_deleted = graph_builder.delete_graph(doc_id)
        result["deleted"]["graph"] = graph_deleted

        if show_progress and graph_deleted:
            print(f"已删除文档 {doc_id} 的知识图谱")

    except Exception as e:
        if show_progress:
            print(f"删除知识图谱失败: {str(e)}")

    try:
        # 删除关键字索引
        keyword_indexer = KeywordIndexer()
        index_deleted = keyword_indexer.delete_index(doc_id)
        result["deleted"]["keyword_index"] = index_deleted

        if show_progress and index_deleted:
            print(f"已删除文档 {doc_id} 的关键字索引")

    except Exception as e:
        if show_progress:
            print(f"删除关键字索引失败: {str(e)}")

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
def parse_pdf(pdf_path: str, doc_id: str) -> Dict[str, Any]:
    """
    向后兼容的 parse_pdf 函数

    内部调用完整的 process_document 流程

    Args:
        pdf_path: PDF 文件路径
        doc_id: 文档 ID

    Returns:
        处理结果字典
    """
    return process_document(pdf_path, doc_id, show_progress=True)
