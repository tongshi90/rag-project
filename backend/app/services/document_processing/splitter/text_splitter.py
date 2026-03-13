"""
================================================================================
文本分片服务 - PDF 智能分片完整流程
================================================================================

【功能说明】
将 PDF 文档中的文本内容按标题层级智能切分成多个语义分片（chunks），
每个分片包含完整的标题路径和文本内容，保证所有分片拼接后为完整文档。

【主入口函数】
- split_pdf_to_chunks(pdf_path)  # 从 PDF 文件路径直接生成分片（包含完整预处理）

================================================================================
【PDF 分片完整拆分步骤】（split_pdf_to_chunks 函数流程）
================================================================================

第一步：提取页面文本（extract_pages）
--------------------------------------
1. 使用 pdfplumber 打开 PDF 文件
2. 逐页遍历，获取页面高度和所有表格区域的 bbox 边界坐标
3. 调用 extract_text_lines() 提取每页的文本行
4. 过滤掉空行
5. 判断每一行是否位于表格区域内（通过 top 坐标判断）
6. 排除表格区域内的文本行
7. 保留非表格区域的文本行，每行记录：text（文本内容）、top（顶部位置）、page_height（页面高度）
8. 返回：List[List[Dict]]，按页分组的文本行列表


第二步：去除页眉页脚（remove_repeated_headers_footers）
--------------------------------------
1. 统计总页数 total_pages
2. 遍历每一页，收集每页的首行文本（first_lines）和尾行文本（last_lines）
3. 使用 Counter 统计首行文本的出现次数，同理统计尾行文本的出现次数
4. 计算判定阈值：某文本出现次数 / 总页数 >= 0.7（70%），则认为是页眉或页脚
5. 将需要删除的首行文本集合存为 first_to_delete，尾行文本集合存为 last_to_delete
6. 遍历每一页，若首行文本在 first_to_delete 中则删除该行，若尾行文本在 last_to_delete 中则删除该行
7. 返回：删除页眉页脚后的页面列表 List[List[Dict]]


第三步：去除页码（remove_page_numbers）
--------------------------------------
1. 遍历每一页，对每页的首行和尾行调用 extract_page_number() 提取页码数字
2. extract_page_number() 的匹配规则（按优先级）：
   a) 匹配 "第X页" 格式，提取 X
   b) 匹配 "X页" 格式，提取 X
   c) 匹配纯数字格式，提取该数字
   d) 若都不匹配则返回 None
3. 记录每页首行是否为页码（first_line_candidates），尾行是否为页码（last_line_candidates）
4. 统计首行是页码的页面数量，计算比例：若 >= 0.7（70%），则判定需要删除每页首行
5. 若首行不删除，则同理判定尾行：若 >= 70% 页面尾行是页码，则判定需要删除每页尾行
6. 遍历每一页，根据判定结果删除首行或尾行
7. 将所有页面的文本行合并为一个列表（flatten）
8. 返回：List[Dict]，包含所有文本行（已去除页眉页脚和页码）


第四步：动态修正标题规则（refine_title_patterns）
--------------------------------------
1. 初始化计数器：hit_count（命中次数）、consecutive（连续命中次数）、last（上一次命中的规则名）
2. 遍历所有文本行，对每一行：
   a) 依次用 RAW_TITLE_PATTERNS 中的规则进行正则匹配
   b) 若匹配成功且文本长度 < 40 字符：
      - hit_count[name] += 1
      - 若当前规则名 == last，则 consecutive[name] += 1
      - 否则重置 consecutive[name] = 1
      - 记录 last = 当前规则名
   c) 若都不匹配，则重置 last = None
3. 遍历 RAW_TITLE_PATTERNS，过滤掉连续命中次数 >= 5 的规则（这些规则误判率太高）
4. 返回：修正后的标题规则列表 List[(level_name, pattern)]


第五步：按标题层级构建分片（split_chunks）
--------------------------------------
1. 初始化：chunks 列表、current_title_path 当前标题路径栈、current_chunk 当前分片、order 排序序号
2. 定义 flush() 函数：将当前非空的 current_chunk 保存到 chunks 列表
3. 遍历所有文本行，对每一行：
   a) 依次用修正后的标题规则进行正则匹配
   b) 若匹配成功（matched 为某个 level）：
      - 调用 flush() 保存上一个分片
      - 根据 matched 的层级更新 current_title_path：
        * level1: current_title_path = [当前标题文本]
        * level2: current_title_path = [第一级标题, 当前标题文本]
        * level3: current_title_path = [第一级标题, 第二级标题, 当前标题文本]
      - 创建新的 current_chunk，包含：chunk_id、order、title_path、text（标题文本）
      - continue 进入下一行
   c) 若不匹配任何标题规则（正文行）：
      - 若 current_chunk 为空：创建新分片，以当前正文行开始
      - 若 current_chunk 不为空：将当前正文行追加到 current_chunk["text"]
4. 循环结束后，调用 flush() 保存最后一个分片
5. 返回：初步分片列表 List[Dict]，每个包含 chunk_id、order、title_path、text


第六步：后处理 - 合并仅含标题的分片（merge_title_only_chunks）
--------------------------------------
1. 初始化 result 空列表，i = 0
2. 遍历所有 chunks：
   a) 获取当前 chunk 的 text 和 title_path
   b) 判断是否为"仅含标题"的 chunk：
      - 若 title_path 不为空 且 text.strip() == title_path[-1].strip()
      - 说明该分片内容与标题完全一致，仅有标题没有正文
   c) 若是"仅含标题"分片 且存在下一个 chunk：
      - 将当前 chunk 与下一个 chunk 合并
      - 合并规则：
        * chunk_id 保持当前 chunk 的 id
        * order 保持当前 chunk 的 order
        * title_path = 当前 title_path + 下一个 title_path（拼接）
        * text = 当前 text + "\n" + 下一个 text（拼接）
      - 将合并后的 chunk 添加到 result
      - i += 2（跳过下一个 chunk）
   d) 否则：
      - 直接将当前 chunk 添加到 result
      - i += 1
3. 返回：合并后的分片列表


第七步：后处理 - 去重相同格式的标题（dedup_same_format_titles）
--------------------------------------
1. 遍历所有 chunks
2. 对每个 chunk 的 title_path 中的每个标题：
   a) 调用 get_title_pattern_type() 获取该标题匹配的格式类型（level1/level2/level3）
   b) 按格式类型分组记录所有位置索引：format_positions[format_type] = [idx1, idx2, ...]
3. 构建待删除索引列表：
   a) 对每种格式，除最后一个位置外的所有索引进入待删除列表 to_delete_indices
4. 检查待删除的标题是否在 text 中存在：
   a) 遍历 to_delete_indices 中的每个索引
   b) 若标题不在 text 中，或 text 只包含该标题（无实际内容），则加入最终删除列表
   c) 若标题在 text 中存在且有其他内容，则保留该标题
5. 根据 final_delete_indices 过滤 title_path
6. 返回：去重后的分片列表


第八步：输出结果（post_process_chunks）
--------------------------------------
1. 依次调用 merge_title_only_chunks() 和 dedup_same_format_titles()
2. 返回最终的分片列表 List[Dict]，每个分片包含：
   - chunk_id: 分片唯一标识
   - order: 排序序号
   - title_path: 多级标题路径（已去重相同格式）
   - text: 完整的文本内容（包含标题和正文）


================================================================================
【分片数据结构】
================================================================================

每个分片（chunk）的格式：
{
    "chunk_id": "1",                    # 分片唯一 ID
    "order": 1,                         # 排序序号
    "title_path": ["第一章 概述", "一、背景"],  # 多级标题路径（从大到小）
    "text": "完整文本内容（包含标题和正文）"    # 文本内容
}


================================================================================
【标题规则定义】（RAW_TITLE_PATTERNS）
================================================================================

层级    格式类型            正则表达式示例                    优先级
------------------------------------------------------------------------
level1  第X章               ^第[一二三四五六七八九十百]+章\s+.+    最高
level2  第X节               ^第[一二三四五六七八九十百]+节\s+.+    高
level2  中文数字顿号        ^[一二三四五六七八九十百]+、\s*.+     高
level2  阿拉伯数字点        ^\d+(\.\d+)*\s+.+                     高
level3  括号中文数字        ^[（(][一二三四五六七八九十百]+[）)]\s*.+  低

注意：规则会根据实际命中情况动态调整，连续误判 >= 5 次的规则会被移除。

================================================================================
"""
import re
import pdfplumber
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, Counter
import difflib

