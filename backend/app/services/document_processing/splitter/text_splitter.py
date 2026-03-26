"""
================================================================================
文本分片服务 - PDF 智能分片完整流程
================================================================================

【功能说明】
将 PDF 文档中的文本内容和表格内容按标题层级智能切分成多个语义分片（chunks），
每个分片包含完整的标题路径和文本内容，保证所有分片拼接后为完整文档。

【主入口函数】
- split_pdf_to_chunks(pdf_path)  # 从 PDF 文件路径直接生成分片（包含完整预处理）

【更新内容】
- 整合表格提取功能，支持 PDF 文档中表格数据的完整提取
- 表格内容会被格式化为可读文本并参与分片

================================================================================
【PDF 分片完整拆分步骤】（split_pdf_to_chunks 函数流程）
================================================================================

第一步：提取页面文本和表格（extract_pages_with_tables）
--------------------------------------
1. 使用 pdfplumber 打开 PDF 文件
2. 逐页遍历，识别表格区域和文本区域
3. 提取非表格区域的文本行
4. 提取表格内容并格式化为文本
5. 合并文本和表格内容，保持原始顺序
6. 返回：List[Dict]，包含所有文本行（包含表格内容）


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


第四步：使用TitleDetector识别标题和目录（refine_title_patterns）
--------------------------------------
使用 chapter_breakdown.py 中的 TitleDetector 类来检测标题和目录：
1. 提取所有候选标题行（符合标题正则规则的行）
2. 检测目录范围（连续符合标题结构且以页码结尾，章节名在后面重复出现）
3. 过滤掉目录区域内的标题，只保留正文标题
4. 按规则首次出现顺序分配层级
5. 构建标题树
6. 返回：标题树列表和目录范围


第五步：按标题层级构建分片（split_chunks）
--------------------------------------
1. 目录前的内容为第一个chunk
2. 目录为第二个chunk（如果没有目录，则正文标题前的内容为第一个chunk）
3. 之后按照标题树结构，按行进行chunk拆分：
   - 每个标题行作为一个chunk的开始
   - 从该标题行到下一个同级或更高级标题行之前的内容都属于该chunk
4. 每个chunk包含：chunk_id、order、title_path、text、page、type


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
【标题规则定义】（使用 TitleDetector 类）
================================================================================

TitleDetector 类支持的标题规则：
- CN_CHAPTER: 第X章(中文数字) 如：第一章 概述
- CN_PART: 第X部分(中文数字) 如：第一部分 背景
- CN_SECTION: 第X节(中文数字) 如：第一节 绪论
- CN_ARTICLE: 第X篇(中文数字) 如：第一篇 总则
- CN_ITEM: 第X条(中文数字) 如：第一条 总则
- NUM_CHAPTER: 第X章(阿拉伯数字) 如：第1章 概述
- NUM_PART: 第X部分(阿拉伯数字) 如：第1部分 背景
- NUM_SECTION: 第X节(阿拉伯数字) 如：第1节 绪论
- NUM_ARTICLE: 第X篇(阿拉伯数字) 如：第1篇 总则
- NUM_ITEM: 第X条(阿拉伯数字) 如：第1条 总则
- NUM_DECIMAL: 序号 如：1.1 概述
- NUM_SIMPLE: 纯数字+空格 如：1 概述
- CN_LIST: 纯中文+顿号 如：一、概述

注意：
1. 使用 TitleDetector 类自动检测标题规则
2. 规则会按首次出现顺序确定层级
3. 目录区域会被单独识别并处理

================================================================================
"""
import re
import pdfplumber
import logging
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, Counter
import difflib
import sys
from pathlib import Path

# 导入 TitleDetector 类
from .chapter_breakdown import TitleDetector, build_outline
# 导入新的 PDF 读取模块
from .pdf_reader import extract_pdf_content, format_table_as_text

logger = logging.getLogger(__name__)

