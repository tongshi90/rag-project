---
name: add_skill
description: "Query knowledge base using RAG (Retrieval-Augmented Generation) platform. Use when: user asks for knowledge base information, needs to query specific documents, or requests involving knowledge retrieval or document search."
homepage: https://github.com/openclaw/openclaw
metadata: {"openclaw": {"emoji": "🔍", "requires": {"bins": ["uv"]}}}

---

# add_skill - Knowledge Base Search

Query your RAG platform knowledge base with natural language questions.

## Basic Query

```bash
uv run {baseDir}/scripts/main.py --question "你的问题"
```

## Advanced Options

Query with specific document:

```bash
uv run {baseDir}/scripts/main.py --question "问题" --doc-id "doc_123"
```

Custom API endpoint:

```bash
uv run {baseDir}/scripts/main.py --question "问题" --api-url "http://localhost:8080"
```

Custom timeout:

```bash
uv run {baseDir}/scripts/main.py --question "问题" --timeout 180
```

## Usage Examples

**User:** "What is the RAG platform?"
**Execute:** `uv run {baseDir}/scripts/main.py --question "What is the RAG platform?"`

**User:** "How to upload documents?"
**Execute:** `uv run {baseDir}/scripts/main.py --question "How to upload documents?"`

## Notes

- The script outputs the RAG response directly
- Supports Chinese and English queries
- Requires RAG service to be running and accessible
- Timeout errors indicate the RAG service is down or slow