# 章节切分的正则匹配规则（预设规则，作为兜底）
RAW_TITLE_PATTERNS = [
    ("1", r'^第[一二三四五六七八九十百]+章\s+.+'),
    ("2", r'^第[一二三四五六七八九十百]+节\s+.+'),
    ("3", r'^[一二三四五六七八九十百]+、\s*.+'),
    ("4", r'^\d+(\.\d+)*[\. 、,]\s*.+'),
    ("5", r'^[（(][一二三四五六七八九十百]+[）)]\s*.+'),
]

# 页码的正则匹配规则
PAGE_NUM_PATTERNS = [
    r'^\d+$',
    r'^第\s*\d+\s*页$',
    r'^\d+\s*页$',
]


# ============================================
# 动态标题提取模块（混合方案：数字模式挖掘 + 特征聚类）
# ============================================

def extract_line_features(line_text: str, line_index: int, total_lines: int,
                          prev_empty: bool, next_empty: bool) -> Dict:
    """
    提取单行文本的特征，用于判断是否为标题候选

    Args:
        line_text: 行文本内容
        line_index: 行在文档中的索引
        total_lines: 文档总行数
        prev_empty: 前一行是否为空
        next_empty: 后一行是否为空

    Returns:
        特征字典
    """
    text = line_text.strip()
    if not text:
        return {}

    features = {
        'text': text,
        'index': line_index,
        'length': len(text),
        'word_count': len(text.split()),
        'prev_empty': prev_empty,
        'next_empty': next_empty,
        'starts_with_digit': False,
        'starts_with_chinese_num': False,
        'starts_with_bracket': False,
        'starts_with_chapter_keyword': False,
        'has_dot_separated_numbers': False,
        'has_punctuation_after_num': False,
        'prefix_pattern': '',  # 记录前缀模式，如 "1.", "（一）"
    }

    # 检查行首模式
    if text:
        # 以数字开头
        if text[0].isdigit():
            features['starts_with_digit'] = True
            # 检查是否有点分隔的数字
            if re.match(r'^\d+(\.\d+)', text):
                features['has_dot_separated_numbers'] = True
            # 检查数字后是否有标点
            if re.match(r'^\d+[\.\s、,]', text):
                features['has_punctuation_after_num'] = True

        # 以中文数字开头
        chinese_nums = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
                        '百', '千', '零']
        if text[0] in chinese_nums:
            features['starts_with_chinese_num'] = True

        # 以括号开头
        if text[0] in '([（':
            features['starts_with_bracket'] = True

        # 包含章节关键词
        if re.match(r'^第[一二三四五六七八九十百]+[章节篇]', text):
            features['starts_with_chapter_keyword'] = True

        # 提取前缀模式（用于后续聚类）
        prefix_match = re.match(r'^([0-9一二三四五六七八九十百（）()\.\s、,]+)', text)
        if prefix_match:
            features['prefix_pattern'] = prefix_match.group(1)

    return features


