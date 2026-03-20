#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
# ]
# ///
"""
Product Definition Skill - Interactive product design assistant.

This skill helps product managers with:
- Requirement analysis
- Product design
- PRD writing
- Competitor analysis

Usage:
    python main.py                           # Interactive mode
    python main.py --stage analysis --requirement "Build a note-taking app"
    python main.py --stage prd --analysis-file "./analysis.json"
"""

import argparse
import io
import json
import os
import sys
from pathlib import Path
from typing import Optional, Any, Tuple

# Force UTF-8 output for Chinese/English support
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# OpenClaw 标准技能入口
from openclaw import llm  # 直接调用平台绑定的大模型

# Stage definitions
STAGES = ["dialogue", "analysis", "design", "prd", "competitor"]

# Output file names (JSON and Markdown versions)
OUTPUT_FILES = {
    "dialogue": ("requirement.json", "requirement.md"),
    "analysis": ("analysis.json", "analysis.md"),
    "design": ("design.json", "design.md"),
    "prd": ("prd.json", "prd.md"),
    "competitor": ("competitor.json", "competitor.md")
}


def call_llm(prompt: str, system_prompt: Optional[str] = None) -> str:
    """调用 LLM 返回文本结果。"""
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    response = llm.chat(full_prompt)
    return response.strip()


def call_llm_with_json(prompt: str, system_prompt: Optional[str] = None) -> Tuple[str, dict]:
    """调用 LLM 并同时返回 Markdown 和 JSON 格式结果。"""
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

    # 要求同时输出 Markdown 和 JSON
    json_prompt = f"""{full_prompt}

**输出要求：**
1. 首先输出 Markdown 格式的文档（用户可读）
2. 然后输出 JSON 格式的数据（程序使用）
3. 两者之间用分隔线 `---JSON---` 分隔
4. JSON 部分不要包含任何其他文字，只输出纯 JSON

示例格式：
# Markdown 标题
内容...

---JSON---
{{"key": "value"}}
"""

    response = llm.chat(json_prompt).strip()

    # 分割 Markdown 和 JSON
    if "---JSON---" in response:
        parts = response.split("---JSON---", 1)
        md_content = parts[0].strip()
        json_content = parts[1].strip()

        # 清理 JSON 中的代码块标记
        if json_content.startswith("```json"):
            json_content = json_content[7:]
        if json_content.startswith("```"):
            json_content = json_content[3:]
        if json_content.endswith("```"):
            json_content = json_content[:-3]
        json_content = json_content.strip()

        try:
            data = json.loads(json_content)
            return md_content, data
        except json.JSONDecodeError:
            # JSON 解析失败，尝试补救
            return md_content, {"error": "JSON parse failed", "markdown": md_content}
    else:
        # 没有找到分隔符，全部当作 Markdown
        return response, {"markdown_only": True}


