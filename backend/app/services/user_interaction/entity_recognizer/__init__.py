"""
问题实体识别模块 (Query Entity Recognizer)

从用户问题中识别实体，用于增强检索
"""

from .entity_recognizer import QueryEntityRecognizer, recognize_query_entities

__all__ = [
    'QueryEntityRecognizer',
    'recognize_query_entities',
]