def analyze_prefix_pattern(prefix: str) -> Dict:
    """
    分析前缀模式，生成对应的正则表达式

    Args:
        prefix: 前缀文本，如 "1.1. ", "（一）", "第一章 "

    Returns:
        包含 regex 和 level_info 的字典
    """
    if not prefix:
        return None

    # 去除多余空格
    prefix = prefix.strip()
    if not prefix:
        return None

    result = {
        'original_prefix': prefix,
        'regex': None,
        'level_info': None,
        'type': None
    }

    # 类型1：第X章/节/篇格式
    match = re.match(r'^第([一二三四五六七八九十百]+)([章节篇])\s*', prefix)
    if match:
        result['type'] = 'chinese_chapter'
        result['regex'] = r'^第[一二三四五六七八九十百]+[章节篇]\s+.+'
        result['level_info'] = 'high'
        return result

    # 类型2：中文数字+顿号/空格
    match = re.match(r'^([一二三四五六七八九十百]+)[、\s]+', prefix)
    if match and len(prefix) < 10:
        result['type'] = 'chinese_num_dot'
        result['regex'] = r'^[一二三四五六七八九十百]+[、\s].+'
        result['level_info'] = 'medium'
        return result

    # 类型3：括号包围的中文数字
    match = re.match(r'^[（(]([一二三四五六七八九十百]+)[）)]\s*', prefix)
    if match:
        result['type'] = 'bracket_chinese_num'
        result['regex'] = r'^[（(][一二三四五六七八九十百]+[）)]\s*.+'
        result['level_info'] = 'low'
        return result

    # 类型4：点分隔的阿拉伯数字 (1., 1.1., 1.1.1.)
    match = re.match(r'^(\d+(\.\d+)*)[\.\s、,]', prefix)
    if match:
        num_parts = match.group(1).split('.')
        depth = len(num_parts)  # 层级深度
        result['type'] = 'numbered_dotted'
        if depth == 1:
            result['regex'] = r'^\d+[\.\s、,]\s*.+'
            result['level_info'] = 'high'
        elif depth == 2:
            result['regex'] = r'^\d+\.\d+[\.\s、,]?\s*.+'
            result['level_info'] = 'medium'
        else:
            result['regex'] = r'^\d+(\.\d+){2,}[\.\s、,]?\s*.+'
            result['level_info'] = 'low'
        return result

    # 类型5：括号包围的阿拉伯数字
    match = re.match(r'^[（(](\d+)[）)]\s*', prefix)
    if match:
        result['type'] = 'bracket_number'
        result['regex'] = r'^[（(]\d+[）)]\s*.+'
        result['level_info'] = 'low'
        return result

    # 类型6：纯数字加空格
    match = re.match(r'^(\d+)\s+', prefix)
    if match:
        result['type'] = 'number_space'
        result['regex'] = r'^\d+\s+.+'
        result['level_info'] = 'medium'
        return result

    return None


