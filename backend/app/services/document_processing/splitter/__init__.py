"""
文档拆分模块

负责将 PDF 文档解析并拆分为文本、表格、图片等多种类型的 chunk。

TODO: 当前 split_pdf_to_chunks() 只处理文本内容
TODO: 表格处理函数 split_tables_from_pdf() 和图片处理函数 split_images_from_pdf() 已实现但未集成
TODO: 需要修改 split_pdf_to_chunks() 以返回包含文本、表格、图片的完整分片列表
"""

from .text_splitter import split_pdf_to_chunks, extract_keywords
from .form_splitter import split_tables, split_tables_from_pdf
from .img_splitter import split_images, split_images_from_pdf

__all__ = [
    'split_pdf_to_chunks',
    'extract_keywords',
    'split_tables',
    'split_tables_from_pdf',
    'split_images',
    'split_images_from_pdf',
]
