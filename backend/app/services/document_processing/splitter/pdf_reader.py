"""
PDF 文档内容读取模块
整合了 test_1.py 的表格解析逻辑，提供统一的 PDF 内容提取接口

核心功能：
- 页眉页脚检测
- 页码识别
- 表头识别（基于元素数量变化）
- 表格扩充（处理行列合并）
- 多级表头扁平化
- 续表判断
"""
import pdfplumber
from collections import defaultdict
import re
from typing import List, Dict, Any, Optional


# =========================
# 工具函数：文本清洗
# =========================
def clean(s):
    """基础文本清洗"""
    if s is None:
        return ""
    return str(s).replace("\n", " ").strip()


def clean_cell(cell):
    """清洗单元格内容"""
    if cell is None:
        return ""
    return str(cell).replace("\n", " ").strip()


# =========================
# 行合并函数
# =========================
def merge_words_to_lines(words, tolerance=3):
    """
    将单词列表按 top 坐标合并成行

    Args:
        words: extract_words() 返回的单词列表
        tolerance: top 坐标容差（像素），默认3

    Returns:
        List[Dict]: 合并后的行列表，每行包含 text, top, x0
    """
    if not words:
        return []

    # 按 top 分组
    groups = []

    for word in words:
        word_top = word["top"]
        word_text = word["text"]
        word_x0 = word["x0"]

        # 查找是否有相近的 top 组
        found = False
        for group in groups:
            if abs(group["top"] - word_top) <= tolerance:
                group["words"].append({
                    "text": word_text,
                    "x0": word_x0
                })
                found = True
                break

        if not found:
            groups.append({
                "top": word_top,
                "words": [{"text": word_text, "x0": word_x0}]
            })

    # 每组内按 x0 排序后合并
    lines = []
    for group in groups:
        group["words"].sort(key=lambda w: w["x0"])
        line_text = " ".join(w["text"] for w in group["words"])
        lines.append({
            "text": line_text,
            "top": group["top"],
            "x0": group["words"][0]["x0"] if group["words"] else 0
        })

    return lines