def cluster_title_candidates(all_features: List[Dict]) -> List[Dict]:
    """
    对标题候选进行聚类分析

    Args:
        all_features: 所有行的特征列表

    Returns:
        聚类后的标题模式列表
    """
    # 第一步：筛选出可能是标题的行
    candidates = []
    for features in all_features:
        if not features:
            continue

        # 标题特征判断：
        # 1. 前后有空行（或位于文档首尾）
        # 2. 长度适中（不太长）
        # 3. 有编号或特殊格式

        is_title_candidate = False
        confidence = 0

        # 检查前后空行
        has_isolation = features['prev_empty'] or features['next_empty'] or \
                        features['index'] == 0 or features['index'] == len(all_features) - 1
        if has_isolation:
            confidence += 2

        # 检查长度（标题通常较短）
        if features['length'] < 80:
            confidence += 1
        if features['length'] < 50:
            confidence += 1

        # 检查格式特征
        if features['starts_with_chapter_keyword']:
            confidence += 5
            is_title_candidate = True
        if features['has_dot_separated_numbers']:
            confidence += 4
            is_title_candidate = True
        if features['starts_with_chinese_num'] and features['has_punctuation_after_num']:
            confidence += 4
            is_title_candidate = True
        if features['starts_with_bracket']:
            confidence += 3
            is_title_candidate = True
        if features['starts_with_digit'] and features['has_punctuation_after_num']:
            confidence += 3
            is_title_candidate = True

        # 至少有一定置信度才认为是标题候选
        if confidence >= 3 or is_title_candidate:
            # 分析前缀模式
            pattern_info = analyze_prefix_pattern(features['prefix_pattern'])
            if pattern_info:
                candidates.append({
                    'text': features['text'],
                    'index': features['index'],
                    'confidence': confidence,
                    'pattern_info': pattern_info,
                    'prefix': features['prefix_pattern']
                })
            elif confidence >= 5:  # 高置信度但没有明显前缀模式的，可能是纯文字标题
                candidates.append({
                    'text': features['text'],
                    'index': features['index'],
                    'confidence': confidence,
                    'pattern_info': None,
                    'prefix': ''
                })

    return candidates


def merge_similar_patterns(candidates: List[Dict]) -> Dict[str, Dict]:
    """
    合并相似的前缀模式，生成最终的标题正则

    Args:
        candidates: 标题候选列表

    Returns:
        按类型分组的模式字典 {type: {regex, level_info, count}}
    """
    # 按模式类型分组
    pattern_groups = defaultdict(lambda: {
        'regex': None,
        'level_info': None,
        'count': 0,
        'examples': []
    })

    for candidate in candidates:
        pattern_info = candidate['pattern_info']
        if not pattern_info or not pattern_info['regex']:
            continue

        ptype = pattern_info['type']
        pattern_groups[ptype]['regex'] = pattern_info['regex']
        pattern_groups[ptype]['level_info'] = pattern_info['level_info']
        pattern_groups[ptype]['count'] += 1
        pattern_groups[ptype]['examples'].append(candidate['text'][:30])

    # 过滤掉出现次数太少的模式（至少出现2次）
    filtered_patterns = {
        k: v for k, v in pattern_groups.items()
        if v['count'] >= 2
    }

    return filtered_patterns


