"""
Knowledge Base Management API Routes
"""
import os
import shutil
from datetime import datetime
from pathlib import Path

from flask import request, jsonify

from app.api import api_bp
from app.config.paths import UPLOAD_PATH, VECTOR_DB_PATH
from app.models import knowledge_base_db, db
from app.models import retrieval_test_history_db

# Note: delete_document_vectors depends on chromadb which requires sqlite3 >= 3.35.0
# We import it lazily in the functions that use it to avoid import errors


def get_upload_dir():
    """获取上传目录"""
    env_upload_path = os.getenv('UPLOAD_FOLDER')
    if env_upload_path:
        return Path(env_upload_path)
    else:
        return UPLOAD_PATH


def get_absolute_file_path(relative_path):
    """将相对路径转换为绝对路径"""
    from app.config.paths import PROJECT_ROOT
    return str(PROJECT_ROOT / relative_path)


def get_relative_file_path(absolute_path):
    """将绝对路径转换为相对路径"""
    from app.config.paths import PROJECT_ROOT
    try:
        return str(Path(absolute_path).relative_to(PROJECT_ROOT))
    except ValueError:
        return str(Path(absolute_path))


@api_bp.route('/knowledge-bases', methods=['GET'])
def get_knowledge_bases():
    """
    获取所有知识库列表
    """
    kbs = knowledge_base_db.get_all_knowledge_bases()

    # 为每个知识库添加文件数量
    for kb in kbs:
        kb['fileCount'] = knowledge_base_db.get_knowledge_base_file_count(kb['id'])

    return jsonify({
        'success': True,
        'data': {
            'knowledgeBases': kbs,
            'total': len(kbs)
        }
    })


@api_bp.route('/knowledge-bases/<kb_id>', methods=['GET'])
def get_knowledge_base(kb_id):
    """
    获取单个知识库信息
    """
    kb = knowledge_base_db.get_knowledge_base_by_id(kb_id)
    if not kb:
        return jsonify({'success': False, 'error': '知识库不存在'}), 404

    kb_data = kb.to_dict()
    kb_data['fileCount'] = knowledge_base_db.get_knowledge_base_file_count(kb_id)

    return jsonify({
        'success': True,
        'data': kb_data
    })


@api_bp.route('/knowledge-bases', methods=['POST'])
def create_knowledge_base():
    """
    创建新知识库

    Request body:
        {
            "name": "知识库名称",
            "description": "描述"
        }
    """
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'success': False, 'error': '知识库名称不能为空'}), 400

    name = data['name']
    description = data.get('description', '')

    # 生成知识库ID
    kb_id = str(int(datetime.now().timestamp() * 1000))
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    from app.models.knowledge_base import KnowledgeBase
    new_kb = KnowledgeBase(
        id=kb_id,
        name=name,
        description=description,
        created_at=created_at,
        updated_at=created_at
    )

    knowledge_base_db.insert_knowledge_base(new_kb)

    return jsonify({
        'success': True,
        'data': new_kb.to_dict()
    })


@api_bp.route('/knowledge-bases/<kb_id>', methods=['PUT'])
def update_knowledge_base(kb_id):
    """
    更新知识库信息

    Request body:
        {
            "name": "新名称",
            "description": "新描述"
        }
    """
    kb = knowledge_base_db.get_knowledge_base_by_id(kb_id)
    if not kb:
        return jsonify({'success': False, 'error': '知识库不存在'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '无效的请求数据'}), 400

    name = data.get('name')
    description = data.get('description')

    knowledge_base_db.update_knowledge_base(kb_id, name=name, description=description)

    updated_kb = knowledge_base_db.get_knowledge_base_by_id(kb_id)
    updated_data = updated_kb.to_dict()
    updated_data['fileCount'] = knowledge_base_db.get_knowledge_base_file_count(kb_id)

    return jsonify({
        'success': True,
        'data': updated_data
    })


