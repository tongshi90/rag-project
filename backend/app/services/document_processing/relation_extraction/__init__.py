"""
关系抽取模块 (Relation Extraction)

从实体中抽取关系，构建实体之间的连接
"""

from .relation_extractor import RelationExtractor, extract_relations

__all__ = [
    'RelationExtractor',
    'extract_relations',
]
