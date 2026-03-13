# 关键字 + Graph 增强 RAG 升级方案

> 本文档详细说明如何将现有向量RAG系统升级为 **关键字检索 + 知识图谱增强RAG** 系统
>
> 📝 标记说明：`[新增]` 表示新增模块，`[修改]` 表示修改现有模块

---

## 一、系统架构对比

### 1.1 现有架构（纯向量RAG）

```
离线阶段：PDF → 拆分 → 验证 → 优化 → 向量化 → ChromaDB
在线阶段：查询 → 向量化 → 检索 → 重排序 → LLM生成 → 答案
```

### 1.2 升级后架构（关键字 + Graph增强RAG）

```
┌─────────────────────────────────────────────────────────────────────┐
│ 离线阶段（文档处理）- 新增知识图谱构建                               │
├─────────────────────────────────────────────────────────────────────┤
│  用户上传 PDF                                                        │
│      ↓                                                              │
│  [1] Splitter: PDF → Chunks [修改]                                   │
│      ↓                                                              │
│  [2] Validator: 质量检测                                             │
│      ↓                                                              │
│  [3] Entity Extractor [新增]: 实体抽取（LLM）                        │
│      ↓                                                              │
│  [4] Relation Extractor [新增]: 关系抽取（LLM）                      │
│      ↓                                                              │
│  [5] Graph Builder [新增]: 构建知识图谱                              │
│      ↓                                                              │
│  [6] Keyword Indexer [新增]: 关键字索引（BM25）                      │
│      ↓                                                              │
│  [7] Optimizer: LLM 优化                                             │
│      ↓                                                              │
│  [8] Embedding: 向量化存储                                           │
│      ↓                                                              │
│  ChromaDB (向量) + GraphDB (图谱) + KeywordIndex (关键字)           │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ 在线阶段（用户交互）- 混合检索增强                                    │
├─────────────────────────────────────────────────────────────────────┤
│  用户提问                                                            │
│      ↓                                                              │
│  [1] Question Splitter: 问题拆分                                     │
│      ↓                                                              │
│  [2] Entity Recognizer [新增]: 问题实体识别（LLM）                   │
│      ↓                                                              │
│  [3] Query Encoder: 问题向量化                                       │
│      ↓                                                              │
│  [4] Multi-Retrieval [修改]: 混合检索                                │
│      ├── 向量检索（ChromaDB）                                        │
│      ├── 关键字检索（BM25） [新增]                                   │
│      └── 图谱检索（Graph Traversal） [新增]                          │
│      ↓                                                              │
│  [5] Fusion & Rerank [修改]: 结果融合 + 重排序                      │
│      ↓                                                              │
│  [6] Context Enricher [新增]: 图谱上下文增强                         │
│      ↓                                                              │
│  [7] Generator: LLM 答案生成                                         │
│      ↓                                                              │
│  返回答案                                                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、核心模块设计

### 2.1 实体抽取模块 [新增]

**文件路径**: `backend/app/services/document_processing/entity_extraction/`

**功能**: 从文档分片中抽取实体（人名、地名、机构、概念等）

**模型选择**（硅基流动平台）:
- `Qwen/Qwen2.5-7B-Instruct` - 实体抽取任务（性价比高）
- 或 `deepseek-ai/DeepSeek-V3` - 复杂实体关系抽取（更准确）

**实现思路**:

```python
# entity_extractor.py

class EntityExtractor:
    """实体抽取器"""

    def __init__(self, chat_model: ChatModel):
        self.chat_model = chat_model
        self.entity_types = [
            "人物", "地点", "组织机构", "时间", "数量",
            "产品", "技术概念", "事件"
        ]

    def extract_from_chunk(self, chunk: Dict) -> List[Entity]:
        """
        从单个chunk中抽取实体

        Args:
            chunk: 文档分片

        Returns:
            实体列表
        """
        prompt = f"""请从以下文本中抽取实体，按类型分类。

文本：
{chunk['text']}

请按以下JSON格式返回：
{{
    "entities": [
        {{"text": "实体文本", "type": "实体类型", "confidence": 0.95}}
    ]
}}

实体类型：{', '.join(self.entity_types)}
"""

        response = self.chat_model.chat([{"role": "user", "content": prompt}])
        return self._parse_entities(response, chunk)

    def extract_from_document(self, chunks: List[Dict]) -> List[Entity]:
        """
        从整个文档中抽取实体（批量处理，优化API调用）

        使用滑动窗口 + 去重策略
        """
        # 按文档分组，使用窗口合并chunks
        # 调用LLM批量抽取
        # 实体去重和合并
        pass