@api_bp.route('/knowledge-bases/<kb_id>', methods=['DELETE'])
def delete_knowledge_base(kb_id):
    """
    删除知识库及其所有文件

    同时删除：
    1. 知识库记录
    2. 知识库下的所有文件（物理文件）
    3. 文件在向量数据库中的数据
    4. 知识图谱
    5. 关键字索引
    6. 召回测试历史记录
    """
    kb = knowledge_base_db.get_knowledge_base_by_id(kb_id)
    if not kb:
        return jsonify({'success': False, 'error': '知识库不存在'}), 404

    # 获取知识库下的所有文件ID
    file_ids = db.delete_files_by_kb_id(kb_id)

    # 删除物理文件和向量数据
    from app.services import delete_document_vectors
    for file_id in file_ids:
        file = db.get_file_by_id(file_id)
        if file and file.file_path:
            absolute_path = get_absolute_file_path(file.file_path)
            if os.path.exists(absolute_path):
                os.remove(absolute_path)
        # 删除向量数据（包括向量、知识图谱、关键字索引）
        delete_document_vectors(file_id, show_progress=False)

    # 删除召回测试历史记录
    history_count = retrieval_test_history_db.clear_history_by_kb_id(kb_id)

    # 删除知识库记录
    knowledge_base_db.delete_knowledge_base(kb_id)

    return jsonify({
        'success': True,
        'data': {
            'deletedFiles': len(file_ids),
            'deletedHistory': history_count
        }
    })


@api_bp.route('/knowledge-bases/<kb_id>/files', methods=['GET'])
def get_knowledge_base_files(kb_id):
    """
    获取知识库下的文件列表
    """
    # 验证知识库存在
    kb = knowledge_base_db.get_knowledge_base_by_id(kb_id)
    if not kb:
        return jsonify({'success': False, 'error': '知识库不存在'}), 404

    files = db.get_files_by_kb_id(kb_id)

    return jsonify({
        'success': True,
        'data': {
            'files': files,
            'total': len(files)
        }
    })


@api_bp.route('/knowledge-bases/<kb_id>/files/upload', methods=['POST'])
def upload_to_knowledge_base(kb_id):
    """
    上传文件到知识库

    Request body:
        - file: 文件对象（form data）

    文件会关联到指定知识库，不再关联到folder
    """
    # 验证知识库存在
    kb = knowledge_base_db.get_knowledge_base_by_id(kb_id)
    if not kb:
        return jsonify({'success': False, 'error': '知识库不存在'}), 404

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未上传文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '未选择文件'}), 400

    # 检查文件格式
    file_ext = os.path.splitext(file.filename)[1].lower()
    supported_formats = ['.pdf', '.docx', '.doc']
    if file_ext not in supported_formats:
        return jsonify({'success': False, 'error': f'暂不支持此格式，支持的格式: {", ".join(supported_formats)}'}), 400

    # 生成文件ID
    file_id = str(int(datetime.now().timestamp() * 1000))

    # 保存文件（使用原始扩展名）
    upload_dir = get_upload_dir()
    file_path = upload_dir / f"{file_id}{file_ext}"
    file.save(str(file_path))

    # 获取文件大小
    file_size = os.path.getsize(str(file_path))

    # 存储相对路径
    relative_path = get_relative_file_path(str(file_path))

    # 根据文件扩展名确定 MIME 类型
    mime_types = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword'
    }

    from app.models.file import File
    new_file = File(
        id=file_id,
        name=file.filename,
        size=file_size,
        file_type=file.content_type or mime_types.get(file_ext, 'application/octet-stream'),
        upload_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        status='parsing',
        file_path=relative_path,
        kb_id=kb_id  # 关联知识库
    )

    # 保存到数据库
    db.insert_file(new_file)

    # 异步处理文档
    from app.api.files import process_document_async
    process_document_async(str(file_path), file.filename, file_id, kb_id)

    return jsonify({
        'success': True,
        'data': new_file.to_dict()
    })