def determine_pattern_hierarchy(patterns: Dict[str, Dict],
                                lines: List[Dict]) -> List[Tuple[str, str]]:
    """
    根据模式在文档中首次出现的顺序，确定标题层级

    Args:
        patterns: 模式字典
        lines: 原始行列表

    Returns:
        [(level_name, regex), ...] 按层级排序的正则列表
    """
    # 记录每种模式首次出现的位置
    first_appearance = {}  # type -> index

    for idx, line in enumerate(lines):
        text = line["text"]
        for ptype, info in patterns.items():
            regex = info['regex']
            if re.match(regex, text) and len(text) < 50:
                if ptype not in first_appearance:
                    first_appearance[ptype] = idx
                    break

    # 按首次出现顺序排序
    sorted_patterns = sorted(patterns.items(),
                             key=lambda x: first_appearance.get(x[0], float('inf')))

    # 生成最终的正则列表
    result = []
    for level, (ptype, info) in enumerate(sorted_patterns, start=1):
        result.append((f"level{level}", info['regex']))

    return result


def auto_detect_title_patterns(lines: List[Dict]) -> List[Tuple[str, str]]:
    """
    自动检测文档中的标题模式（混合方案）

    流程：
    1. 提取所有行的特征
    2. 基于特征筛选标题候选
    3. 对候选进行聚类分析
    4. 合并相似模式生成正则
    5. 按出现顺序确定层级

    Args:
        lines: 文本行列表

    Returns:
        [(level_name, regex), ...] 自动检测到的标题正则列表
    """
    if not lines:
        return []

    total_lines = len(lines)

    # 第一步：提取所有行的特征
    all_features = []
    for i, line in enumerate(lines):
        prev_empty = (i == 0) or (not lines[i - 1]["text"].strip())
        next_empty = (i == total_lines - 1) or (not lines[i + 1]["text"].strip())
        features = extract_line_features(line["text"], i, total_lines, prev_empty, next_empty)
        if features:
            all_features.append(features)

    # 第二步：筛选标题候选
    candidates = cluster_title_candidates(all_features)

    if not candidates:
        return []

    # 第三步：合并相似模式
    pattern_groups = merge_similar_patterns(candidates)

    if not pattern_groups:
        return []

    # 第四步：确定层级顺序
    detected_patterns = determine_pattern_hierarchy(pattern_groups, lines)

    return detected_patterns


def extract_page_number(text: str) -> Optional[int]:
    """尝试从文本中提取页码数字（模糊匹配）"""
    text = text.strip()

    # 模糊匹配：第X页
    match = re.search(r'第\s*(\d+)\s*页', text)
    if match:
        return int(match.group(1))
    # 模糊匹配：X页
    match = re.search(r'(\d+)\s*页', text)
    if match:
        return int(match.group(1))

    # 纯数字
    match = re.fullmatch(r'\d+', text)
    if match:
        return int(match.group(0))

    return None


def extract_pages(pdf_path: str) -> List[List[Dict]]:
    """从 PDF 中提取所有页面（排除表格）"""
    pages = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_height = page.height
            table_bboxes = [t.bbox for t in page.find_tables()]

            lines = []
            for line in page.extract_text_lines():
                text = line["text"].strip()
                if not text:
                    continue

                # 忽略表格内容
                in_table = False
                for x0, top, x1, bottom in table_bboxes:
                    if top <= line["top"] <= bottom:
                        in_table = True
                        break
                if in_table:
                    continue

                lines.append({
                    "text": text,
                    "top": line["top"],
                    "page_height": page_height
                })

            pages.append(lines)

    return pages


def remove_repeated_headers_footers(pages: List[List[Dict]], threshold: float = 0.7) -> List[List[Dict]]:
    """
    去掉重复出现的页眉或页脚
    """
    total_pages = len(pages)
    first_lines = []
    last_lines = []

    # 收集每页首尾行文本
    for page in pages:
        if not page:
            first_lines.append(None)
            last_lines.append(None)
            continue
        first_lines.append(page[0]["text"])
        last_lines.append(page[-1]["text"])

    # 统计出现次数
    first_counter = Counter([t for t in first_lines if t is not None])
    last_counter = Counter([t for t in last_lines if t is not None])

    # 判定哪些文本是重复页眉/页脚
    first_to_delete = {t for t, count in first_counter.items() if count / total_pages >= threshold}
    last_to_delete = {t for t, count in last_counter.items() if count / total_pages >= threshold}

    # 构建新的 pages
    cleaned_pages = []
    for page in pages:
        new_page = page.copy()
        # 删除首行
        if new_page and new_page[0]["text"] in first_to_delete:
            new_page = new_page[1:]
        # 删除尾行
        if new_page and new_page[-1]["text"] in last_to_delete:
            new_page = new_page[:-1]
        cleaned_pages.append(new_page)

    return cleaned_pages


