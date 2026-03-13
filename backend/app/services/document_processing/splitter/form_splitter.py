"""
表格分片服务
处理 PDF 中提取的表格数据的切片和结构化处理
"""
from typing import List, Dict, Any


def split_tables(tables: List[Dict]) -> List[Dict[str, Any]]:
    """
    对表格列表进行分片处理

    Args:
        tables: 原始表格数据列表，每个元素包含：
            - page: 页码
            - index: 表格索引
            - headers: 表头列表
            - rows: 数据行列表
            - bbox: 表格位置 (x0, y0, x1, y1)

    Returns:
        List[Dict]: 表格分片列表，每个分片包含：
            - chunk_id: 分片ID
            - type: "table"
            - page: 页码
            - headers: 表头路径（支持多级表头）
            - content: 格式化的表格内容
            - row_count: 行数
            - bbox: 表格位置
    """
    if not tables:
        return []

    chunks = []

    for idx, table_data in enumerate(tables):
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])

        # 构建表头路径
        header_path = build_header_path(headers)

        # 格式化表格内容
        content = format_table_content(headers, rows)

        chunk = {
            "chunk_id": f"table_{table_data.get('page', 0)}_{idx}",
            "type": "table",
            "page": table_data.get("page", 0),
            "order": idx + 1,
            "headers": header_path,
            "content": content,
            "row_count": len(rows),
            "col_count": len(headers),
            "bbox": table_data.get("bbox", []),
        }
        chunks.append(chunk)

    return chunks


def build_header_path(headers: List[str]) -> List[str]:
    """
    构建表头路径

    Args:
        headers: 表头列表（支持多级表头用 "." 分隔）

    Returns:
        List[str]: 表头路径列表
    """
    path = []
    for header in headers:
        if not header:
            path.append("未命名")
        elif "." in header:
            # 多级表头：如 "基本信息.姓名"
            parts = header.split(".")
            path.extend(parts)
        else:
            path.append(header)
    return path


def format_table_content(headers: List[str], rows: List[List[str]]) -> str:
    """
    将表格数据格式化为文本

    Args:
        headers: 表头列表
        rows: 数据行列表

    Returns:
        str: 格式化的表格文本
    """
    if not headers and not rows:
        return ""

    lines = []

    # 添加表头
    if headers:
        lines.append(" | ".join(headers))

    # 添加分隔线
    if headers:
        lines.append("-" * len(lines[0]))

    # 添加数据行
    for row in rows:
        lines.append(" | ".join(str(cell) if cell else "" for cell in row))

    return "\n".join(lines)


def split_tables_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    直接从 PDF 文件提取表格并进行分片

    Args:
        pdf_path: PDF 文件路径

    Returns:
        List[Dict]: 表格分片列表
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("请安装 pdfplumber: pip install pdfplumber")

    tables = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_tables = page.extract_tables()
            if page_tables:
                for table_idx, table in enumerate(page_tables):
                    if not table or len(table) < 1:
                        continue

                    # 处理表头和数据行
                    headers, rows = process_table(table)

                    # 获取表格位置
                    table_bbox = None
                    found_tables = page.find_tables()
                    if table_idx < len(found_tables):
                        table_bbox = found_tables[table_idx].bbox

                    tables.append({
                        "page": page_num + 1,
                        "index": table_idx,
                        "headers": headers,
                        "rows": rows,
                        "bbox": list(table_bbox) if table_bbox else [],
                    })

    return split_tables(tables)


def process_table(table: List[List[Any]]) -> tuple[List[str], List[List[str]]]:
    """
    处理单个表格，提取表头和数据行

    Args:
        table: 原始表格数据（二维列表）

    Returns:
        tuple: (headers, rows)
    """
    if not table or len(table) < 1:
        return [], []

    # 检测是否为多级表头
    if is_two_level_header(table):
        # 双级表头
        level1 = table[0]
        level2 = table[1]
        headers = build_two_level_headers(level1, level2)
        rows = table[2:]
    else:
        # 单级表头
        headers = [str(cell).strip() if cell else f"列{i+1}" for i, cell in enumerate(table[0])]
        rows = table[1:]

    # 清理数据行
    cleaned_rows = []
    for row in rows:
        if row:
            cleaned_row = [str(cell).strip() if cell else "" for cell in row]
            cleaned_rows.append(cleaned_row)

    return headers, cleaned_rows


def is_two_level_header(table: List[List[Any]]) -> bool:
    """
    判断表格是否为双级表头

    Args:
        table: 表格数据

    Returns:
        bool: 是否为双级表头
    """
    if len(table) < 2:
        return False

    first_row = table[0]
    second_row = table[1]

    # 第一行有较多空单元格（合并单元格）
    first_row_empty = sum(1 for cell in first_row if cell is None or str(cell).strip() == "")
    second_row_empty = sum(1 for cell in second_row if cell is None or str(cell).strip() == "")

    return first_row_empty > len(first_row) / 3 or second_row_empty > len(second_row) / 3


