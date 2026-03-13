"""
文档分片异常校验模块

本模块是文档拆分流程的第二步，用于检查章节拆分异常情况。

主要功能：
1. 分片长度验证 (拆分为过短检测和过长检测)
   - validate_chunk_too_short: 检测过短分片 (handling_mode: merge)
   - validate_chunk_too_long: 检测过长分片 (handling_mode: split)
2. 正文长度验证 (handling_mode: merge)
   - 综合检查正文长度和标题占比，确保正文足够作为独立chunk分片
3. 参数混杂检测 (handling_mode: split)
4. 标题结构验证 (handling_mode: split)
5. 分片关系异常检测
   - validate_long_chunk_multi_topic: 长chunk内部多主题 (handling_mode: split)
   - validate_continuous_short_chunk_same_topic: 连续短chunk同一知识点 (handling_mode: merge)

handling_mode 说明：
- merge: 合并分片，需要将当前分片与相邻分片一起交给 LLM 处理
- split: 拆分分片，只需要将当前分片交给 LLM 处理

使用方式：
    from app.services.document_processing.splitter.text_splitter import refine_title_patterns, split_chunks
    from app.services.document_processing.validator.validate import validate_chunks

    # 第一步：文档拆分
    title_patterns = refine_title_patterns(lines)
    chunks = split_chunks(lines, title_patterns)

    # 第二步：异常校验（使用第一步得到的 title_patterns）
    validated_chunks = validate_chunks(chunks, title_patterns)
"""

import hashlib
import re
from typing import List, Dict, Optional

import numpy as np
import tiktoken

try:
    from app.config.model_config import get_embedding_model
except ImportError:
    def get_embedding_model():
        return None


# ============================================
# Embedding 缓存和工具函数
# ============================================
_embedding_model = None
_embedding_cache: Dict[str, np.ndarray] = {}


def calc_token_len(text: str) -> int:
    """计算文本的 token 长度"""
    tokenizer = tiktoken.get_encoding("cl100k_base")
    return len(tokenizer.encode(text))


def _get_embedding_model():
    """获取 embedding 模型实例（单例模式）"""
    global _embedding_model
    if _embedding_model is None:
        try:
            _embedding_model = get_embedding_model()
        except Exception as e:
            print(f"警告: 无法初始化 Embedding 模型: {e}")
            _embedding_model = None
    return _embedding_model


