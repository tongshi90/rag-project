"""
Retrieval Test API Routes

提供召回测试功能，用于测试检索效果，不调用LLM生成答案。
"""
from flask import request, jsonify

from app.api import api_bp

# Note: The following imports depend on chromadb which requires sqlite3 >= 3.35.0
# We import them lazily in the functions that use them to avoid import errors:
# - get_query_encoder
# - RetrievalPipeline
# - Reranker
# - get_vector_store


@api_bp.route('/retrieval-test', methods=['POST'])
def retrieval_test():
    """
    召回测试接口

    Request body:
        {
            "query": "测试查询文本",
            "kb_id": "知识库ID（可选，如果提供则只检索该知识库的文件）",
            "top_k": 5,  // 可选，默认5
            "retrieval_top_k": 20  // 可选，默认20
        }

    Response:
        {
            "success": true,
            "data": {
                "query": "测试查询文本",
                "chunks": [
                    {
                        "chunk_id": "doc_001_1",
                        "text": "文本内容",
                        "score": 0.95,
                        "rerank_score": 0.92,
                        "metadata": {
                            "doc_id": "doc_001",
                            "page": 1,
                            "order": 1,
                            "type": "text",
                            "length": 100
                        }
                    },
                    ...
                ],
                "total": 5
            }
        }
    """
    data = request.get_json()

    if not data or 'query' not in data:
        return jsonify({'success': False, 'error': '未提供查询文本'}), 400

    query = data['query']
    # 同时支持 kbId (前端驼峰式) 和 kb_id (蛇形式)
    kb_id = data.get('kb_id') or data.get('kbId')
    top_k = data.get('top_k') or data.get('topK', 5)
    retrieval_top_k = data.get('retrieval_top_k') or data.get('retrievalTopK', 20)

    try:
        # 获取编码器
        from app.services.user_interaction.query_encoder import get_query_encoder
        encoder = get_query_encoder()

        # 编码查询文本
        query_embedding = encoder.encode_query(query)

        if kb_id:
            # 获取知识库下的所有文件ID
            from app.models import knowledge_base_db
            from app.models.file import db

            files = db.get_files_by_kb_id(kb_id)
            file_ids = [f['id'] for f in files]

            if not file_ids:
                return jsonify({
                    'success': True,
                    'data': {
                        'query': query,
                        'chunks': [],
                        'total': 0,
                        'message': '知识库中没有文件'
                    }
                })

            # 向量检索 - 使用 filter 参数直接限制在当前知识库范围内
            from app.services.document_processing.embedding.vector_store import get_vector_store
            from app.services.user_interaction.retrieval import Reranker
            vector_store = get_vector_store()

            # 尝试使用 ChromaDB 的 $in 操作符进行过滤（如果支持）
            try:
                raw_results = vector_store.search(
                    query_embedding,
                    top_k=retrieval_top_k,
                    filter={"doc_id": {"$in": file_ids}}
                )
            except Exception as e:
                # 如果 filter 不支持，则回退到全局检索+后过滤
                raw_results = vector_store.search(query_embedding, top_k=retrieval_top_k * 3)

                # 后过滤
                filtered_results = []
                for result in raw_results:
                    doc_id = result.get('metadata', {}).get('doc_id', '')
                    if doc_id in file_ids:
                        filtered_results.append(result)
                raw_results = filtered_results

            # 如果没有足够的结果，返回空列表
            if not raw_results:
                return jsonify({
                    'success': True,
                    'data': {
                        'query': query,
                        'chunks': [],
                        'total': 0,
                        'message': '未找到相关文档片段'
                    }
                })

            # 取前 retrieval_top_k 个进行重排序
            candidates = raw_results[:retrieval_top_k]

            # 重排序
            reranker = Reranker()
            final_results = reranker.rerank(query, candidates, top_k=top_k)

        else:
            # 全局检索
            from app.services.user_interaction.retrieval import RetrievalPipeline
            pipeline = RetrievalPipeline(
                retrieval_top_k=retrieval_top_k,
                final_top_k=top_k
            )
            final_results = pipeline.retrieve(query, query_embedding)

        # 格式化结果
        formatted_chunks = []
        for result in final_results:
            metadata = result.get('metadata', {})
            formatted_chunk = {
                'chunkId': result.get('chunk_id', ''),
                'text': result.get('text', ''),
                'score': result.get('score', 0),
                'rerankScore': result.get('rerank_score', result.get('score', 0)),
                'metadata': {
                    'docId': metadata.get('doc_id', ''),
                    'page': metadata.get('page', 0),
                    'order': metadata.get('order', 0),
                    'type': metadata.get('type', ''),
                    'length': metadata.get('length', 0),
                    'bbox': metadata.get('bbox')
                }
            }
            formatted_chunks.append(formatted_chunk)

        return jsonify({
            'success': True,
            'data': {
                'query': query,
                'chunks': formatted_chunks,
                'total': len(formatted_chunks)
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/retrieval-test/health', methods=['GET'])
def retrieval_test_health():
    """
    召回测试服务健康检查
    """
    try:
        from app.services.document_processing.embedding.vector_store import get_vector_store
        vector_store = get_vector_store()
        stats = vector_store.get_stats()

        return jsonify({
            'success': True,
            'data': {
                'vector_db': {
                    'status': 'ok',
                    'total_chunks': stats.get('total_count', 0),
                    'doc_count': stats.get('doc_count', 0)
                }
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
