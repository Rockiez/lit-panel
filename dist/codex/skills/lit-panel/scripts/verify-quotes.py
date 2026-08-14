#!/usr/bin/env python3
"""lit-panel 阶段二机械核验工具（随包分发，供用户自行复核评审报告）。

复现 `skills/lit-panel/SKILL.md` §4「阶段二：机械核验」的核验引擎，独立于任何
Claude Code / Codex / Antigravity 会话运行，供复核报告中每条 quote 的真实性。

核验引擎分级（Tier 1–5 分层核验）：
  - Tier 1: Exact (精确匹配)
    首尾空白 trim 后做精确子串包含匹配。
  - Tier 2: Normalized (归一化匹配)
    全角/半角、引号变体（“”‘’「」『』""''）、中文/英文标点、连续空白折叠归一化匹配。
  - Tier 3: Span Ellipsis (省略号跨度匹配)
    智能识别引文中的省略号（……、...、…、——），拆分为有序片段依序在原文中查找跨度匹配。
  - Tier 4: Fuzzy Alignment (模糊对齐候选)
    针对轻微字词笔误、错别字、OCR差异生成字符级候选与相似度，但不直接通过，
    必须进入人工仲裁。
  - Tier 5: Void / 作废与跳过
    格式违约（如「／」或非日期半角「/」并置多引文）、未提供 --source、占位符跳过（"-" 或空）、
    以及 Tier 1-4 均未命中的捏造/查无此文引文判定作废并归入人工仲裁。

输入 JSON 格式（数组，每项一条待核验判定）：
  [
    {"seat": "lit-continuity", "id": "C1", "quote": "……", "target": "text"},
    {"seat": "lit-fidelity",   "id": "F1", "quote": "……", "target": "source"}
  ]
  - 顶层必须为数组，每项必须为对象；"quote" 必填且必须为字符串。
  - "target" 可省略，默认 "text"（在被评文本中核验）；填 "source" 则在
    --source 提供的来源素材中核验（对应席01的"来源引文"标记内容）。
  - quote 为 "-" 或空字符串会被当作 ABSTAIN/NA 的占位符，直接跳过不计入统计。

用法：
    python3 scripts/verify-quotes.py <quotes.json> <被评文本路径> [--source <来源素材路径或目录>]
                                     [--format text|markdown|json]
                                     [--fuzzy-threshold 0.85]
                                     [--max-tier 1|2|3|4|5] [--include-tier]

退出码：
    0 = 全部通过或跳过（无作废条目）；
    1 = 存在核验失败/作废/格式违约条目；
    2 = 命令行参数错误、文件读取错误或 JSON 语法错误。
"""
from __future__ import annotations

import argparse
from bisect import bisect_left
import difflib
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from enum import IntEnum
from pathlib import Path


class VerificationTier(IntEnum):
    EXACT = 1
    NORMALIZED = 2
    SPAN_ELLIPSIS = 3
    FUZZY = 4
    VOID = 5


TIER_NAMES: dict[int, str] = {
    VerificationTier.EXACT: "Exact",
    VerificationTier.NORMALIZED: "Normalized",
    VerificationTier.SPAN_ELLIPSIS: "Span Ellipsis",
    VerificationTier.FUZZY: "Fuzzy Alignment",
    VerificationTier.VOID: "Void",
}

VALID_TARGET_KINDS = {"text", "source"}
MIN_FUZZY_THRESHOLD = 0.5

INVISIBLE_CHARS_PATTERN = re.compile(r"[\u200b-\u200f\u2060\ufeff\u00ad]")

ELLIPSIS_PATTERN = re.compile(r"(?:…{1,}|(?:\.\s*){3,}|(?:[—―]{2,})|(?:--+)|(?:[·•‧・]{2,}))")

QUOTE_PUNCT_MAP: dict[str, str] = {
    # 双引号变体
    "“": '"', "”": '"', "「": '"', "」": '"', "『": '"', "』": '"',
    "〝": '"', "〞": '"', "〟": '"', "❝": '"', "❞": '"', "„": '"', "‟": '"',
    # 单引号变体
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "‹": "'", "›": "'",
    "❛": "'", "❜": "'", "‵": "'", "′": "'", "＇": "'", "｀": "'",
    # 书名号与尖括号变体
    "《": "<", "》": ">", "〈": "<", "〉": ">", "⟨": "<", "⟩": ">",
    "«": "<", "»": ">", "﹤": "<", "﹥": ">",
    # 方括号与六角括号
    "【": "[", "】": "]", "〔": "[", "〕": "]",
    "［": "[", "］": "]", "﹝": "[", "﹞": "]", "〚": "[", "〛": "]",
    # 逗号、句号、叹号、问号、顿号
    "、": ",", "，": ",", "。": ".", "！": "!", "？": "?",
    "﹐": ",", "﹑": ",", "﹒": ".", "﹗": "!", "﹖": "?",
    # 冒号、分号、破折号、波浪号、中点
    "：": ":", "；": ";", "﹕": ":", "﹔": ";",
    "—": "-", "–": "-", "―": "-", "－": "-", "～": "~", "〜": "~",
    "·": ".", "•": ".", "‧": ".", "・": ".",
}


