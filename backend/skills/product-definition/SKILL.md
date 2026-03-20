---
name: product-definition
description: "产品定义技能：辅助需求分析、产品设计、PRD 撰写、竞品分析。适用于：产品经理进行产品规划、需求整理、文档撰写等场景。"
metadata: {"openclaw": {"emoji": "📋", "requires": {"bins": ["uv"]}}}


---

# 产品定义 - 产品设计助手

智能辅助产品经理完成从需求分析到 PRD 撰写的全流程工作。

## 工作流程

产品定义技能采用分步交互式工作流，每步生成后需要您确认后再继续：

```
1. 需求对话 → 2. 需求分析 → 3. 产品设计 → 4. PRD 撰写 → 5. 竞品分析
                 [确认]         [确认]         [确认]         [确认]
```

## 基础使用

### 启动对话模式

```bash
uv run {baseDir}/scripts/main.py
```

进入交互模式，系统会引导您完成产品定义流程。

### 指定阶段

从特定阶段开始（需要已提供需求上下文）：

```bash
# 直接进入需求分析（使用已有需求描述）
uv run {baseDir}/scripts/main.py --stage analysis --requirement "用户需要一个在线笔记应用"

# 直接进入产品设计
uv run {baseDir}/scripts/main.py --stage design --requirement "在线笔记应用" --analysis-file "./analysis.json"

# 生成 PRD
uv run {baseDir}/scripts/main.py --stage prd --analysis-file "./analysis.json" --design-file "./design.json"

# 竞品分析
uv run {baseDir}/scripts/main.py --stage competitor --prd-file "./prd.json"
```

## 使用示例

### 完整流程示例

```
[用户] uv run {baseDir}/scripts/main.py

[系统] 请描述您的产品需求或想法：
[用户] 我想要做一个面向程序员的知识管理工具，支持代码片段管理...

[系统] === 需求分析 ===
目标用户：程序员、开发者
核心痛点：...
功能优先级：...

确认是否继续产品设计？(y/n/修改):
[用户] y

[系统] === 产品设计 ===
产品架构：...
功能模块：...
交互流程：...

确认是否继续撰写 PRD？(y/n/修改):
[用户] n
[用户] 请把功能模块拆分更细一点
...
```

### 使用 LLM 配置

使用 OpenClaw 绑定的模型配置：

```bash
uv run {baseDir}/scripts/main.py --model-url "$OPENCLAW_MODEL_URL" --api-key "$OPENCLAW_API_KEY" --model "$OPENCLAW_MODEL_NAME"
```

## 各阶段说明

| 阶段 | 输入 | 输出 | 说明 |
|------|------|------|------|
| 需求对话 | 用户自然语言描述 | 结构化需求 | 理解并整理用户需求 |
| 需求分析 | 需求描述 | 需求分析报告 | 目标用户、痛点、功能优先级 |
| 产品设计 | 需求分析 | 产品设计方案 | 架构、模块、交互、技术选型 |
| PRD 撰写 | 设计方案 | PRD 文档 | 完整产品需求文档 |
| 竞品分析 | PRD/需求 | 竞品分析报告 | 市场对比、差异化分析 |

## 输出文件

每次确认后，脚本会生成对应的 JSON 文件：

- `requirement.json` - 结构化需求
- `analysis.json` - 需求分析报告
- `design.json` - 产品设计方案
- `prd.json` - PRD 文档
- `competitor.json` - 竞品分析报告

## 注意事项

- 确保已配置有效的 LLM API 密钥
- 每个阶段需要您确认后才会进入下一阶段
- 可随时输入 `quit` 或 `exit` 退出
- 支持对当前输出提出修改建议

## 目标用户与使用场景

| 使用场景       | 目标用户             |
| -------------- | -------------------- |
| 产品定义与设计 | 产品经理             |
| 需求分析       | 产品经理、业务分析师 |
| PRD 撰写       | 产品经理             |
| 竞品分析       | 产品经理、市场人员   |
