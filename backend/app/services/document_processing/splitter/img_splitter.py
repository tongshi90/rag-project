"""
图片分片服务
处理 PDF 中提取的图片数据的切片和 OCR 识别
"""
import io
from typing import List, Dict, Any

from PIL import Image


def split_images(images: List[Dict]) -> List[Dict[str, Any]]:
    """
    对图片列表进行分片处理

    Args:
        images: 原始图片数据列表，每个元素包含：
            - page: 页码
            - index: 图片索引
            - image_bytes: 图片字节数据
            - bbox: 图片位置 (x0, y0, x1, y1)
            - ocr_text: OCR 识别的文本（可选）

    Returns:
        List[Dict]: 图片分片列表，每个分片包含：
            - chunk_id: 分片ID
            - type: "image"
            - page: 页码
            - content: OCR 识别的文本内容
            - image_info: 图片元数据（尺寸、格式等）
            - bbox: 图片位置信息
    """
    if not images:
        return []

    chunks = []

    for idx, img_data in enumerate(images):
        chunk = {
            "chunk_id": f"img_{img_data.get('page', 0)}_{idx}",
            "type": "image",
            "page": img_data.get("page", 0),
            "order": idx + 1,
            "content": img_data.get("ocr_text", ""),
            "image_info": {
                "width": img_data.get("width", 0),
                "height": img_data.get("height", 0),
                "format": img_data.get("format", "unknown"),
            },
            "bbox": img_data.get("bbox", []),
        }
        chunks.append(chunk)

    return chunks


def split_images_from_pdf(pdf_path: str, ocr_model=None) -> List[Dict[str, Any]]:
    """
    直接从 PDF 文件提取图片并进行分片

    Args:
        pdf_path: PDF 文件路径
        ocr_model: OCR 模型（可选）

    Returns:
        List[Dict]: 图片分片列表
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("请安装 PyMuPDF: pip install PyMuPDF")

    images = []
    pdf_document = fitz.open(pdf_path)

    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        image_list = page.get_images(full=True)

        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = pdf_document.extract_image(xref)

            if base_image:
                image_bytes = base_image["image"]
                image = Image.open(io.BytesIO(image_bytes))

                # 获取图片位置
                rects = page.get_image_rects(xref)
                bbox = []
                if rects:
                    rect = rects[0]
                    bbox = [rect.x0, rect.y0, rect.x1, rect.y1]

                # OCR 识别
                ocr_text = ""
                if ocr_model:
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format='PNG')
                    ocr_text = ocr_model.recognize(img_byte_arr.getvalue())

                images.append({
                    "page": page_num + 1,
                    "index": img_index,
                    "image_bytes": image_bytes,
                    "width": image.width,
                    "height": image.height,
                    "format": image.format or "PNG",
                    "bbox": bbox,
                    "ocr_text": ocr_text,
                })

    pdf_document.close()
    return split_images(images)


def merge_nearby_images(chunks: List[Dict], max_distance: float = 50.0) -> List[Dict]:
    """
    合并位置相近的图片分片

    Args:
        chunks: 图片分片列表
        max_distance: 最大距离阈值（同页内）

    Returns:
        List[Dict]: 合并后的分片列表
    """
    if not chunks:
        return chunks

    # 按页码分组
    pages = {}
    for chunk in chunks:
        page = chunk["page"]
        if page not in pages:
            pages[page] = []
        pages[page].append(chunk)

    result = []
    chunk_id = 0

    for page, page_chunks in pages.items():
        i = 0
        while i < len(page_chunks):
            current = page_chunks[i]
            merged_content = [current["content"]]
            merged_bbox = current["bbox"].copy() if current["bbox"] else []

            # 检查后续是否有相近的图片
            j = i + 1
            while j < len(page_chunks):
                next_chunk = page_chunks[j]
                if is_nearby(merged_bbox, next_chunk.get("bbox", []), max_distance):
                    merged_content.append(next_chunk["content"])
                    # 扩展 bbox
                    if next_chunk["bbox"]:
                        merged_bbox = merge_bbox(merged_bbox, next_chunk["bbox"])
                    j += 1
                else:
                    break

            # 创建合并后的 chunk
            chunk_id += 1
            merged_chunk = {
                "chunk_id": f"img_merged_{page}_{chunk_id}",
                "type": "image",
                "page": page,
                "order": chunk_id,
                "content": " ".join(filter(None, merged_content)),
                "image_info": current.get("image_info", {}),
                "bbox": merged_bbox,
            }
            result.append(merged_chunk)
            i = j

    return result


def is_nearby(bbox1: List[float], bbox2: List[float], max_distance: float) -> bool:
    """判断两个 bbox 是否相近"""
    if not bbox1 or not bbox2:
        return False

    # 计算中心点距离
    center1_x = (bbox1[0] + bbox1[2]) / 2
    center1_y = (bbox1[1] + bbox1[3]) / 2
    center2_x = (bbox2[0] + bbox2[2]) / 2
    center2_y = (bbox2[1] + bbox2[3]) / 2

    distance = ((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2) ** 0.5
    return distance <= max_distance


def merge_bbox(bbox1: List[float], bbox2: List[float]) -> List[float]:
    """合并两个 bbox"""
    return [
        min(bbox1[0], bbox2[0]),  # x0
        min(bbox1[1], bbox2[1]),  # y0
        max(bbox1[2], bbox2[2]),  # x1
        max(bbox1[3], bbox2[3]),  # y1
    ]


def filter_small_images(chunks: List[Dict], min_area: int = 10000) -> List[Dict]:
    """
    过滤掉面积过小的图片

    Args:
        chunks: 图片分片列表
        min_area: 最小面积阈值（平方像素）

    Returns:
        List[Dict]: 过滤后的分片列表
    """
    result = []
    for chunk in chunks:
        bbox = chunk.get("bbox", [])
        if bbox and len(bbox) == 4:
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            area = width * height
            if area >= min_area:
                result.append(chunk)
        else:
            # 没有 bbox 信息则保留
            result.append(chunk)

    return result