def _hash_text(text: str) -> str:
    """计算文本的 MD5 哈希值，用于缓存 key"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def get_embedding(text: str, use_cache: bool = True) -> Optional[np.ndarray]:
    """获取文本的 embedding 向量"""
    if not text or not text.strip():
        return None

    text_hash = _hash_text(text)

    # 检查缓存
    if use_cache and text_hash in _embedding_cache:
        return _embedding_cache[text_hash]

    model = _get_embedding_model()
    if model is None:
        return None

    try:
        embedding_list = model.embed(text)
        if embedding_list:
            vec = np.array(embedding_list, dtype=np.float32)
            if use_cache:
                _embedding_cache[text_hash] = vec
            return vec
    except Exception as e:
        print(f"Embedding 调用失败: {e}")

    return None


def cosine_similarity(v1: Optional[np.ndarray], v2: Optional[np.ndarray]) -> float:
    """计算两个向量的余弦相似度"""
    if v1 is None or v2 is None:
        return 0.0
    denom = np.linalg.norm(v1) * np.linalg.norm(v2)
    if denom == 0:
        return 0.0
    return float(np.dot(v1, v2) / denom)


def clear_embedding_cache():
    """清空 embedding 缓存"""
    global _embedding_cache
    _embedding_cache = {}


# ============================================
# 前置统计计算
# ============================================

def calculate_pre_validation_metrics(chunks: List[Dict]) -> Dict:
    """
    计算异常chunk检测之前的前置参数

    Args:
        chunks: 分片列表

    Returns:
        包含以下字段的字典：
        - doc_total_tokens: 文档总token数
        - chunk_count: 分片数量
        - median_chunk_tokens: 分片中位token数
        - doc_is_short: 是否为短文档
        - doc_is_long: 是否为长文档
        - chunk_details: 每个分片的详细信息
    """
    chunk_count = len(chunks)

    # 遍历计算每个chunk的统计数据
    chunk_token_lengths = []
    chunk_details = []
    for chunk_item in chunks:
        text = chunk_item.get('text', '')
        title_path = chunk_item.get('title_path', [])
        total_tokens = calc_token_len(text)
        chunk_token_lengths.append(total_tokens)

        # 确定标题和内容的边界
        title_len_tokens = 0
        if title_path:
            # 遍历 title_path 中的每个标题
            for title in title_path:
                title_clean = title.strip()
                if not title_clean:
                    continue
                # 去除标题中的换行符，方便匹配
                title_no_newline = title_clean.replace('\n', '')
                # 检查标题是否在 text 中存在
                if title_no_newline in text:
                    # 匹配上，增加标题长度
                    title_len_tokens += calc_token_len(title_no_newline)

            content_len_tokens = total_tokens - title_len_tokens
        else:
            # 没有标题，全部是内容
            content_len_tokens = total_tokens
        chunk_details.append({
            'chunk_id': chunk_item.get('chunk_id', ''),
            'total_tokens': total_tokens,
            'title_len': title_len_tokens,
            'content_len': content_len_tokens,
            'title_proportion': title_len_tokens / total_tokens if total_tokens > 0 else 0.0
        })

    # 统计整个文档的相关数据
    doc_total_tokens = sum(chunk_token_lengths)
    median_chunk_tokens = float(np.median(chunk_token_lengths)) if chunk_token_lengths else 0
    doc_is_short = doc_total_tokens < 3000
    doc_is_long = doc_total_tokens > 20000

    # 生成统计结果
    metrics = {
        'doc_total_tokens': doc_total_tokens,
        'chunk_count': chunk_count,
        'median_chunk_tokens': median_chunk_tokens,
        'doc_is_short': doc_is_short,
        'doc_is_long': doc_is_long,
        'chunk_details': chunk_details
    }
    return metrics


# ============================================
# 各项校验规则
# ============================================

def validate_chunk_too_short(chunks: List[Dict], metrics: Dict) -> None:
    """
    校验chunk长度是否过短（需要合并）
    规则如下：
        1、如果text长度<80，得分为15分
        2、如果text长度<中位值*0.25，得分为10分
        3、如果text长度<中位值*0.4，得分为5分

    Args:
        chunks: 分片列表（会直接修改）
        metrics: 前置统计指标
    """
    # 从metrics获取chunk长度的中位数值
    median_length = metrics.get('median_chunk_tokens', 0)
    chunk_details = metrics.get('chunk_details', [])

    # 遍历每个chunk进行校验
    for chunk_order, chunk_item in enumerate(chunks):
        # 从chunk_details中获取token长度
        token_len = chunk_details[chunk_order].get('total_tokens', 0)

        if 'error_info' not in chunk_item:
            chunk_item['error_info'] = []
        # 初始化risk_score
        if 'total_risk_score' not in chunk_item:
            chunk_item['total_risk_score'] = 0
        risk_score = None
        if token_len < 80:
            risk_score = 15
        elif token_len < median_length * 0.25:
            risk_score = 10
        elif token_len < median_length * 0.4:
            risk_score = 5

        # 如果有异常，添加到error_info列表并累加risk_score
        if risk_score is not None:
            chunk_item['error_info'].append({
                'risk_score': risk_score,
                'type': 'validate_chunk_too_short',
                'handling_mode': 'merge'
            })
            chunk_item['total_risk_score'] += risk_score


def validate_chunk_too_long(chunks: List[Dict], metrics: Dict) -> None:
    """
    校验chunk长度是否过长（需要拆分）
    规则如下：
        1、如果text长度>1000，得分为15分
        2、如果text长度>中位值*3.5，得分为10分
        3、如果text长度>中位值*2.5，得分为5分

    Args:
        chunks: 分片列表（会直接修改）
        metrics: 前置统计指标
    """
    # 从metrics获取chunk长度的中位数值
    median_length = metrics.get('median_chunk_tokens', 0)
    chunk_details = metrics.get('chunk_details', [])

    # 遍历每个chunk进行校验
    for chunk_order, chunk_item in enumerate(chunks):
        # 从chunk_details中获取token长度
        token_len = chunk_details[chunk_order].get('total_tokens', 0)

        if 'error_info' not in chunk_item:
            chunk_item['error_info'] = []
        # 初始化risk_score
        if 'total_risk_score' not in chunk_item:
            chunk_item['total_risk_score'] = 0
        risk_score = None
        if token_len > 1000:
            risk_score = 15
        elif token_len > median_length * 3.5:
            risk_score = 10
        elif token_len > median_length * 2.5:
            risk_score = 5

        # 如果有异常，添加到error_info列表并累加risk_score
        if risk_score is not None:
            chunk_item['error_info'].append({
                'risk_score': risk_score,
                'type': 'validate_chunk_too_long',
                'handling_mode': 'split'
            })
            chunk_item['total_risk_score'] += risk_score


def validate_content_length(chunks: List[Dict], metrics: Dict) -> None:
    """
    校验正文长度是否足够（合并了正文存在性和标题占比检查）

    目的：确保正文长度足够作为一个独立的chunk分片，方便后续embedding使用

    规则如下（综合正文长度和标题占比）：
        1、如果无正文(正文长度为0)，得分为20分
        2、如果标题占比 > 80%（正文极少），得分为15分
        3、如果正文长度 < 0.5 * 阈值 或 标题占比 > 60%，得分为15分
        4、如果正文长度 < 阈值 或 标题占比 > 40%，得分为10分

    Args:
        chunks: 分片列表（会直接修改）
        metrics: 前置统计指标
    """
    # 短文档跳过正文长度校验
    if metrics.get('doc_is_short', False):
        return

    chunk_details = metrics.get('chunk_details', [])
    # 最小正文阈值
    min_content_threshold = 200

    for chunk_order, chunk_item in enumerate(chunks):
        # 从metrics中获取正文token长度和标题占比
        content_len = chunk_details[chunk_order].get('content_len', 0)
        title_proportion = chunk_details[chunk_order].get('title_proportion', 0)

        if 'error_info' not in chunk_item:
            chunk_item['error_info'] = []
        # 初始化risk_score
        if 'total_risk_score' not in chunk_item:
            chunk_item['total_risk_score'] = 0
        risk_score = None

        # 综合判断正文长度和标题占比
        if content_len == 0:
            risk_score = 20
        elif title_proportion > 0.8:
            risk_score = 15
        elif content_len < min_content_threshold * 0.5 or title_proportion > 0.6:
            risk_score = 15
        elif content_len < min_content_threshold or title_proportion > 0.4:
            risk_score = 10

        # 如果有异常，添加到error_info列表并累加risk_score
        if risk_score is not None:
            chunk_item['error_info'].append({
                'risk_score': risk_score,
                'type': 'validate_content_length',
                'handling_mode': 'merge'
            })
            chunk_item['total_risk_score'] += risk_score


def validate_parameter_mixing(chunks: List[Dict]) -> None:
    """
    校验参数类和描述类文档是否混杂
    规则如下：
        1、参数类比例 < 0.2 或 > 0.8 → 忽略，不加异常分
        2、参数类比例 < 0.3 或 > 0.7 → 得分 10
        3、参数类比例 < 0.4 或 > 0.6 → 得分 18
        4、其他情况（0.4 ≤ ratio ≤ 0.6）→ 得分 25

    Args:
        chunks: 分片列表（会直接修改）
    """
    # 参数类格式的正则表达式
    param_patterns = [
        r'^\s*\w+\s*=\s*.+',  # key=value
        r'^\s*\w+\s*:\s*.+',  # key:value 或 key：value
        r'^\s*\w+\s*：\s*.+',  # key：value（中文冒号）
        r'^\s*[\"\'\{\[\(].*',  # json/yaml起始符开头
        r'^\s*-\s+\w+\s*:',  # yaml列表格式 - key:
        r'^\s*\w+\s*\|\s*',  # key|value
    ]

    for chunk_item in chunks:
        # 计算参数类占比
        text = chunk_item.get('text', '')
        if not text:
            continue
        total_tokens = calc_token_len(text)
        if total_tokens == 0:
            continue
        param_tokens = 0
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            is_param_line = False
            for pattern in param_patterns:
                if re.match(pattern, line):
                    is_param_line = True
                    break
            if is_param_line:
                param_tokens += calc_token_len(line)
        parameter_ratio = param_tokens / total_tokens

        # 按规则计算异常分
        if 'error_info' not in chunk_item:
            chunk_item['error_info'] = []
        # 初始化risk_score
        if 'total_risk_score' not in chunk_item:
            chunk_item['total_risk_score'] = 0
        risk_score = None
        if parameter_ratio < 0.2 or parameter_ratio > 0.8:
            pass
        elif parameter_ratio < 0.3 or parameter_ratio > 0.7:
            risk_score = 10
        elif parameter_ratio < 0.4 or parameter_ratio > 0.6:
            risk_score = 18
        else:
            risk_score = 25
        if risk_score is not None:
            chunk_item['error_info'].append({
                'risk_score': risk_score,
                'type': 'validate_parameter_mixing',
                'handling_mode': 'split'
            })
            chunk_item['total_risk_score'] += risk_score


def validate_title_structure(chunks: List[Dict], title_patterns: List[tuple]) -> None:
    """
    校验标题层级结构是否混乱
    规则如下：
        1、出现任何类型的标题异常，得分 20

    Args:
        chunks: 分片列表（会直接修改）
        title_patterns: 标题正则规则列表，格式如 [('level1', 'pattern'), ('level2', 'pattern')]
                       应该是 text_splitter.refine_title_patterns() 的返回结果
    """
    # 如果没有标题正则规则，跳过校验，认为没有异常
    if not title_patterns:
        return

    # 将title_patterns转换为字典，方便查找
    pattern_dict = {level_name: pattern for level_name, pattern in title_patterns}

    for chunk_item in chunks:
        title_path = chunk_item.get('title_path', [])

        # 空的title_path跳过
        if not title_path:
            continue
        # 检查每个标题是否符合对应层级格式
        has_error = False
        for idx, title in enumerate(title_path):
            # 获取对应层级的正则表达式
            level_key = f'level{idx + 1}'
            if level_key not in pattern_dict:
                # 超出定义的级别数量，报异常
                has_error = True
                break
            pattern = pattern_dict[level_key]
            # 检查标题是否符合该层级的正则格式
            if not re.match(pattern, title):
                has_error = True
                break

        # 如果有异常，添加到error_info列表并累加risk_score
        if has_error:
            if 'error_info' not in chunk_item:
                chunk_item['error_info'] = []
            # 初始化risk_score
            if 'risk_score' not in chunk_item:
                chunk_item['risk_score'] = 0
            chunk_item['error_info'].append({
                'risk_score': 20,
                'type': 'validate_title_structure',
                'handling_mode': 'split'
            })
            chunk_item['total_risk_score'] += 20




def validate_long_chunk_multi_topic(chunks: List[Dict]) -> None:
    """
    检测长chunk是否包含多个知识点（内部多主题检测）

    检测逻辑：将长chunk按token长度分滑动窗口，计算相邻窗口的相似度，相似度过低说明存在多个主题
    - 滑块长度：150-200个token（根据chunk长度动态调整）
    - 步长：滑块长度的一半
    - 最后滑块不足时与倒数第二个合并

    风险评分规则：
        - 相似度在 0.65–0.75 之间 → 得分 20
        - 相似度在 0.5–0.65 之间 → 得分 35
        - 相似度 < 0.5 → 得分 60，并强制异常

    Args:
        chunks: 分片列表（会直接修改）
    """
    model = _get_embedding_model()
    if model is None:
        return

    # 长chunk的阈值限制
    long_chunk_token_threshold = 800

    for idx, chunk_item in enumerate(chunks):
        text = chunk_item.get('text', '')
        token_len = calc_token_len(text)

        if token_len <= long_chunk_token_threshold:
            continue

        # 根据chunk长度动态调整滑块大小
        # chunk越长，滑块越大，范围150-200
        if token_len < 1200:
            window_size = 150
        elif token_len < 1600:
            window_size = 175
        else:
            window_size = 200

        # 步长为滑块长度的一半
        step_size = window_size // 2

        # 获取tokenizer用于精确分token
        tokenizer = tiktoken.get_encoding("cl100k_base")
        tokens = tokenizer.encode(text)

        # 生成滑动窗口
        windows = []
        start = 0
        while start < len(tokens):
            end = min(start + window_size, len(tokens))
            window_tokens = tokens[start:end]
            window_text = tokenizer.decode(window_tokens)
            windows.append(window_text)

            # 如果已经到末尾，退出
            if end >= len(tokens):
                break

            start += step_size

        # 处理最后一个滑块：如果长度不足窗口大小的60%，与倒数第二个合并
        if len(windows) >= 2:
            last_window_len = calc_token_len(windows[-1])
            if last_window_len < window_size * 0.6:
                # 合并最后两个窗口
                merged_window = windows[-2] + '\n' + windows[-1]
                windows[-2] = merged_window
                windows.pop()

        if len(windows) < 2:
            continue

        # 获取窗口的embedding
        win_embeddings = []
        for w in windows:
            emb = get_embedding(w)
            if emb is not None:
                win_embeddings.append(emb)
            else:
                continue

        if len(win_embeddings) < 2:
            continue

        # 计算相邻窗口之间的相似度
        sims = []
        for x in range(len(win_embeddings) - 1):
            sim = cosine_similarity(win_embeddings[x], win_embeddings[x + 1])
            sims.append(sim)

        if not sims:
            continue

        # 取最小相似度进行判断
        min_sim = min(sims)
        risk_score = None
        hard_violation = False
        if 0.65 <= min_sim < 0.75:
            risk_score = 20
        elif 0.5 <= min_sim < 0.65:
            risk_score = 35
        elif min_sim < 0.5:
            risk_score = 60
            hard_violation = True

        # 如果有异常，添加到error_info列表并累加risk_score
        if risk_score is not None:
            if 'error_info' not in chunk_item:
                chunk_item['error_info'] = []
            if 'risk_score' not in chunk_item:
                chunk_item['risk_score'] = 0
            chunk_item['error_info'].append({
                'risk_score': risk_score,
                'type': 'validate_long_chunk_multi_topic',
                'handling_mode': 'split'
            })
            chunk_item['total_risk_score'] += risk_score
            if hard_violation:
                chunk_item['hard_violation'] = True


def validate_continuous_short_chunk_same_topic(chunks: List[Dict]) -> None:
    """
    检测连续短chunk是否是同一知识点被错误拆分

    检测逻辑：查找连续的短chunk，计算它们与相邻chunk的相似度，相似度过高说明应该合并

    风险评分规则：
        - 相似度在 0.75–0.85 之间 → 得分 15
        - 相似度在 0.85–0.93 之间 → 得分 40
        - 相似度 > 0.93 → 得分 60，并强制异常

    Args:
        chunks: 分片列表（会直接修改）
    """
    model = _get_embedding_model()
    if model is None:
        return

    n = len(chunks)
    if n < 2:
        return

    # 短chunk的阈值限制
    short_chunk_token_threshold = 150

    # 计算所有chunk的token长度
    token_lens = [calc_token_len(chunk_item.get('text', '')) for chunk_item in chunks]

    i = 0
    while i < n:
        if token_lens[i] < short_chunk_token_threshold:
            j = i
            while j < n and token_lens[j] < short_chunk_token_threshold:
                j += 1

            # 连续短chunk数量 >= 2 时才检测
            if j - i >= 2:
                # 确定计算范围：加入前后chunk
                start_idx = max(0, i - 1)
                end_idx = min(n, j + 1)
                calc_indices = list(range(start_idx, end_idx))

                # 获取embedding
                embeddings = []
                for idx in calc_indices:
                    text = chunks[idx].get('text', '')
                    emb = get_embedding(text)
                    if emb is not None:
                        embeddings.append((idx, emb))

                # 计算所有相邻chunk之间的相似度
                if len(embeddings) >= 2:
                    # 计算相邻pair的相似度
                    pair_sims = {}  # (idx1, idx2) -> similarity
                    for x in range(len(embeddings) - 1):
                        idx1, emb1 = embeddings[x]
                        idx2, emb2 = embeddings[x + 1]
                        sim = cosine_similarity(emb1, emb2)
                        pair_sims[(idx1, idx2)] = sim

                    # 为每个连续短chunk计算与相邻chunk的最大相似度
                    for k in range(i, j):  # 遍历每个连续短chunk
                        adjacent_sims = []
                        # 查找与前面chunk的相似度
                        if k - 1 >= 0 and (k - 1, k) in pair_sims:
                            adjacent_sims.append(pair_sims[(k - 1, k)])
                        # 查找与后面chunk的相似度
                        if (k, k + 1) in pair_sims:
                            adjacent_sims.append(pair_sims[(k, k + 1)])

                        if not adjacent_sims:
                            continue

                        # 取最大相似度
                        max_adjacent_sim = max(adjacent_sims)
                        risk_score = None
                        hard_violation = False
                        if 0.75 < max_adjacent_sim <= 0.85:
                            risk_score = 15
                        elif 0.85 < max_adjacent_sim <= 0.93:
                            risk_score = 40
                        elif max_adjacent_sim > 0.93:
                            risk_score = 60
                            hard_violation = True

                        # 如果有异常，添加到error_info列表并累加risk_score
                        if risk_score is not None:
                            chunk_item = chunks[k]
                            if 'error_info' not in chunk_item:
                                chunk_item['error_info'] = []
                            if 'risk_score' not in chunk_item:
                                chunk_item['risk_score'] = 0
                            chunk_item['error_info'].append({
                                'risk_score': risk_score,
                                'type': 'validate_continuous_short_chunk_same_topic',
                                'handling_mode': 'merge'
                            })
                            chunk_item['total_risk_score'] += risk_score
                            if hard_violation:
                                chunk_item['hard_violation'] = True
            i = j
        else:
            i += 1


# ============================================
# 主入口函数
# ============================================

def validate_chunks(chunks: List[Dict], title_patterns: Optional[List[tuple]] = None) -> List[Dict]:
    """
    对分片列表进行异常校验（主入口函数）

    Args:
        chunks: 第一步 text_splitter 返回的分片列表
        title_patterns: 标题正则规则列表，应该是 text_splitter.refine_title_patterns() 的返回结果
                       格式如 [('level1', 'pattern'), ('level2', 'pattern')]
                       如果为 None 或空列表，validate_title_structure 步骤将被跳过

    Returns:
        校验后的分片列表，每个分片可能新增以下字段：
        - error_info: 异常信息列表 [{'risk_score': int, 'type': str, 'handling_mode': str}]
        - total_risk_score: 总风险分数
        - hard_violation: 是否存在强制异常标志
    """
    # title_patterns 允许为 None 或空列表，此时 validate_title_structure 会跳过校验
    if title_patterns is None:
        title_patterns = []

    # 清空之前的缓存（避免跨文档污染）
    clear_embedding_cache()

    # 初始化每个chunk的校验相关字段
    for chunk in chunks:
        if 'error_info' not in chunk:
            chunk['error_info'] = []
        if 'total_risk_score' not in chunk:
            chunk['total_risk_score'] = 0

    # 前置统计信息计算
    metrics = calculate_pre_validation_metrics(chunks)

    # 1. 长度异常检测（拆分：过短检测和过长检测）
    validate_chunk_too_short(chunks, metrics)
    validate_chunk_too_long(chunks, metrics)

    # 2. 正文长度异常检测（合并了正文存在性和标题占比检查）
    validate_content_length(chunks, metrics)

    # 3. 文本类型混杂异常检测
    validate_parameter_mixing(chunks)

    # 4. 标题结构混乱异常检测
    validate_title_structure(chunks, title_patterns)

    # 5. 长chunk内部多主题检测
    validate_long_chunk_multi_topic(chunks)

    # 7 连续短chunk同一知识点拆分检测
    validate_continuous_short_chunk_same_topic(chunks)

    return chunks


def get_validation_summary(chunks: List[Dict]) -> Dict:
    """
    获取校验结果摘要

    Args:
        chunks: 校验后的分片列表

    Returns:
        校验摘要信息，包含：
        - total_chunks: 总分片数
        - chunks_with_errors: 有异常的分片数
        - chunks_with_hard_violation: 有强制异常的分片数
        - total_risk_score: 总风险分数
        - high_risk_chunks: 高风险分片列表 (total_risk_score >= 40)
    """
    total = len(chunks)
    with_errors = 0
    with_hard_violation = 0
    total_risk = 0
    high_risk = []

    for chunk in chunks:
        total_risk_score = chunk.get('total_risk_score', 0)
        total_risk += total_risk_score

        if total_risk_score > 0:
            with_errors += 1

        if chunk.get('hard_violation', False):
            with_hard_violation += 1

        if total_risk_score >= 40:
            high_risk.append({
                'chunk_id': chunk.get('chunk_id'),
                'total_risk_score': total_risk_score,
                'error_types': [e.get('type') for e in chunk.get('error_info', [])]
            })

    return {
        'total_chunks': total,
        'chunks_with_errors': with_errors,
        'chunks_with_hard_violation': with_hard_violation,
        'total_risk_score': total_risk,
        'high_risk_chunks': high_risk
    }


def get_risk_chunk_ids(chunks: List[Dict], min_risk_score: int = 60) -> List[Dict[str, str]]:
    """
    获取风险分数达到阈值或有强制异常的分片信息列表

    处理类型规则：
    - 只要有一条异常是 merge，处理类型就是 merge
    - 只有全是 split 的时候，处理类型才是 split

    Args:
        chunks: 校验后的分片列表
        min_risk_score: 最小风险分数阈值，默认 60

    Returns:
        风险分片信息列表，格式：
        [
            {'chunk_id': 'xxx', 'handling_mode': 'merge'},
            {'chunk_id': 'yyy', 'handling_mode': 'split'},
            ...
        ]
    """
    risk_chunks = []
    for chunk in chunks:
        total_risk_score = chunk.get('total_risk_score', 0)
        hard_violation = chunk.get('hard_violation', False)
        if total_risk_score >= min_risk_score or hard_violation:
            chunk_id = chunk.get('chunk_id')
            if chunk_id:
                # 获取所有异常的 handling_mode
                error_info = chunk.get('error_info', [])
                handling_modes = [e.get('handling_mode', 'split') for e in error_info]

                # 判断处理类型：只要有一条是 merge，就是 merge
                handling_mode = 'merge' if 'merge' in handling_modes else 'split'

                risk_chunks.append({
                    'chunk_id': chunk_id,
                    'handling_mode': handling_mode
                })
    return risk_chunks