# =========================
# 页眉页脚 + 页码识别
# =========================
class PageHeaderFooterDetector:
    """页眉页脚检测器"""
    def __init__(self):
        self.top_counts = defaultdict(int)
        self.bottom_counts = defaultdict(int)
        self.total_pages = 0
        # 存储每个页面的高度信息，用于判断位置
        self.page_heights = []
        # 页码识别相关
        self.page_num_format = None  # 页码格式
        self.page_num_pos = None     # 页码位置
        self.page_num_value = None   # 上一个页码值

    def analyze_all_pages(self, pdf_path):
        """分析所有页面，识别页眉页脚模式"""
        all_lines = []
        self.page_heights = []
        with pdfplumber.open(pdf_path) as pdf:
            self.total_pages = len(pdf.pages)
            for page in pdf.pages:
                lines = self._get_clean_lines(page)
                all_lines.append(lines)
                self.page_heights.append(page.height)

        for lines in all_lines:
            # 统计前3行
            top3 = lines[:3]
            for l in top3:
                if l:
                    self.top_counts[l] += 1
            # 统计后3行，如果不足3行则统计所有行
            bottom3 = lines[-3:] if len(lines) >= 3 else lines[:]
            for l in bottom3:
                if l:
                    self.bottom_counts[l] += 1

    def _get_clean_lines(self, page):
        """获取页面上的非表格区域文本行"""
        tables = page.find_tables()
        table_boxes = [t.bbox for t in tables]
        words = []
        for w in page.extract_words():
            x0, y0 = w["x0"], w["top"]
            inside = False
            for (tx0, ty0, tx1, ty1) in table_boxes:
                if tx0 - 1 <= x0 <= tx1 + 1 and ty0 - 1 <= y0 <= ty1 + 1:
                    inside = True
                    break
            if not inside:
                txt = clean(w["text"])
                if txt:
                    words.append(txt)
        return words

    def extract_page_num(self, text):
        """
        提取页码数字和格式类型

        Returns:
            tuple: (页码数字, 格式类型) 或 (None, None)
            格式类型: 'chinese'（第X页）, 'slash'（X/Y）, 'pure'（纯数字）, 'page_en'（Page X）, None
        """
        t = text.strip()

        # 优先匹配特定格式（减少误判）
        # 格式1：第X页 / 第X节
        m = re.search(r'第\s*(\d+)\s*[页节条款]', text)
        if m: return (int(m.group(1)), 'chinese')

        # 格式2：X/Y 或 X\Y
        m = re.match(r'^(\d+)\s*[\\/]\s*\d+$', t)
        if m: return (int(m.group(1)), 'slash')

        # 格式3：Page X / page X
        m = re.search(r'[Pp]age\s*(\d+)', text)
        if m: return (int(m.group(1)), 'page_en')

        # 格式4：纯数字（仅当文本只有一个数字时）
        # 使用正则确保只匹配ASCII数字，排除②等Unicode数字
        if re.match(r'^\d+$', t) and len(t) <= 3:  # 限制长度，避免年份等长数字
            return (int(t), 'pure')

        return (None, None)

    def is_page(self, text, top, page_num):
        """
        判断文本是否为页码

        新逻辑：
        1. 同一文档只有一种页码格式
        2. 第一次检测到页码时，记录格式和位置
        3. 后续检测时，只有格式匹配、位置相同、数字连续才认为是页码
        """
        num, format_type = self.extract_page_num(text)
        if num is None:
            return False

        key = round(top, 0)

        # 第一次检测到页码
        if self.page_num_format is None:
            # 检查数字是否匹配当前页码
            if num == page_num:
                self.page_num_format = format_type
                self.page_num_pos = key
                self.page_num_value = num
                return True
            return False

        # 后续检测：必须格式匹配、位置相同、数字连续
        format_match = (format_type == self.page_num_format)
        pos_match = (key == self.page_num_pos)
        num_match = (num == self.page_num_value + 1)

        if format_match and pos_match and num_match:
            self.page_num_value = num
            return True

        return False

    def is_hf(self, text, top, page_height, page_num):
        """
        判断文本是否为页眉或页脚

        Args:
            text: 文本内容
            top: 文本在页面中的顶部位置（y坐标）
            page_height: 页面高度
            page_num: 页码

        Returns:
            True 表示是页眉或页脚，应该被过滤
        """
        if not text:
            return True

        # 判断是否在页面顶部区域（前10%的区域）
        is_in_top_area = top <= page_height * 0.1
        # 判断是否在页面底部区域（后10%的区域）
        is_in_bottom_area = top >= page_height * 0.9

        # 只有在顶部或底部区域的文本才可能是页眉页脚
        if is_in_top_area:
            # 检查该文本是否在大部分页面的顶部出现过
            return self.top_counts[text] >= self.total_pages * 0.8
        elif is_in_bottom_area:
            # 检查该文本是否在大部分页面的底部出现过
            return self.bottom_counts[text] >= self.total_pages * 0.8

        # 不在顶部或底部区域，不是页眉页脚
        return False


# =========================
# 表格上下文（用于续表判断）
# =========================
class TableCtx:
    """表格上下文，用于处理跨页表格"""
    def __init__(self):
        self.cached = None  # 缓存完整的多级表头
        self.last_table = False
        self.last_header = False


# =========================
# 表格处理核心逻辑
# =========================
def fill_down(table):
    """向下填充，处理行合并"""
    if not table:
        return []

    filled = []
    last_row = [""] * len(table[0])

    for row in table:
        new_row = []
        for i, cell in enumerate(row):
            cell = clean_cell(cell)
            if cell == "":
                new_row.append(last_row[i])
            else:
                new_row.append(cell)
        filled.append(new_row)
        last_row = new_row

    return filled


def fill_right(table):
    """向右填充，处理列合并"""
    if not table:
        return []

    new_table = []

    for row in table:
        new_row = []
        last = ""
        for cell in row:
            if cell == "":
                new_row.append(last)
            else:
                new_row.append(cell)
                last = cell
        new_table.append(new_row)

    return new_table


def detect_header_end_simple(table):
    """
    表头识别逻辑
    - 只做向下填充
    - "" 认为无元素，非空认为有元素
    - 找到行元素首次不再增加 → 前一行才是表头最后一行
    """
    if not table:
        return -1

    filled_table = fill_down(table)
    prev_count = 0

    for i, row in enumerate(filled_table):
        current_count = sum(1 for c in row if c not in ("", None))
        if current_count <= prev_count and i > 0:
            # 元素数首次不再增加 → 前一行是表头最后一行
            return i - 1
        prev_count = current_count

    # 默认最后一行是表头
    return len(filled_table) - 1