# System prompts for each stage (Markdown 输出格式)
SYSTEM_PROMPTS = {
    "analysis": """你是一位资深产品经理，擅长需求分析。请根据用户的描述，生成结构化的需求分析报告。

请按以下 Markdown 格式输出：

# 需求分析报告

## 1. 目标用户
- 用户群体1：描述
- 用户群体2：描述

## 2. 用户痛点
- 痛点1：详细描述
- 痛点2：详细描述
- 痛点3：详细描述

## 3. 核心功能
| 功能名称 | 优先级 | 功能描述 |
|---------|--------|----------|
| 功能1   | P0     | 描述     |
| 功能2   | P1     | 描述     |

## 4. 成功指标
- 指标1：具体数值/目标
- 指标2：具体数值/目标

## 5. 约束条件
- 约束1
- 约束2

JSON 格式要求（用于程序解析）：
{
  "target_users": [{"group": "用户群体", "description": "描述"}],
  "pain_points": [{"point": "痛点", "description": "详细描述"}],
  "core_features": [{"name": "功能名", "priority": "P0/P1/P2", "description": "描述"}],
  "success_metrics": [{"metric": "指标", "target": "目标"}],
  "constraints": ["约束条件"]
}""",

    "design": """你是一位资深产品设计师，擅长产品设计。请根据需求分析，生成详细的产品设计方案。

请按以下 Markdown 格式输出：

# 产品设计方案

## 1. 产品愿景
简述产品的长远愿景和核心价值主张

## 2. 技术架构
### 前端技术栈
- 技术选型1
- 技术选型2

### 后端技术栈
- 技术选型1
- 技术选型2

### 数据库选型
- 数据库1：用途
- 数据库2：用途

## 3. 功能模块
### 模块1：名称
- **描述**：模块功能说明
- **核心功能**：
  - 功能1
  - 功能2
- **依赖模块**：其他模块

### 模块2：名称
...

## 4. 用户流程
1. 步骤一
2. 步骤二
3. 步骤三

## 5. 界面风格
描述产品的视觉和交互风格

JSON 格式要求：
{
  "product_vision": "愿景",
  "architecture": {"frontend": [], "backend": [], "database": []},
  "modules": [{"name": "名称", "description": "描述", "features": [], "dependencies": []}],
  "user_flow": ["步骤"],
  "ui_style": "风格描述"
}""",

    "prd": """你是一位资深产品经理，擅长撰写PRD文档。请根据需求分析和产品设计，生成完整的PRD文档。

请按以下 Markdown 格式输出：

# 产品需求文档 (PRD)

## 文档信息
- **标题**：xxx产品PRD
- **版本**：v1.0.0
- **日期**：2024-xx-xx

## 1. 项目背景
描述项目的背景和起因

## 2. 产品目标
- 目标1
- 目标2

## 3. 范围界定
### 包含范围
- 功能1
- 功能2

### 不包含范围
- 功能1
- 功能2

## 4. 功能需求
### FR-001：功能标题
- **优先级**：P0
- **描述**：功能详细描述
- **验收标准**：
  - [ ] 标准1
  - [ ] 标准2

### FR-002：功能标题
...

## 5. 非功能需求
### 性能要求
- 要求1
- 要求2

### 安全要求
- 要求1
- 要求2

### 扩展性要求
- 要求1

## 6. 接口规格
| 端点 | 方法 | 描述 |
|------|------|------|
| /api/xxx | POST | 描述 |

## 7. 里程碑
| 阶段 | 时间规划 | 交付物 |
|------|----------|--------|
| 阶段1 | Q1 2024 | 交付物1 |
| 阶段2 | Q2 2024 | 交付物2 |

JSON 格式要求：
{
  "document_info": {"title": "", "version": "", "date": ""},
  "background": "背景",
  "objectives": ["目标"],
  "scope": {"in_scope": [], "out_of_scope": []},
  "functional_requirements": [{"id": "FR-001", "title": "", "description": "", "acceptance_criteria": [], "priority": "P0"}],
  "non_functional_requirements": {"performance": [], "security": [], "scalability": []},
  "api_specifications": [{"endpoint": "", "method": "", "description": ""}],
  "milestones": [{"phase": "", "timeline": "", "deliverables": []}]
}""",

    "competitor": """你是一位资深市场分析师，擅长竞品分析。请根据产品PRD，生成竞品分析报告。

请按以下 Markdown 格式输出：

# 竞品分析报告

## 1. 市场概况
描述当前市场环境和趋势

## 2. 竞品分析
### 竞品1：名称
- **类型**：直接竞品/间接竞品
- **市场定位**：定位描述
- **优势**：
  - 优势1
  - 优势2
- **劣势**：
  - 劣势1
  - 劣势2

### 竞品2：名称
...

## 3. 差异化分析
### 我们的优势
- 优势1
- 优势2

### 独特功能
- 功能1
- 功能2

### 竞争策略
描述我们的竞争策略

## 4. 市场机会
- 机会1
- 机会2

## 5. 潜在威胁
- 威胁1
- 威胁2

JSON 格式要求：
{
  "market_overview": "市场概况",
  "competitors": [{"name": "名称", "type": "类型", "strengths": [], "weaknesses": [], "market_position": "定位"}],
  "differentiation": {"our_advantages": [], "unique_features": [], "competitive_strategy": "策略"},
  "market_opportunities": [],
  "threats": []
}"""
}