def remove_page_numbers(pages: List[List[Dict]], threshold: float = 0.7) -> List[Dict]:
    """
    检测并删除页码行，同时保留页码信息
    """
    first_line_candidates = []
    last_line_candidates = []

    # 每页首尾条检查
    for page_lines in pages:
        first_line_num = extract_page_number(page_lines[0]["text"]) if page_lines else None
        last_line_num = extract_page_number(page_lines[-1]["text"]) if page_lines else None
        first_line_candidates.append(first_line_num)
        last_line_candidates.append(last_line_num)

    total_pages = len(pages)
    # 首条页码判定
    first_valid_count = sum(1 for n in first_line_candidates if n is not None)
    delete_first = (first_valid_count / total_pages) >= threshold

    # 尾条页码判定
    delete_last = False
    if not delete_first:
        last_valid_count = sum(1 for n in last_line_candidates if n is not None)
        delete_last = (last_valid_count / total_pages) >= threshold

    # 构建最终 lines，同时添加页码信息（页码从1开始）
    cleaned_lines = []
    for idx, page_lines in enumerate(pages):
        new_page_lines = page_lines.copy()
        if delete_first and first_line_candidates[idx] is not None:
            new_page_lines = new_page_lines[1:]  # 删除首条
        elif delete_last and last_line_candidates[idx] is not None:
            new_page_lines = new_page_lines[:-1]  # 删除尾条

        # 为每一行添加页码信息（页码从1开始，不是0）
        page_number = idx + 1
        for line in new_page_lines:
            line["page_number"] = page_number

        cleaned_lines.extend(new_page_lines)

    return cleaned_lines


def refine_title_patterns(lines: List[Dict]) -> List:
    """
    根据实际命中情况动态调整标题规则

    新增功能：整合自动检测的标题模式与预设规则

    流程：
    1. 先自动检测文档中的标题模式
    2. 将检测到的模式与预设规则合并
    3. 根据命中情况筛选有效规则
    4. 按首次出现顺序确定层级
    """
    # 第一步：自动检测文档中的标题模式
    detected_patterns = auto_detect_title_patterns(lines)

    # 第二步：合并检测到的模式和预设规则
    # 如果自动检测到了模式，优先使用；否则使用预设规则
    if detected_patterns:
        # 使用自动检测的模式
        all_patterns = detected_patterns
        use_detected = True
    else:
        # 使用预设规则
        all_patterns = [(name, pattern) for name, pattern in RAW_TITLE_PATTERNS]
        use_detected = False

    # 第三步：根据命中情况筛选规则
    hit_count = defaultdict(int)
    consecutive = defaultdict(int)
    max_consecutive = defaultdict(int)
    last_index = None

    for line in lines:
        text = line["text"]
        for idx, (name, pattern) in enumerate(all_patterns):
            if re.match(pattern, text) and len(text) < 50:
                hit_count[idx] += 1
                if last_index == idx:
                    consecutive[idx] += 1
                else:
                    consecutive[idx] = 1

                if consecutive[idx] > max_consecutive[idx]:
                    max_consecutive[idx] = consecutive[idx]

                last_index = idx
                break
        else:
            last_index = None

    # 第四步：筛选有效规则
    refined = []
    valid_indices = []
    for idx, (name, pattern) in enumerate(all_patterns):
        # 只保留命中过的规则，且连续误判次数 < 5
        if hit_count[idx] == 0:
            continue
        if max_consecutive[idx] >= 5:
            continue
        refined.append((name, pattern))
        valid_indices.append(idx)

    # 如果使用预设规则且有有效规则，按原有逻辑重新排序
    if not use_detected and refined:
        pattern_first_appearance = {}
        pattern_appearance_order = []

        for line in lines:
            text = line["text"]
            for idx, (name, pattern) in enumerate(all_patterns):
                if idx not in valid_indices:
                    continue
                if idx in pattern_first_appearance:
                    continue
                if re.match(pattern, text) and len(text) < 50:
                    pattern_first_appearance[idx] = len(pattern_appearance_order)
                    pattern_appearance_order.append(idx)
                    break

            if len(pattern_appearance_order) == len(valid_indices):
                break

        if pattern_appearance_order:
            final_refined = []
            idx_to_pattern = {idx: pat for idx, pat in zip(valid_indices, refined)}
            for level, idx in enumerate(pattern_appearance_order, start=1):
                final_refined.append((f"level{level}", idx_to_pattern[idx]))
            return final_refined

    # 使用自动检测模式时，或预设规则无需重排序时
    return refined


