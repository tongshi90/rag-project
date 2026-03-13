"""
关键字索引模块 (Keyword Index)

使用 BM25 算法构建关键字检索索引
"""

from .keyword_indexer import KeywordIndexer, get_keyword_indexer

__all__ = [
    'KeywordIndexer',
    'get_keyword_indexer',
]