```

**输出格式**:

```python
{
    "entity_id": "ent_001",
    "text": "张三",
    "type": "人物",
    "chunk_id": "doc_001_1",
    "doc_id": "doc_001",
    "confidence": 0.95,
    "metadata": {
        "page": 12,
        "bbox": [x0, y0, x1, y1]
    }
}
```

---

### 2.2 关系抽取模块 [新增]

**文件路径**: `backend/app/services/document_processing/relation_extraction/`

**功能**: 抽取实体之间的语义关系

**模型选择**: `deepseek-ai/DeepSeek-V3`（关系推理能力强）

**实现思路**:

```python
# relation_extractor.py

class RelationExtractor:
    """关系抽取器"""

    def __init__(self, chat_model: ChatModel):
        self.chat_model = chat_model
        self.relation_types = [
            "包含关系", "因果关系", "所属关系", "定义关系",
            "相似关系", "对比关系", "时序关系", "位置关系"
        ]

    def extract_relations(self, entities: List[Entity], chunk: Dict) -> List[Relation]:
        """
        抽取实体间关系

        Args:
            entities: 实体列表
            chunk: 文档分片

        Returns:
            关系列表
        """
        # 构建实体上下文
        entity_context = self._build_entity_context(entities, chunk)

        prompt = f"""请分析以下文本中实体之间的关系。

实体列表：
{entity_context}

文本：
{chunk['text']}

请按以下JSON格式返回：
{{
    "relations": [
        {{
            "source": "源实体",
            "target": "目标实体",
            "relation": "关系类型",
            "evidence": "支持该关系的原文片段",
            "confidence": 0.9
        }}
    ]
}}

关系类型：{', '.join(self.relation_types)}
"""

        response = self.chat_model.chat([{"role": "user", "content": prompt}])
        return self._parse_relations(response)
```

**输出格式**:

```python
{
    "relation_id": "rel_001",
    "source_entity": "张三",
    "target_entity": "XX公司",
    "relation_type": "所属关系",
    "evidence": "张三是XX公司的技术总监",
    "chunk_id": "doc_001_1",
    "doc_id": "doc_001",
    "confidence": 0.9
}
```

---

### 2.3 知识图谱构建模块 [新增]

**文件路径**: `backend/app/services/document_processing/graph_builder/`

**存储方案**:
- **方案A（轻量级）**: 使用NetworkX内存图谱 + JSON序列化存储
- **方案B（生产级）**: 使用Neo4j图数据库

**实现思路**:

```python
# graph_builder.py

import networkx as nx
from typing import Dict, List

