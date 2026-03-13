"""
业务逻辑服务模块

本模块包含 RAG 系统的所有业务逻辑，按两个阶段组织：
1. Document Processing（文档处理）：离线预处理阶段
2. User Interaction（用户交互）：在线查询阶段
"""

# ============================================
# 完整文档处理流程（推荐使用）
# ============================================
from .document_processing.document_processor import (
    process_document,
    delete_document_vectors,
    get_document_stats,
    # 向后兼容
    parse_pdf,
)

# ============================================
# 文档拆分（第一步）
# ============================================
from .document_processing.splitter.text_splitter import split_pdf_to_chunks
from .document_processing.splitter.img_splitter import (
    split_images,
    split_images_from_pdf,
)
from .document_processing.splitter.form_splitter import (
    split_tables,
    split_tables_from_pdf,
)

# ============================================
# 导出接口
# ============================================
__all__ = [
    # ========== 完整流程 ==========
    'process_document',          # 完整文档处理流程（主入口）
    'delete_document_vectors',   # 删除文档向量数据
    'get_document_stats',        # 获取文档统计信息
    'parse_pdf',                 # 向后兼容：完整处理流程

    # ========== 第一步：文档拆分 ==========
    'split_pdf_to_chunks',       # 文本分片
    'split_images',              # 图片分片
    'split_images_from_pdf',     # 从 PDF 提取图片
    'split_tables',              # 表格分片
    'split_tables_from_pdf',     # 从 PDF 提取表格
]