@dataclass
class VerificationResult:
    seat: str
    id: str
    verdict: str  # "通过", "作废", "跳过"
    tier: int  # 1..5
    tier_name: str  # "Exact", "Normalized", "Span Ellipsis", "Fuzzy Alignment", "Void"
    quote: str
    target_kind: str  # "text" or "source"
    reason: str
    score: float = 1.0  # 1.0 for Tier 1-3, 0.0-1.0 for Tier 4, 0.0 for Tier 5
    matched_snippet: str | None = None
    source_file: str | None = None

    def __iter__(self):
        """支持元组解构，保持对 (verdict, reason) = verify_one(...) 的完全向后兼容。"""
        return iter((self.verdict, self.reason))

    def __getitem__(self, index: int):
        return (self.verdict, self.reason)[index]

    def __len__(self) -> int:
        return 2

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tier"] = int(self.tier)
        return d


def has_multi_quote_format_violation(quote: str) -> bool:
    """检测 SKILL.md §3.4 明文禁止的 quote 列多引文并置写法。"""
    if "／" in quote:
        return True

    # 半角斜杠只豁免完整、月日数值有界的 YYYY/MM/DD 日期；单看两侧是否为数字
    # 会让「第一段】1/2【第二段」一类拼接绕过格式门。
    date_core = (
        r"(?:[12][0-9]{3})/(?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12][0-9]|3[01])"
    )
    closing_mark = r"[）)\]】〕］」』”’》〉]"
    opening_mark = r"[（(\[【〔［「『“‘《〈]"
    if re.search(rf"{closing_mark}\s*{date_core}\s*{opening_mark}", quote):
        return True

    without_dates = re.sub(
        rf"(?<![0-9]){date_core}(?![0-9])", "", quote
    )
    if "/" in without_dates:
        return True

    opening = r"[（\(\[【〔［]"
    closing = r"[）\)\]】〕］]"
    first_label = r"(?:前|上|前文|前段|句一|引文一|1|一)"
    second_label = r"(?:后|下|后文|后段|句二|引文二|2|二)"
    if bool(
        re.search(
            rf"{opening}{first_label}{closing}.*?{opening}{second_label}{closing}|"
            rf"{opening}{second_label}{closing}.*?{opening}{first_label}{closing}",
            quote,
        )
    ):
        return True
    if bool(re.search(r"(?:前[文段]|句[一1]|引文[一1])[:：].*?(?:后[文段]|句[二2]|引文[二2])[:：]", quote)):
        return True
    return False


def normalize_text(s: str) -> str:
    """标点、引号、全半角、不可见字符及空白归一化。"""
    if not s:
        return ""
    # 0. 剔除零宽字符与格式控制符
    s = INVISIBLE_CHARS_PATTERN.sub("", s)
    # 1. NFKC 归一化（全半角英数/符号）
    s = unicodedata.normalize("NFKC", s)
    # 2. 引号与括号等通用标点统一映射
    for k, v in QUOTE_PUNCT_MAP.items():
        s = s.replace(k, v)
    # 3. 连续空白（含换行/制表符/中文全角空格）折叠为单个半角空格
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_compact(s: str) -> str:
    """剔除全部标点符号与空白/不可见字符，仅保留文本内容（字母/数字/汉字）。"""
    if not s:
        return ""
    s = INVISIBLE_CHARS_PATTERN.sub("", s)
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"[\s\W_]+", "", s, flags=re.UNICODE)


def is_ellipsis_quote(quote: str) -> bool:
    """判断引文是否包含省略号跨度标记。"""
    return bool(ELLIPSIS_PATTERN.search(quote))


def match_tier_1_exact(quote: str, haystack: str) -> bool:
    """Tier 1: 精确子串命中。"""
    q = quote.strip()
    if not q:
        return False
    return q in haystack


def match_tier_2_normalized(quote: str, haystack: str) -> tuple[bool, str | None]:
    """Tier 2: 归一化子串命中（标点/全半角/空白差异）。"""
    q = quote.strip()
    if not q or not haystack:
        return False, None

    nq = normalize_text(q)
    nh = normalize_text(haystack)
    if nq and nq in nh:
        return True, nq

    # 若标点映射后仍未命中，尝试纯字符无标点压缩匹配（模型漏写/替换标点但文字完全一致）
    # 必须保证去标点后的实质内容字符数 >= 4，防止少量高频字词无标点跨句碰撞产生假阳性
    cq = normalize_compact(q)
    if len(cq) >= 4:
        ch = normalize_compact(haystack)
        if cq in ch:
            return True, cq

    return False, None