# ============================================================================
# 固化的标题正则规则（所有文档统一使用这套规则）
# ============================================================================

# 中文数字映射
CHINESE_NUMS = '一二三四五六七八九十百千零'

# 固化标题规则定义（带ID）
FIXED_TITLE_RULES = [
    {
        "id": "rule_001",
        "name": "第X章(中文数字)",
        "regex": r'^第[一二三四五六七八九十百]+章\b\s*(.+)',
        "description": "如：第一章 概述"
    },
    {
        "id": "rule_002",
        "name": "第X节(中文数字)",
        "regex": r'^第[一二三四五六七八九十百]+节\b\s*(.+)',
        "description": "如：第一节 背景"
    },
    {
        "id": "rule_003",
        "name": "第X篇(中文数字)",
        "regex": r'^第[一二三四五六七八九十百]+篇\b\s*(.+)',
        "description": "如：第一篇 绪论"
    },
    {
        "id": "rule_004",
        "name": "第X条(中文数字)",
        "regex": r'^第[一二三四五六七八九十百]+条\b\s*(.+)',
        "description": "如：第一条 总则"
    },
    {
        "id": "rule_005",
        "name": "第X章(阿拉伯数字)",
        "regex": r'^第\d+章\b\s*(.+)',
        "description": "如：第1章 概述"
    },
    {
        "id": "rule_006",
        "name": "第X节(阿拉伯数字)",
        "regex": r'^第\d+节\b\s*(.+)',
        "description": "如：第1节 背景"
    },
    {
        "id": "rule_007",
        "name": "第X篇(阿拉伯数字)",
        "regex": r'^第\d+篇\b\s*(.+)',
        "description": "如：第1篇 绪论"
    },
    {
        "id": "rule_008",
        "name": "第X条(阿拉伯数字)",
        "regex": r'^第\d+条\b\s*(.+)',
        "description": "如：第1条 总则"
    },
    {
        "id": "rule_009",
        "name": "纯中文+空格",
        "regex": r'^[一二三四五六七八九十百]+[　\s]+(.+)',
        "description": "如：一  概述"
    },
    {
        "id": "rule_010",
        "name": "纯中文+顿号",
        "regex": r'^[一二三四五六七八九十百]+[、,]\s*(.+)',
        "description": "如：一、概述"
    },
    {
        "id": "rule_011",
        "name": "纯数字+空格",
        "regex": r'^\d+[　\s]+(.+)',
        "description": "如：1  概述"
    },
    {
        "id": "rule_012",
        "name": "纯数字+顿号",
        "regex": r'^\d+[、,]\s*(.+)',
        "description": "如：1、概述"
    },
    {
        "id": "rule_013",
        "name": "序号+空格",
        "regex": r'^\d+(?:\.\d+)+[　\s]+(.+)',
        "description": "如：1.1  概述"
    },
    {
        "id": "rule_014",
        "name": "序号+顿号",
        "regex": r'^\d+(?:\.\d+)+[、,]\s*(.+)',
        "description": "如：1.1、概述"
    },
]

# 编译正则表达式缓存
_COMPILED_PATTERNS = {rule["id"]: re.compile(rule["regex"]) for rule in FIXED_TITLE_RULES}

