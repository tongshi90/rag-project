"""
模型配置模块

集中管理所有外部 LLM/模型配置，从 .env.example 读取配置
统一使用硅基流动 SiliconFlow 模型
"""
import os
import base64
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import requests


# ============================================
# 配置读取模块
# ============================================

_CONFIG_CACHE: Dict[str, str] = {}
_ENV_FILE_PATH: Optional[str] = None


def _load_env_file() -> None:
    """从 .env.example 文件加载配置到内存"""
    global _CONFIG_CACHE, _ENV_FILE_PATH

    # 获取项目根目录（backend 目录）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(os.path.dirname(current_dir))
    env_path = os.path.join(backend_dir, '.env.example')

    _ENV_FILE_PATH = env_path

    if not os.path.exists(env_path):
        raise FileNotFoundError(f"配置文件不存在: {env_path}")

    _CONFIG_CACHE.clear()
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue
            # 解析 KEY=VALUE 格式
            if '=' in line:
                key, value = line.split('=', 1)
                _CONFIG_CACHE[key.strip()] = value.strip()


def get_config(key: str, default: Optional[str] = None) -> str:
    """
    从 .env.example 获取配置项

    Args:
        key: 配置键名
        default: 默认值，当配置不存在时返回

    Returns:
        配置值

    Raises:
        ValueError: 当配置不存在且没有默认值时
    """
    if not _CONFIG_CACHE:
        _load_env_file()

    if key in _CONFIG_CACHE:
        return _CONFIG_CACHE[key]
    elif default is not None:
        return default
    else:
        raise ValueError(f"配置项 '{key}' 在 .env.example 中未设置")


def get_int_config(key: str, default: int = 0) -> int:
    """获取整数类型配置"""
    value = get_config(key, str(default))
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"配置项 '{key}' 的值 '{value}' 不是有效的整数")


def get_float_config(key: str, default: float = 0.0) -> float:
    """获取浮点数类型配置"""
    value = get_config(key, str(default))
    try:
        return float(value)
    except ValueError:
        raise ValueError(f"配置项 '{key}' 的值 '{value}' 不是有效的浮点数")


def get_bool_config(key: str, default: bool = False) -> bool:
    """获取布尔类型配置"""
    value = get_config(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')


def reload_config() -> None:
    """重新加载配置文件"""
    _load_env_file()


# ============================================
# 模型抽象基类
# ============================================

class OCRModel(ABC):
    """OCR 模型抽象基类"""

    @abstractmethod
    def recognize(self, image_bytes: bytes, prompt: Optional[str] = None) -> str:
        """识别图片中的文字内容"""
        pass


class ChatModel(ABC):
    """聊天模型抽象基类"""

    @abstractmethod
    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """生成聊天回复"""
        pass


class EmbeddingModel(ABC):
    """嵌入模型抽象基类"""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """生成文本的嵌入向量"""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成文本的嵌入向量"""
        pass


class RerankModel(ABC):
    """重排序模型抽象基类"""

    @abstractmethod
    def rerank(self, query: str, documents: List[str], top_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        对文档列表进行重排序

        Args:
            query: 查询文本
            documents: 候选文档列表
            top_n: 返回前 N 个结果

        Returns:
            重排序结果列表，格式: [{"index": int, "relevance_score": float, "document": str}, ...]
        """
        pass


# ============================================
# SiliconFlow 模型实现
# ============================================

class SiliconFlowOCR(OCRModel):
    """硅基流动 OCR 模型实现"""

    def __init__(self):
        """初始化 OCR 模型"""
        self.api_key = get_config("SILICONFLOW_API_KEY")
        self.api_url = get_config("SILICONFLOW_OCR_URL")
        self.model = get_config("SILICONFLOW_OCR_MODEL")
        self.timeout = get_int_config("OCR_TIMEOUT", 60)
        self.default_prompt = get_config("OCR_DEFAULT_PROMPT")

    def recognize(self, image_bytes: bytes, prompt: Optional[str] = None) -> str:
        """调用硅基流动 API 识别图片内容"""
        try:
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            prompt_text = prompt or self.default_prompt

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt_text
                            }
                        ]
                    }
                ],
                "stream": False
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                description = (
                    result
                    .get('choices', [{}])[0]
                    .get('message', {})
                    .get('content', '')
                )
                return description
            else:
                print(f"OCR API error: {response.status_code}, {response.text}")
                return f"OCR识别失败: {response.status_code}"

        except Exception as e:
            print(f"OCR API call error: {e}")
            return f"OCR识别异常: {str(e)}"