def match_tier_3_ellipsis(
    quote: str, haystack: str, max_span_distance: int = 5000
) -> tuple[bool, int, int, str | None]:
    """Tier 3: 省略号跨度匹配。

    返回值：(是否命中, 片段数量, 跨度字符数, 匹配片段说明)
    """
    raw_segments = ELLIPSIS_PATTERN.split(quote)
    segments = [s.strip() for s in raw_segments if s.strip()]
    if len(segments) < 2:
        return False, 0, 0, None

    compact_lengths = [len(normalize_compact(segment)) for segment in segments]
    if any(length < 2 for length in compact_lengths) or sum(compact_lengths) < 4:
        return False, len(segments), 0, None
    valid_segments = segments

    def find_all_occurrences(sub: str, text: str) -> list[int]:
        sub = sub.strip()
        if not sub:
            return []
        res = []
        start = 0
        while True:
            idx = text.find(sub, start)
            if idx == -1:
                break
            res.append(idx)
            start = idx + 1
        return res

    def find_ordered_span(parts: list[str], text: str) -> tuple[int, int] | None:
        occurrence_lists = [find_all_occurrences(part, text) for part in parts]
        if any(not occurrences for occurrences in occurrence_lists):
            return None

        for start_pos in occurrence_lists[0]:
            curr_pos = start_pos + len(parts[0])
            all_found = True
            for part, occurrences in zip(parts[1:], occurrence_lists[1:]):
                occurrence_index = bisect_left(occurrences, curr_pos)
                if occurrence_index >= len(occurrences):
                    all_found = False
                    break
                next_idx = occurrences[occurrence_index]
                if next_idx - curr_pos > max_span_distance:
                    all_found = False
                    break
                curr_pos = next_idx + len(part)
            if all_found:
                return start_pos, curr_pos
        return None

    # 1. 尝试精确片段序列匹配。每个片段只扫描一次，再用二分查找后继位置。
    exact_segments = [segment.strip() for segment in valid_segments]
    exact_span = find_ordered_span(exact_segments, haystack)
    if exact_span is not None:
        start_pos, end_pos = exact_span
        span_len = end_pos - start_pos
        return True, len(valid_segments), span_len, haystack[start_pos:end_pos]

    # 2. 尝试归一化片段序列匹配
    norm_haystack = normalize_text(haystack)
    norm_segments = [normalize_text(s) for s in valid_segments]
    normalized_span = find_ordered_span(norm_segments, norm_haystack)
    if normalized_span is not None:
        start_pos, end_pos = normalized_span
        span_len = end_pos - start_pos
        return True, len(valid_segments), span_len, f"归一化跨度 {span_len} 字"

    return False, len(valid_segments), 0, None