def build_two_level_headers(level1: List[Any], level2: List[Any]) -> List[str]:
    """
    构建双级表头

    Args:
        level1: 第一级表头
        level2: 第二级表头

    Returns:
        List[str]: 组合后的表头列表
    """
    headers = []

    for i in range(len(level2)):
        # 获取一级表头值
        l1_value = str(level1[i]).strip() if i < len(level1) and level1[i] else ""

        # 如果一级表头为空，向前查找
        if not l1_value:
            for j in range(i - 1, -1, -1):
                if j < len(level1) and level1[j]:
                    l1_value = str(level1[j]).strip()
                    break

        # 二级表头值
        l2_value = str(level2[i]).strip() if level2[i] else ""

        # 组合
        if l1_value and l2_value:
            headers.append(f"{l1_value}.{l2_value}")
        elif l2_value:
            headers.append(l2_value)
        elif l1_value:
            headers.append(l1_value)
        else:
            headers.append(f"列{i+1}")

    return headers


def split_large_tables(chunks: List[Dict], max_rows: int = 50) -> List[Dict]:
    """
    将大表格拆分成多个小表格

    Args:
        chunks: 表格分片列表
        max_rows: 每个表格最大行数

    Returns:
        List[Dict]: 拆分后的分片列表
    """
    result = []
    chunk_id_counter = 0

    for chunk in chunks:
        if chunk["row_count"] <= max_rows:
            result.append(chunk)
            continue

        # 需要拆分
        headers = chunk["headers"]
        content_lines = chunk["content"].split("\n")

        # 分离表头和分隔线
        header_line = content_lines[0] if content_lines else ""
        separator_line = content_lines[1] if len(content_lines) > 1 else ""
        data_lines = content_lines[2:] if len(content_lines) > 2 else []

        # 按最大行数拆分数据行
        for i in range(0, len(data_lines), max_rows):
            chunk_id_counter += 1
            part_lines = [header_line, separator_line] + data_lines[i:i + max_rows]

            result.append({
                "chunk_id": f"{chunk['chunk_id']}_part{chunk_id_counter}",
                "type": "table",
                "page": chunk["page"],
                "order": chunk_id_counter,
                "headers": headers,
                "content": "\n".join(part_lines),
                "row_count": min(max_rows, len(data_lines) - i),
                "col_count": chunk["col_count"],
                "bbox": chunk["bbox"],
                "parent_table": chunk["chunk_id"],  # 记录来源
            })

    return result


def merge_related_tables(chunks: List[Dict], max_gap: int = 2) -> List[Dict]:
    """
    合并同一页面中相邻的表格

    Args:
        chunks: 表格分片列表
        max_gap: 允许的最大间隔页数

    Returns:
        List[Dict]: 合并后的分片列表
    """
    if not chunks:
        return chunks

    result = []
    i = 0

    while i < len(chunks):
        current = chunks[i]
        merged_content = [current["content"]]
        merged_row_count = current["row_count"]
        merged_bbox = current["bbox"].copy() if current["bbox"] else []

        # 检查后续是否有可合并的表格
        j = i + 1
        while j < len(chunks):
            next_chunk = chunks[j]
            # 同页且相邻
            if (next_chunk["page"] == current["page"] and
                next_chunk["order"] - current["order"] <= max_gap):
                merged_content.append(next_chunk["content"])
                merged_row_count += next_chunk["row_count"]
                # 扩展 bbox
                if next_chunk["bbox"]:
                    merged_bbox = merge_bbox(merged_bbox, next_chunk["bbox"])
                j += 1
            else:
                break

        # 如果合并了多个表格
        if j > i + 1:
            result.append({
                "chunk_id": f"merged_{current['chunk_id']}",
                "type": "table",
                "page": current["page"],
                "order": len(result) + 1,
                "headers": current["headers"],
                "content": "\n\n".join(merged_content),
                "row_count": merged_row_count,
                "col_count": current["col_count"],
                "bbox": merged_bbox,
                "merged": True,
                "original_chunks": [chunks[k]["chunk_id"] for k in range(i, j)],
            })
        else:
            result.append(current)

        i = j

    return result


def merge_bbox(bbox1: List[float], bbox2: List[float]) -> List[float]:
    """合并两个 bbox"""
    if not bbox1:
        return bbox2
    if not bbox2:
        return bbox1
    return [
        min(bbox1[0], bbox2[0]),  # x0
        min(bbox1[1], bbox2[1]),  # y0
        max(bbox1[2], bbox2[2]),  # x1
        max(bbox1[3], bbox2[3]),  # y1
    ]