def expand_table(cleaned_table, header_end_idx):
    """
    表格扩充逻辑
    根据规则扩充表格：
    - 表头：先右扩充再下扩充
    - 正文：先下扩充再右扩充
    """
    if not cleaned_table:
        return []

    header = cleaned_table[:header_end_idx + 1] if header_end_idx >= 0 else []
    content = cleaned_table[header_end_idx + 1:] if header_end_idx + 1 < len(cleaned_table) else []

    header_expanded = fill_down(fill_right(header)) if header else []
    content_expanded = fill_right(fill_down(content)) if content else []

    return header_expanded + content_expanded


def flatten_multi_level_headers(headers):
    """
    将多级表头扁平化为单级表头
    - 多级表头用点号连接：一级表头.二级表头
    - 如果下级表头与上级完全一致，则只保留上级
    - 支持三级或更多级表头

    Args:
        headers: 二维列表，如 [["姓名", "成绩"], ["", "语文", "数学"]]

    Returns:
        扁平化后的表头列表，如 ["姓名", "成绩.语文", "成绩.数学"]
    """
    if not headers:
        return []

    # 确定列数（以最多列的行为准）
    num_cols = max(len(row) for row in headers)

    # 对每一列，从上到下合并表头
    flat_headers = []
    for col_idx in range(num_cols):
        header_parts = []
        last_value = ""

        for row_idx, row in enumerate(headers):
            # 获取当前单元格的值
            cell_value = clean(row[col_idx]) if col_idx < len(row) else ""

            # 如果有值，且与上一个值不同，则添加
            if cell_value and cell_value != last_value:
                header_parts.append(cell_value)
                last_value = cell_value

        # 用点号连接多级表头
        if header_parts:
            flat_headers.append(".".join(header_parts))
        else:
            flat_headers.append("")

    return flat_headers


def merge_headers(headers, body):
    """合并重复表头"""
    if not headers or not body: return headers, body
    mapping = defaultdict(list)
    for i, name in enumerate(headers):
        if name: mapping[name].append(i)
    new_h = list(mapping.keys())
    new_b = []
    for row in body:
        nr = []
        for cols in mapping.values():
            vals = [row[c] for c in cols if c < len(row) and clean(row[c])]
            nr.append(" ".join(vals))
        new_b.append(nr)
    return new_h, new_b


def parse(table, ctx, force_new=False):
    """
    整合版本的表格解析函数
    - 使用 detect_header_end_simple 识别表头
    - 使用 expand_table 进行内容扩充
    - 保留续表判断和表头缓存逻辑
    """
    raw = table.extract()
    if not raw: return []

    # 清洗原始表格数据
    cleaned_table = [[clean_cell(cell) for cell in row] for row in raw]

    # 使用表头识别逻辑
    header_end_idx = detect_header_end_simple(cleaned_table)

    # 使用表格扩充逻辑
    expanded_table = expand_table(cleaned_table, header_end_idx)

    # 分离表头和正文
    headers = expanded_table[:header_end_idx + 1] if header_end_idx >= 0 else []
    body = expanded_table[header_end_idx + 1:] if header_end_idx + 1 < len(expanded_table) else []

    # 续表判断逻辑
    if force_new or not ctx.cached:
        ctx.cached = headers  # 缓存表头
        ctx.last_header = len(body) == 0 and len(headers) > 0
    else:
        headers = ctx.cached
        body = expanded_table  # 续表时，全部数据作为正文
        ctx.last_header = False

    # 扁平化多级表头
    flat_headers = []
    if headers:
        flat_headers = flatten_multi_level_headers(headers)

    # 合并重复表头
    if flat_headers and body:
        flat_headers, body = merge_headers(flat_headers, body)

    # 转换为字典列表（保留所有字段，包括空表头和空值）
    res = []
    for r in body:
        d = {}
        for i, k in enumerate(flat_headers):
            # 保留所有表头字段，包括空的
            # 值为None时显示为""
            val = r[i] if i < len(r) else ""
            d[k] = "" if val is None else val
        res.append(d)

    ctx.last_table = len(body) > 0 or ctx.last_header
    return res


# =========================
# 过滤函数
# =========================
def filter_elements(elems, page_num, page_height, hf_detector):
    """过滤页眉页脚和页码"""
    res = []
    for e in elems:
        if e["type"] != "text":
            res.append(e)
            continue
        txt = e["content"]
        top = e["top"]
        is_p = hf_detector.is_page(txt, top, page_num)
        is_h = hf_detector.is_hf(txt, top, page_height, page_num)
        if not is_p and not is_h:
            res.append(e)
    final = []
    for e in res:
        if e["type"] == "text":
            if e["content"].strip():
                final.append(e)
        else:
            final.append(e)
    return final