def get_user_input(prompt: str) -> str:
    """Get user input from stdin."""
    try:
        return input(prompt).strip()
    except EOFError:
        return ""
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)


def confirm_action(message: str) -> bool:
    """Ask user for confirmation."""
    while True:
        response = get_user_input(f"{message} (y/n/quit): ").lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        elif response in ['q', 'quit', 'exit']:
            print("\nExiting...")
            sys.exit(0)
        else:
            print("Please enter 'y' (yes) or 'n' (no), or 'quit' to exit.")


def save_outputs(data: dict, markdown: str, json_file: str, md_file: str) -> None:
    """同时保存 JSON 和 Markdown 文件。"""
    # 保存 JSON
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[JSON Saved] {json_file}")

    # 保存 Markdown
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(markdown)
    print(f"[MD Saved] {md_file}")


def load_json(filepath: str) -> Optional[dict]:
    """Load data from JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[Error] File not found: {filepath}")
        return None
    except json.JSONDecodeError as e:
        print(f"[Error] Invalid JSON in {filepath}: {e}")
        return None


def load_markdown(filepath: str) -> Optional[str]:
    """Load data from Markdown file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"[Error] File not found: {filepath}")
        return None


def stage_dialogue(requirement: Optional[str] = None, output_dir: str = ".") -> Tuple[dict, str]:
    """Stage 1: Collect and structure user requirement."""
    print("\n" + "="*60)
    print("Stage 1: Requirement Collection")
    print("="*60)

    if not requirement:
        print("\nPlease describe your product requirement or idea:")
        print("(Enter 'quit' to exit)")
        requirement = get_user_input("\n> ")

    if not requirement or requirement.lower() in ['quit', 'exit']:
        print("\nExiting...")
        sys.exit(0)

    result = {
        "raw_input": requirement,
        "structured": True
    }

    markdown = f"""# 需求收集

## 用户输入
{requirement}

## 状态
✅ 需求已收集
"""

    json_file, md_file = OUTPUT_FILES["dialogue"]
    json_path = os.path.join(output_dir, json_file)
    md_path = os.path.join(output_dir, md_file)
    save_outputs(result, markdown, json_path, md_path)

    print("\n" + "-"*60)
    print("Requirement captured:")
    print(f"  {requirement[:200]}{'...' if len(requirement) > 200 else ''}")
    print("-"*60)

    return result, markdown


def stage_analysis(
    requirement: str,
    output_dir: str = "."
) -> Tuple[dict, str]:
    """Stage 2: Generate requirement analysis."""
    print("\n" + "="*60)
    print("Stage 2: Requirement Analysis")
    print("="*60)

    print("\n[Generating requirement analysis...]")

    prompt = f"""请分析以下产品需求，生成详细的需求分析报告：

用户需求：
{requirement}

请按照系统要求的格式输出。"""

    markdown, analysis = call_llm_with_json(prompt, SYSTEM_PROMPTS["analysis"])

    json_file, md_file = OUTPUT_FILES["analysis"]
    json_path = os.path.join(output_dir, json_file)
    md_path = os.path.join(output_dir, md_file)
    save_outputs(analysis, markdown, json_path, md_path)

    print("\n" + "-"*60)
    print(markdown)
    print("-"*60)

    return analysis, markdown


