"""
文档处理阶段 (Document Processing)

本阶段是 RAG 系统的离线预处理阶段，负责将上传的 PDF 文档转换为可检索的向量数据。

包含的子模块：
-------------
- splitter: 文档拆分（PDF → Chunks）
- validator: Chunk 质量检测
- optimizer: Chunk 优化（LLM 确认 + 调整）
- entity_extraction: 实体抽取
- relation_extraction: 关系抽取
- graph_builder: 知识图谱构建
- keyword_index: 关键字索引（BM25）
- embedding: 向量化 + 存储

使用示例：
---------
```python
from app.services.document_processing import process_document

# 处理上传的 PDF 文件（完整流程）
result = process_document(pdf_path, doc_id)
# 包含：拆分 → 验证 → 优化 → 实体抽取 → 关系抽取 → 图谱构建 → 关键字索引 → 向量化
```
"""

# 完整文档处理流程
from .document_processor import (
    process_document,
    delete_document_vectors,
    get_document_stats,
    # 向后兼容
    parse_pdf,
)

# 单独使用各个步骤
from .splitter import split_pdf_to_chunks, extract_keywords
from .validator.validate import validate_chunks, get_validation_summary
from .optimizer.chunk_optimizer import optimize_chunks
from .entity_extraction import EntityExtractor, extract_entities_from_document
from .relation_extraction import RelationExtractor, extract_relations
from .graph_builder import KnowledgeGraphBuilder, get_graph_builder
from .keyword_index import KeywordIndexer, get_keyword_indexer
from .embedding import embed_and_store_chunks

__all__ = [
    # 完整流程
    'process_document',
    'delete_document_vectors',
    'get_document_stats',
    'parse_pdf',  # 向后兼容

    # 单独步骤
    'split_pdf_to_chunks',
    'extract_keywords',
    'validate_chunks',
    'get_validation_summary',
    'optimize_chunks',
    'embed_and_store_chunks',

    # 新增模块
    'EntityExtractor',
    'extract_entities_from_document',
    'RelationExtractor',
    'extract_relations',
    'KnowledgeGraphBuilder',
    'get_graph_builder',
    'KeywordIndexer',
    'get_keyword_indexer',
]
