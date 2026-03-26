import re
from collections import Counter


class TitleDetector:

    def __init__(self):
        self.rules = [
            # 中文数字
            ("CN_CHAPTER", re.compile(r"^(第[一二三四五六七八九十百千]+章)")),
            ("CN_PART", re.compile(r"^(第[一二三四五六七八九十百千]+部分)")),
            ("CN_SECTION", re.compile(r"^(第[一二三四五六七八九十百千]+节)")),
            ("CN_ARTICLE", re.compile(r"^(第[一二三四五六七八九十百千]+篇)")),
            ("CN_ITEM", re.compile(r"^(第[一二三四五六七八九十百千]+条)")),
            # 阿拉伯数字
            ("NUM_CHAPTER", re.compile(r"^(第[0-9]+章)")),
            ("NUM_PART", re.compile(r"^(第[0-9]+部分)")),
            ("NUM_SECTION", re.compile(r"^(第[0-9]+节)")),
            ("NUM_ARTICLE", re.compile(r"^(第[0-9]+篇)")),
            ("NUM_ITEM", re.compile(r"^(第[0-9]+条)")),
            # 序号规则
            ("NUM_DECIMAL", re.compile(r"^\d+(\.\d+)+")),
            ("NUM_SIMPLE", re.compile(r"^\d+\s+")),
            ("CN_LIST", re.compile(r"^[一二三四五六七八九十]+、")),
        ]

    def clean(self, line):
        return re.sub(r"\s+", " ", line.strip())

    def normalize_title(self, text):
        return re.sub(r"\s*\d+\s*$", "", text).strip()

    def match_line(self, line):
        for rule_id, pattern in self.rules:
            if pattern.match(line):
                return True, rule_id
        return False, None

    def extract_candidates(self, lines):
        candidates = []
        for idx, line in enumerate(lines, 1):  # 从1开始计数
            clean = self.clean(line)
            if not clean:
                continue
            matched, rule_id = self.match_line(clean)
            if matched:
                candidates.append({
                    "line_index": idx,
                    "text": clean,
                    "norm": self.normalize_title(clean),
                    "rule_id": rule_id
                })
        return candidates

    def is_toc_entry_line(self, line):
        """
        判断是否为目录条目行
        特征：
        1. 符合标题正则结构
        2. 以数字结尾（页码）
        """
        # 检查是否以数字结尾
        if not re.search(r'\d+$', line.strip()):
            return False, None

        # 检查是否符合标题正则
        matched, rule_id = self.match_line(line.strip())
        if not matched:
            return False, None

        # 提取章节名（去掉页码部分）
        for rule_id, pattern in self.rules:
            m = pattern.match(line.strip())
            if m:
                title_core = m.group(1)
                return True, title_core

        return False, None

    def check_title_reappears(self, title_core, start_idx, lines):
        """
        检查章节名在后面内容中是否重复出现
        """
        for idx in range(start_idx, len(lines)):
            line = lines[idx].strip()
            if not line:
                continue
            # 检查是否包含章节名
            if title_core in line:
                return True, idx + 1  # 1-based
        return False, None

    def detect_toc_start_by_pattern(self, candidates, lines):
        """
        新的目录开始点判断逻辑：
        1. 连续多条都符合标题的正则结构
        2. 且都是以数字结尾（页码）
        3. 拆分出章节名之后，在后面的内容中重复出现
        """
        consecutive_count = 0
        min_consecutive = 2  # 至少连续2条
        toc_start_candidate = None

        for idx, line in enumerate(lines):
            is_toc_entry, title_core = self.is_toc_entry_line(line)

            if is_toc_entry:
                # 检查章节名是否在后面重复出现
                reappears, reappear_idx = self.check_title_reappears(title_core, idx + 1, lines)

                if reappears:
                    if consecutive_count == 0:
                        toc_start_candidate = idx + 1  # 1-based
                    consecutive_count += 1

                    # 如果连续达到阈值，返回开始点
                    if consecutive_count >= min_consecutive:
                        return toc_start_candidate
                else:
                    consecutive_count = 0
                    toc_start_candidate = None
            else:
                consecutive_count = 0
                toc_start_candidate = None

        return None

    def detect_toc(self, candidates, lines):
        if not candidates:
            return None

        # 使用新模式检测目录开始点
        toc_start = self.detect_toc_start_by_pattern(candidates, lines)

        if toc_start is None:
            return None

        # TOC标题行前一行是"目录"，扩展范围
        prev_line_idx = toc_start - 2  # 1-based
        if prev_line_idx >= 0:
            prev_line = lines[prev_line_idx].strip()
            if re.fullmatch(r"目\s*录", prev_line):
                toc_start = prev_line_idx + 1  # TOC范围从"目录"行开始

        # 找 TOC条目第一行（用于正文判断）
        first_title_core = None
        first_title_idx = None
        for idx in range(toc_start - 1, len(lines)):
            line = lines[idx].strip()
            if not line:
                continue
            for rule_id, pattern in self.rules:
                m = pattern.match(line)
                if m:
                    first_title_core = m.group(1)
                    first_title_idx = idx + 1  # 1-based
                    break
            if first_title_core:
                break

        if not first_title_core or not first_title_idx:
            # 容错
            toc_end = toc_start + 10
        else:
            # 搜索正文起始行，从 TOC条目第一行下一行开始
            last_occurrence = None
            for idx2 in range(first_title_idx, len(lines)):
                if first_title_core in self.normalize_title(lines[idx2]):
                    last_occurrence = idx2 + 1  # 1-based
                    break
            toc_end = last_occurrence - 1 if last_occurrence else len(lines)

        return (toc_start, toc_end)

    def filter_titles(self, candidates, toc_range):
        results = []
        # 核心修改：只保留 目录结束行之后 的标题（正文开始）
        if toc_range:
            toc_end_line = toc_range[1]
            for c in candidates:
                # 行号 > 目录结束行 → 才是正文标题
                if c["line_index"] > toc_end_line:
                    results.append(c)
        else:
            # 没有识别到目录，保留全部
            results = candidates
        return results

    def assign_levels(self, titles):
        """
        按rule_id首次出现顺序分配层级
        第一个出现的rule_id为level 1，第二个新rule_id为level 2，以此类推
        """
        rule_to_level = {}
        current_level = 0
        seen_rules = set()

        for t in titles:
            rule_id = t["rule_id"]
            if rule_id not in seen_rules:
                seen_rules.add(rule_id)
                current_level += 1
                rule_to_level[rule_id] = current_level

        for t in titles:
            t["level"] = rule_to_level.get(t["rule_id"], 1)

        return titles

    def build_tree(self, titles):
        root = []
        stack = []
        for t in titles:
            node = {
                "title": t["text"],
                "line": t["line_index"],
                "rule": t["rule_id"],
                "level": t["level"],
                "children": []
            }
            while stack and stack[-1]["level"] >= node["level"]:
                stack.pop()
            if stack:
                stack[-1]["children"].append(node)
            else:
                root.append(node)
            stack.append(node)
        return root

    def print_tree(self, tree, indent=0):
        for n in tree:
            print("  " * indent +
                  f"{n['title']} [line={n['line']}, level={n['level']}, rule={n['rule']}]")
            self.print_tree(n["children"], indent + 1)

    def print_level_rules(self, titles):
        """
        调整后的规则：
        1. 按标题出现先后顺序定层级
        2. 同一个rule_id只保留第一次出现，后续重复忽略
        3. 第一个=一级，第二个新规则=二级，以此类推
        """
        seen_rules = set()  # 记录已经出现过的规则
        level_mapping = []  # 按顺序保存 [规则ID]

        for title in titles:
            rule_id = title["rule_id"]
            if rule_id not in seen_rules:
                seen_rules.add(rule_id)
                level_mapping.append(rule_id)

        # 输出：按先后顺序 = 层级
        print("\n【按出现先后顺序的层级规则】")
        for level, rule in enumerate(level_mapping, start=1):
            print(f"Level {level}: {rule}")


def build_outline(lines):
    detector = TitleDetector()

    candidates = detector.extract_candidates(lines)
    toc_range = detector.detect_toc(candidates, lines)

    # 只保留正文里的标题（目录之后）
    titles = detector.filter_titles(candidates, toc_range)
    titles = detector.assign_levels(titles)

    tree = detector.build_tree(titles)

    detector.print_tree(tree)
    detector.print_level_rules(titles)

    print("\nTOC范围:", toc_range)
    return {"outline": tree, "toc_range": toc_range}


if __name__ == "__main__":
    file_path = r"C:\Users\Administrator\Desktop\txt\2024年拓维员工手册.txt"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\n") for line in f.readlines()]

        print(f"成功读取文件: {file_path}")
        print(f"总行数: {len(lines)}")
        print("=" * 60)

        result = build_outline(lines)

    except FileNotFoundError:
        print(f"错误: 文件不存在 - {file_path}")
    except Exception as e:
        print(f"错误: {e}")
