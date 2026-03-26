"""
Chunk 优化模块

这是文档处理流程的第三步，负责使用 LLM 分析异常 chunk 并给出合并/拆分建议。

使用方式：
    from app.services.document_processing.optimizer.chunk_optimizer import optimize_chunks

    # 第三步：chunk 优化，返回优化后的 chunk 列表
    optimized_chunks = optimize_chunks(validated_chunks)
"""

import json
import copy
from typing import List, Dict, Any, Optional, Set
from app.services.document_processing.validator.validate import get_risk_chunk_ids
from app.config.model_config import get_text_splitter_llm


# ============================================
# LLM Prompt 模板
# ============================================

MERGE_ANALYSIS_PROMPT = """你是一个文档知识分片专家，负责将文档内容按章节结构和知识点拆分成适合知识库的语义分片。

【任务目标】
分析这些分片内容的章节结构，按照章节和知识点的关系进行合理拆分。

【分析步骤】

第一步：识别章节结构
- 找出所有章节标题，如："第一章"、"一、"、"1.1"、"第一节"等
- 注意章节层级（一级章节、二级章节等）

第二步：分析章节间的知识点关系
- 判断相邻章节是否属于同一个大知识点的不同小点
- 如果是同一知识点的延续，应该合并
- 如果是独立的新知识点，应该在此处切分

【判断同一知识点的标准】
- 章节标题是否有关联性（如"概述"与"详细说明"）
- 内容是否在讨论同一个主题的不同方面
- 是否存在"综上"、"因此"等承接性词汇
- 章节层级：同一层级的平行章节通常是不同知识点

【判断新知识点的标准】
- 出现新的一级章节标题（如"第二章"）
- 主题明显转换，与前文无直接关联
- 开始讨论完全不同的概念或内容

【输出规则】
1. 如果所有章节属于同一知识点的不同方面，合并成一个，返回空数组 []
2. 如果章节间是独立的知识点，在章节切换处切分，返回切分点的文本片段
3. 如果不需要调整，返回空数组 []

【输出格式】严格按照以下JSON格式（文本仅为示例，请根据实际内容返回）：
```json
{{
  "split_at": ["第二章 概述", "第三章 实现"]
}}
```

【重要说明】
- 返回的是切分点的**起始文本片段**（约10-30个字符）
- 程序会根据这个文本片段在原文中查找实际切分位置
- 文本片段要足够独特，避免在文中多处出现
- 选择章节标题或段落开头作为切分点标记
- 如果返回空数组 []，表示所有内容合并为一个分片
- 注意：只需要按照输出格式输出就行，不需要添加其他额外信息

【示例说明】
- 文本："第一章 背景...第二章 实现...第三章 总结..."
- 合并成一个 → 返回 []
- 切分为3个 → 返回 ["第二章 实现", "第三章 总结"]

以下是分片内容：

{chunks_content}
"""


SPLIT_ANALYSIS_PROMPT = """你是一个文档知识分片专家，负责将文档内容拆分成适合知识库的语义分片。

【任务目标】
分析这个分片内容，按照**知识点**和**语义完整性**判断是否需要拆分，确保每个拆分后的片段包含一个完整的知识点。

【核心原则】
1. **语义优先**: 同一知识点的内容必须放在同一个分片中，不要拆散
2. **完整性**: 每个分片应该是一个独立的、完整的语义单元，可以单独被理解和检索
3. **识别知识点边界**: 观察标题变化、主题转换、段落切换等语义边界

【判断标准】
- 如果当前分片只讨论一个知识点，内容语义完整，不需要拆分，返回 []
- 如果当前分片包含多个独立的知识点或主题，需要拆分

【拆分位置识别】
- 标题/小标题之后（如"一、""第一章""1.1"等）
- 段落主题明显转换的地方
- 不同知识点的交界处

【输出格式】严格按照以下JSON格式（文本仅为示例，请根据实际内容返回）：
```json
{{
  "split_at": ["1.2 具体说明", "1.3 注意事项"]
}}
```

【重要说明】
- 返回的是切分点的**起始文本片段**（约10-30个字符）
- 程序会根据这个文本片段在原文中查找实际切分位置
- 文本片段要足够独特，避免在文中多处出现
- 选择章节标题或段落开头作为切分点标记
- 如果返回空数组 []，表示保持原样不拆分
- 注意：只需要按照输出格式输出就行，不需要添加其他额外信息

【示例说明】
- 文本："1.1 背景...1.2 具体说明...1.3 注意事项..."
- 不拆分 → 返回 []
- 切分为3个 → 返回 ["1.2 具体说明", "1.3 注意事项"]

以下是分片内容：

**Chunk ID:** {chunk_id}
**标题路径:** {title_path}
**内容:**
{text}
"""


