---
name: dify-knowledge-retrieval
description: Dify 知识库检索工具。根据用户查询从 Dify 知识库中检索相关内容。使用场景：(1) 查询知识库中的信息 (2) 基于知识库内容回答问题 (3) 测试知识库检索效果 (4) 查看知识库列表。需要提供 Dify API 地址、知识库 ID 和 API Key。
重要：
1. 检索到内容后，**直接返回原文，不要进行精简**。可以增加你的总结结论，但必须先展示完整的原文内容。
2. **不要写死知识库 ID**。必须先调用 list 命令获取所有知识库，然后根据用户问题的关键词匹配最相关的知识库，再进行检索。

---

# Dify 知识库工具

支持两种操作：

1. **检索知识库内容** - 从指定知识库查询相关内容
2. **列出知识库** - 查看账户下所有知识库

## 检索流程（重要）

**每次检索前必须执行以下步骤：**

1. **先列出所有知识库** - 调用 `list` 命令获取知识库列表
2. **根据问题匹配知识库** - 根据用户问题的关键词，从知识库名称和描述中找出最相关的知识库
3. **执行检索** - 使用匹配到的知识库 ID 进行检索

**匹配逻辑示例：**

- 问"打卡规则" → 匹配"员工手册"知识库
- 问"在鸿云平台" → 匹配"在鸿云AI平台私有知识文档"知识库
- 问"展台/展厅" → 匹配"展台资料"或"资料"知识库
- 无法确定时，尝试检索多个相关知识库

## 默认配置

脚本会自动从 `~/.opencloak/workspace/TOOLS.md` 读取默认配置：

```markdown
## Dify 知识库 (Dify Knowledge Retrieval)

公共环境配置（默认使用的知识库）：

- **API 地址**: http://192.168.18.77:18020/v1
- **API Key**: dataset-Thr9V6L6LqrSr3cPiv96931g
- **Dataset ID**: 68984a29-f2c0-4636-b838-7714504cc883
```

## 快速开始

### 检索知识库内容

```bash
# 使用默认配置（从 TOOLS.md 读取）
python scripts/retrieve.py retrieve --query "查询内容"

# 手动指定配置
python scripts/retrieve.py retrieve \
  --api-url "http://192.168.18.77:18020/v1" \
  --api-key "dataset-xxx" \
  --dataset-id "xxx" \
  --query "查询内容"
```

### 列出所有知识库

```bash
# 使用默认配置
python scripts/retrieve.py list
```

## 子命令说明

### retrieve - 检索知识库

| 参数                | 必需 | 说明                                |
| ------------------- | ---- | ----------------------------------- |
| `--api-url`         | 否   | Dify API 地址 (默认: 读取 TOOLS.md) |
| `--api-key`         | 否   | Dify API Key (默认: 读取 TOOLS.md)  |
| `--dataset-id`      | 否   | 知识库 ID (默认: 读取 TOOLS.md)     |
| `--query`           | 是   | 搜索查询文本                        |
| `--top-k`           | 否   | 返回结果数量 (默认: 3)              |
| `--search-method`   | 否   | 搜索方法 (默认: hybrid_search)      |
| `--score-threshold` | 否   | 分数阈值过滤                        |
| `--json`            | 否   | 输出原始 JSON                       |

### list - 列出知识库

| 参数        | 必需 | 说明                                |
| ----------- | ---- | ----------------------------------- |
| `--api-url` | 否   | Dify API 地址 (默认: 读取 TOOLS.md) |
| `--api-key` | 否   | Dify API Key (默认: 读取 TOOLS.md)  |

## 搜索方法

- `hybrid_search`: 混合搜索 (语义 + 关键词)
- `semantic_search`: 语义搜索
- `full_text_search`: 全文搜索
- `keyword_search`: 关键词搜索

## 输出格式

### retrieve 结果

返回 JSON 数组，每项包含：

- `content`: 段落内容
- `score`: 相关度分数
- `segment.document.name`: 文档名称
- `segment.document.id`: 文档 ID

### list 结果

格式化输出的知识库列表，包含：

- ID
- 名称
- 描述
- 文档数、字数
- 创建时间

## 使用示例

```bash
# 检索（使用默认配置）
python scripts/retrieve.py retrieve --query "什么是机器学习"

# 检索（指定参数）
python scripts/retrieve.py retrieve \
  --query "Python 教程" \
  --top-k 5 \
  --search-method semantic_search

# 列出所有知识库
python scripts/retrieve.py list
```

## 认证

所有请求需要在 `Header` 中包含 API Key：

```
Authorization: Bearer {API_KEY}
```