def split_chunks(lines: List[Dict], title_patterns: List) -> List[Dict]:
    """按标题层级构建 chunks"""
    chunks = []
    current_title_path = []
    current_chunk = None
    order = 0

    def flush():
        nonlocal current_chunk
        if current_chunk and current_chunk["text"].strip():
            chunks.append(current_chunk)
        current_chunk = None

    for line in lines:
        text = line["text"]
        page_number = line.get("page_number", 1)  # 获取页码，默认为1
        matched = None

        for level, pattern in title_patterns:
            if re.match(pattern, text):
                matched = level
                break

        if matched:
            flush()

            # 支持任意层级的标题（level1, level2, level3, ...）
            if matched.startswith("level"):
                level_num = int(matched.replace("level", ""))
                # 保留前 (level_num - 1) 个标题，替换当前层级
                current_title_path = current_title_path[:level_num - 1] + [text]
            else:
                # 兼容旧格式：直接使用原逻辑
                if matched == "level1" or matched == "1":
                    current_title_path = [text]
                elif matched == "level2" or matched == "2":
                    current_title_path = current_title_path[:1] + [text]
                elif matched == "level3" or matched == "3":
                    current_title_path = current_title_path[:2] + [text]

            # 标题作为新 chunk 的开始
            order += 1
            current_chunk = {
                "chunk_id": str(order),
                "order": order,
                "title_path": current_title_path.copy(),
                "text": text,
                "page": page_number  # 添加页码
            }
            continue

        if not current_chunk:
            order += 1
            current_chunk = {
                "chunk_id": str(order),
                "order": order,
                "title_path": current_title_path.copy(),
                "text": text,
                "page": page_number  # 添加页码
            }
        else:
            current_chunk["text"] += "\n" + text
            # 更新页码为最新页面的页码（chunk 可能跨越多页）
            current_chunk["page"] = page_number

    flush()
    return chunks


def get_title_pattern_type(title: str) -> Optional[str]:
    """获取标题匹配的格式类型"""
    for level, pattern in RAW_TITLE_PATTERNS:
        if re.match(pattern, title):
            return level
    return None


def merge_title_only_chunks(chunks: List[Dict]) -> List[Dict]:
    """
    合并内容仅为标题的 chunk 到下一个 chunk
    这种情况通常是一级标题下直接接二级标题
    """
    if not chunks:
        return chunks

    def dedup_title_path(title_path: List[str]) -> List[str]:
        """对 title_path 去重，相同内容的标题只保留第一次出现的"""
        if not title_path:
            return title_path

        seen = set()
        result = []
        for title in title_path:
            title_stripped = title.strip()
            if title_stripped not in seen:
                seen.add(title_stripped)
                result.append(title)
        return result

    result = []
    i = 0

    while i < len(chunks):
        current = chunks[i]
        text = current["text"].strip()
        title_path = current["title_path"]

        # 检查是否是"只有标题"的 chunk
        is_title_only = False
        if title_path and text == title_path[-1].strip():
            is_title_only = True

        if is_title_only and i + 1 < len(chunks):
            # 与下一个 chunk 合并
            next_chunk = chunks[i + 1]
            # 合并 title_path 后去重
            merged_title_path = dedup_title_path(title_path + next_chunk["title_path"])
            merged = {
                "chunk_id": current["chunk_id"],
                "order": current["order"],
                "title_path": merged_title_path,
                "text": text + "\n" + next_chunk["text"],
                "page": next_chunk.get("page", current.get("page", 1))  # 保留页码，优先使用下一个chunk的页码
            }
            result.append(merged)
            i += 2  # 跳过下一个 chunk
        else:
            result.append(current)
            i += 1

    return result


