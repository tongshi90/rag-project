---
name: rag-query
description: "Query knowledge base using RAG (Retrieval-Augmented Generation) platform. Use when: user asks for knowledge base information, needs to query specific documents, or requests involving knowledge retrieval or document search."
homepage: https://github.com/openclaw/openclaw
metadata: {"openclaw": {"emoji": "🔍", "requires": {"bins": ["uv"]}}}

---

# RAG Query - Knowledge Base Search

Query your RAG platform knowledge base with natural language questions.

## Basic Query

```bash
uv run {baseDir}/main.py --question "你的问题"
```

## Advanced Options

Query with specific document:

```bash
uv run {baseDir}/main.py --question "问题" --doc-id "doc_123"
```

Custom API endpoint:

```bash
uv run {baseDir}/main.py --question "问题" --api-url "http://localhost:8080"
```

Custom timeout:

```bash
uv run {baseDir}/main.py --question "问题" --timeout 180
```

## Usage Examples

**User:** "What is the RAG platform?"
**Execute:** `uv run {baseDir}/main.py --question "What is the RAG platform?"`

**User:** "How to upload documents?"
**Execute:** `uv run {baseDir}/main.py --question "How to upload documents?"`

## Notes

- The script outputs the RAG response directly
- Supports Chinese and English queries
- Requires RAG service to be running and accessible
- Timeout errors indicate the RAG service is down or slow

## Target Audience & Use Cases

| Use Case | Target Audience |
|----------|-----------------|
| 经营分析 | ST成员 |
| 解决方案 | 解决方案专家 |
| 驱动代码评审 | - |
| 内核代码评审 | - |
| 项目跟踪 | 项目经理（自动收集） |
| PMT运作 | PMT成员 |
| 产品定义与设计 | 产品经理 |
| 人才画像Skill | HR、AT成员 |