class KnowledgeGraphBuilder:
    """知识图谱构建器"""

    def __init__(self, storage_type: str = "memory"):
        self.storage_type = storage_type
        if storage_type == "memory":
            self.graph = nx.MultiDiGraph()
        elif storage_type == "neo4j":
            # Neo4j连接
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(...)

    def build_graph(self, entities: List[Entity], relations: List[Relation]):
        """构建图谱"""
        # 添加实体节点
        for entity in entities:
            self.graph.add_node(
                entity['entity_id'],
                label=entity['text'],
                type=entity['type'],
                chunk_id=entity['chunk_id'],
                doc_id=entity['doc_id']
            )

        # 添加关系边
        for relation in relations:
            self.graph.add_edge(
                relation['source_entity'],
                relation['target_entity'],
                relation_type=relation['relation_type'],
                evidence=relation['evidence'],
                confidence=relation['confidence']
            )

    def save_graph(self, doc_id: str):
        """保存图谱"""
        if self.storage_type == "memory":
            import json
            from networkx.readwrite import json_graph

            data = json_graph.node_link_data(self.graph)
            with open(f'data/graph/{doc_id}.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def load_graph(self, doc_id: str):
        """加载图谱"""
        if self.storage_type == "memory":
            import json
            from networkx.readwrite import json_graph

            with open(f'data/graph/{doc_id}.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.graph = json_graph.node_link_graph(data)
```

**图谱存储结构**:

```json
{
  "nodes": [
    {
      "id": "ent_001",
      "label": "张三",
      "type": "人物",
      "doc_id": "doc_001"
    }
  ],
  "links": [
    {
      "source": "ent_001",
      "target": "ent_002",
      "relation": "所属关系",
      "evidence": "张三是XX公司的技术总监"
    }
  ]
}
```

---

### 2.4 关键字索引模块 [新增]

**文件路径**: `backend/app/services/document_processing/keyword_index/`

**功能**: 构建BM25倒排索引，支持关键字检索

**实现思路**:

```python
# keyword_indexer.py

import jieba
from rank_bm25 import BM25Okapi
from typing import List, Dict
import pickle

class KeywordIndexer:
    """关键字索引器（BM25）"""

    def __init__(self):
        self.bm25 = None
        self.corpus = []
        self.chunk_ids = []
        self.tokenized_corpus = []

    def build_index(self, chunks: List[Dict]):
        """
        构建BM25索引

        Args:
            chunks: 文档分片列表
        """
        self.corpus = []
        self.chunk_ids = []

        for chunk in chunks:
            # 中文分词
            tokens = list(jieba.cut(chunk['text']))
            self.tokenized_corpus.append(tokens)
            self.chunk_ids.append(chunk['chunk_id'])

        # 构建BM25索引
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def save_index(self, doc_id: str):
        """保存索引"""
        index_data = {
            'bm25': self.bm25,
            'chunk_ids': self.chunk_ids,
            'corpus': self.corpus
        }
        with open(f'data/keyword_index/{doc_id}.pkl', 'wb') as f:
            pickle.dump(index_data, f)

    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        关键字检索

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            检索结果列表
        """
        query_tokens = list(jieba.cut(query))
        scores = self.bm25.get_scores(query_tokens)

        # 获取top_k结果
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        results = []
        for idx in top_indices:
            results.append({
                'chunk_id': self.chunk_ids[idx],
                'score': float(scores[idx]),
                'match_type': 'keyword'
            })

        return results
```

---

### 2.5 问题实体识别模块 [新增]

**文件路径**: `backend/app/services/user_interaction/entity_recognizer/`

**功能**: 识别用户问题中的实体，用于图谱检索

**模型选择**: `Qwen/Qwen2.5-7B-Instruct`

**实现思路**:

```python
# entity_recognizer.py

class QueryEntityRecognizer:
    """问题实体识别器"""

    def __init__(self, chat_model: ChatModel, graph_builder: KnowledgeGraphBuilder):
        self.chat_model = chat_model
        self.graph_builder = graph_builder

    def recognize_entities(self, query: str) -> List[Dict]:
        """
        识别问题中的实体

        Args:
            query: 用户问题

        Returns:
            识别出的实体列表
        """
        prompt = f"""请从以下问题中识别关键实体。

问题：{query}

请按以下JSON格式返回：
{{
    "entities": [
        {{"text": "实体文本", "type": "实体类型"}}
    ]
}}

只返回明确的实体名称，不要抽取描述性词语。
"""

        response = self.chat_model.chat([{"role": "user", "content": prompt}])
        entities = self._parse_entities(response)

        # 与图谱中的实体进行匹配
        matched_entities = self._match_with_graph(entities)

        return matched_entities

    def _match_with_graph(self, entities: List[Dict]) -> List[Dict]:
        """将识别的实体与图谱中的实体进行匹配"""
        matched = []
        for entity in entities:
            # 在图谱中搜索相似节点
            graph_nodes = self.graph_builder.find_nodes_by_label(entity['text'])
            if graph_nodes:
                matched.extend(graph_nodes)
        return matched
```

---

### 2.6 图谱检索模块 [新增]

**文件路径**: `backend/app/services/user_interaction/graph_retrieval/`

**功能**: 基于图谱进行邻域检索和路径发现

**实现思路**:

```python
# graph_retrieval.py

class GraphRetriever:
    """图谱检索器"""

    def __init__(self, graph_builder: KnowledgeGraphBuilder):
        self.graph_builder = graph_builder

    def retrieve_by_entity(
        self,
        entity_id: str,
        hop_depth: int = 2,
        top_k: int = 10
    ) -> List[Dict]:
        """
        基于实体的邻域检索

        Args:
            entity_id: 起始实体ID
            hop_depth: 跳数（1-2跳）
            top_k: 返回结果数量

        Returns:
            相关chunk列表
        """
        graph = self.graph_builder.graph

        # 获取n跳邻域
        neighbors = set()
        current_hop = {entity_id}

        for hop in range(hop_depth):
            next_hop = set()
            for node in current_hop:
                # 获取邻居节点
                neighbors.update(graph.neighbors(node))
                next_hop.update(graph.neighbors(node))
            current_hop = next_hop

        # 收集相关chunks
        related_chunks = []
        for node_id in neighbors:
            node_data = graph.nodes[node_id]
            if 'chunk_id' in node_data:
                related_chunks.append({
                    'chunk_id': node_data['chunk_id'],
                    'retrieval_method': 'graph_neighbor',
                    'hop_distance': hop_depth,
                    'entity': node_data.get('label', '')
                })

        return related_chunks[:top_k]

    def retrieve_by_path(
        self,
        source_entity: str,
        target_entity: str
    ) -> List[Dict]:
        """
        基于路径的检索（寻找两个实体之间的关系）

        Args:
            source_entity: 源实体
            target_entity: 目标实体

        Returns:
            路径上的chunks
        """
        graph = self.graph_builder.graph

        # 寻找最短路径
        try:
            path = nx.shortest_path(
                graph,
                source=source_entity,
                target=target_entity
            )

            # 收集路径上的chunks
            path_chunks = []
            for i in range(len(path) - 1):
                edge_data = graph.get_edge_data(path[i], path[i+1])
                path_chunks.append({
                    'evidence': edge_data.get('evidence', ''),
                    'relation': edge_data.get('relation_type', ''),
                    'retrieval_method': 'graph_path'
                })

            return path_chunks
        except nx.NetworkXNoPath:
            return []
```

---

### 2.7 混合检索模块 [修改]

**文件路径**: `backend/app/services/user_interaction/retrieval/retrieval.py`

**功能**: 整合向量检索、关键字检索、图谱检索

**修改思路**:

```python
# retrieval.py (修改)

class HybridRetrievalPipeline:
    """混合检索管道"""

    def __init__(
        self,
        vector_store: VectorStore,
        keyword_indexer: KeywordIndexer,      # [新增]
        graph_retriever: GraphRetriever,      # [新增]
        encoder: QueryEncoder,
        retrieval_top_k: int = 20,
        final_top_k: int = 5
    ):
        self.vector_store = vector_store
        self.keyword_indexer = keyword_indexer  # [新增]
        self.graph_retriever = graph_retriever  # [新增]
        self.encoder = encoder
        self.retrieval_top_k = retrieval_top_k
        self.final_top_k = final_top_k

        # 检索权重配置
        self.weights = {
            'vector': 0.5,      # 向量检索权重
            'keyword': 0.3,     # 关键字检索权重
            'graph': 0.2        # 图谱检索权重
        }

    def batch_retrieve(
        self,
        queries: List[str],
        query_embeddings: np.ndarray,
        entities: List[str] = None  # [新增] 实体列表
    ) -> List[List[Dict]]:
        """
        批量混合检索

        Args:
            queries: 查询列表
            query_embeddings: 查询向量
            entities: 识别出的实体 [新增]

        Returns:
            检索结果列表
        """
        all_results = []

        for query, embedding in zip(queries, query_embeddings):
            # 1. 向量检索
            vector_results = self._vector_retrieve(embedding)

            # 2. 关键字检索 [新增]
            keyword_results = self._keyword_retrieve(query)

            # 3. 图谱检索 [新增]
            graph_results = self._graph_retrieve(entities) if entities else []

            # 4. 结果融合
            fused_results = self._fuse_results(
                vector_results,
                keyword_results,
                graph_results
            )

            # 5. 重排序
            final_results = self._rerank(query, fused_results)

            all_results.append(final_results[:self.final_top_k])

        return all_results

    def _vector_retrieve(self, embedding: np.ndarray) -> List[Dict]:
        """向量检索"""
        results = self.vector_store.search_by_vector(
            embedding,
            top_k=self.retrieval_top_k
        )
        return [{'chunk_id': r['id'], 'score': r['score'], 'method': 'vector'} for r in results]

    def _keyword_retrieve(self, query: str) -> List[Dict]:  # [新增]
        """关键字检索"""
        results = self.keyword_indexer.search(query, top_k=self.retrieval_top_k)
        return [{'chunk_id': r['chunk_id'], 'score': r['score'], 'method': 'keyword'} for r in results]

    def _graph_retrieve(self, entities: List[str]) -> List[Dict]:  # [新增]
        """图谱检索"""
        all_chunks = []
        for entity_id in entities:
            chunks = self.graph_retriever.retrieve_by_entity(
                entity_id,
                hop_depth=2,
                top_k=self.retrieval_top_k // len(entities)
            )
            all_chunks.extend(chunks)

        # 归一化分数
        for chunk in all_chunks:
            chunk['method'] = 'graph'
            chunk['score'] = 0.8  # 默认图谱分数

        return all_chunks

    def _fuse_results(
        self,
        vector_results: List[Dict],
        keyword_results: List[Dict],
        graph_results: List[Dict]
    ) -> List[Dict]:  # [修改]
        """
        结果融合（使用RRF - Reciprocal Rank Fusion）

        RRF公式：score = Σ(weight / (k + rank))
        """
        k = 60  # RRF常数
        fused_scores = {}

        # 融合向量检索结果
        for rank, result in enumerate(vector_results):
            chunk_id = result['chunk_id']
            score = self.weights['vector'] / (k + rank + 1)
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + score

        # 融合关键字检索结果 [新增]
        for rank, result in enumerate(keyword_results):
            chunk_id = result['chunk_id']
            score = self.weights['keyword'] / (k + rank + 1)
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + score

        # 融合图谱检索结果 [新增]
        for rank, result in enumerate(graph_results):
            chunk_id = result['chunk_id']
            score = self.weights['graph'] / (k + rank + 1)
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + score

        # 按融合分数排序
        sorted_results = sorted(
            fused_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [{'chunk_id': cid, 'fused_score': score} for cid, score in sorted_results]
```

---

### 2.8 上下文增强模块 [新增]

**文件路径**: `backend/app/services/user_interaction/context_enricher/`

**功能**: 使用图谱信息增强检索到的上下文

**实现思路**:

```python
# context_enricher.py

class ContextEnricher:
    """上下文增强器"""

    def __init__(self, graph_builder: KnowledgeGraphBuilder):
        self.graph_builder = graph_builder

    def enrich(
        self,
        chunks: List[Dict],
        entities: List[str]
    ) -> List[Dict]:
        """
        使用图谱信息增强chunks

        Args:
            chunks: 检索到的chunks
            entities: 相关实体

        Returns:
            增强后的chunks
        """
        enriched_chunks = []

        for chunk in chunks:
            enriched_chunk = chunk.copy()

            # 获取chunk中实体的关系信息
            entity_relations = self._get_entity_relations(
                chunk.get('entities', []),
                entities
            )

            # 构建增强上下文
            if entity_relations:
                enrichment = self._build_enrichment_context(entity_relations)
                enriched_chunk['graph_enrichment'] = enrichment

            enriched_chunks.append(enriched_chunk)

        return enriched_chunks

    def _get_entity_relations(
        self,
        chunk_entities: List[str],
        query_entities: List[str]
    ) -> List[Dict]:
        """获取实体间的关系信息"""
        graph = self.graph_builder.graph
        relations = []

        for chunk_ent in chunk_entities:
            for query_ent in query_entities:
                # 查找两个实体间的关系
                if graph.has_edge(chunk_ent, query_ent):
                    edge_data = graph.get_edge_data(chunk_ent, query_ent)
                    relations.append({
                        'source': chunk_ent,
                        'target': query_ent,
                        'relation': edge_data.get('relation_type', ''),
                        'evidence': edge_data.get('evidence', '')
                    })

        return relations

    def _build_enrichment_context(self, relations: List[Dict]) -> str:
        """构建增强上下文文本"""
        if not relations:
            return ""

        context_parts = []
        for rel in relations:
            context_parts.append(
                f"{rel['source']} {rel['relation']} {rel['target']} "
                f"（证据：{rel['evidence']}）"
            )

        return "[相关知识背景] " + "; ".join(context_parts)
```

---

## 三、数据结构设计

### 3.1 实体数据结构 [新增]

```python
# 实体表（SQLite）
CREATE TABLE entities (
    entity_id TEXT PRIMARY KEY,
    text TEXT NOT NULL,              # 实体文本
    type TEXT NOT NULL,              # 实体类型
    chunk_id TEXT NOT NULL,          # 所属chunk
    doc_id TEXT NOT NULL,            # 所属文档
    confidence REAL,                 # 置信度
    metadata TEXT,                   # JSON格式的元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id),
    FOREIGN KEY (doc_id) REFERENCES files(id)
);
```

### 3.2 关系数据结构 [新增]

```python
# 关系表（SQLite）
CREATE TABLE relations (
    relation_id TEXT PRIMARY KEY,
    source_entity TEXT NOT NULL,     # 源实体ID
    target_entity TEXT NOT NULL,     # 目标实体ID
    relation_type TEXT NOT NULL,     # 关系类型
    evidence TEXT,                   # 支持证据
    chunk_id TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_entity) REFERENCES entities(entity_id),
    FOREIGN KEY (target_entity) REFERENCES entities(entity_id)
);
```

### 3.3 Chunk结构扩展 [修改]

```python
# 原有chunk结构新增字段
{
    "chunk_id": "doc_001_1",
    "order": 1,
    "doc_id": "doc_001",
    "title_path": ["第一章 概述"],
    "text": "完整文本内容...",
    "page": 12,
    "type": "text",
    "bbox": [x0, y0, x1, y1],
    "length": 62,
    "embedding": [0.12, 0.34, ...],

    # [新增] 图谱相关字段
    "entities": ["ent_001", "ent_002"],        # chunk中包含的实体ID列表
    "entity_count": 2,                         # 实体数量

    # [新增] 关键字相关字段
    "keywords": ["关键词1", "关键词2"],         # 提取的关键字
    "keyword_count": 2                         # 关键字数量
}
```

---

## 四、API 接口调整

### 4.1 聊天接口调整 [修改]

**文件**: `backend/app/api/chat.py`

```python
@api_bp.route('/chat/stream', methods=['POST'])
def chat_stream():
    """
    流式聊天接口

    Request body (调整):
        {
            "message": "用户问题",
            "conversation_history": [...],
            "top_k": 5,
            "retrieval_top_k": 20,
            "retrieval_config": {          # [新增] 检索配置
                "enable_vector": true,     # 启用向量检索
                "enable_keyword": true,    # 启用关键字检索
                "enable_graph": true,      # 启用图谱检索
                "vector_weight": 0.5,      # 向量检索权重
                "keyword_weight": 0.3,     # 关键字检索权重
                "graph_weight": 0.2        # 图谱检索权重
            }
        }
    """
```

### 4.2 新增图谱相关接口 [新增]

**文件**: `backend/app/api/graph.py` (新建)

```python
@api_bp.route('/graph/entities/<doc_id>', methods=['GET'])
def get_document_entities(doc_id: str):
    """获取文档的所有实体"""

@api_bp.route('/graph/relations/<doc_id>', methods=['GET'])
def get_document_relations(doc_id: str):
    """获取文档的所有关系"""

@api_bp.route('/graph/entity_neighbors', methods=['POST'])
def get_entity_neighbors():
    """获取实体的邻居节点"""

@api_bp.route('/graph/path', methods=['POST'])
def find_entity_path():
    """查找两个实体之间的关系路径"""
```

---

## 五、依赖包更新

### requirements.txt 新增依赖 [修改]

```txt
# 现有依赖
flask==3.0.0
# ... 其他现有依赖

# [新增] 图谱相关
networkx==3.2.1              # 图数据处理
neo4j==5.15.0               # Neo4j驱动（可选）

# [新增] 关键字检索相关
jieba==0.42.1               # 中文分词
rank-bm25==0.2.2            # BM25算法

# [新增] 数据处理
numpy>=1.24.0               # 数值计算
```

---

## 六、实施步骤

### 阶段一：基础架构搭建（1-2周）

1. [新增] 创建实体抽取模块
2. [新增] 创建关系抽取模块
3. [新增] 创建知识图谱构建模块
4. [新增] 创建关键字索引模块

### 阶段二：在线检索升级（1-2周）

1. [新增] 创建问题实体识别模块
2. [新增] 创建图谱检索模块
3. [新增] 创建上下文增强模块
4. [修改] 升级混合检索模块

### 阶段三：数据迁移与测试（1周）

1. [修改] 修改文档处理流程，集成新模块
2. [新增] 添加数据迁移脚本
3. [新增] 添加单元测试
4. [修改] API接口调整

### 阶段四：前端适配（可选）

1. [新增] 图谱可视化组件（使用D3.js或ECharts）
2. [新增] 检索结果来源标注（向量/关键字/图谱）

---

## 七、性能优化建议

### 7.1 实体/关系抽取优化

- **批量抽取**: 对多个chunks合并后统一抽取，减少API调用
- **缓存机制**: 对相同文本的抽取结果进行缓存
- **异步处理**: 实体和关系抽取使用异步任务队列

### 7.2 检索优化

- **并行检索**: 向量、关键字、图谱检索并行执行
- **结果缓存**: 对常见问题的检索结果进行缓存
- **索引预热**: 系统启动时预加载常用索引

### 7.3 存储优化

- **图谱分区**: 按文档对图谱进行分区存储
- **增量更新**: 文档更新时只更新受影响的图谱部分

---

## 八、模型选择总结

| 任务 | 推荐模型（硅基流动） | 说明 |
|------|---------------------|------|
| 实体抽取 | `Qwen/Qwen2.5-7B-Instruct` | 性价比高，结构化输出稳定 |
| 关系抽取 | `deepseek-ai/DeepSeek-V3` | 推理能力强，关系识别准确 |
| 实体识别（问题） | `Qwen/Qwen2.5-7B-Instruct` | 快速响应，适合在线场景 |
| 图谱路径推理 | `deepseek-ai/DeepSeek-V3` | 复杂推理任务 |

---

## 九、配置示例

### 新增配置项 (.env.example)

```env
# [新增] 图谱配置
GRAPH_STORAGE_TYPE=memory          # memory / neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# [新增] 检索权重配置
VECTOR_WEIGHT=0.5
KEYWORD_WEIGHT=0.3
GRAPH_WEIGHT=0.2

# [新增] 实体抽取配置
ENTITY_EXTRACTION_BATCH_SIZE=5     # 每次处理的chunk数量
ENTITY_CONFIDENCE_THRESHOLD=0.7    # 实体置信度阈值

# [新增] 图谱检索配置
GRAPH_HOP_DEPTH=2                  # 默认跳数
GRAPH_MAX_NEIGHBORS=20             # 最大邻居数量
```

---

## 十、预期效果

### 检索准确性提升

- **关键字检索**: 解决专有名词、缩写的匹配问题
- **图谱检索**: 发现隐含关系，提供多跳关联信息
- **混合检索**: 综合多种信号，提高召回率和准确率

### 答案质量提升

- **上下文增强**: 通过图谱关系补充背景信息
- **关系推理**: 支持复杂关系问题的回答
- **溯源清晰**: 可展示实体关系路径

### 适用场景扩展

- **知识密集型问答**: 技术文档、百科知识
- **关系推理**: 人物关系、组织结构、产品关系
- **多跳问答**: 需要跨文档关联的问题
