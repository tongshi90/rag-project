"""
File Management API Routes
"""
import os
import shutil
import threading
import logging
from datetime import datetime
from pathlib import Path

from flask import request, jsonify

from app.api import api_bp
from app.config.paths import UPLOAD_PATH, VECTOR_DB_PATH
from app.models import db, File
from app.services import parse_pdf, delete_document_vectors

logger = logging.getLogger(__name__)


def get_upload_dir():
    """
    获取上传目录

    使用统一路径管理，支持环境变量覆盖（Docker 部署）
    """
    # 优先使用环境变量
    env_upload_path = os.getenv('UPLOAD_FOLDER')

    if env_upload_path:
        return Path(env_upload_path)
    else:
        return UPLOAD_PATH


def get_relative_file_path(absolute_path):
    """
    将绝对路径转换为相对于项目根目录的路径
    存储到数据库时使用相对路径，确保跨平台兼容
    """
    from app.config.paths import PROJECT_ROOT

    try:
        return str(Path(absolute_path).relative_to(PROJECT_ROOT))
    except ValueError:
        # 如果路径不在项目根目录下，返回绝对路径
        return str(Path(absolute_path))


def get_absolute_file_path(relative_path):
    """
    将相对路径转换为绝对路径
    """
    from app.config.paths import PROJECT_ROOT
    return str(PROJECT_ROOT / relative_path)


def process_document_async(file_path, file_name, file_id, kb_id: str = None):
    """
    异步处理文档（完整流程）

    处理流程：
    1. 文档拆分 → 2. 异常检测 → 3. LLM 优化 → 4. 向量化存储

    Args:
        file_path: 文件绝对路径
        file_name: 文件名
        file_id: 文档 ID
        kb_id: 知识库 ID（可选）
    """
    def _process():
        try:
            # 调用完整的文档处理流程
            result = parse_pdf(file_path, file_id, kb_id)

            # 根据处理结果更新文件状态
            if result.get('success'):
                db.update_file_status(file_id, 'completed')
            else:
                db.update_file_status(file_id, 'failed')
                logger.error(f"[异步处理] 文档 {file_id} 处理失败: {result.get('error', 'Unknown error')}")

        except Exception as e:
            logger.error(f"[异步处理] 文档 {file_id} 处理异常: {e}", exc_info=True)
            db.update_file_status(file_id, 'failed')

    # 在后台线程中处理
    thread = threading.Thread(target=_process, daemon=True)
    thread.start()


@api_bp.route('/files', methods=['GET'])
def get_files():
    """
    Get list of uploaded files
    """
    files = db.get_all_files()
    return jsonify({
        'success': True,
        'data': {
            'files': files,
            'total': len(files)
        }
    })


