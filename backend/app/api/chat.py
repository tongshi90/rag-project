"""
Chat API Routes
"""
import json
import time
from flask import request, jsonify, Response, stream_with_context
from app.api import api_bp
from app.services.user_interaction.question_splitter import split_question
from app.services.user_interaction.query_encoder import get_query_encoder
from app.services.user_interaction.retrieval import RetrievalPipeline
from app.services.user_interaction.generator import generate_answer_stream
from app.services.user_interaction.conversation_processor import process_conversation
from app.config.model_config import get_chat_model


def _stream_response(user_message, conversation_history, top_k, retrieval_top_k):
    """内部生成器函数，用于流式响应"""
    try:
        print(f"[Stream] Starting stream for: {user_message}")

        # 第一步：问题拆分（使用 LLM）
        chat_model = get_chat_model()
        sub_questions = split_question(user_message, chat_model)
        print(f"[Stream] Sub-questions: {sub_questions}")

        # 第二步：问题向量化
        encoder = get_query_encoder()
        query_embeddings = encoder.encode_queries(sub_questions)
        print(f"[Stream] Encoded {len(query_embeddings)} queries")

        # 第三步：检索和重排序
        retrieval_pipeline = RetrievalPipeline(
            retrieval_top_k=retrieval_top_k,
            final_top_k=top_k
        )
        all_retrieved_chunks = retrieval_pipeline.batch_retrieve(
            queries=sub_questions,
            query_embeddings=query_embeddings,
            encoder=encoder
        )
        print(f"[Stream] Retrieved chunks for {len(all_retrieved_chunks)} sub-questions")

        # 第四步：流式生成答案
        if len(sub_questions) == 1:
            # 单个问题，直接流式生成
            print("[Stream] Starting stream generation...")
            chunk_count = 0
            for chunk in generate_answer_stream(
                query=sub_questions[0],
                retrieved_chunks=all_retrieved_chunks[0],
                conversation_history=conversation_history
            ):
                chunk_count += 1
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        else:
            # 多个问题，先完整生成再返回（简化处理）
            from app.services.user_interaction.generator import AnswerGenerator
            generator = AnswerGenerator()
            answer = generator.generate_for_sub_questions(
                sub_questions=sub_questions,
                all_retrieved_chunks=all_retrieved_chunks,
                original_query=user_message
            )
            print(f"[Stream] Generated answer length: {len(answer)}")
            # 分块发送完整答案
            chunk_size = 20
            for i in range(0, len(answer), chunk_size):
                chunk = answer[i:i + chunk_size]
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
                time.sleep(0.01)  # 模拟流式效果

        # 发送结束标记
        print("[Stream] Sending [DONE] signal")
        yield "data: [DONE]\n\n"

    except Exception as e:
        import traceback
        print(f"[Stream] Error: {e}")
        traceback.print_exc()
        yield f"data: {{'error': '{str(e)}'}}\n\n"


@api_bp.route('/chat', methods=['POST'])
def chat():
    """
    Process chat message and return RAG response

    Request body:
        {
            "message": "用户问题",
            "conversation_history": [  // 可选
                {"role": "user", "content": "之前的问题"},
                {"role": "assistant", "content": "之前的回答"}
            ],
            "top_k": 5,  // 可选，默认5
            "retrieval_top_k": 20  // 可选，默认20
        }

    Response:
        {
            "success": true,
            "data": {
                "answer": "AI回答内容",
                "sub_questions": ["子问题1", "子问题2"],
                "sources": [{"chunk_id": "...", "text": "..."}],
                "elapsed": 1.23
            }
        }
    """
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({'success': False, 'error': 'No message provided'}), 400

    user_message = data['message']
    conversation_history = data.get('conversation_history')
    top_k = data.get('top_k', 5)
    retrieval_top_k = data.get('retrieval_top_k', 20)

    try:
        # 调用完整的对话处理流程
        result = process_conversation(
            question=user_message,
            conversation_history=conversation_history,
            top_k=top_k,
            retrieval_top_k=retrieval_top_k,
            show_progress=False  # API 模式不显示进度
        )

        return jsonify({
            'success': True,
            'data': {
                'answer': result['answer'],
                'elapsed': result['total_elapsed']
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/chat/stream', methods=['POST'])
def chat_stream():
    """
    流式聊天接口 (SSE)

    Request body:
        {
            "message": "用户问题",
            "conversation_history": [...],  // 可选
            "top_k": 5,
            "retrieval_top_k": 20
        }

    Response: Server-Sent Events (SSE)
        data: {"content": "回答片段"}
        data: {"content": "回答片段"}
        data: [DONE]
    """
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'success': False, 'error': 'No message provided'}), 400

    # 获取本次对话用户的提问
    user_message = data['message']
    # 获取历史对话
    conversation_history = data.get('conversation_history')
    # retrieval_top_k是检索后的结果(向量距离计算的top_k)，top_k是重排序后的结果(语义排序后的top_k)
    top_k = data.get('top_k', 5)
    retrieval_top_k = data.get('retrieval_top_k', 20)

    return Response(
        stream_with_context(_stream_response(user_message, conversation_history, top_k, retrieval_top_k)),
        content_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@api_bp.route('/chat/health', methods=['GET'])
def chat_health():
    """
    Health check for chat service

    检查聊天服务的健康状态
    """
    try:
        from app.services.document_processing.embedding.vector_store import get_vector_store
        from app.config.model_config import get_chat_model, get_embedding_model

        vector_store = get_vector_store()
        stats = vector_store.get_stats()

        return jsonify({
            'success': True,
            'data': {
                'vector_db': {
                    'status': 'ok',
                    'total_chunks': stats.get('total_count', 0),
                    'doc_count': stats.get('doc_count', 0)
                },
                'chat_model': {
                    'status': 'ok',
                    'provider': 'siliconflow'
                },
                'embedding_model': {
                    'status': 'ok',
                    'provider': 'siliconflow'
                }
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
