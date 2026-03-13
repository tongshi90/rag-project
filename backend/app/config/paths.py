"""
路径配置模块

统一管理项目中所有数据文件的路径，确保跨平台兼容性。

支持：
- Windows 本地开发
- Linux Docker 部署

使用方式：
    from app.config.paths import DATA_DIR, DB_PATH, VECTOR_DB_PATH, UPLOAD_PATH

    # 获取路径
    db_path = DB_PATH  # Path 对象
    str_path = str(DB_PATH)  # 字符串路径
"""
import os
from pathlib import Path

# ============================================
# 项目根目录
# ============================================

# 获取项目根目录
# 当前文件位置：backend/app/config/paths.py
# 项目根目录：向上两级 -> backend -> rag_project
PROJECT_ROOT = Path(__file__).parent.parent.parent

# ============================================
# 数据目录
# ============================================

# 数据目录根路径
DATA_DIR = PROJECT_ROOT / 'data'

# 数据目录路径（字符串形式，用于环境变量默认值）
DATA_DIR_STR = str(DATA_DIR)

# ============================================
# 各数据文件路径
# ============================================

# 数据库文件路径
DB_PATH = DATA_DIR / 'rag.db'

# 向量数据库路径
VECTOR_DB_PATH = DATA_DIR / 'vector_db'

# 上传文件目录路径
UPLOAD_PATH = DATA_DIR / 'upload'

# 知识图谱目录路径
GRAPH_DB_PATH = DATA_DIR / 'graph'

# 关键字索引目录路径
KEYWORD_INDEX_PATH = DATA_DIR / 'keyword_index'

# Skills 目录路径（与 app 同级）
SKILLS_PATH = PROJECT_ROOT / 'skills'

# ============================================
# 路径字符串（用于环境变量）
# ============================================

DB_PATH_STR = str(DB_PATH)
VECTOR_DB_PATH_STR = str(VECTOR_DB_PATH)
UPLOAD_PATH_STR = str(UPLOAD_PATH)
GRAPH_DB_PATH_STR = str(GRAPH_DB_PATH)
KEYWORD_INDEX_PATH_STR = str(KEYWORD_INDEX_PATH)

# ============================================
# 便捷函数
# ============================================

def get_db_path(env_path: str = None) -> str:
    """
    获取数据库路径

    Args:
        env_path: 环境变量覆盖路径（Docker 部署时使用）

    Returns:
        数据库路径字符串
    """
    if env_path:
        return env_path
    return str(DB_PATH)


def get_vector_db_path(env_path: str = None) -> str:
    """
    获取向量数据库路径

    Args:
        env_path: 环境变量覆盖路径（Docker 部署时使用）

    Returns:
        向量数据库路径字符串
    """
    if env_path:
        return env_path
    return str(VECTOR_DB_PATH)


def get_upload_path(env_path: str = None) -> str:
    """
    获取上传文件目录路径

    Args:
        env_path: 环境变量覆盖路径（Docker 部署时使用）

    Returns:
        上传目录路径字符串
    """
    if env_path:
        return env_path
    return str(UPLOAD_PATH)


def ensure_data_dirs():
    """
    确保数据目录存在

    创建以下目录（如果不存在）：
    - data/
    - data/vector_db/
    - data/upload/
    - data/graph/
    - data/keyword_index/
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)
    UPLOAD_PATH.mkdir(parents=True, exist_ok=True)
    GRAPH_DB_PATH.mkdir(parents=True, exist_ok=True)
    KEYWORD_INDEX_PATH.mkdir(parents=True, exist_ok=True)


# 模块加载时自动创建数据目录
ensure_data_dirs()