def stage_design(
    requirement: str,
    analysis: dict,
    output_dir: str = "."
) -> Tuple[dict, str]:
    """Stage 3: Generate product design."""
    print("\n" + "="*60)
    print("Stage 3: Product Design")
    print("="*60)

    print("\n[Generating product design...]")

    # 从分析中提取关键信息作为上下文
    analysis_md = load_markdown(os.path.join(output_dir, OUTPUT_FILES["analysis"][1]))

    prompt = f"""请根据以下需求和分析，生成详细的产品设计方案：

用户需求：
{requirement}

需求分析：
{analysis_md if analysis_md else json.dumps(analysis, ensure_ascii=False, indent=2)}

请按照系统要求的格式输出。"""

    markdown, design = call_llm_with_json(prompt, SYSTEM_PROMPTS["design"])

    json_file, md_file = OUTPUT_FILES["design"]
    json_path = os.path.join(output_dir, json_file)
    md_path = os.path.join(output_dir, md_file)
    save_outputs(design, markdown, json_path, md_path)

    print("\n" + "-"*60)
    print(markdown)
    print("-"*60)

    return design, markdown


def stage_prd(
    requirement: str,
    analysis: dict,
    design: dict,
    output_dir: str = "."
) -> Tuple[dict, str]:
    """Stage 4: Generate PRD document."""
    print("\n" + "="*60)
    print("Stage 4: PRD Document")
    print("="*60)

    print("\n[Generating PRD document...]")

    # 读取之前生成的 Markdown 文件作为上下文
    analysis_md = load_markdown(os.path.join(output_dir, OUTPUT_FILES["analysis"][1]))
    design_md = load_markdown(os.path.join(output_dir, OUTPUT_FILES["design"][1]))

    prompt = f"""请根据以下信息，生成完整的PRD文档：

用户需求：
{requirement}

需求分析：
{analysis_md if analysis_md else json.dumps(analysis, ensure_ascii=False, indent=2)}

产品设计：
{design_md if design_md else json.dumps(design, ensure_ascii=False, indent=2)}

请按照系统要求的格式输出。"""

    markdown, prd = call_llm_with_json(prompt, SYSTEM_PROMPTS["prd"])

    json_file, md_file = OUTPUT_FILES["prd"]
    json_path = os.path.join(output_dir, json_file)
    md_path = os.path.join(output_dir, md_file)
    save_outputs(prd, markdown, json_path, md_path)

    print("\n" + "-"*60)
    print(markdown)
    print("-"*60)

    return prd, markdown


def stage_competitor(
    prd: dict,
    output_dir: str = "."
) -> Tuple[dict, str]:
    """Stage 5: Generate competitor analysis."""
    print("\n" + "="*60)
    print("Stage 5: Competitor Analysis")
    print("="*60)

    print("\n[Generating competitor analysis...]")

    prd_md = load_markdown(os.path.join(output_dir, OUTPUT_FILES["prd"][1]))

    prompt = f"""请根据以下PRD，生成竞品分析报告：

PRD文档：
{prd_md if prd_md else json.dumps(prd, ensure_ascii=False, indent=2)}

请按照系统要求的格式输出。"""

    markdown, competitor = call_llm_with_json(prompt, SYSTEM_PROMPTS["competitor"])

    json_file, md_file = OUTPUT_FILES["competitor"]
    json_path = os.path.join(output_dir, json_file)
    md_path = os.path.join(output_dir, md_file)
    save_outputs(competitor, markdown, json_path, md_path)

    print("\n" + "-"*60)
    print(markdown)
    print("-"*60)

    return competitor, markdown