def match_tier_4_fuzzy(
    quote: str,
    haystack: str,
    threshold: float = 0.85,
    min_length: int = 4,
) -> tuple[bool, float, str | None]:
    """Tier 4: 模糊对齐候选（容错匹配与编辑距离/相似度计算）。

    返回值：(是否命中, 最高相似度, 最优对齐文本片段)
    """
    if not (MIN_FUZZY_THRESHOLD <= threshold <= 1.0):
        raise ValueError(
            f"Tier 4 threshold 必须在 {MIN_FUZZY_THRESHOLD} 到 1.0 之间: {threshold}"
        )

    q = quote.strip()
    if len(q) < min_length or not haystack:
        return False, 0.0, None

    q_len = len(q)
    candidate_support: Counter[int] = Counter()

    def sampled_anchor_positions(ngram_size: int, limit: int = 64) -> list[int]:
        count = q_len - ngram_size + 1
        if count <= 0:
            return []
        if count <= limit:
            return list(range(count))
        return sorted(
            {
                round(sample_index * (count - 1) / (limit - 1))
                for sample_index in range(limit)
            }
        )

    def add_anchor_candidates(ngram_size: int, shifts: tuple[int, ...]) -> None:
        # 每个锚点限制出现次数，但遍历横跨整条 quote 的采样锚点；这样高频首锚
        # 不会独占 300 个窗口，多个独特锚点对同一 base 的支持会被优先保留。
        for q_idx in sampled_anchor_positions(ngram_size):
            ngram = q[q_idx : q_idx + ngram_size]
            search_from = 0
            occurrences = 0
            while occurrences < 32:
                found_at = haystack.find(ngram, search_from)
                if found_at == -1:
                    break
                base = found_at - q_idx
                for shift in shifts:
                    window_start = max(
                        0, min(len(haystack) - 1, base + shift)
                    )
                    candidate_support[window_start] += 1
                search_from = found_at + max(1, ngram_size)
                occurrences += 1

    # 1. 先用 3-gram 对齐并按多锚点支持度排序候选。
    if q_len >= 3:
        add_anchor_candidates(3, (-1, 0, 1))

    # 2. 3-gram 候选不足时再用 2-gram 补充。
    if len(candidate_support) < 10 and q_len >= 2:
        add_anchor_candidates(2, (-2, -1, 0, 1, 2))

    window_starts = [
        start
        for start, _support in sorted(
            candidate_support.items(), key=lambda item: (-item[1], item[0])
        )[:300]
    ]

    # 3. 若仍无任何 n-gram 命中，按步长均匀采样窗口
    if not window_starts:
        step = max(1, q_len // 2)
        for i in range(0, max(1, len(haystack) - q_len + 1), step):
            window_starts.append(i)
            if len(window_starts) >= 300:
                break

    best_ratio = 0.0
    best_snippet: str | None = None
    delta_limit = max(4, int(q_len * 0.15))

    q_counter = Counter(q)

    window_deltas = [0]
    for distance in range(1, delta_limit + 1):
        window_deltas.extend((-distance, distance))

    for w_start in window_starts:
        for delta in window_deltas:
            w_len = q_len + delta
            if w_len <= 0:
                continue
            w_end = min(len(haystack), w_start + w_len)
            window = haystack[w_start:w_end]
            if not window:
                continue

            w_len_actual = len(window)
            if abs(w_len_actual - q_len) > delta_limit:
                continue
            # 长度上下界剪枝：若理论最大可能相似度无法达到 threshold 或当前最优，直接跳过
            max_possible_ratio = (2.0 * min(q_len, w_len_actual)) / (q_len + w_len_actual)
            if max_possible_ratio < threshold or max_possible_ratio <= best_ratio:
                continue

            # 字符集交集上界剪枝：LCS 最大长度不超过多重集交集大小
            overlap = sum(min(count, window.count(char)) for char, count in q_counter.items() if char in window)
            char_bound = (2.0 * overlap) / (q_len + w_len_actual)
            if char_bound < threshold or char_bound <= best_ratio:
                continue

            ratio = difflib.SequenceMatcher(None, q, window).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_snippet = window

    if best_ratio >= threshold:
        return True, best_ratio, best_snippet
    return False, best_ratio, best_snippet


def read_file_safely(path: Path) -> str | None:
    """安全读取文本文件，支持 UTF-8 (含 BOM)、UTF-16 与 GB18030 兼容解码，自动跳过二进制文件。"""
    try:
        raw_bytes = path.read_bytes()
    except OSError:
        return None
    # 优先检测 UTF-16 BOM 文本
    if raw_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return raw_bytes.decode("utf-16")
        except UnicodeDecodeError:
            pass
    # 检查是否为二进制文件（包含 NUL 字节）
    if b"\x00" in raw_bytes[:4096]:
        return None
    for enc in ("utf-8-sig", "gb18030"):
        try:
            return raw_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return None


def load_source_targets(source_arg: str) -> dict[str, str] | str:
    """--source 可以是单个文件或一个目录。

    返回值：
      - 单文件：直接返回该文件全文（str）。
      - 目录：返回 {相对文件名: 文件全文} 字典，供逐文件核验。
    """
    path = Path(source_arg)
    if not path.exists():
        raise FileNotFoundError(f"指定的 --source 路径不存在: {source_arg}")

    if path.is_dir():
        targets: dict[str, str] = {}
        for f in sorted(path.rglob("*")):
            if f.is_file():
                content = read_file_safely(f)
                if content is not None:
                    # 使用相对路径支持多层子目录结构且避免同名覆盖
                    rel_name = str(f.relative_to(path))
                    targets[rel_name] = content
        return targets

    content = read_file_safely(path)
    if content is None:
        raise ValueError(f"指定的 --source 文件无法作为文本解码或为二进制文件: {source_arg}")
    return content


def verify_one(
    quote: str,
    text_haystack: str | None,
    source_haystack: dict[str, str] | str | None,
    target_kind: str = "text",
    *,
    fuzzy_threshold: float = 0.85,
    max_tier: int = 5,
    min_fuzzy_length: int = 4,
    seat: str = "?",
    cid: str = "?",
) -> VerificationResult:
    """核验单条引文（Tier 1–5 分层核验）。

    返回值：VerificationResult 对象，支持 (result, reason) 解构。
    """
    if target_kind not in VALID_TARGET_KINDS:
        raise ValueError(
            f"target 必须是 text 或 source: {target_kind!r}"
        )
    if not (MIN_FUZZY_THRESHOLD <= fuzzy_threshold <= 1.0):
        raise ValueError(
            f"fuzzy_threshold 必须在 {MIN_FUZZY_THRESHOLD} 到 1.0 之间: {fuzzy_threshold}"
        )

    quote_raw = str(quote) if quote is not None else ""
    quote_clean = quote_raw.strip()
    seat_str = str(seat) if seat is not None else "?"
    cid_str = str(cid) if cid is not None else "?"

    # Tier 5: 占位符跳过
    if not quote_clean or quote_clean == "-":
        return VerificationResult(
            seat=seat_str,
            id=cid_str,
            verdict="跳过",
            tier=VerificationTier.VOID,
            tier_name=TIER_NAMES[VerificationTier.VOID],
            quote=quote_raw,
            target_kind=target_kind,
            reason="Tier 5: 跳过（ABSTAIN/NA 占位，无需核验）",
            score=0.0,
        )

    # Tier 5: 格式违约
    if has_multi_quote_format_violation(quote_clean):
        return VerificationResult(
            seat=seat_str,
            id=cid_str,
            verdict="作废",
            tier=VerificationTier.VOID,
            tier_name=TIER_NAMES[VerificationTier.VOID],
            quote=quote_raw,
            target_kind=target_kind,
            reason="Tier 5: 作废（格式违约：quote 列出现多条引文并置，禁止用「／」、非日期「/」或（前）（后）注记）",
            score=0.0,
        )

    # 确定目标核验文本
    if target_kind == "source":
        if source_haystack is None:
            return VerificationResult(
                seat=seat_str,
                id=cid_str,
                verdict="作废",
                tier=VerificationTier.VOID,
                tier_name=TIER_NAMES[VerificationTier.VOID],
                quote=quote_raw,
                target_kind=target_kind,
                reason="Tier 5: 作废（未提供 --source，无法核验来源引文）",
                score=0.0,
            )
        if isinstance(source_haystack, dict) and not source_haystack:
            return VerificationResult(
                seat=seat_str,
                id=cid_str,
                verdict="作废",
                tier=VerificationTier.VOID,
                tier_name=TIER_NAMES[VerificationTier.VOID],
                quote=quote_raw,
                target_kind=target_kind,
                reason="Tier 5: 作废（--source 目录为空或无可读文本文件）",
                score=0.0,
            )
        haystack_map = (
            source_haystack
            if isinstance(source_haystack, dict)
            else {"--source": source_haystack}
        )
    else:
        if text_haystack is None:
            return VerificationResult(
                seat=seat_str,
                id=cid_str,
                verdict="作废",
                tier=VerificationTier.VOID,
                tier_name=TIER_NAMES[VerificationTier.VOID],
                quote=quote_raw,
                target_kind=target_kind,
                reason="Tier 5: 作废（缺少被评文本，无法核验）",
                score=0.0,
            )
        haystack_map = {"text": text_haystack}

    # ================= Tier 1: Exact Match =================
    if max_tier >= VerificationTier.EXACT:
        for fname, content in haystack_map.items():
            if match_tier_1_exact(quote_clean, content):
                if target_kind == "source" and isinstance(source_haystack, dict):
                    loc_desc = f"命中来源文件：{fname}"
                elif target_kind == "source":
                    loc_desc = "精确子串命中来源素材"
                else:
                    loc_desc = "精确子串命中被评文本"
                return VerificationResult(
                    seat=seat_str,
                    id=cid_str,
                    verdict="通过",
                    tier=VerificationTier.EXACT,
                    tier_name=TIER_NAMES[VerificationTier.EXACT],
                    quote=quote_raw,
                    target_kind=target_kind,
                    reason=f"Tier 1: {loc_desc}",
                    score=1.0,
                    matched_snippet=quote_clean,
                    source_file=fname if fname not in ("text", "--source") else None,
                )

    # ================= Tier 2: Normalized Match =================
    if max_tier >= VerificationTier.NORMALIZED:
        for fname, content in haystack_map.items():
            matched, snippet = match_tier_2_normalized(quote_clean, content)
            if matched:
                if target_kind == "source" and isinstance(source_haystack, dict):
                    loc_desc = f"归一化命中来源文件：{fname}"
                elif target_kind == "source":
                    loc_desc = "归一化命中来源素材"
                else:
                    loc_desc = "归一化命中被评文本"
                return VerificationResult(
                    seat=seat_str,
                    id=cid_str,
                    verdict="通过",
                    tier=VerificationTier.NORMALIZED,
                    tier_name=TIER_NAMES[VerificationTier.NORMALIZED],
                    quote=quote_raw,
                    target_kind=target_kind,
                    reason=f"Tier 2: {loc_desc}（标点/全半角/空白差异）",
                    score=1.0,
                    matched_snippet=snippet,
                    source_file=fname if fname not in ("text", "--source") else None,
                )

    # ================= Tier 3: Span Ellipsis Match =================
    if max_tier >= VerificationTier.SPAN_ELLIPSIS and is_ellipsis_quote(quote_clean):
        for fname, content in haystack_map.items():
            matched, n_segs, span_len, snippet = match_tier_3_ellipsis(quote_clean, content)
            if matched:
                if target_kind == "source" and isinstance(source_haystack, dict):
                    loc_desc = f"省略号跨度命中来源文件：{fname}"
                elif target_kind == "source":
                    loc_desc = "省略号跨度命中来源素材"
                else:
                    loc_desc = "省略号跨度命中被评文本"
                return VerificationResult(
                    seat=seat_str,
                    id=cid_str,
                    verdict="通过",
                    tier=VerificationTier.SPAN_ELLIPSIS,
                    tier_name=TIER_NAMES[VerificationTier.SPAN_ELLIPSIS],
                    quote=quote_raw,
                    target_kind=target_kind,
                    reason=f"Tier 3: {loc_desc}（{n_segs}个片段依序匹配，跨度{span_len}字）",
                    score=1.0,
                    matched_snippet=snippet,
                    source_file=fname if fname not in ("text", "--source") else None,
                )

    # ================= Tier 4: Fuzzy Alignment Match =================
    if max_tier >= VerificationTier.FUZZY and len(quote_clean) >= min_fuzzy_length:
        best_match: tuple[str, float, str | None] | None = None
        for fname, content in haystack_map.items():
            matched, ratio, snippet = match_tier_4_fuzzy(
                quote_clean, content, threshold=fuzzy_threshold, min_length=min_fuzzy_length
            )
            # 若原始未命中，尝试归一化模糊对齐（消除全半角/引号/标点干扰）
            if not matched:
                norm_q = normalize_text(quote_clean)
                norm_c = normalize_text(content)
                if norm_q and norm_c and len(norm_q) >= min_fuzzy_length:
                    n_matched, n_ratio, n_snippet = match_tier_4_fuzzy(
                        norm_q, norm_c, threshold=fuzzy_threshold, min_length=min_fuzzy_length
                    )
                    if n_matched and (not matched or n_ratio > ratio):
                        matched, ratio, snippet = n_matched, n_ratio, n_snippet

            if matched and (best_match is None or ratio > best_match[1]):
                best_match = (fname, ratio, snippet)

        if best_match is not None:
            fname, ratio, snippet = best_match
            if target_kind == "source" and isinstance(source_haystack, dict):
                loc_desc = f"模糊对齐命中来源文件：{fname}"
            elif target_kind == "source":
                loc_desc = "模糊对齐命中来源素材"
            else:
                loc_desc = "模糊对齐命中被评文本"
            return VerificationResult(
                seat=seat_str,
                id=cid_str,
                verdict="作废",
                tier=VerificationTier.FUZZY,
                tier_name=TIER_NAMES[VerificationTier.FUZZY],
                quote=quote_raw,
                target_kind=target_kind,
                reason=f"Tier 4: 待人工仲裁（{loc_desc}，相似度 {ratio:.1%}；不得进入有效证据集合）",
                score=ratio,
                matched_snippet=snippet,
                source_file=fname if fname not in ("text", "--source") else None,
            )

    # ================= Tier 5: Void =================
    if target_kind == "source":
        if isinstance(source_haystack, dict):
            reason_str = "Tier 5: 作废（quote 未在 --source 目录任一文件中命中）"
        else:
            reason_str = "Tier 5: 作废（quote 未在 --source 中命中）"
    else:
        reason_str = "Tier 5: 作废（quote 未在被评文本中命中）"

    return VerificationResult(
        seat=seat_str,
        id=cid_str,
        verdict="作废",
        tier=VerificationTier.VOID,
        tier_name=TIER_NAMES[VerificationTier.VOID],
        quote=quote_raw,
        target_kind=target_kind,
        reason=reason_str,
        score=0.0,
    )


def verify_entries(
    entries: list[dict],
    text_haystack: str | None,
    source_haystack: dict[str, str] | str | None,
    *,
    fuzzy_threshold: float = 0.85,
    max_tier: int = 5,
    min_fuzzy_length: int = 4,
) -> list[VerificationResult]:
    """批量核验 entries 列表并返回 VerificationResult 列表。"""
    validated_entries: list[tuple[str, str, str, str]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"第 {index + 1} 项必须是 JSON 对象")
        if "quote" not in entry:
            raise ValueError(f"第 {index + 1} 项缺少必填字符串字段 quote")
        quote = entry["quote"]
        if not isinstance(quote, str):
            raise ValueError(f"第 {index + 1} 项的 quote 必须是字符串")
        target_kind = entry.get("target", "text")
        if not isinstance(target_kind, str) or target_kind not in VALID_TARGET_KINDS:
            raise ValueError(
                f"第 {index + 1} 项的 target 必须是 text 或 source"
            )
        seat = str(entry.get("seat", "?"))
        cid = str(entry.get("id", "?"))
        validated_entries.append((seat, cid, quote, target_kind))

    results: list[VerificationResult] = []
    for seat, cid, quote, target_kind in validated_entries:
        res = verify_one(
            quote=quote,
            text_haystack=text_haystack,
            source_haystack=source_haystack,
            target_kind=target_kind,
            fuzzy_threshold=fuzzy_threshold,
            max_tier=max_tier,
            min_fuzzy_length=min_fuzzy_length,
            seat=seat,
            cid=cid,
        )
        results.append(res)
    return results


def format_output_text(
    results: list[VerificationResult], *, include_tier: bool = False
) -> str:
    """生成 TSV 格式输出；默认保持旧版五列契约。"""
    lines: list[str] = []
    for r in results:
        q_preview = r.quote.strip()[:30].replace("\t", " ").replace("\r", " ").replace("\n", " ")
        safe_seat = r.seat.replace("\t", " ").replace("\r", " ").replace("\n", " ")
        safe_id = r.id.replace("\t", " ").replace("\r", " ").replace("\n", " ")
        safe_reason = r.reason.replace("\t", " ").replace("\r", " ").replace("\n", " ")
        columns = [safe_seat, safe_id, r.verdict]
        if include_tier:
            columns.append(f"Tier {r.tier} ({r.tier_name})")
        columns.extend([q_preview, safe_reason])
        lines.append("\t".join(columns))
    return "\n".join(lines)


def format_output_markdown(
    results: list[VerificationResult], *, include_tier: bool = False
) -> str:
    """生成 Markdown 表格；默认保持旧版五列契约。"""
    if include_tier:
        lines: list[str] = [
            "| 席位 | id | 结果 | Tier | 引文 | 说明 |",
            "|---|---|---|---|---|---|",
        ]
    else:
        lines = [
            "| 席位 | id | 结果 | 引文 | 说明 |",
            "|---|---|---|---|---|",
        ]
    for r in results:
        safe_seat = r.seat.replace("|", "\\|").replace("\r", " ").replace("\n", " ")
        safe_id = r.id.replace("|", "\\|").replace("\r", " ").replace("\n", " ")
        safe_quote = r.quote.strip().replace("|", "\\|").replace("\r", " ").replace("\n", " ")
        safe_reason = r.reason.replace("|", "\\|").replace("\r", " ").replace("\n", " ")
        if include_tier:
            lines.append(
                f"| {safe_seat} | {safe_id} | {r.verdict} | "
                f"Tier {r.tier} ({r.tier_name}) | “{safe_quote}” | {safe_reason} |"
            )
        else:
            lines.append(
                f"| {safe_seat} | {safe_id} | {r.verdict} | “{safe_quote}” | {safe_reason} |"
            )
    return "\n".join(lines)


def format_output_json(results: list[VerificationResult]) -> str:
    """生成 JSON 结构化格式输出。"""
    n_pass = sum(1 for r in results if r.verdict == "通过")
    n_fail = sum(1 for r in results if r.verdict == "作废")
    n_skip = sum(1 for r in results if r.verdict == "跳过")

    tier_breakdown = {
        "tier_1_exact": sum(1 for r in results if r.tier == VerificationTier.EXACT and r.verdict == "通过"),
        "tier_2_normalized": sum(1 for r in results if r.tier == VerificationTier.NORMALIZED and r.verdict == "通过"),
        "tier_3_span_ellipsis": sum(1 for r in results if r.tier == VerificationTier.SPAN_ELLIPSIS and r.verdict == "通过"),
        "tier_4_fuzzy_candidates": sum(
            1 for r in results if r.tier == VerificationTier.FUZZY
        ),
        "tier_5_void": sum(
            1
            for r in results
            if r.tier == VerificationTier.VOID and r.verdict == "作废"
        ),
        "tier_5_skipped": n_skip,
    }

    data = {
        "schema_version": "lit-panel.quote-verification/v1",
        "summary": {
            "total": len(results),
            "passed": n_pass,
            "failed": n_fail,
            "skipped": n_skip,
            "tier_breakdown": tier_breakdown,
        },
        "results": [r.to_dict() for r in results],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="lit-panel 阶段二机械核验工具（Tier 1–5 分层核验引擎）。"
    )
    parser.add_argument("quotes_json", help="待核验条目的 JSON 文件路径")
    parser.add_argument("text_path", help="被评文本文件路径")
    parser.add_argument(
        "--source",
        help="来源素材路径（文件或目录，对应席01的核验目标）",
    )
    parser.add_argument(
        "--format",
        choices=["text", "markdown", "json"],
        default="text",
        help="输出格式，默认 text（TSV），可选 markdown（表格）或 json（结构化）",
    )
    parser.add_argument(
        "--fuzzy-threshold",
        type=float,
        default=0.85,
        help="Tier 4 模糊对齐相似度阈值（默认 0.85，取值 0.5–1.0）",
    )
    parser.add_argument(
        "--max-tier",
        type=int,
        choices=[1, 2, 3, 4, 5],
        default=1,
        help="启用的最高核验等级（默认 1；1: Exact, 2: +Normalized, 3: +Ellipsis, 4: +Fuzzy, 5: All）",
    )
    parser.add_argument(
        "--include-tier",
        action="store_true",
        help="在 text/markdown 输出中显式添加 Tier 列（默认保持旧版五列）",
    )

    args = parser.parse_args(argv)

    if not (MIN_FUZZY_THRESHOLD <= args.fuzzy_threshold <= 1.0):
        print(
            f"错误：--fuzzy-threshold 必须在 {MIN_FUZZY_THRESHOLD} 到 1.0 之间: {args.fuzzy_threshold}",
            file=sys.stderr,
        )
        return 2

    # 参数边界检查与输入加载
    try:
        text_path = Path(args.text_path)
        if not text_path.exists() or text_path.is_dir():
            print(f"错误：被评文本文件不存在或为目录: {args.text_path}", file=sys.stderr)
            return 2
        text_haystack = read_file_safely(text_path)
        if text_haystack is None:
            print(f"错误：读取被评文本失败（非有效文本或二进制文件）: {args.text_path}", file=sys.stderr)
            return 2
    except Exception as exc:
        print(f"错误：读取被评文本失败 ({args.text_path}): {exc}", file=sys.stderr)
        return 2

    source_haystack = None
    if args.source:
        try:
            source_haystack = load_source_targets(args.source)
        except Exception as exc:
            print(f"错误：读取来源素材失败 ({args.source}): {exc}", file=sys.stderr)
            return 2

    try:
        quotes_path = Path(args.quotes_json)
        if not quotes_path.exists() or quotes_path.is_dir():
            print(f"错误：quotes JSON 文件不存在或为目录: {args.quotes_json}", file=sys.stderr)
            return 2
        raw_content = read_file_safely(quotes_path)
        if raw_content is None:
            print(f"错误：读取 quotes JSON 失败（非有效文本或二进制文件）: {args.quotes_json}", file=sys.stderr)
            return 2
        entries = json.loads(raw_content)
        if not isinstance(entries, list):
            print(f"错误：quotes JSON 顶层必须为数组列表: {args.quotes_json}", file=sys.stderr)
            return 2
    except json.JSONDecodeError as exc:
        print(f"错误：quotes JSON 解析失败: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"错误：读取 quotes JSON 失败 ({args.quotes_json}): {exc}", file=sys.stderr)
        return 2

    try:
        results = verify_entries(
            entries=entries,
            text_haystack=text_haystack,
            source_haystack=source_haystack,
            fuzzy_threshold=args.fuzzy_threshold,
            max_tier=args.max_tier,
        )
    except ValueError as exc:
        print(f"错误：quotes JSON 输入无效: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(format_output_json(results))
    elif args.format == "markdown":
        print(format_output_markdown(results, include_tier=args.include_tier))
    else:
        print(format_output_text(results, include_tier=args.include_tier))

    n_pass = sum(1 for r in results if r.verdict == "通过")
    n_fail = sum(1 for r in results if r.verdict == "作废")
    n_skip = sum(1 for r in results if r.verdict == "跳过")

    t1 = sum(1 for r in results if r.tier == VerificationTier.EXACT and r.verdict == "通过")
    t2 = sum(1 for r in results if r.tier == VerificationTier.NORMALIZED and r.verdict == "通过")
    t3 = sum(1 for r in results if r.tier == VerificationTier.SPAN_ELLIPSIS and r.verdict == "通过")
    t4 = sum(1 for r in results if r.tier == VerificationTier.FUZZY)

    print(
        f"\n# 汇总：通过 {n_pass} 条（Tier 1 精确: {t1}, Tier 2 归一化: {t2}, Tier 3 省略号: {t3}），Tier 4 仲裁候选 {t4} 条，作废 {n_fail} 条，跳过 {n_skip} 条（ABSTAIN/NA）。",
        file=sys.stderr,
    )

    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
