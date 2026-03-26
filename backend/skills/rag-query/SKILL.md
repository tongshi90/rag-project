---
name: rag-query
description: "使用 RAG（检索增强生成）平台查询知识库。适用于：用户询问知识库信息、需要查询特定文档、或涉及知识检索和文档搜索的请求。"
metadata: {"openclaw": {"emoji": "🔍", "requires": {"bins": ["uv"]}}}


---

# RAG 查询 - 知识库搜索

使用自然语言问题查询您的 RAG 平台知识库。

## 基础查询

```bash
uv run {baseDir}/scripts/main.py --question "你的问题"
```

## 高级选项

查询指定知识库：

```bash
uv run {baseDir}/scripts/main.py --question "问题" --kb-id "kb_123"
```

自定义 API 端点：

```bash
uv run {baseDir}/scripts/main.py --question "问题" --api-url "http://localhost:8080"
```

自定义超时时间：

```bash
uv run {baseDir}/scripts/main.py --question "问题" --timeout 180
```

## 使用示例

**用户：** "什么是 RAG 平台？"
**执行：** `uv run {baseDir}/scripts/main.py --question "什么是 RAG 平台？"`

**用户：** "如何上传文档？"
**执行：** `uv run {baseDir}/scripts/main.py --question "如何上传文档？"`

## 注意事项

- 脚本直接输出 RAG 响应结果
- 支持中英文查询
- 需要 RAG 服务处于运行状态且可访问
- 超时错误表明 RAG 服务未运行或响应缓慢

## 目标用户与使用场景

| 使用场景       | 目标用户             |
| -------------- | -------------------- |
| 经营分析       | ST成员               |
| 解决方案       | 解决方案专家         |
| 驱动代码评审   | -                    |
| 内核代码评审   | -                    |
| 项目跟踪       | 项目经理（自动收集） |
| PMT运作        | PMT成员              |
| 产品定义与设计 | 产品经理             |
| 人才画像Skill  | HR、AT成员           |