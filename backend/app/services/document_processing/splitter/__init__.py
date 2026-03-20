"""
文档拆分模块

负责将 PDF/Word 文档解析并拆分为文本、表格、图片等多种类型的 chunk。

支持格式：
- PDF: split_pdf_to_chunks()
- Word (.docx): split_word_to_chunks()

TODO: 当前只处理文本内容
TODO: 表格处理函数 split_tables_from_pdf() 和图片处理函数 split_images_from_pdf() 已实现但未集成
"""

from .text_splitter import split_pdf_to_chunks, extract_keywords
from .word_splitter import split_word_to_chunks, is_word_file
from .form_splitter import split_tables, split_tables_from_pdf
from .img_splitter import split_images, split_images_from_pdf

__all__ = [
    'split_pdf_to_chunks',
    'split_word_to_chunks',
    'is_word_file',
    'extract_keywords',
    'split_tables',
    'split_tables_from_pdf',
    'split_images',
    'split_images_from_pdf',
]