def interactive_workflow(
    requirement: Optional[str] = None,
    output_dir: str = "."
) -> None:
    """Run interactive product definition workflow."""
    print("\n" + "="*60)
    print("Product Definition Assistant")
    print("="*60)

    # Stage 1: Dialogue
    _, requirement_md = stage_dialogue(requirement, output_dir)
    requirement_text = json.loads(load_json(os.path.join(output_dir, OUTPUT_FILES["dialogue"][0])) or {}).get("raw_input", requirement)

    # Stage 2: Analysis
    _, analysis_md = stage_analysis(requirement_text, output_dir)
    if not confirm_action("\n确认需求分析无误？继续产品设计？"):
        modification = get_user_input("请描述需要修改的内容（按 Enter 跳过）：")
        if modification:
            requirement_text = f"{requirement_text}\n\n用户修改意见：{modification}"
            _, analysis_md = stage_analysis(requirement_text, output_dir)
        if not confirm_action("\n继续产品设计？"):
            print("\n工作流已暂停。可使用 --stage design 恢复")
            return

    # Stage 3: Design
    _, design_md = stage_design(requirement_text, {}, output_dir)
    if not confirm_action("\n确认产品设计无误？继续撰写 PRD？"):
        print("\n工作流已暂停。可使用 --stage prd 恢复")
        return

    # Stage 4: PRD
    _, prd_md = stage_prd(requirement_text, {}, {}, output_dir)
    if not confirm_action("\n确认 PRD 无误？继续竞品分析？"):
        print("\n工作流已暂停。可使用 --stage competitor 恢复")
        return

    # Stage 5: Competitor Analysis
    stage_competitor({}, output_dir)

    print("\n" + "="*60)
    print("🎉 产品定义工作流全部完成！")
    print("="*60)
    print("\n生成的文件：")
    for stage_name, (json_file, md_file) in OUTPUT_FILES.items():
        print(f"  - {md_file} (Markdown 可读版本)")
        print(f"  - {json_file} (JSON 数据版本)")


# OpenClaw 标准技能入口 - 简单调用模式
def run(user_input: str) -> str:
    """
    产品定义技能的简单调用入口。
    用于 OpenClaw 直接调用场景，执行完整的产品定义流程。
    """
    output_dir = "."
    requirement_text = user_input

    # 执行各阶段
    _, requirement_md = stage_dialogue(requirement_text, output_dir)
    _, analysis_md = stage_analysis(requirement_text, output_dir)
    _, design_md = stage_design(requirement_text, {}, output_dir)
    _, prd_md = stage_prd(requirement_text, {}, {}, output_dir)
    _, competitor_md = stage_competitor({}, output_dir)

    # 返回完整的 Markdown 报告
    result = f"""# 产品定义报告

{analysis_md}

---

{design_md}

---

{prd_md}

---

{competitor_md}
"""
    return result


# 技能入口执行
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Product Definition Assistant - Interactive product design workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'user_query',
        nargs='?',
        help='Product requirement or idea (for simple invocation)'
    )
    parser.add_argument(
        '--stage', '-s',
        choices=STAGES,
        help='Start from specific stage'
    )
    parser.add_argument(
        '--requirement', '-r',
        help='Product requirement description'
    )
    parser.add_argument(
        '--analysis-file', '-a',
        help='Path to analysis.json file'
    )
    parser.add_argument(
        '--design-file', '-d',
        help='Path to design.json file'
    )
    parser.add_argument(
        '--prd-file', '-p',
        help='Path to prd.json file'
    )
    parser.add_argument(
        '--output-dir', '-o',
        default=".",
        help='Output directory for generated files (default: current directory)'
    )
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='%(prog)s 1.0.0'
    )

    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # OpenClaw 简单调用模式：直接传递用户查询
    if args.user_query and not args.stage:
        result = run(args.user_query)
        print(result)
        sys.exit(0)

    # 交互式模式或指定阶段模式
    if args.stage is None:
        # Full interactive workflow
        interactive_workflow(args.requirement, args.output_dir)
    elif args.stage == "dialogue":
        stage_dialogue(args.requirement, args.output_dir)
    elif args.stage == "analysis":
        if not args.requirement:
            print("[Error] --requirement is required for analysis stage")
            sys.exit(1)
        stage_analysis(args.requirement, args.output_dir)
    elif args.stage == "design":
        requirement = args.requirement or "Product design"
        stage_design(requirement, {}, args.output_dir)
    elif args.stage == "prd":
        requirement = args.requirement or "Product requirements document"
        stage_prd(requirement, {}, {}, args.output_dir)
    elif args.stage == "competitor":
        stage_competitor({}, args.output_dir)
