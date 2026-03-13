"""配置包：集中化配置管理"""

from app.config.model_config import (
    get_ocr_model,
    get_chat_model,
    get_embedding_model,
    get_reranker_model,
    get_text_splitter_llm,
    OCRModel,
    ChatModel,
    EmbeddingModel,
    RerankModel,
)

from app.config.paths import (
    PROJECT_ROOT,
    DATA_DIR,
    DB_PATH,
    VECTOR_DB_PATH,
    UPLOAD_PATH,
    get_db_path,
    get_vector_db_path,
    get_upload_path,
    ensure_data_dirs,
)

__all__ = [
    # 模型配置
    "get_ocr_model",
    "get_chat_model",
    "get_embedding_model",
    "get_reranker_model",
    "get_text_splitter_llm",
    "OCRModel",
    "ChatModel",
    "EmbeddingModel",
    "RerankModel",
    # 路径配置
    "PROJECT_ROOT",
    "DATA_DIR",
    "DB_PATH",
    "VECTOR_DB_PATH",
    "UPLOAD_PATH",
    "get_db_path",
    "get_vector_db_path",
    "get_upload_path",
    "ensure_data_dirs",
]