class SiliconFlowChat(ChatModel):
    """硅基流动聊天模型实现"""

    def __init__(self, model: Optional[str] = None):
        """
        初始化聊天模型

        Args:
            model: 可选的模型名称，不传则使用默认 Chat 模型
        """
        self.api_key = get_config("SILICONFLOW_API_KEY")
        self.api_url = get_config("SILICONFLOW_CHAT_URL", "https://api.siliconflow.cn/v1/chat/completions")
        self.model = model or get_config("SILICONFLOW_CHAT_MODEL")
        self.timeout = get_int_config("CHAT_TIMEOUT", 60)
        self.max_tokens = get_int_config("CHAT_MAX_TOKENS", 4096)
        self.temperature = get_float_config("CHAT_TEMPERATURE", 0.7)

    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """调用硅基流动 API 生成聊天回复"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # 合并默认参数和自定义参数
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature)
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                content = (
                    result
                    .get('choices', [{}])[0]
                    .get('message', {})
                    .get('content', '')
                )
                return content
            else:
                print(f"Chat API error: {response.status_code}, {response.text}")
                return f"聊天API调用失败: {response.status_code}"

        except Exception as e:
            print(f"Chat API call error: {e}")
            return f"聊天API调用异常: {str(e)}"

    def chat_stream(self, messages: List[Dict[str, Any]], **kwargs):
        """
        调用硅基流动 API 生成流式聊天回复

        Returns:
            生成器，每次产出一个文本片段
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # 合并默认参数和自定义参数
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": True,  # 开启流式
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature)
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                stream=True,  # 开启请求流
                timeout=self.timeout
            )

            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data_str = line[6:]  # 去掉 'data: ' 前缀
                            if data_str.strip() == '[DONE]':
                                break
                            try:
                                import json
                                data = json.loads(data_str)
                                content = (
                                    data
                                    .get('choices', [{}])[0]
                                    .get('delta', {})
                                    .get('content', '')
                                )
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
            else:
                print(f"Chat API error: {response.status_code}, {response.text}")
                yield f"聊天API调用失败: {response.status_code}"

        except Exception as e:
            print(f"Chat API stream error: {e}")
            yield f"聊天API流式调用异常: {str(e)}"


class SiliconFlowEmbedding(EmbeddingModel):
    """硅基流动 Embedding 模型实现"""

    def __init__(self):
        """初始化 Embedding 模型"""
        self.api_key = get_config("SILICONFLOW_API_KEY")
        self.api_url = get_config("SILICONFLOW_EMBEDDING_URL", "https://api.siliconflow.cn/v1/embeddings")
        self.model = get_config("SILICONFLOW_EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-4B")
        self.timeout = get_int_config("EMBEDDING_TIMEOUT", 30)

    def embed(self, text: str) -> List[float]:
        """生成单个文本的嵌入向量"""
        embeddings = self.embed_batch([text])
        return embeddings[0] if embeddings else []

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成文本的嵌入向量"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "input": texts,
                "encoding_format": "float"
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                embeddings = [item["embedding"] for item in result.get("data", [])]
                return embeddings
            else:
                print(f"Embedding API error: {response.status_code}, {response.text}")
                return []

        except Exception as e:
            print(f"Embedding API call error: {e}")
            return []