# 全局变量：存储目录区域的行索引
_toc_indices: set = set()

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
            # 手动提取完整的章节前缀（包括"章"、"节"、"篇"字）
            chapter_match = re.match(r'^(第[一二三四五六七八九十百]+[章节篇])\s*', text)
            if chapter_match:
                features['prefix_pattern'] = chapter_match.group(1)

        # 提取前缀模式（用于后续聚类）- 只有在章节格式未设置时才执行
        if 'prefix_pattern' not in features:
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
    chapter_keyword_count = 0  # 统计"第X章"格式的数量

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
            chapter_keyword_count += 1
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

    logger.debug(f"[标题候选筛选] 找到 {len(candidates)} 个候选, 其中 {chapter_keyword_count} 个章节格式标题")

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

    # 过滤掉出现次数太少的模式
    # - 章节格式(chinese_chapter)至少出现1次即可（文档通常只有一个"第一章"）
    # - 其他格式至少出现2次
    filtered_patterns = {}
    for k, v in pattern_groups.items():
        if k == 'chinese_chapter':
            # 章节格式放宽限制
            if v['count'] >= 1:
                filtered_patterns[k] = v
        else:
            # 其他格式需要至少出现2次
            if v['count'] >= 2:
                filtered_patterns[k] = v

    logger.debug(f"[模式合并] 原始模式 {len(pattern_groups)} 个, 过滤后 {len(filtered_patterns)} 个")

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
        logger.debug(f"[自动检测] 未检测到标题候选，将使用预设规则")
        return []

    # 第三步：合并相似模式
    pattern_groups = merge_similar_patterns(candidates)

    if not pattern_groups:
        print(f"  [自动检测] 未找到有效的标题模式组，将使用预设规则")
        return []

    # 第四步：确定层级顺序
    detected_patterns = determine_pattern_hierarchy(pattern_groups, lines)

    print(f"  [自动检测] 检测到 {len(detected_patterns)} 个标题模式")

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


# ============================================
# 🆕 表格提取模块（整合 test_1.py 逻辑）
# - 使用 title.py 的表头识别和内容扩充逻辑
# - 支持多级表头扁平化
# - 保留空值字段
# ============================================

# 注意：表格处理逻辑已移至 pdf_reader.py（基于 test_1.py）
# 以下保留旧函数用于向后兼容

def clean_cell(s):
    """清洗单元格内容"""
    if s is None:
        return ""
    return str(s).replace("\n", " ").strip()


def extract_pages_with_tables(pdf_path: str) -> List[Dict]:
    """
    从 PDF 中提取所有页面内容（包括文本和表格）
    使用 pdf_reader.py 中的逻辑（基于 test_1.py）

    Returns:
        List[Dict]: 包含所有文本行的列表，每行包含 text, top, page_number
    """
    # 使用新的 PDF 读取模块
    all_elements = extract_pdf_content(pdf_path)

    # 转换为统一格式
    all_lines = []

    for elem in all_elements:
        if elem["type"] == "text":
            all_lines.append({
                "text": elem["content"],
                "top": elem["top"],
                "page_number": elem["page_number"]
            })
        elif elem["type"] == "table":
            # 将表格转换为文本行
            table_text = format_table_as_text(elem["content"])
            if table_text:
                # 按行分割表格内容
                for line in table_text.split("\n"):
                    if line.strip():
                        all_lines.append({
                            "text": line.strip(),
                            "top": elem["top"],
                            "page_number": elem["page_number"]
                        })

    return all_lines


def remove_header_footer_from_elements(elements):
    """从元素列表中去除页眉页脚"""
    if len(elements) < 3:
        return elements

    HEADER_LINES = 2
    FOOTER_LINES = 2
    header_candidates = []
    footer_candidates = []

    for idx, elem in enumerate(elements):
        if elem["type"] != "text":
            continue
        txt = elem["content"].strip()
        if idx < HEADER_LINES:
            header_candidates.append(txt)
        elif idx >= len(elements) - FOOTER_LINES:
            footer_candidates.append(txt)

    def is_likely_page_num(s):
        return any(k in s for k in ["第", "页", "页码", "Page", "page"]) or s.isdigit()

    new_elements = []
    for idx, elem in enumerate(elements):
        if elem["type"] != "text":
            new_elements.append(elem)
            continue

        txt = elem["content"].strip()
        is_header = idx < HEADER_LINES and txt in header_candidates
        is_footer = idx >= len(elements) - FOOTER_LINES and txt in footer_candidates
        is_page = is_likely_page_num(txt)

        if is_header or is_footer or is_page:
            continue
        new_elements.append(elem)

    return new_elements