def dedup_same_format_titles(chunks: List[Dict]) -> List[Dict]:
    """
    title_path 中相同格式（正则类型）的标题，除最后一个外进入待删除列表。
    检查待删除的标题是否在 text 中存在：如果存在则保留，不存在才删除。
    """
    result = []

    for chunk in chunks:
        title_path = chunk["title_path"]
        text = chunk.get("text", "")

        if not title_path:
            result.append(chunk)
            continue

        # 按格式类型分组记录所有位置
        format_positions = {}  # 格式类型 -> 位置索引列表

        for idx, title in enumerate(title_path):
            format_type = get_title_pattern_type(title)
            if format_type:
                if format_type not in format_positions:
                    format_positions[format_type] = []
                format_positions[format_type].append(idx)

        # 构建待删除索引列表（每种格式除最后一个外的所有索引）
        to_delete_indices = set()
        for positions in format_positions.values():
            if len(positions) > 1:
                # 除最后一个外的所有索引进入待删除列表
                to_delete_indices.update(positions[:-1])

        # 检查待删除的标题是否在 text 中存在
        # 如果标题在 text 中不存在（说明只是重复的标题，没有实际内容），才真正删除
        final_delete_indices = set()
        for idx in to_delete_indices:
            title_to_check = title_path[idx].strip()
            # 检查标题是否在 text 中出现（去除标题本身后的内容）
            if title_to_check not in text or text.strip() == title_to_check:
                # 标题不在 text 中，或者 text 只有这个标题（没有实际内容），可以删除
                final_delete_indices.add(idx)

        # 构建新的 title_path
        new_path = [title for idx, title in enumerate(title_path) if idx not in final_delete_indices]

        result.append({
            **chunk,
            "title_path": new_path
        })

    return result


def post_process_chunks(chunks: List[Dict], file_id: str = None) -> List[Dict]:
    """
    对生成的 chunk 进行后处理
    1. 合并仅有标题的 chunk
    2. 去重 title_path 中相同格式的标题
    3. 重新调整 order 和 chunk_id
    4. 保留页码信息
    5. 提取关键字
    """
    chunks = merge_title_only_chunks(chunks)

    # 重新调整 order 和 chunk_id
    for new_order, chunk in enumerate(chunks, start=1):
        chunk["order"] = new_order
        # 确保有 page 字段，如果没有则使用 1 作为默认值
        if "page" not in chunk:
            chunk["page"] = 1
        if file_id:
            # chunk_id 格式：{doc_id}_{order}，doc_id 使用毫秒级时间戳（纯数字）
            chunk["chunk_id"] = f"{file_id}_{new_order}"
            chunk["doc_id"] = file_id
        else:
            chunk["chunk_id"] = str(new_order)
            chunk["doc_id"] = "unknown"

        # 提取关键字
        chunk["keywords"] = extract_keywords(chunk.get("text", ""), top_k=10)
        chunk["length"] = len(chunk.get("text", ""))
        chunk["type"] = "text"  # 标记 chunk 类型

    return chunks


def split_pdf_to_chunks(pdf_path: str, file_id: str = None) -> tuple[List[Dict], List]:
    """
    从 PDF 文件直接生成 chunks

    TODO: 当前仅处理文本内容，表格和图片数据未包含
    TODO: 需要调用 split_tables_from_pdf() 和 split_images_from_pdf() 并合并结果

    Returns:
        (chunks, title_patterns): 分片列表和标题正则规则
    """
    pages = extract_pages(pdf_path)
    pages = remove_repeated_headers_footers(pages)
    lines = remove_page_numbers(pages)
    title_patterns = refine_title_patterns(lines)
    chunks = split_chunks(lines, title_patterns)
    chunks = post_process_chunks(chunks, file_id)
    return chunks, title_patterns


def extract_keywords(text: str, top_k: int = 10) -> List[str]:
    """
    使用 jieba.analyse.extract_tags 提取关键字

    Args:
        text: 输入文本
        top_k: 返回关键字数量

    Returns:
        关键字列表
    """
    try:
        import jieba.analyse
        keywords = jieba.analyse.extract_tags(text, topK=top_k)
        return keywords
    except Exception as e:
        print(f"关键字提取失败: {e}")
        return []



if __name__ == "__main__":
    pdf_path = r"F:\rag_project\backend\upload\sample.pdf"
    file_id = "1770601282.390849"
    text_chunks, title_patterns = split_pdf_to_chunks(pdf_path, file_id)
    # 打印分片信息
    print(f"\n========== 文本分片结果 ==========")
    print(f"分片数量: {len(text_chunks)}")
    print(f"标题规则: {title_patterns}")
    print(f"{'=' * 40}")

    import json

    for i, chunk in enumerate(text_chunks, 1):
        print(f"\n--- 分片 {i} ---")
        print(json.dumps(chunk, ensure_ascii=False, indent=2))

    print(f"\n{'=' * 40}\n")
