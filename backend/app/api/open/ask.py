"""
开放问答 API

提供简洁的第三方调用接口，无认证（调试用）

支持智能两阶段召回：
1. 如果用户指定 kb_id，直接查询该知识库
2. 如果用户未指定 kb_id：
   - 使用 LLM 进行意图识别，预测最相关的知识库
   - 进行定向召回
   - 如果所有 chunk 分数 < 0.6，则进行全局召回
"""
import logging
from flask import request, jsonify
from app.api import api_bp
from app.services.user_interaction.conversation_processor import process_conversation_with_intent

logger = logging.getLogger(__name__)


@api_bp.route('/chat', methods=['POST'])
def chat():
    """
    开放问答接口（支持智能两阶段召回）

    请求体：
        {
            "question": "用户问题",      # 必填
            "kb_id": "kb_001",          # 可选，指定知识库ID
                                       # 如果不指定，系统将自动预测最相关的知识库
            "top_k": 5                   # 可选，默认5
        }

    智能召回流程：
        1. 如果指定 kb_id：直接查询该知识库
        2. 如果未指定 kb_id：
           a. 使用 LLM 意图识别，预测最相关的知识库
           b. 定向召回，检查最高分数
           c. 如果分数 < 0.6：自动切换到全局召回

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
        kb_id = data.get('kb_id')  # 知识库 ID，为空时自动预测
        top_k = data.get('top_k', 5)

        # 参数类型验证
        if kb_id is not None and not isinstance(kb_id, str):
            return jsonify({
                'code': 40002,
                'message': 'kb_id 参数类型错误',
                'data': None
            }), 400

        if not isinstance(top_k, int) or top_k <= 0:
            return jsonify({
                'code': 40002,
                'message': 'top_k 必须是正整数',
                'data': None
            }), 400

        # 调用智能两阶段召回流程
        result = process_conversation_with_intent(
            question=question,
            conversation_history=None,
            top_k=top_k,
            retrieval_top_k=top_k * 4,
            kb_id=kb_id,  # 如果指定则直接使用，否则自动预测
            show_progress=False
        )

        if not result.get('success'):
            return jsonify({
                'code': 50001,
                'message': result.get('error', '处理失败'),
                'data': None
            }), 500

        answer = result.get('answer', '')

        return jsonify({
            'code': 0,
            'message': '操作成功',
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