# ============================================
# 辅助函数
# ============================================

def _build_chunk_context(chunks: List[Dict], chunk_id: str, include_adjacent: bool = True) -> List[Dict]:
    """获取指定 chunk 及其相邻 chunk 作为上下文"""
    target_idx = None
    for idx, chunk in enumerate(chunks):
        if chunk.get('chunk_id') == chunk_id:
            target_idx = idx
            break

    if target_idx is None:
        return []

    if not include_adjacent:
        return [chunks[target_idx]]

    result = []
    start_idx = max(0, target_idx - 1)
    end_idx = min(len(chunks), target_idx + 2)

    for idx in range(start_idx, end_idx):
        result.append(chunks[idx])

    return result


def _group_consecutive_chunks(chunk_ids: List[str], chunks: List[Dict]) -> List[List[str]]:
    """将 chunk_ids 按照在原文中的顺序分组，连续的 chunk 分为一组"""
    if not chunk_ids:
        return []

    id_to_order = {}
    for chunk in chunks:
        chunk_id = chunk.get('chunk_id')
        order = chunk.get('order', 0)
        if chunk_id:
            id_to_order[chunk_id] = order

    sorted_ids = sorted(chunk_ids, key=lambda x: id_to_order.get(x, float('inf')))

    groups = []
    current_group = [sorted_ids[0]]

    for i in range(1, len(sorted_ids)):
        prev_id = sorted_ids[i - 1]
        curr_id = sorted_ids[i]

        if id_to_order.get(curr_id, float('inf')) == id_to_order.get(prev_id, float('inf')) + 1:
            current_group.append(curr_id)
        else:
            groups.append(current_group)
            current_group = [curr_id]

    groups.append(current_group)
    return groups


def _format_chunks_for_llm(chunks: List[Dict]) -> str:
    """格式化内容用于 LLM 分析"""
    result = []
    for chunk in chunks:
        chunk_id = chunk.get('chunk_id', 'unknown')
        title_path = chunk.get('title_path', [])
        text = chunk.get('text', '')
        title_str = ' -> '.join(title_path) if title_path else '无标题'

        result.append(f"""**Chunk ID:** {chunk_id}
**标题路径:** {title_str}
**内容:**
{text}
---""")
    return '\n'.join(result)


def _concatenate_chunks_text(chunks: List[Dict]) -> str:
    """将多个 chunk 的文本拼接成一个字符串"""
    texts = []
    for chunk in chunks:
        text = chunk.get('text', '')
        if text:
            texts.append(text)
    return ''.join(texts)


def _merge_title_paths(chunks: List[Dict]) -> List[str]:
    """合并多个 chunk 的 title_path，去重并保持顺序"""
    all_titles = []
    seen = set()

    for chunk in chunks:
        title_path = chunk.get('title_path', [])
        for title in title_path:
            title_clean = title.strip()
            if title_clean and title_clean not in seen:
                seen.add(title_clean)
                all_titles.append(title_clean)

    return all_titles