def extract_pages(pdf_path: str) -> List[List[Dict]]:
    """从 PDF 中提取所有页面（排除表格）- 保留用于向后兼容"""
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


def refine_title_patterns(lines: List[Dict]) -> Tuple[List, Dict]:
    """
    使用 TitleDetector 类进行标题检测和目录识别

    流程：
    1. 将 Dict 类型的 lines 转换为字符串列表
    2. 使用 TitleDetector 提取候选标题
    3. 检测目录范围
    4. 过滤标题（只保留正文标题）
    5. 按规则首次出现顺序分配层级
    6. 构建标题树

    Returns:
        Tuple[List, Dict]: (标题树列表, 目录范围信息)
        标题树格式: [{"title": "标题文本", "line": 行号, "rule": 规则ID, "level": 层级, "children": [...]}]
        目录范围: {"toc_start": 开始行号, "toc_end": 结束行号} 或 None
    """
    print(f"\n{'='*60}")
    print(f"【开始标题格式识别 - TitleDetector版本】")
    print(f"{'='*60}")

    if not lines:
        print(f"  [警告] 文档为空，无法检测标题")
        return [], None

    # 第一步：将 Dict 类型的 lines 转换为字符串列表（保留原始行索引）
    lines_as_strings = [line.get("text", "") for line in lines]

    print(f"\n  [步骤1] 使用 TitleDetector 扫描 {len(lines_as_strings)} 行文本...")

    # 第二步：使用 TitleDetector 检测标题和目录
    detector = TitleDetector()

    # 提取候选标题
    candidates = detector.extract_candidates(lines_as_strings)
    logger.debug(f"发现 {len(candidates)} 个候选标题")

    # 检测目录范围
    toc_range = detector.detect_toc(candidates, lines_as_strings)

    # 过滤标题（只保留正文标题）
    titles = detector.filter_titles(candidates, toc_range)
    logger.debug(f"过滤目录后剩余标题: {len(titles)} 个")

    # 分配层级
    titles = detector.assign_levels(titles)

    # 构建标题树
    tree = detector.build_tree(titles)

    # 保存目录范围信息
    toc_info = None
    if toc_range:
        toc_info = {"toc_start": toc_range[0], "toc_end": toc_range[1]}

    return tree, toc_info


