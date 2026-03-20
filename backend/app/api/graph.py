"""
Graph API Routes

知识图谱相关 API 接口
"""
from flask import request, jsonify
from app.api import api_bp
from app.services.document_processing.graph_builder import get_graph_builder
from app.services.user_interaction.graph_retrieval import get_graph_retriever
from app.services.user_interaction.entity_recognizer import QueryEntityRecognizer


@api_bp.route('/graph/stats/<doc_id>', methods=['GET'])
def get_graph_stats(doc_id: str):
    """
    获取文档的知识图谱统计信息

    Args:
        doc_id: 文档 ID

    Request:
        GET /api/graph/stats/{doc_id}

    Response:
        {
            "success": true,
            "data": {
                "total_nodes": 10,
                "total_edges": 15,
                "entity_types": {"人物": 3, "地点": 2, ...},
                "relation_types": {"包含关系": 5, ...}
            }
        }
    """
    try:
        graph_builder = get_graph_builder()

        # 加载图谱
        if not graph_builder.load_graph(doc_id):
            return jsonify({
                'success': False,
                'error': f'未找到文档的知识图谱: {doc_id}'
            }), 404

        # 获取统计信息
        stats = graph_builder.get_graph_stats()

        return jsonify({
            'success': True,
            'data': stats
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/graph/entities/<doc_id>', methods=['GET'])
def get_document_entities(doc_id: str):
    """
    获取文档的所有实体

    Args:
        doc_id: 文档 ID

    Query Parameters:
        type: 实体类型过滤（可选）

    Request:
        GET /api/graph/entities/{doc_id}?type=人物

    Response:
        {
            "success": true,
            "data": {
                "entities": [
                    {
                        "entity_id": "xxx_0",
                        "text": "实体文本",
                        "type": "人物",
                        "description": "描述",
                        "chunk_id": "xxx_1"
                    }
                ],
                "total": 10
            }
        }
    """
    try:
        graph_builder = get_graph_builder()

        # 加载图谱
        if not graph_builder.load_graph(doc_id):
            return jsonify({
                'success': False,
                'error': f'未找到文档的知识图谱: {doc_id}'
            }), 404

        entity_type = request.args.get('type')

        if entity_type:
            entities = graph_builder.search_entities_by_type(entity_type, doc_id)
        else:
            # 获取所有实体
            entities = []
            for node_id, node_data in graph_builder.graph.nodes(data=True):
                if node_data.get("doc_id") == doc_id:
                    entities.append({
                        "entity_id": node_id,
                        **node_data
                    })

        return jsonify({
            'success': True,
            'data': {
                'entities': entities,
                'total': len(entities)
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/graph/neighbors', methods=['POST'])
def get_entity_neighbors():
    """
    获取实体的邻居节点

    Request Body:
        {
            "doc_id": "文档 ID",
            "entity_id": "实体 ID",
            "hop_depth": 2,  // 可选，默认 1
            "max_neighbors": 20  // 可选，默认 50
        }

    Response:
        {
            "success": true,
            "data": {
                "neighbors": [
                    {
                        "entity_id": "xxx_1",
                        "text": "邻居实体",
                        "type": "类型",
                        "hop": 1,
                        "direction": "outgoing",
                        "relation_type": "包含关系"
                    }
                ],
                "total": 5
            }
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'error': '未提供数据'}), 400

    doc_id = data.get('doc_id')
    entity_id = data.get('entity_id')
    hop_depth = data.get('hop_depth', 1)
    max_neighbors = data.get('max_neighbors', 50)

    if not doc_id or not entity_id:
        return jsonify({'success': False, 'error': 'doc_id 和 entity_id 参数是必需的'}), 400

    try:
        graph_retriever = get_graph_retriever()

        neighbors = graph_retriever.retrieve_by_entity(
            entity_id=entity_id,
            doc_id=doc_id,
            hop_depth=hop_depth,
            max_neighbors=max_neighbors
        )

        return jsonify({
            'success': True,
            'data': {
                'neighbors': neighbors,
                'total': len(neighbors)
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/graph/search', methods=['POST'])
def search_graph_entities():
    """
    在知识图谱中搜索实体

    Request Body:
        {
            "doc_id": "文档 ID",
            "keyword": "关键词",
            "entity_type": "类型"  // 可选
        }

    Response:
        {
            "success": true,
            "data": {
                "entities": [...],
                "total": 3
            }
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'error': '未提供数据'}), 400

    doc_id = data.get('doc_id')
    keyword = data.get('keyword', '')
    entity_type = data.get('entity_type')

    if not doc_id:
        return jsonify({'success': False, 'error': 'doc_id 参数是必需的'}), 400

    try:
        graph_retriever = get_graph_retriever()

        entities = graph_retriever.search_entities(
            keyword=keyword,
            doc_id=doc_id,
            entity_type=entity_type
        )

        return jsonify({
            'success': True,
            'data': {
                'entities': entities,
                'total': len(entities)
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/graph/recognize', methods=['POST'])
def recognize_query_entities():
    """
    从问题中识别实体

    Request Body:
        {
            "query": "用户问题",
            "doc_id": "文档 ID"  // 可选，用于匹配知识图谱
        }

    Response:
        {
            "success": true,
            "data": {
                "entities": [
                    {
                        "text": "实体文本",
                        "type": "实体类型",
                        "matched": true
                    }
                ],
                "total": 2
            }
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'error': '未提供数据'}), 400

    query = data.get('query', '')
    doc_id = data.get('doc_id')

    if not query:
        return jsonify({'success': False, 'error': 'query 参数是必需的'}), 400

    try:
        recognizer = QueryEntityRecognizer()
        entities = recognizer.recognize_entities(query, doc_id, use_graph=bool(doc_id))

        return jsonify({
            'success': True,
            'data': {
                'entities': entities,
                'total': len(entities)
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/graph/path', methods=['POST'])
def find_entity_path():
    """
    查找两个实体之间的路径

    Request Body:
        {
            "doc_id": "文档 ID",
            "source_id": "源实体 ID",
            "target_id": "目标实体 ID",
            "max_length": 3  // 可选，默认 3
        }

    Response:
        {
            "success": true,
            "data": {
                "paths": [...],
                "total": 1
            }
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'error': '未提供数据'}), 400

    doc_id = data.get('doc_id')
    source_id = data.get('source_id')
    target_id = data.get('target_id')
    max_length = data.get('max_length', 3)

    if not all([doc_id, source_id, target_id]):
        return jsonify({'success': False, 'error': 'doc_id、source_id 和 target_id 参数是必需的'}), 400

    try:
        graph_retriever = get_graph_retriever()

        paths = graph_retriever.retrieve_by_path(
            source_id=source_id,
            target_id=target_id,
            doc_id=doc_id,
            max_length=max_length
        )

        return jsonify({
            'success': True,
            'data': {
                'paths': paths,
                'total': len(paths)
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
