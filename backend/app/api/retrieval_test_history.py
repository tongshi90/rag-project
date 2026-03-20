"""
Retrieval Test History API
"""
from flask import request, jsonify
from app.api import api_bp
from app.models.retrieval_test_history import retrieval_test_history_db


@api_bp.route('/retrieval-test-history/<kb_id>', methods=['GET'])
def get_history(kb_id):
    """Get retrieval test history for a knowledge base"""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 10, type=int)

        offset = (page - 1) * page_size

        histories = retrieval_test_history_db.get_history_by_kb_id(
            kb_id, limit=page_size, offset=offset
        )
        total = retrieval_test_history_db.get_history_count_by_kb_id(kb_id)

        return jsonify({
            'success': True,
            'data': {
                'histories': histories,
                'total': total,
                'page': page,
                'pageSize': page_size,
                'totalPages': (total + page_size - 1) // page_size
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/retrieval-test-history', methods=['POST'])
def add_history():
    """Add a new retrieval test history record"""
    try:
        data = request.get_json()
        kb_id = data.get('kbId')
        query = data.get('query')

        if not kb_id or not query:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: kbId, query'
            }), 400

        history = retrieval_test_history_db.add_history(kb_id, query)

        return jsonify({
            'success': True,
            'data': history.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/retrieval-test-history/<history_id>', methods=['DELETE'])
def delete_history(history_id):
    """Delete a retrieval test history record"""
    try:
        success = retrieval_test_history_db.delete_history(history_id)

        if success:
            return jsonify({
                'success': True,
                'data': {'deletedId': history_id}
            })
        else:
            return jsonify({
                'success': False,
                'error': 'History record not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/retrieval-test-history/<kb_id>/all', methods=['DELETE'])
def clear_history(kb_id):
    """Clear all retrieval test history for a knowledge base"""
    try:
        count = retrieval_test_history_db.clear_history_by_kb_id(kb_id)

        return jsonify({
            'success': True,
            'data': {'deletedCount': count}
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
