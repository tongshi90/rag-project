"""
关键字索引器

使用 jieba 分词和 BM25 算法构建关键字检索索引
"""
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import jieba
    from rank_bm25 import BM25Okapi
except ImportError:
    jieba = None
    BM25Okapi = None
    print("警告: jieba 或 rank-bm25 未安装，请运行: pip install jieba rank-bm25")


from app.config.paths import KEYWORD_INDEX_PATH


class KeywordIndexer:
    """
    关键字索引器

    使用 BM25 算法实现基于关键字的文档检索
    """

    def __init__(self):
        """初始化关键字索引器"""
        if jieba is None or BM25Okapi is None:
            raise ImportError("jieba 或 rank-bm25 未安装")

        self.bm25: Optional[BM25Okapi] = None
        self.chunk_ids: List[str] = []
        self.chunk_texts: List[str] = []
        self.current_doc_id: Optional[str] = None
        self.top_k = 10

    def _tokenize(self, text: str) -> List[str]:
        """
        使用 jieba 分词

        Args:
            text: 输入文本

        Returns:
            分词列表
        """
        return list(jieba.cut(text))

    def build_index(
        self,
        chunks: List[Dict[str, Any]],
        doc_id: str
    ) -> Dict[str, Any]:
        """
        构建 BM25 索引

        Args:
            chunks: chunk 列表
            doc_id: 文档 ID

        Returns:
            构建结果
        """
        self.current_doc_id = doc_id
        self.chunk_ids = []
        self.chunk_texts = []

        for chunk in chunks:
            chunk_id = chunk.get("chunk_id", "")
            text = chunk.get("text", "")
            if chunk_id and text:
                self.chunk_ids.append(chunk_id)
                self.chunk_texts.append(text)

        # 分词
        tokenized_corpus = [self._tokenize(text) for text in self.chunk_texts]

        # 构建 BM25 索引
        self.bm25 = BM25Okapi(tokenized_corpus)

        return {
            "success": True,
            "doc_id": doc_id,
            "total_chunks": len(self.chunk_ids)
        }

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        doc_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        BM25 检索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            doc_id: 文档 ID（用于过滤）

        Returns:
            检索结果列表
        """
        if self.bm25 is None:
            return []

        top_k = top_k or self.top_k

        # 分词
        tokenized_query = self._tokenize(query)

        # BM25 评分
        scores = self.bm25.get_scores(tokenized_query)

        # 获取 top-k 结果
        top_indices = scores.argsort()[-top_k:][::-1]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # 只返回有分数的结果
                results.append({
                    "chunk_id": self.chunk_ids[idx],
                    "score": float(scores[idx]),
                    "doc_id": doc_id or self.current_doc_id
                })

        return results

    def get_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """
        提取文本的关键字

        Args:
            text: 输入文本
            top_k: 返回关键字数量

        Returns:
            关键字列表
        """
        try:
            import jieba.analyse
            keywords = jieba.analyse.extract_tags(text, topK=top_k)
            return keywords
        except Exception as e:
            print(f"关键字提取失败: {e}")
            return []

    def save_index(self, doc_id: str) -> str:
        """
        保存索引到文件

        Args:
            doc_id: 文档 ID

        Returns:
            保存路径
        """
        KEYWORD_INDEX_PATH.mkdir(parents=True, exist_ok=True)
        file_path = KEYWORD_INDEX_PATH / f"{doc_id}.pkl"

        index_data = {
            "bm25": self.bm25,
            "chunk_ids": self.chunk_ids,
            "chunk_texts": self.chunk_texts,
            "doc_id": doc_id
        }

        with open(file_path, 'wb') as f:
            pickle.dump(index_data, f)

        return str(file_path)

    def load_index(self, doc_id: str) -> bool:
        """
        从文件加载索引

        Args:
            doc_id: 文档 ID

        Returns:
            是否加载成功
        """
        file_path = KEYWORD_INDEX_PATH / f"{doc_id}.pkl"

        if not file_path.exists():
            return False

        try:
            with open(file_path, 'rb') as f:
                index_data = pickle.load(f)

            self.bm25 = index_data.get("bm25")
            self.chunk_ids = index_data.get("chunk_ids", [])
            self.chunk_texts = index_data.get("chunk_texts", [])
            self.current_doc_id = doc_id

            return True

        except Exception as e:
            print(f"加载索引失败: {e}")
            return False

    def delete_index(self, doc_id: str) -> bool:
        """
        删除索引文件

        Args:
            doc_id: 文档 ID

        Returns:
            是否删除成功
        """
        file_path = KEYWORD_INDEX_PATH / f"{doc_id}.pkl"

        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def clear(self):
        """清空索引"""
        self.bm25 = None
        self.chunk_ids = []
        self.chunk_texts = []
        self.current_doc_id = None


# 全局索引器实例
_keyword_indexer_instance = None


def get_keyword_indexer() -> KeywordIndexer:
    """
    获取全局关键字索引器实例

    Returns:
        KeywordIndexer 实例
    """
    global _keyword_indexer_instance
    if _keyword_indexer_instance is None:
        _keyword_indexer_instance = KeywordIndexer()
    return _keyword_indexer_instance


def extract_keywords(text: str, top_k: int = 10) -> List[str]:
    """
    提取关键字的便捷函数

    Args:
        text: 输入文本
        top_k: 返回关键字数量

    Returns:
        关键字列表
    """
    try:
        import jieba.analyse
        return jieba.analyse.extract_tags(text, topK=top_k)
    except Exception:
        return []