def _find_split_positions_by_fragments(text: str, fragments: List[str]) -> List[int]:
    """根据文本片段在原文中查找切分位置"""
    if not fragments or not text:
        return []

    positions = []
    for fragment in fragments:
        # 在文本中查找片段位置
        pos = text.find(fragment)
        if pos != -1:
            positions.append((pos, fragment))
        else:
            # 如果找不到完整片段，尝试查找部分匹配
            partial = fragment[:len(fragment)//2]
            pos = text.find(partial)
            if pos != -1:
                positions.append((pos, fragment))

    # 按位置排序
    positions.sort(key=lambda x: x[0])

    # 去重并过滤掉位置0（不应在开头切分）
    seen = set()
    result = []
    for pos, frag in positions:
        if pos > 0 and pos not in seen:
            result.append(pos)
            seen.add(pos)

    return result


def _split_text_by_positions(text: str, positions: List[int]) -> List[str]:
    """根据位置列表拆分文本"""
    if not positions:
        return [text]

    result = []
    start = 0
    for pos in positions:
        if pos > start and pos <= len(text):
            result.append(text[start:pos])
            start = pos
    if start < len(text):
        result.append(text[start:])

    return result


def _call_llm_for_merge_analysis(chunks: List[Dict]) -> Optional[List[str]]:
    """调用 LLM 分析合并后的拆分位置，返回切分点文本片段列表"""
    try:
        llm = get_text_splitter_llm()
        chunks_content = _format_chunks_for_llm(chunks)
        prompt = MERGE_ANALYSIS_PROMPT.format(chunks_content=chunks_content)
        messages = [
            {"role": "system", "content": "你是一个专业的文档分片分析专家。返回切分点的文本片段数组。"},
            {"role": "user", "content": prompt}
        ]

        print(f"\n{'='*60}")
        print(f"【LLM 合并分析请求】")
        print(f"{'='*60}")
        print(f"涉及 chunks: {[c.get('chunk_id') for c in chunks]}")
        print(f"\n>>> 提交给 LLM 的 Chunk 内容 <<<")
        print(f"{'─'*60}")
        print(chunks_content)
        print(f"{'─'*60}")

        response = llm.chat(messages, temperature=0.1)

        print(f"\n>>> LLM 原始返回结果 <<<")
        print(f"{'─'*60}")
        print(response)
        print(f"{'─'*60}")

        # 解析 JSON 响应
        response = response.strip()
        if "```json" in response:
            json_start = response.find("```json") + 7
            json_end = response.find("```", json_start)
            response = response[json_start:json_end].strip()
        elif "```" in response:
            json_start = response.find("```") + 3
            json_end = response.find("```", json_start)
            response = response[json_start:json_end].strip()

        result = json.loads(response)
        fragments = result.get('split_at', [])

        print(f"\n>>> LLM 解析结果 <<<")
        print(f"{'─'*60}")
        if not fragments:
            print(f"建议: 合并为一个分片")
        else:
            print(f"建议: 合并后按以下位置拆分:")
            for i, frag in enumerate(fragments, 1):
                print(f"  切分点 {i}: \"{frag}\"")
        print(f"{'='*60}\n")

        if not fragments:
            return []

        return fragments

    except Exception as e:
        print(f"  ❌ LLM 调用失败 (merge analysis): {e}")
        print(f"{'─'*50}\n")
        return None


def _call_llm_for_split_analysis(chunk: Dict) -> Optional[List[str]]:
    """调用 LLM 分析拆分位置，返回切分点文本片段列表"""
    try:
        llm = get_text_splitter_llm()

        chunk_id = chunk.get('chunk_id', 'unknown')
        title_path = chunk.get('title_path', [])
        text = chunk.get('text', '')
        title_str = ' -> '.join(title_path) if title_path else '无标题'

        prompt = SPLIT_ANALYSIS_PROMPT.format(
            chunk_id=chunk_id,
            title_path=title_str,
            text=text
        )

        messages = [
            {"role": "system", "content": "你是一个专业的文档分片分析专家。返回切分点的文本片段数组。"},
            {"role": "user", "content": prompt}
        ]

        print(f"\n{'='*60}")
        print(f"【LLM 拆分分析请求】")
        print(f"{'='*60}")
        print(f"Chunk ID: {chunk_id}")
        print(f"标题路径: {title_str}")
        print(f"内容长度: {len(text)} 字符")
        print(f"\n>>> 提交给 LLM 的 Chunk 内容 <<<")
        print(f"{'─'*60}")
        print(f"**Chunk ID:** {chunk_id}")
        print(f"**标题路径:** {title_str}")
        print(f"**内容:**")
        print(text)
        print(f"{'─'*60}")

        response = llm.chat(messages, temperature=0.1)

        print(f"\n>>> LLM 原始返回结果 <<<")
        print(f"{'─'*60}")
        print(response)
        print(f"{'─'*60}")

        response = response.strip()
        if "```json" in response:
            json_start = response.find("```json") + 7
            json_end = response.find("```", json_start)
            response = response[json_start:json_end].strip()
        elif "```" in response:
            json_start = response.find("```") + 3
            json_end = response.find("```", json_start)
            response = response[json_start:json_end].strip()

        result = json.loads(response)
        fragments = result.get('split_at', [])

        print(f"\n>>> LLM 解析结果 <<<")
        print(f"{'─'*60}")
        if not fragments:
            print(f"建议: 保持原样，不拆分")
        else:
            print(f"建议: 按以下位置拆分:")
            for i, frag in enumerate(fragments, 1):
                print(f"  切分点 {i}: \"{frag}\"")
        print(f"{'='*60}\n")

        if not fragments:
            return []

        return fragments

    except Exception as e:
        print(f"  ❌ LLM 调用失败 (split analysis): {e}")
        print(f"{'─'*50}\n")
        return None


def _print_split_text_preview(split_texts: List[str], max_preview: int = 200) -> None:
    """打印拆分后的文本预览"""
    for i, text in enumerate(split_texts, 1):
        preview = text[:max_preview]
        if len(text) > max_preview:
            preview += "..."
        print(f"    【分片 {i} 预览】({len(text)} 字符)")
        print(f"    {preview}")
        print()


def _print_result_detail(result: Dict[str, Any], chunks: List[Dict], show_content: bool = True) -> None:
    """打印处理结果的详细信息"""
    result_type = result.get('type')
    input_chunks = result.get('input_chunk', [])
    split_fragments = result.get('split_fragments', [])
    output_chunks = result.get('output_chunks', [])

    if result_type == 'merge':
        input_str = ' + '.join(input_chunks)
        group_chunks = [c for c in chunks if c.get('chunk_id') in input_chunks]
        concatenated_text = _concatenate_chunks_text(group_chunks)

        if len(output_chunks) == 1:
            # 合并成一个
            print(f"[合并校验] {input_str}")
            print(f"  结果: 合并为 1 个分片 (总长度: {len(concatenated_text)} 字符)")
            if show_content:
                _print_split_text_preview([concatenated_text])
        else:
            # 按拆分点拆分
            print(f"[合并校验] {input_str}")
            print(f"  结果: 合并后拆分为 {len(output_chunks)} 个分片")

            if split_fragments:
                print(f"  切分点标记: {split_fragments}")

            for i, out_chunk in enumerate(output_chunks):
                text = out_chunk.get('text', '')
                title_path = out_chunk.get('title_path', [])
                print(f"    分片 {i + 1}: {len(text)} 字符 | 标题: {title_path}")

            if show_content:
                split_texts = [c.get('text', '') for c in output_chunks]
                print(f"  【实际拆分内容预览】")
                _print_split_text_preview(split_texts)

    elif result_type == 'split':
        chunk_id = input_chunks[0] if input_chunks else 'unknown'
        chunk = next((c for c in chunks if c.get('chunk_id') == chunk_id), None)

        if len(output_chunks) == 1:
            # 保持不变
            text = chunk.get('text', '') if chunk else ''
            print(f"[拆分校验] {chunk_id}")
            print(f"  结果: 保持不变 (长度: {len(text)} 字符)")
        else:
            # 需要拆分
            print(f"[拆分校验] {chunk_id}")
            print(f"  结果: 拆分为 {len(output_chunks)} 个分片")

            if split_fragments:
                print(f"  切分点标记: {split_fragments}")

            for i, out_chunk in enumerate(output_chunks):
                text = out_chunk.get('text', '')
                print(f"    分片 {i + 1}: {len(text)} 字符")

            if show_content:
                split_texts = [c.get('text', '') for c in output_chunks]
                print(f"  【实际拆分内容预览】")
                _print_split_text_preview(split_texts)

    print()


# ============================================
# 主优化函数
# ============================================

def optimize_chunks(chunks: List[Dict], min_risk_score: int = 40, show_content: bool = True) -> List[Dict]:
    """
    对分片列表进行优化分析（主入口函数）

    Args:
        chunks: 第二步 validator 返回的校验后分片列表（不会被修改，返回新的列表）
        min_risk_score: 最小风险分数阈值，默认 60
        show_content: 是否显示拆分后的内容预览，默认 True

    Returns:
        优化后的分片列表（新的列表，不影响原始 chunks）
    """
    # 深拷贝 chunks，避免修改原始数据
    optimized_chunks = copy.deepcopy(chunks)

    # 步骤1：获取需要处理的 risk chunk（从原始 chunks 获取）
    risk_chunks = get_risk_chunk_ids(chunks, min_risk_score)

    merge_chunk_ids = [rc['chunk_id'] for rc in risk_chunks if rc['handling_mode'] == 'merge']
    split_chunk_ids = [rc['chunk_id'] for rc in risk_chunks if rc['handling_mode'] == 'split']

    print(f"\n{'='*50}")
    print(f"========== 开始 Chunk 优化 ==========")
    print(f"{'='*50}\n")

    print(f"风险分片统计 (阈值 >= {min_risk_score}):")
    print(f"  - 需要合并的分片数: {len(merge_chunk_ids)}")
    print(f"  - 需要拆分的分片数: {len(split_chunk_ids)}")
    print()

    processed_chunk_ids: Set[str] = set()

    # 用于追踪需要删除的 chunk 和需要添加的新 chunk
    chunks_to_remove: Set[str] = set()
    chunks_to_add: List[Dict] = []

    # 获取 doc_id（从第一个 chunk 获取）
    # 如果 chunk 中没有 doc_id 字段，从 chunk_id 中提取
    if optimized_chunks:
        first_chunk = optimized_chunks[0]
        doc_id = first_chunk.get('doc_id')
        if not doc_id:
            # 从 chunk_id 中提取 doc_id（去掉最后的 order 部分）
            chunk_id = first_chunk.get('chunk_id', '')
            if '_' in chunk_id:
                # chunk_id 格式为 {doc_id}_{order}，提取 doc_id 部分
                doc_id = '_'.join(chunk_id.rsplit('_', 1)[:-1])
            else:
                doc_id = chunk_id if chunk_id else 'unknown'
    else:
        doc_id = 'unknown'

    # ========== 处理合并操作 ==========
    if merge_chunk_ids:
        print(f"【开始处理合并操作】")

        # 获取上下文 chunk 并去重
        adjacent_chunks_set: Set[str] = set()
        for chunk_id in merge_chunk_ids:
            context = _build_chunk_context(optimized_chunks, chunk_id, include_adjacent=True)
            for c in context:
                adjacent_chunks_set.add(c.get('chunk_id'))

        # 去重后，按连续性分组
        all_merge_ids = list(set(merge_chunk_ids) | adjacent_chunks_set)
        grouped = _group_consecutive_chunks(list(all_merge_ids), optimized_chunks)

        # 对每组调用 LLM
        for group_ids in grouped:
            group_chunks = [c for c in optimized_chunks if c.get('chunk_id') in group_ids]
            concatenated_text = _concatenate_chunks_text(group_chunks)

            # 获取第一个 chunk 的信息（用于 page, bbox 等字段）
            first_chunk = group_chunks[0]

            llm_fragments = _call_llm_for_merge_analysis(group_chunks)

            if llm_fragments is not None:
                if not llm_fragments:
                    # 合并成一个 chunk
                    merged_title_path = _merge_title_paths(group_chunks)

                    new_chunk = {
                        'chunk_id': f"{doc_id}_{first_chunk.get('order', 0)}",
                        'doc_id': doc_id,
                        'order': first_chunk.get('order', 0),
                        'title_path': merged_title_path,
                        'text': concatenated_text,
                        'page': first_chunk.get('page', 0),
                        'bbox': first_chunk.get('bbox', []),
                        'type': first_chunk.get('type', 'text'),
                        'length': len(concatenated_text)
                    }

                    chunks_to_remove.update(group_ids)
                    chunks_to_add.append(new_chunk)
                    processed_chunk_ids.update(group_ids)

                    # 打印结果
                    print(f"[合并校验] {' + '.join(group_ids)}")
                    print(f"  结果: 合并为 1 个分片 (总长度: {len(concatenated_text)} 字符)")
                    if show_content:
                        _print_split_text_preview([concatenated_text])
                else:
                    # 根据文本片段查找实际位置并拆分
                    positions = _find_split_positions_by_fragments(concatenated_text, llm_fragments)

                    if not positions:
                        # 没有找到有效的拆分位置，合并成一个
                        merged_title_path = _merge_title_paths(group_chunks)
                        new_chunk = {
                            'chunk_id': f"{doc_id}_{first_chunk.get('order', 0)}",
                            'doc_id': doc_id,
                            'order': first_chunk.get('order', 0),
                            'title_path': merged_title_path,
                            'text': concatenated_text,
                            'page': first_chunk.get('page', 0),
                            'bbox': first_chunk.get('bbox', []),
                            'type': first_chunk.get('type', 'text'),
                            'length': len(concatenated_text)
                        }
                        chunks_to_remove.update(group_ids)
                        chunks_to_add.append(new_chunk)
                        processed_chunk_ids.update(group_ids)

                        print(f"[合并校验] {' + '.join(group_ids)}")
                        print(f"  结果: 合并为 1 个分片 (总长度: {len(concatenated_text)} 字符)")
                        if show_content:
                            _print_split_text_preview([concatenated_text])
                    else:
                        # 拆分成多个 chunk
                        split_texts = _split_text_by_positions(concatenated_text, positions)

                        # 计算每个原始 chunk 在拼接文本中的起止位置
                        chunk_boundaries = []  # [(start, end, chunk_obj), ...]
                        current_pos = 0
                        for chunk in group_chunks:
                            chunk_text = chunk.get('text', '')
                            chunk_len = len(chunk_text)
                            chunk_boundaries.append((current_pos, current_pos + chunk_len, chunk))
                            current_pos += chunk_len

                        # 根据拆分位置确定每个新 chunk 对应哪些原始 chunk
                        output_chunks = []
                        base_order = first_chunk.get('order', 0)

                        for i, split_text in enumerate(split_texts):
                            # 确定当前分片的位置范围
                            # split_texts 长度是 len(positions) + 1，最后一个分片的 split_end 是文本末尾
                            split_start = 0 if i == 0 else positions[i - 1]
                            split_end = positions[i] if i < len(positions) else len(concatenated_text)

                            # 找出这个范围内包含哪些原始 chunk
                            related_chunks = []
                            for start, end, chunk in chunk_boundaries:
                                # 如果有重叠，说明这个 chunk 部分或全部属于当前分片
                                if not (end <= split_start or start >= split_end):
                                    related_chunks.append(chunk)

                            # 合并这些相关 chunk 的 title_path
                            merged_title_path = _merge_title_paths(related_chunks) if related_chunks else []

                            # 确定使用哪个 chunk 的 page/bbox（使用第一个相关 chunk）
                            ref_chunk = related_chunks[0] if related_chunks else first_chunk

                            new_chunk = {
                                'chunk_id': f"{doc_id}_{base_order + i}",
                                'doc_id': doc_id,
                                'order': base_order + i,
                                'title_path': merged_title_path,
                                'text': split_text,
                                'page': ref_chunk.get('page', 0),
                                'bbox': ref_chunk.get('bbox', []),
                                'type': ref_chunk.get('type', 'text'),
                                'length': len(split_text)
                            }
                            output_chunks.append(new_chunk)

                        chunks_to_remove.update(group_ids)
                        chunks_to_add.extend(output_chunks)
                        processed_chunk_ids.update(group_ids)

                        # 打印结果
                        print(f"[合并校验] {' + '.join(group_ids)}")
                        print(f"  结果: 合并后拆分为 {len(output_chunks)} 个分片")
                        if llm_fragments:
                            print(f"  切分点标记: {llm_fragments}")
                        for i, out_chunk in enumerate(output_chunks):
                            text = out_chunk.get('text', '')
                            title_path = out_chunk.get('title_path', [])
                            print(f"    分片 {i + 1}: {len(text)} 字符 | 标题: {title_path}")
                        if show_content:
                            split_texts = [c.get('text', '') for c in output_chunks]
                            print(f"  【实际拆分内容预览】")
                            _print_split_text_preview(split_texts)
            else:
                print(f"[合并校验] {' + '.join(group_ids)} → LLM 调用失败\n")

    # ========== 处理拆分操作 ==========
    if split_chunk_ids:
        print(f"【开始处理拆分操作】")

        # 过滤掉已处理的 chunk
        final_split_ids = [cid for cid in split_chunk_ids if cid not in processed_chunk_ids]

        for chunk_id in final_split_ids:
            chunk = next((c for c in optimized_chunks if c.get('chunk_id') == chunk_id), None)
            if not chunk:
                continue

            text = chunk.get('text', '')

            llm_fragments = _call_llm_for_split_analysis(chunk)

            if llm_fragments is not None:
                if not llm_fragments:
                    # 保持不变
                    print(f"[拆分校验] {chunk_id}")
                    print(f"  结果: 保持不变 (长度: {len(text)} 字符)\n")
                else:
                    # 根据文本片段查找实际位置并拆分
                    positions = _find_split_positions_by_fragments(text, llm_fragments)

                    if not positions:
                        # 没有找到有效的拆分位置，保持不变
                        print(f"[拆分校验] {chunk_id}")
                        print(f"  结果: 保持不变 (长度: {len(text)} 字符)\n")
                    else:
                        # 拆分成多个 chunk
                        split_texts = _split_text_by_positions(text, positions)
                        original_title_path = chunk.get('title_path', []).copy()
                        base_order = chunk.get('order', 0)

                        output_chunks = []
                        for i, split_text in enumerate(split_texts):
                            new_chunk = {
                                'chunk_id': f"{doc_id}_{base_order + i}",
                                'doc_id': doc_id,
                                'order': base_order + i,
                                'title_path': original_title_path.copy(),
                                'text': split_text,
                                'page': chunk.get('page', 0),
                                'bbox': chunk.get('bbox', []),
                                'type': chunk.get('type', 'text'),
                                'length': len(split_text)
                            }
                            output_chunks.append(new_chunk)

                        chunks_to_remove.add(chunk_id)
                        chunks_to_add.extend(output_chunks)

                        # 打印结果
                        print(f"[拆分校验] {chunk_id}")
                        print(f"  结果: 拆分为 {len(output_chunks)} 个分片")
                        if llm_fragments:
                            print(f"  切分点标记: {llm_fragments}")
                        for i, out_chunk in enumerate(output_chunks):
                            text_out = out_chunk.get('text', '')
                            print(f"    分片 {i + 1}: {len(text_out)} 字符")
                        if show_content:
                            split_texts = [c.get('text', '') for c in output_chunks]
                            print(f"  【实际拆分内容预览】")
                            _print_split_text_preview(split_texts)
            else:
                print(f"[拆分校验] {chunk_id} → LLM 调用失败\n")

    # ========== 更新 optimized_chunks 列表 ==========
    # 先删除需要移除的 chunk
    optimized_chunks = [c for c in optimized_chunks if c.get('chunk_id') not in chunks_to_remove]

    # 再添加新的 chunk
    optimized_chunks.extend(chunks_to_add)

    # 重新排序并更新 order 和 chunk_id
    optimized_chunks.sort(key=lambda x: x.get('order', float('inf')))
    for i, chunk in enumerate(optimized_chunks):
        chunk['order'] = i + 1
        # 更新 chunk_id 以匹配新的 order
        chunk['chunk_id'] = f"{doc_id}_{i + 1}"

    print(f"{'='*50}")
    print(f"优化完成！原分片数: {len(chunks)}, 现分片数: {len(optimized_chunks)}, "
          f"变化: {len(optimized_chunks) - len(chunks)}")
    print(f"{'='*50}\n")

    return optimized_chunks
