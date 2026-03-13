"""
开放问答 API

提供简洁的第三方调用接口，无认证（调试用）
"""
import logging
from flask import request, jsonify
from app.api import api_bp
from app.services.user_interaction.conversation_processor import process_conversation

logger = logging.getLogger(__name__)


@api_bp.route('/v1/ask', methods=['POST'])
def ask():
    """
    开放问答接口

    请求体：
        {
            "question": "用户问题",      # 必填
            "doc_id": "doc_001",         # 可选，指定文档ID
            "top_k": 5                   # 可选，默认5
        }

    成功响应：
        {
            "code": 0,
            "message": "success",
            "data": {
                "answer": "AI回答内容"
            }
        }

    错误响应：
        {
            "code": 40001,
            "message": "错误描述",
            "data": null
        }
    """
    try:
        data = request.get_json()

        # 参数验证
        if not data:
            return jsonify({
                'code': 40001,
                'message': '请求体不能为空',
                'data': None
            }), 400

        if 'question' not in data:
            return jsonify({
                'code': 40001,
                'message': '缺少必要参数: question',
                'data': None
            }), 400

        question = data.get('question', '').strip()
        if not question:
            return jsonify({
                'code': 40001,
                'message': 'question 参数不能为空',
                'data': None
            }), 400

        # 可选参数
        doc_id = data.get('doc_id')
        top_k = data.get('top_k', 5)

        # 参数类型验证
        if doc_id is not None and not isinstance(doc_id, str):
            return jsonify({
                'code': 40002,
                'message': 'doc_id 参数类型错误',
                'data': None
            }), 400

        if not isinstance(top_k, int) or top_k <= 0:
            return jsonify({
                'code': 40002,
                'message': 'top_k 必须是正整数',
                'data': None
            }), 400

        logger.info(f"[OpenAPI] 收到问题: {question[:100]}...")

        # 调用对话处理流程
        result = process_conversation(
            question=question,
            conversation_history=None,
            top_k=top_k,
            retrieval_top_k=top_k * 4,
            show_progress=False
        )

        if not result.get('success'):
            return jsonify({
                'code': 50001,
                'message': result.get('error', '处理失败'),
                'data': None
            }), 500

        answer = result.get('answer', '')
        logger.info(f"[OpenAPI] 回答长度: {len(answer)} 字符")

        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'answer': answer
            }
        })

    except Exception as e:
        logger.error(f"[OpenAPI] 处理异常: {e}", exc_info=True)
        return jsonify({
            'code': 50001,
            'message': f'服务内部错误: {str(e)}',
            'data': None
        }), 500