def split_chunks(lines: List[Dict], title_tree: List, toc_info: Dict = None) -> List[Dict]:
    """
    按标题层级构建 chunks

    新规则：
    1. 目录前的内容为第一个chunk
    2. 目录为第二个chunk（如果没有目录，则正文标题前的内容为第一个chunk）
    3. 之后按照标题树结构，按行进行chunk拆分

    Args:
        lines: 文本行列表（Dict类型，包含text和page_number）
        title_tree: 标题树列表（由refine_title_patterns返回）
        toc_info: 目录范围信息 {"toc_start": 开始行号, "toc_end": 结束行号}

    Returns:
        chunks列表
    """
    logger.debug(f"开始按标题层级拆分 Chunks，总行数: {len(lines)}, 标题树节点数: {len(title_tree)}")

    chunks = []
    order = 0

    # 将标题树展平为按行号排序的列表
    def flatten_tree(tree, level=1, parent_path=[]):
        """将标题树展平为列表，每个元素包含标题信息和层级"""
        result = []
        for node in tree:
            title_path = parent_path + [node["title"]]
            result.append({
                "title": node["title"],
                "line": node["line"],  # 1-based 行号
                "level": node["level"],
                "rule": node["rule"],
                "title_path": title_path.copy()
            })
            # 递归处理子节点
            if node.get("children"):
                result.extend(flatten_tree(node["children"], level + 1, title_path))
        return result

    # 展平标题树
    flat_titles = flatten_tree(title_tree)
    # 按行号排序
    flat_titles.sort(key=lambda x: x["line"])

    # 获取目录范围
    toc_start = toc_info.get("toc_start") - 1 if toc_info else None  # 转换为0-based
    toc_end = toc_info.get("toc_end") - 1 if toc_info else None  # 转换为0-based

    def is_catalog_title(text: str) -> bool:
        """判断是否是目录标题（如"目录"、"目  录"、"CONTENTS"等）"""
        text = text.strip().replace(" ", "").replace("　", "")
        catalog_keywords = ["目录", "目錄", "contents", "catalog", "index"]
        text_lower = text.lower()
        for keyword in catalog_keywords:
            if keyword in text_lower or text_lower in keyword:
                return True
        return False

    # 第一步：处理目录前的内容
    pre_catalog_lines = []
    pre_catalog_end = toc_start - 1 if toc_start is not None else -1

    print(f"\n[步骤1] 处理目录前的内容")
    if pre_catalog_end >= 0:
        for i in range(pre_catalog_end + 1):
            text = lines[i].get("text", "").strip()
            if text:
                pre_catalog_lines.append(text)

        if pre_catalog_lines:
            order += 1
            chunk = {
                "chunk_id": str(order),
                "order": order,
                "title_path": [],
                "text": "\n".join(pre_catalog_lines),
                "page": lines[0].get("page_number", 1),
                "type": "text"
            }
            chunks.append(chunk)
    else:
        logger.debug("无目录前内容")

    # 第二步：处理目录内容
    catalog_lines = []
    if toc_start is not None and toc_end is not None:
        for i in range(toc_start, toc_end + 1):
            text = lines[i].get("text", "").strip()
            if text:
                catalog_lines.append(text)

        if catalog_lines:
            order += 1
            chunk = {
                "chunk_id": str(order),
                "order": order,
                "title_path": ["目录"],
                "text": "\n".join(catalog_lines),
                "page": lines[toc_start].get("page_number", 1),
                "type": "catalog"
            }
            chunks.append(chunk)
    else:
        logger.debug("无目录内容")

    # 第三步：按标题树拆分正文内容
    # 确定正文起始行
    content_start = toc_end + 1 if toc_end is not None else 0
    if content_start >= len(lines):
        content_start = len(lines) - 1

    logger.debug(f"正文起始行: {content_start + 1}")

    # 构建行号到标题的映射（只包含正文区域）
    line_to_title = {}
    for title_info in flat_titles:
        line_num = title_info["line"] - 1  # 转换为0-based
        if line_num >= content_start:
            line_to_title[line_num] = title_info

    logger.debug(f"标题行数量: {len(line_to_title)}")

    # 获取排序后的标题行号列表
    sorted_title_lines = sorted(line_to_title.keys())

    # 分组连续的标题行
    title_groups = []
    i = 0
    while i < len(sorted_title_lines):
        current_line = sorted_title_lines[i]
        current_group = [current_line]

        # 检查后续行是否连续
        while i + 1 < len(sorted_title_lines):
            next_line = sorted_title_lines[i + 1]
            if next_line == current_line + 1:
                # 连续的行
                current_group.append(next_line)
                current_line = next_line
                i += 1
            else:
                # 不连续，停止
                break

        title_groups.append(current_group)
        i += 1

    logger.debug(f"连续标题分组数: {len(title_groups)}")

    # 兜底逻辑：如果没有检测到标题，将整个正文内容作为一个chunk
    if not title_groups and content_start < len(lines):
        print(f"\n  [兜底处理] 未检测到标题，将整个正文内容作为一个chunk")

        # 收集所有正文内容
        content_lines = []
        for j in range(content_start, len(lines)):
            text = lines[j].get("text", "").strip()
            if text:
                content_lines.append(text)

        if content_lines:
            order += 1
            chunk = {
                "chunk_id": str(order),
                "order": order,
                "title_path": [],  # 无标题路径
                "text": "\n".join(content_lines),
                "page": lines[content_start].get("page_number", 1),
                "type": "text"
            }
            chunks.append(chunk)

            print(f"  创建了1个无标题chunk，包含 {len(content_lines)} 行文本")

    # 为每个分组创建chunk
    for group_idx, title_lines in enumerate(title_groups):
        # 获取该分组中所有标题信息
        group_titles = [line_to_title[l] for l in title_lines]

        # chunk 的起始行是第一个标题行
        chunk_start = title_lines[0]

        # chunk 的结束行是下一个标题行之前，或者文档末尾
        if group_idx + 1 < len(title_groups):
            chunk_end = title_groups[group_idx + 1][0]
        else:
            chunk_end = len(lines)

        # 标题路径使用最后一个标题的路径
        last_title = group_titles[-1]
        chunk_title_path = last_title["title_path"]
        chunk_page = lines[chunk_start].get("page_number", 1)

        # 收集该chunk的所有内容
        chunk_lines = []
        for j in range(chunk_start, chunk_end):
            text = lines[j].get("text", "").strip()
            if text:
                chunk_lines.append(text)

        if chunk_lines:
            order += 1
            chunk = {
                "chunk_id": str(order),
                "order": order,
                "title_path": chunk_title_path,
                "text": "\n".join(chunk_lines),
                "page": chunk_page,
                "type": "text"
            }
            chunks.append(chunk)

    return chunks


