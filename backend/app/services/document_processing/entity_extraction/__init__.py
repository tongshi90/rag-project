"""
实体抽取模块 (Entity Extraction)

从文档 chunks 中抽取实体（人物、地点、组织机构、时间、数量、产品、技术概念、事件）

使用示例：
---------
from app.services.document_processing.entity_extraction import EntityExtractor

extractor = EntityExtractor()
entities = extractor.extract_from_document(chunks, doc_id)
"""

from .entity_extractor import EntityExtractor, extract_entities_from_document

__all__ = [
    'EntityExtractor',
    'extract_entities_from_document',
]