class SiliconFlowReranker(RerankModel):
    """硅基流动 Rerank 模型实现"""

    def __init__(self):
        """初始化 Rerank 模型"""
        self.api_key = get_config("SILICONFLOW_API_KEY")
        self.api_url = get_config("SILICONFLOW_RERANK_URL", "https://api.siliconflow.cn/v1/rerank")
        self.model = get_config("SILICONFLOW_RERANK_MODEL", "Qwen/Qwen3-Reranker-0.6B")
        self.timeout = get_int_config("RERANK_TIMEOUT", 30)

    def rerank(self, query: str, documents: List[str], top_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        对文档列表进行重排序

        Args:
            query: 查询文本
            documents: 候选文档列表
            top_n: 返回前 N 个结果

        Returns:
            重排序结果列表，格式: [{"index": int, "relevance_score": float, "document": str}, ...]
        """
        if not documents:
            return []

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "query": query,
                "documents": documents,
                "top_n": top_n if top_n else len(documents)
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                reranked_results = []

                for item in result.get("results", []):
                    reranked_results.append({
                        "index": item.get("index"),
                        "relevance_score": item.get("relevance_score"),
                        "document": documents[item.get("index")]
                    })

                return reranked_results
            else:
                print(f"Rerank API error: {response.status_code}, {response.text}")
                # 失败时返回原始顺序
                return [{"index": i, "relevance_score": 0.0, "document": doc} for i, doc in enumerate(documents)]

        except Exception as e:
            print(f"Rerank API call error: {e}")
            # 异常时返回原始顺序
            return [{"index": i, "relevance_score": 0.0, "document": doc} for i, doc in enumerate(documents)]


# ============================================
# 模拟模型实现（用于测试）
# ============================================

class MockChatModel(ChatModel):
    """模拟聊天模型，用于测试"""

    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """返回模拟响应"""
        return "这是一个模拟响应。真实的聊天功能尚未实现。"


# ============================================
# 工厂函数
# ============================================

def get_ocr_model() -> OCRModel:
    """获取 OCR 模型实例"""
    return SiliconFlowOCR()


def get_chat_model() -> ChatModel:
    """获取聊天模型实例"""
    return SiliconFlowChat()


def get_embedding_model() -> EmbeddingModel:
    """获取嵌入模型实例"""
    return SiliconFlowEmbedding()


def get_text_splitter_llm() -> ChatModel:
    """
    获取文本分割专用的 LLM 实例（轻量级模型）

    用于分片优化、问题拆分等场景
    """
    return SiliconFlowChat(model=get_config("SILICONFLOW_TEXT_SPLITTER_MODEL", "Qwen/Qwen2.5-7B-Instruct"))


def get_entity_extraction_model() -> ChatModel:
    """
    获取实体抽取专用模型

    用于实体抽取、关系抽取等场景

    Returns:
        ChatModel 实例
    """
    return SiliconFlowChat(model=get_config("ENTITY_EXTRACTION_MODEL", "Qwen/Qwen2.5-7B-Instruct"))


def get_reranker_model() -> RerankModel:
    """获取重排序模型实例"""
    return SiliconFlowReranker()


# ============================================
# 便捷函数
# ============================================

def get_siliconflow_embed_fn():
    """
    获取 SiliconFlow embedding 函数

    返回的函数接收句子列表，返回 embedding 向量的 numpy 数组

    Returns:
        embedding 函数: (sentences: List[str]) -> np.ndarray

    Raises:
        ValueError: 当配置未设置时
    """
    import numpy as np

    model = get_embedding_model()

    def embed_fn(sentences: List[str]) -> np.ndarray:
        """将句子列表转换为 embedding 向量数组"""
        embeddings = model.embed_batch(sentences)
        if not embeddings:
            return np.zeros((len(sentences), 1024))
        return np.array(embeddings)

    return embed_fn


# 模块加载时预加载配置
_load_env_file()