@api_bp.route('/files/upload', methods=['POST'])
def upload_file():
    """
    Upload a new file (PDF and Word supported)

    处理流程：
    1. 生成文件 ID
    2. 以 {file_id}.{ext} 格式保存文件（避免同名文件冲突）
    3. 创建数据库记录
    4. 异步执行完整文档处理流程（拆分 → 验证 → 优化 → 向量化）
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未上传文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '未选择文件'}), 400

    # Check file format - support PDF and Word
    file_ext = os.path.splitext(file.filename)[1].lower()
    supported_formats = ['.pdf', '.docx', '.doc']
    if file_ext not in supported_formats:
        return jsonify({'success': False, 'error': f'暂不支持此格式，支持的格式: {", ".join(supported_formats)}'}), 400

    # 先生成文件 ID（用于文件名，使用毫秒级时间戳）
    file_id = str(int(datetime.now().timestamp() * 1000))

    # 获取上传目录
    upload_dir = get_upload_dir()

    # 保存文件（使用 file_id.{ext} 作为文件名，避免同名冲突）
    file_path = upload_dir / f"{file_id}{file_ext}"
    file.save(str(file_path))

    # Get file size
    file_size = os.path.getsize(str(file_path))

    # 存储相对路径到数据库（跨平台兼容）
    relative_path = get_relative_file_path(str(file_path))

    # 根据文件扩展名确定 MIME 类型
    mime_types = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword'
    }

    # Create file record
    new_file = File(
        id=file_id,
        name=file.filename,  # 保留原始文件名
        size=file_size,
        file_type=file.content_type or mime_types.get(file_ext, 'application/octet-stream'),
        upload_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        status='parsing',  # Initial status, will be updated after processing
        file_path=relative_path  # 存储相对路径
    )

    # Save to database
    db.insert_file(new_file)

    # 异步执行完整文档处理流程（传递绝对路径）
    process_document_async(str(file_path), file.filename, file_id)

    # Return immediately without waiting for processing
    return jsonify({
        'success': True,
        'data': new_file.to_dict()
    })


@api_bp.route('/files/<file_id>', methods=['GET'])
def get_file(file_id):
    """
    Get a single file by ID
    """
    file = db.get_file_by_id(file_id)
    if not file:
        return jsonify({'success': False, 'error': '文件不存在'}), 404

    return jsonify({
        'success': True,
        'data': file.to_dict()
    })


@api_bp.route('/files/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    """
    Delete a file by ID

    同时删除：
    1. 物理文件
    2. 数据库记录
    3. 向量数据库中的向量数据
    """
    # Get file info to delete physical file
    file = db.get_file_by_id(file_id)
    if file and file.file_path:
        # 将相对路径转换为绝对路径
        absolute_path = get_absolute_file_path(file.file_path)
        if os.path.exists(absolute_path):
            os.remove(absolute_path)

    # Delete from database
    db.delete_file(file_id)

    # Delete from vector store
    delete_document_vectors(file_id, show_progress=False)

    return jsonify({'success': True})


@api_bp.route('/files/all', methods=['DELETE'])
def delete_all_files():
    """
    Delete all files (both database records and physical files)

    同时删除：
    1. 所有物理文件
    2. 数据库记录
    3. 向量数据库（直接删除 vector_db 文件夹）
    """
    # 先获取所有 file_path 用于删除物理文件
    relative_paths = db.delete_all_files()

    # Delete physical files
    for relative_path in relative_paths:
        absolute_path = get_absolute_file_path(relative_path)
        if os.path.exists(absolute_path):
            try:
                os.remove(absolute_path)
            except Exception as e:
                logger.warning(f"Failed to delete file {absolute_path}: {e}")

    # 直接删除 vector_db 文件夹（更彻底）
    vector_db_to_delete = VECTOR_DB_PATH

    if vector_db_to_delete.exists():
        try:
            shutil.rmtree(vector_db_to_delete)
            logger.info(f"向量数据库已删除: {vector_db_to_delete}")
        except Exception as e:
            logger.error(f"删除向量数据库失败: {e}")

    # 重置向量存储实例（确保下次使用时重新初始化）
    from app.services.document_processing.embedding import reset_vector_store
    reset_vector_store()

    return jsonify({'success': True})


@api_bp.route('/files/clear-knowledge', methods=['POST'])
def clear_knowledge_data():
    """
    清空所有知识库相关数据

    保留：
    - 技能卡片数据库 (skill_cards)
    - skills 文件夹

    删除：
    - 向量数据库 (vector_db)
    - 知识图谱 (graph)
    - 关键字索引 (keyword_index)
    - 上传文件 (upload)
    - 文件数据库记录 (files)
    - 知识库分组 (knowledge_bases)
    - 检索测试历史 (retrieval_test_history)
    """
    from app.config.paths import VECTOR_DB_PATH, GRAPH_DB_PATH, KEYWORD_INDEX_PATH, DATA_DIR
    import time

    result = {
        'success': False,
        'cleared': [],
        'errors': []
    }

    # 1. 先清空向量数据库的集合内容（使用 ChromaDB API）
    try:
        from app.services.document_processing.embedding.vector_store import get_vector_store, reset_vector_store

        # 获取向量存储实例并清空集合
        vector_store = get_vector_store()
        cleared = vector_store.clear_collection()
        if cleared:
            result['cleared'].append('向量数据库集合')

        # 重置向量存储实例（清除全局单例引用）
        reset_vector_store()

    except Exception as e:
        result['errors'].append(f'向量数据库清理失败: {str(e)}')
        import traceback
        traceback.print_exc()

    # 2. 重置关键字索引器实例
    try:
        from app.services.document_processing.keyword_index.keyword_indexer import reset_keyword_indexer
        reset_keyword_indexer()
        result['cleared'].append('关键字索引器实例')
    except Exception as e:
        result['errors'].append(f'关键字索引器重置失败: {str(e)}')

    # 3. 重置图谱检索器实例
    try:
        from app.services.user_interaction.graph_retrieval.graph_retriever import reset_graph_retriever
        reset_graph_retriever()
        result['cleared'].append('图谱检索器实例')
    except Exception as e:
        result['errors'].append(f'图谱检索器重置失败: {str(e)}')

    # 4. 清空 embedding 缓存
    try:
        from app.services.document_processing.validator.validate import clear_embedding_cache
        clear_embedding_cache()
        result['cleared'].append('Embedding 缓存')
    except Exception as e:
        result['errors'].append(f'Embedding 缓存清理失败: {str(e)}')

    # 5. 重置查询编码器实例
    try:
        from app.services.user_interaction.query_encoder.query_encoder import reset_query_encoder
        reset_query_encoder()
        result['cleared'].append('查询编码器实例')
    except Exception as e:
        result['errors'].append(f'查询编码器重置失败: {str(e)}')

    # 5. 删除向量数据库目录
    try:
        if VECTOR_DB_PATH.exists():
            shutil.rmtree(VECTOR_DB_PATH)
            result['cleared'].append('向量数据库目录')
            # 等待文件系统同步
            time.sleep(0.3)
    except Exception as e:
        result['errors'].append(f'向量数据库目录删除失败: {str(e)}')

    # 6. 重新创建向量数据库目录（为后续使用做准备）
    try:
        VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        result['errors'].append(f'向量数据库目录创建失败: {str(e)}')

    # 7. 清空知识图谱
    try:
        if GRAPH_DB_PATH.exists():
            shutil.rmtree(GRAPH_DB_PATH)
            GRAPH_DB_PATH.mkdir(parents=True, exist_ok=True)
            result['cleared'].append('知识图谱')
    except Exception as e:
        result['errors'].append(f'知识图谱清理失败: {str(e)}')

    # 8. 清空关键字索引
    try:
        if KEYWORD_INDEX_PATH.exists():
            shutil.rmtree(KEYWORD_INDEX_PATH)
            KEYWORD_INDEX_PATH.mkdir(parents=True, exist_ok=True)
            result['cleared'].append('关键字索引')
    except Exception as e:
        result['errors'].append(f'关键字索引清理失败: {str(e)}')

    # 9. 清空上传文件
    try:
        upload_path = get_upload_dir()
        if upload_path.exists():
            for item in list(upload_path.iterdir()):
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            result['cleared'].append('上传文件')
    except Exception as e:
        result['errors'].append(f'上传文件清理失败: {str(e)}')

    # 10. 清空数据库记录（保留 skill_cards，删除 knowledge_bases 和 files）
    try:
        files_deleted = db.delete_all_files()
        result['cleared'].append(f'{files_deleted} 条文件记录')

        # 删除知识库分组
        from app.models.knowledge_base import knowledge_base_db
        kb_deleted = knowledge_base_db.delete_all()
        result['cleared'].append(f'{kb_deleted} 条知识库分组记录')

        # 删除检索测试历史
        import sqlite3
        db_path = DATA_DIR / 'rag.db'
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute('DELETE FROM retrieval_test_history')
            conn.commit()
            conn.close()
            result['cleared'].append('检索测试历史')
    except Exception as e:
        result['errors'].append(f'数据库清理失败: {str(e)}')

    result['success'] = len(result['cleared']) > 0

    return jsonify(result)


@api_bp.route('/files/<file_id>/stats', methods=['GET'])
def get_file_stats(file_id):
    """
    Get file processing statistics

    返回文档的处理统计信息，包括：
    - 基本信息（从数据库）
    - 向量存储统计（从向量数据库）
    """
    # Get file info
    file = db.get_file_by_id(file_id)
    if not file:
        return jsonify({'success': False, 'error': '文件不存在'}), 404

    # Get vector stats
    from app.services.document_processing.embedding import get_vector_store
    try:
        vector_store = get_vector_store()
        chunks = vector_store.get_chunks_by_doc_id(file_id)

        stats = {
            'success': True,
            'data': {
                'file': file.to_dict(),
                'vector_stats': {
                    'doc_id': file_id,
                    'chunk_count': len(chunks),
                    'chunks': chunks
                }
            }
        }

        return jsonify(stats)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取统计信息失败: {str(e)}'
        }), 500