def get_title_pattern_type(title: str) -> Optional[str]:
    """获取标题匹配的格式类型"""
    for rule in FIXED_TITLE_RULES:
        pattern = _COMPILED_PATTERNS[rule["id"]]
        if pattern.match(title):
            return rule["id"]
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


def post_process_chunks(chunks: List[Dict], file_id: str = None, kb_id: str = None) -> List[Dict]:
    """
    对生成的 chunk 进行后处理
    1. 合并仅有标题的 chunk
    2. 去重 title_path 中相同格式的标题
    3. 重新调整 order 和 chunk_id
    4. 保留页码信息
    5. 提取关键字
    6. 添加知识库 ID
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

        # 添加知识库 ID（如果有）
        if kb_id:
            chunk["kb_id"] = kb_id

        # 提取关键字
        chunk["keywords"] = extract_keywords(chunk.get("text", ""), top_k=10)
        chunk["length"] = len(chunk.get("text", ""))
        # 保留原有的type字段（如catalog），如果没有则设置为text
        if "type" not in chunk:
            chunk["type"] = "text"

    return chunks


def split_pdf_to_chunks(pdf_path: str, file_id: str = None, kb_id: str = None) -> tuple[List[Dict], Dict]:
    """
    从 PDF 文件直接生成 chunks

    功能说明：
    - 提取 PDF 中的文本和表格内容
    - 表格内容会被格式化为可读文本并参与分片
    - 支持跨页表格的智能识别和合并
    - 自动去除页眉页脚

    Args:
        pdf_path: PDF 文件路径
        file_id: 文档 ID
        kb_id: 知识库 ID（可选）

    Returns:
        (chunks, result_info): 分片列表和结果信息
        result_info包含: {"title_tree": 标题树, "toc_info": 目录信息}
    """
    # 使用新的表格提取功能（固定包含表格）
    lines = extract_pages_with_tables(pdf_path)

    # 使用新的TitleDetector进行标题检测
    title_tree, toc_info = refine_title_patterns(lines)
    chunks = split_chunks(lines, title_tree, toc_info)
    chunks = post_process_chunks(chunks, file_id, kb_id)

    # 为了向后兼容，生成空的 title_patterns（不再使用正则规则验证）
    # 新的验证逻辑应该基于 title_tree
    result_info = {
        "title_tree": title_tree,
        "toc_info": toc_info,
        "title_patterns": []  # 空列表，表示不使用旧的验证方式
    }

    return chunks, result_info


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
        logger.error(f"关键字提取失败: {e}")
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