# =========================
# 主函数：提取 PDF 内容
# =========================
def extract_pdf_content(pdf_path: str) -> List[Dict[str, Any]]:
    """
    提取 PDF 完整内容（文本 + 表格）

    Args:
        pdf_path: PDF 文件路径

    Returns:
        List[Dict]: 包含所有文本行和表格的列表
            - type: "text" 或 "table"
            - content: 文本内容或表格数据
            - top: 顶部位置
            - page_number: 页码
    """
    print("\n" + "=" * 60)
    print("【PDF 内容提取（使用 test_1.py 逻辑）】")
    print("=" * 60)

    # 初始化页眉页脚检测器
    hf = PageHeaderFooterDetector()
    print("正在全局分析PDF页眉、页脚、页码...")
    hf.analyze_all_pages(pdf_path)
    print("页眉页脚分析完成\n")

    ctx = TableCtx()
    all_elements = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            elements = []
            tables = page.find_tables()
            table_boxes = [t.bbox for t in tables]

            # 提取非表格区域的文本（使用行合并）
            # 先提取所有单词并按 top 合并成行
            all_words = page.extract_words()
            all_lines = merge_words_to_lines(all_words, tolerance=3)

            # 提取非表格区域的文本行
            for line in all_lines:
                x0 = line["x0"]
                y0 = line["top"]

                # 判断行是否在表格内（使用行的第一个字符位置代表整行）
                inside = False
                for (tx0, ty0, tx1, ty1) in table_boxes:
                    if tx0 - 1 <= x0 <= tx1 + 1 and ty0 - 1 <= y0 <= ty1 + 1:
                        inside = True
                        break

                if not inside:
                    elements.append({
                        "type": "text",
                        "content": clean(line["text"]),  # 整行文本
                        "top": y0
                    })

            # 添加表格占位元素
            table_elems = []
            for t in tables:
                table_elems.append({
                    "type": "table",
                    "content": [],
                    "top": t.bbox[1]
                })

            # 合并并按位置排序
            all_elems = elements + table_elems
            all_elems.sort(key=lambda x: x["top"])

            # 过滤页眉页脚和页码
            valid = filter_elements(all_elems, page_num, page.height, hf)

            # 逐行处理，动态清空缓存
            cache_cleared = False
            final = []

            for elem in valid:
                if elem["type"] == "text":
                    # 遇到文本立即清空缓存（仅一次）
                    if not cache_cleared:
                        ctx.cached = None
                        ctx.last_table = False
                        ctx.last_header = False
                        cache_cleared = True
                    final.append(elem)

                elif elem["type"] == "table":
                    # 续表判断：未清空缓存 + 有缓存 + 上一页是表格
                    need_continue = (not cache_cleared) and ctx.cached and ctx.last_table

                    idx = table_elems.index(elem)
                    parsed = parse(tables[idx], ctx, force_new=not need_continue)
                    final.append({
                        "type": "table",
                        "content": parsed,
                        "top": elem["top"]
                    })

            # 收集结果
            for elem in final:
                # 添加页码信息
                elem_copy = elem.copy()
                elem_copy["page_number"] = page_num
                all_elements.append(elem_copy)

    # ==================== 提取完成总结 ====================
    print(f"\n{'='*60}")
    print("【PDF 提取完成】")
    print(f"{'='*60}")
    print(f"总元素数: {len(all_elements)}")

    text_count = sum(1 for e in all_elements if e["type"] == "text")
    table_count = sum(1 for e in all_elements if e["type"] == "table")

    print(f"文本元素数: {text_count}")
    print(f"表格元素数: {table_count}")
    print(f"{'='*60}\n")

    return all_elements


# =========================
# 格式化表格为文本
# =========================
def format_table_as_text(table_data: List[Dict]) -> str:
    """
    将表格数据格式化为可读文本

    Args:
        table_data: 表格数据列表（每行是字典）

    Returns:
        str: 格式化的表格文本
    """
    if not table_data:
        return ""

    lines = []

    # 输出数据行
    for item in table_data:
        row_text = " | ".join(f"{k}: {v}" for k, v in item.items() if k)
        if row_text:
            lines.append(row_text)

    return "\n".join(lines)