@api_bp.route('/knowledge-bases/<kb_id>/files/<file_id>', methods=['DELETE'])
def delete_knowledge_base_file(kb_id, file_id):
    """
    删除知识库中的文件

    删除：
    1. 物理文件
    2. 数据库记录
    3. 向量数据库数据
    """
    # 验证知识库存在
    kb = knowledge_base_db.get_knowledge_base_by_id(kb_id)
    if not kb:
        return jsonify({'success': False, 'error': '知识库不存在'}), 404

    # 获取文件信息
    file = db.get_file_by_id(file_id)
    if not file:
        return jsonify({'success': False, 'error': '文件不存在'}), 404

    # 验证文件属于该知识库
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('PRAGMA table_info(files)')
    columns = [column['name'] for column in cursor.fetchall()]
    has_kb_id = 'kb_id' in columns

    if has_kb_id:
        cursor.execute('SELECT kb_id FROM files WHERE id = ?', (file_id,))
        row = cursor.fetchone()
        if not row or row['kb_id'] != kb_id:
            conn.close()
            return jsonify({'success': False, 'error': '文件不属于该知识库'}), 403
    conn.close()

    # 删除物理文件
    if file.file_path:
        absolute_path = get_absolute_file_path(file.file_path)
        if os.path.exists(absolute_path):
            os.remove(absolute_path)

    # 删除数据库记录
    db.delete_file(file_id)

    # 删除向量数据
    from app.services import delete_document_vectors
    delete_document_vectors(file_id, show_progress=False)

    return jsonify({'success': True})


@api_bp.route('/knowledge-bases/<kb_id>/files/<file_id>/chunks', methods=['GET'])
def get_file_chunks(kb_id, file_id):
    """
    获取文件的 chunk 列表

    返回该文件被拆分的所有 chunk 信息
    """
    # 验证知识库存在
    kb = knowledge_base_db.get_knowledge_base_by_id(kb_id)
    if not kb:
        return jsonify({'success': False, 'error': '知识库不存在'}), 404

    # 获取文件信息
    file = db.get_file_by_id(file_id)
    if not file:
        return jsonify({'success': False, 'error': '文件不存在'}), 404

    # 从向量数据库获取 chunks
    from app.services.document_processing.embedding.vector_store import get_vector_store
    vector_store = get_vector_store()

    try:
        chunks = vector_store.get_chunks_by_doc_id(file_id)

        # 格式化返回数据
        formatted_chunks = []
        for chunk in chunks:
            metadata = chunk.get('metadata', {})
            formatted_chunks.append({
                'chunkId': chunk.get('chunk_id'),
                'text': chunk.get('text', ''),
                'order': metadata.get('order', 0),
                'page': metadata.get('page', 0),
                'type': metadata.get('type', 'text'),
                'length': metadata.get('length', 0)
            })

        return jsonify({
            'success': True,
            'data': {
                'fileId': file_id,
                'fileName': file.name,
                'chunks': formatted_chunks,
                'total': len(formatted_chunks)
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取 chunk 列表失败: {str(e)}'
        }), 500


@api_bp.route('/knowledge-bases/<kb_id>/files/all', methods=['DELETE'])
def delete_all_knowledge_base_files(kb_id):
    """
    删除知识库中的所有文件
    """
    # 验证知识库存在
    kb = knowledge_base_db.get_knowledge_base_by_id(kb_id)
    if not kb:
        return jsonify({'success': False, 'error': '知识库不存在'}), 404

    # 获取知识库下的所有文件ID
    file_ids = db.delete_files_by_kb_id(kb_id)

    # 删除物理文件和向量数据
    from app.services import delete_document_vectors
    for file_id in file_ids:
        file = db.get_file_by_id(file_id)
        if file and file.file_path:
            absolute_path = get_absolute_file_path(file.file_path)
            if os.path.exists(absolute_path):
                os.remove(absolute_path)
        # 删除向量数据
        delete_document_vectors(file_id, show_progress=False)

    return jsonify({
        'success': True,
        'data': {
            'deletedCount': len(file_ids)
        }
    })
