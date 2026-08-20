#!/usr/bin/env python3
"""lit-panel 阶段二机械核验引擎 (Tier 1-5) 单元测试套件。

覆盖范围：
  - Tier 1: Exact Match (精确匹配、空白去除、单/多文件源)
  - Tier 2: Normalized Match (标点归一化、引号变体、全半角、空白折叠、无标点压缩)
  - Tier 3: Span Ellipsis Match (省略号跨度、多片段依序匹配、乱序/缺失拦截)
  - Tier 4: Fuzzy Alignment Match (轻微笔误对齐、相似度阈值控制、短句安全防护、捏造拦截)
  - Tier 5: Void & Skip (格式违约、空占位跳过、缺失源素材、捏造引文作废)
  - CLI 调用与输出格式 (text/markdown/json、--max-tier、--fuzzy-threshold、退出码)
  - 兼容性保障 (元组解构、(result, reason) 向后兼容)
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

# 确保 scripts 目录在 sys.path 中
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import importlib
verify_quotes = importlib.import_module("verify-quotes")

VerificationTier = verify_quotes.VerificationTier
VerificationResult = verify_quotes.VerificationResult
verify_one = verify_quotes.verify_one
verify_entries = verify_quotes.verify_entries
match_tier_1_exact = verify_quotes.match_tier_1_exact
match_tier_2_normalized = verify_quotes.match_tier_2_normalized
match_tier_3_ellipsis = verify_quotes.match_tier_3_ellipsis
match_tier_4_fuzzy = verify_quotes.match_tier_4_fuzzy
normalize_text = verify_quotes.normalize_text
normalize_compact = verify_quotes.normalize_compact
has_multi_quote_format_violation = verify_quotes.has_multi_quote_format_violation
load_source_targets = verify_quotes.load_source_targets
read_file_safely = verify_quotes.read_file_safely
format_output_text = verify_quotes.format_output_text
format_output_markdown = verify_quotes.format_output_markdown
format_output_json = verify_quotes.format_output_json
main = verify_quotes.main


class TestTier1ExactMatching(unittest.TestCase):
    """Tier 1: 精确匹配测试"""

    def setUp(self):
        self.sample_text = (
            "至少一个月，夜晚被这样切开。\n"
            "就在这段日子里，离高考只剩两星期，她改了志愿。\n"
            "志愿已经递交。考试已经结束。能写的字写过，能改的地方也改过。接下来要等。"
        )

    def test_exact_match_basic(self):
        quote = "至少一个月，夜晚被这样切开。"
        res = verify_one(quote, self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "通过")
        self.assertEqual(res.tier, VerificationTier.EXACT)
        self.assertEqual(res.tier_name, "Exact")
        self.assertEqual(res.score, 1.0)
        self.assertIn("精确子串命中", res.reason)

    def test_exact_match_with_whitespace_trimming(self):
        quote = "   就在这段日子里，离高考只剩两星期，她改了志愿。  \n\t"
        res = verify_one(quote, self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "通过")
        self.assertEqual(res.tier, VerificationTier.EXACT)

    def test_exact_match_source_single_file(self):
        source_content = "张红芳反复说自己不会烧饭，平时都是老伴做饭。"
        quote = "张红芳反复说自己不会烧饭"
        res = verify_one(quote, self.sample_text, source_content, target_kind="source")
        self.assertEqual(res.verdict, "通过")
        self.assertEqual(res.tier, VerificationTier.EXACT)
        self.assertIn("精确子串命中来源素材", res.reason)

    def test_exact_match_source_directory_dict(self):
        source_dict = {
            "采访1.txt": "张红芳出生于1952年。",
            "采访2.txt": "三份口述材料里，她反复说自己不会烧饭。",
        }
        quote = "三份口述材料里，她反复说自己不会烧饭。"
        res = verify_one(quote, self.sample_text, source_dict, target_kind="source")
        self.assertEqual(res.verdict, "通过")
        self.assertEqual(res.tier, VerificationTier.EXACT)
        self.assertEqual(res.source_file, "采访2.txt")
        self.assertIn("采访2.txt", res.reason)


class TestTier2NormalizedMatching(unittest.TestCase):
    """Tier 2: 归一化匹配测试 (全半角、标点、引号变体、空白折叠)"""

    def setUp(self):
        self.sample_text = (
            "她把黑布搭上灯泡时，手指先碰到灯泡周围的热气。\n"
            "“婚姻像一盏灯”，她曾经这样写道。\n"
            "志愿（文科第一志愿）已经递交：北京大学中文系；编号：NO.12345。"
        )

    def test_fullwidth_halfwidth_normalization(self):
        # 原文包含 NO.12345，引文使用全角 ＮＯ．１２３４５
        quote = "编号：ＮＯ．１２３４５。"
        res = verify_one(quote, self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "通过")
        self.assertEqual(res.tier, VerificationTier.NORMALIZED)
        self.assertEqual(res.tier_name, "Normalized")

    def test_quotes_variation_normalization(self):
        # 原文使用弯引号 “婚姻像一盏灯”，引文使用直引号或直角引号 "婚姻像一盏灯" / 「婚姻像一盏灯」
        quote1 = '"婚姻像一盏灯",她曾经这样写道.'
        res1 = verify_one(quote1, self.sample_text, None, target_kind="text")
        self.assertEqual(res1.verdict, "通过")
        self.assertEqual(res1.tier, VerificationTier.NORMALIZED)

        quote2 = "「婚姻像一盏灯」，她曾经这样写道。"
        res2 = verify_one(quote2, self.sample_text, None, target_kind="text")
        self.assertEqual(res2.verdict, "通过")
        self.assertEqual(res2.tier, VerificationTier.NORMALIZED)

    def test_punctuation_and_whitespace_collapse(self):
        # 换行/多空格折叠与英文标点归一化
        quote = "她把黑布搭上灯泡时,   手指先碰到灯泡周围的热气."
        res = verify_one(quote, self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "通过")
        self.assertEqual(res.tier, VerificationTier.NORMALIZED)

    def test_omitted_punctuation_compact_match(self):
        # 引文漏写标点但字词完全一致
        quote = "她把黑布搭上灯泡时手指先碰到灯泡周围的热气"
        res = verify_one(quote, self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "通过")
        self.assertEqual(res.tier, VerificationTier.NORMALIZED)

    def test_compact_length_guard_prevents_false_positive(self):
        # 标点繁多但去标点后实质内容短于4字符的引文，不得借助去标点压缩跨句误匹配
        quote = "………………的………………"
        res = verify_one(quote, "今天的天气很好，风景也非常美丽。", None, target_kind="text")
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.VOID)

    def test_zero_width_and_invisible_characters_normalization(self):
        # 包含零宽空格 (\u200b)、零宽非连字符 (\u200c)、BOM (\ufeff)、词连接符 (\u2060) 的引文与原文匹配
        quote = "她把\u200b黑布\ufeff搭上灯泡时\u200c，手指先碰到\u2060灯泡周围的热气。"
        res = verify_one(quote, self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "通过")
        self.assertEqual(res.tier, VerificationTier.NORMALIZED)

    def test_extended_quote_and_bracket_variants(self):
        # 测试 CJK 弯角引号 〝〞、法式双尖引号 «»、二重角括号 〚〛 与波浪线 〜
        sample = "《文选》【卷一】“婚姻像一盏灯”～1952。"
        quote1 = "«文选»〚卷一〛〝婚姻像一盏灯〞〜1952。"
        res1 = verify_one(quote1, sample, None, target_kind="text")
        self.assertEqual(res1.verdict, "通过")
        self.assertEqual(res1.tier, VerificationTier.NORMALIZED)


class TestTier3SpanEllipsisMatching(unittest.TestCase):
    """Tier 3: 省略号跨度匹配测试"""

    def setUp(self):
        self.sample_text = (
            "志愿已经递交。考试已经结束。能写的字写过，能改的地方也改过。接下来要等。\n"
            "书是新的，时间不是。题目不会因为人紧张就变得简单，纸也不会替人留出更多日子。"
        )

    def test_chinese_double_ellipsis(self):
        quote = "志愿已经递交……接下来要等。"
        res = verify_one(quote, self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "通过")
        self.assertEqual(res.tier, VerificationTier.SPAN_ELLIPSIS)
        self.assertEqual(res.tier_name, "Span Ellipsis")
        self.assertIn("2个片段依序匹配", res.reason)

    def test_ascii_dots_ellipsis(self):
        quote = "书是新的... 纸也不会替人留出更多日子。"
        res = verify_one(quote, self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "通过")
        self.assertEqual(res.tier, VerificationTier.SPAN_ELLIPSIS)

    def test_multi_segment_ellipsis(self):
        quote = "志愿已经递交……能写的字写过……接下来要等。"
        res = verify_one(quote, self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "通过")
        self.assertEqual(res.tier, VerificationTier.SPAN_ELLIPSIS)
        self.assertIn("3个片段依序匹配", res.reason)

    def test_out_of_order_ellipsis_fails(self):
        # 颠倒先后顺序应失败
        quote = "接下来要等……志愿已经递交"
        res = verify_one(quote, self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.VOID)

    def test_hallucinated_segment_in_ellipsis_fails(self):
        # 其中一个片段为捏造文本
        quote = "志愿已经递交……她心里十分慌乱……接下来要等。"
        res = verify_one(quote, self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.VOID)

    def test_middle_dots_ellipsis(self):
        # 中文排版中间点省略号 (··· / ······)
        quote = "志愿已经递交···接下来要等。"
        res = verify_one(quote, self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "通过")
        self.assertEqual(res.tier, VerificationTier.SPAN_ELLIPSIS)

    def test_various_ellipsis_patterns(self):
        # 双水平线 ―― 与多破折号 ---、多项目符号 •••• 跨度匹配
        quote_bar = "志愿已经递交――接下来要等。"
        res_bar = verify_one(quote_bar, self.sample_text, None, target_kind="text")
        self.assertEqual(res_bar.verdict, "通过")
        self.assertEqual(res_bar.tier, VerificationTier.SPAN_ELLIPSIS)

        quote_dash = "志愿已经递交---接下来要等。"
        res_dash = verify_one(quote_dash, self.sample_text, None, target_kind="text")
        self.assertEqual(res_dash.verdict, "通过")
        self.assertEqual(res_dash.tier, VerificationTier.SPAN_ELLIPSIS)

        quote_bullet = "志愿已经递交••••接下来要等。"
        res_bullet = verify_one(quote_bullet, self.sample_text, None, target_kind="text")
        self.assertEqual(res_bullet.verdict, "通过")
        self.assertEqual(res_bullet.tier, VerificationTier.SPAN_ELLIPSIS)

    def test_one_character_ellipsis_anchors_fail_closed(self):
        res = verify_one("他……的", "这是他昨天亲口告诉我的。", None, target_kind="text")
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.VOID)

    def test_repeated_ellipsis_anchor_has_linear_runtime(self):
        started = time.perf_counter()
        matched, _, _, _ = match_tier_3_ellipsis(
            "一个……甲乙丙丁",
            "一个" * 40000,
        )
        elapsed = time.perf_counter() - started
        self.assertFalse(matched)
        self.assertLess(elapsed, 1.0, f"ellipsis matching took {elapsed:.3f}s")


class TestTier4FuzzyAlignmentMatching(unittest.TestCase):
    """Tier 4: 模糊对齐匹配测试 (容错对齐、相似度阈值控制)"""

    def setUp(self):
        self.sample_text = (
            "服从分配几个字并不写在她的题本上，却在升学去向的秩序里压着。\n"
            "两件事挤在一盏灯下面，谁也不能替谁让开太多。\n"
            "编号：NO.12345，志愿已经递交。"
        )

    def test_minor_typo_fuzzy_match_requires_manual_arbitration(self):
        # "题本" -> "笔记本" (相似度高于 0.85)，只能进入人工仲裁，不能当作逐字通过。
        quote = "服从分配几个字并不写在她的笔记本上，却在升学去向的秩序里压着。"
        res = verify_one(quote, self.sample_text, None, target_kind="text", fuzzy_threshold=0.85)
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.FUZZY)
        self.assertEqual(res.tier_name, "Fuzzy Alignment")
        self.assertGreaterEqual(res.score, 0.85)
        self.assertIn("待人工仲裁", res.reason)

    def test_fuzzy_with_fullwidth_and_quote_normalization(self):
        # 全角数字 + 引号变体 + 轻微错字（"志原" vs "志愿"），归一化模糊对齐命中
        quote = "编号：ＮＯ．１２３４５，志原已经递交。"
        res = verify_one(quote, self.sample_text, None, target_kind="text", fuzzy_threshold=0.85)
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.FUZZY)
        self.assertGreaterEqual(res.score, 0.85)

    def test_fuzzy_threshold_boundary(self):
        # 轻微差异在默认阈值下成为 Tier 4 仲裁候选，严格阈值下不产生候选。
        quote = "两件事挤在一盏灯下面，谁也不能替谁让开很多。"  # "太多" -> "很多"
        res_pass = verify_one(quote, self.sample_text, None, target_kind="text", fuzzy_threshold=0.85)
        self.assertEqual(res_pass.verdict, "作废")
        self.assertEqual(res_pass.tier, VerificationTier.FUZZY)

        res_strict = verify_one(quote, self.sample_text, None, target_kind="text", fuzzy_threshold=0.98)
        self.assertEqual(res_strict.verdict, "作废")
        self.assertEqual(res_strict.tier, VerificationTier.VOID)

    def test_short_quote_safety_guard(self):
        # 极短引文 (长度 < 4) 不触发模糊对齐，防止短语误报假阳性
        quote = "几件事"
        res = verify_one(quote, self.sample_text, None, target_kind="text", min_fuzzy_length=4)
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.VOID)

    def test_completely_fabricated_quote_fails(self):
        # 纯捏造引文拦截
        quote = "岁月像一条奔涌的长河，把她大半生的悲欢都冲刷成了温柔的鹅卵石。"
        res = verify_one(quote, self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.VOID)

    def test_fuzzy_alignment_speed_large_text(self):
        # 大文本 (>= 1MB) 模糊搜索性能测试
        large_text = ("这是一段很长的关于文学理论与叙事艺术的探讨分析文本，我们在这里做详细的展开论述。" * 1000) * 10
        quote_typo = "这是一段很长的关于哲学理论与叙事艺术的探讨分析文本，我们在这里做详细的展开论述。"
        res = verify_one(quote_typo, large_text, None, target_kind="text")
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.FUZZY)

    def test_fuzzy_factual_changes_never_pass(self):
        cases = [
            ("她明确表示会烧饭。", "她明确表示不会烧饭。"),
            ("他借了八万元用于修建新房。", "他借了三万元用于修建新房。"),
        ]
        for quote, text in cases:
            with self.subTest(quote=quote):
                res = verify_one(quote, text, None, target_kind="text")
                self.assertEqual(res.verdict, "作废")
                self.assertEqual(res.tier, VerificationTier.FUZZY)
                self.assertIn("待人工仲裁", res.reason)

    def test_clipped_fuzzy_window_cannot_accept_fabricated_suffix(self):
        matched, score, snippet = match_tier_4_fuzzy(
            "甲" * 75 + "乙" * 25,
            "甲" * 75,
            threshold=0.85,
        )
        self.assertFalse(matched)
        self.assertLess(score, 0.85)
        self.assertIsNone(snippet)

    def test_fuzzy_threshold_one_is_not_bypassed_by_shortcut(self):
        matched, score, _ = match_tier_4_fuzzy(
            "甲" * 100 + "乙",
            "乙" + "甲" * 100,
            threshold=1.0,
        )
        self.assertFalse(matched)
        self.assertLess(score, 1.0)

    def test_frequent_early_ngram_does_not_hide_distinctive_candidate(self):
        quote = "的确的这是一条非常独特而且完整的引文内容"
        typo_candidate = "的确的这是一条非常独特而且完整的引文字容"
        haystack = "的确的" * 150 + typo_candidate

        matched, score, snippet = match_tier_4_fuzzy(
            quote, haystack, threshold=0.85
        )

        self.assertTrue(matched)
        self.assertGreater(score, 0.9)
        self.assertIsNotNone(snippet)
        self.assertIn("非常独特", snippet)

    def test_fuzzy_matcher_returns_best_near_eof_window(self):
        quote = "甲" * 99 + "乙"
        haystack = "甲" * 99

        matched, score, snippet = match_tier_4_fuzzy(
            quote, haystack, threshold=0.85
        )

        self.assertTrue(matched)
        self.assertGreater(score, 0.99)
        self.assertEqual(snippet, haystack)

    def test_fuzzy_matcher_rejects_threshold_below_documented_floor(self):
        with self.assertRaisesRegex(ValueError, "0.5"):
            match_tier_4_fuzzy("甲乙丙丁", "戊己庚辛", threshold=0.0)


class TestTier5VoidAndSkip(unittest.TestCase):
    """Tier 5: 作废与跳过逻辑测试"""

    def setUp(self):
        self.sample_text = "这是一段测试正文内容，记录于1952/05/01。"

    def test_placeholder_dash_skipped(self):
        res = verify_one("-", self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "跳过")
        self.assertEqual(res.tier, VerificationTier.VOID)
        self.assertIn("跳过", res.reason)

    def test_empty_quote_skipped(self):
        res = verify_one("", self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "跳过")
        self.assertEqual(res.tier, VerificationTier.VOID)

    def test_multi_quote_slash_violation(self):
        quote = "第一句／第二句"
        res = verify_one(quote, self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.VOID)
        self.assertIn("格式违约", res.reason)

    def test_multi_quote_spaced_slash_violation(self):
        quote = "第一句 / 第二句"
        res = verify_one(quote, self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.VOID)
        self.assertIn("格式违约", res.reason)

    def test_multi_quote_unspaced_slash_violation(self):
        quote = "【第一句正文】/【第二句正文】"
        text = "第一句正文。第二句正文。"
        res = verify_one(quote, text, None, target_kind="text")
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.VOID)
        self.assertIn("格式违约", res.reason)

    def test_non_violation_date_slash_allowed(self):
        quote = "记录于1952/05/01"
        res = verify_one(quote, self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "通过")
        self.assertEqual(res.tier, VerificationTier.EXACT)

    def test_numeric_looking_slash_cannot_join_two_quotes(self):
        quote = "【第一句正文】1/2【第二句正文】"
        text = "第一句正文1。2第二句正文"
        res = verify_one(quote, text, None, target_kind="text")
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.VOID)
        self.assertIn("格式违约", res.reason)

    def test_date_slash_cannot_join_two_bracketed_quotes(self):
        quote = "【第一句正文】2024/01/01【第二句正文】"
        text = "第一句正文2024。01。01第二句正文"
        res = verify_one(quote, text, None, target_kind="text")
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.VOID)
        self.assertIn("格式违约", res.reason)

    def test_multi_quote_before_after_annotation_violation(self):
        quote = "（前）这是前一句（后）这是后一句"
        res = verify_one(quote, self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.VOID)
        self.assertIn("格式违约", res.reason)

    def test_multi_quote_halfwidth_annotation_violation(self):
        quote = "(前)这是前一句(后)这是后一句"
        res = verify_one(quote, self.sample_text, None, target_kind="text")
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.VOID)
        self.assertIn("格式违约", res.reason)

    def test_multi_quote_long_and_numbered_annotations_violation(self):
        violations = [
            "（前段）第一句正文（后段）第二句正文",
            "（1）第一句正文（2）第二句正文",
        ]
        for quote in violations:
            with self.subTest(quote=quote):
                self.assertTrue(has_multi_quote_format_violation(quote))
                res = verify_one(quote, self.sample_text, None, target_kind="text")
                self.assertEqual(res.verdict, "作废")
                self.assertEqual(res.tier, VerificationTier.VOID)

    def test_missing_source_when_target_is_source(self):
        quote = "某来源引文"
        res = verify_one(quote, self.sample_text, None, target_kind="source")
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.VOID)
        self.assertIn("未提供 --source", res.reason)

    def test_missing_text_haystack(self):
        quote = "正文引文"
        res = verify_one(quote, None, None, target_kind="text")
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.VOID)
        self.assertIn("缺少被评文本", res.reason)

    def test_empty_source_directory_void(self):
        quote = "某来源引文"
        res = verify_one(quote, self.sample_text, {}, target_kind="source")
        self.assertEqual(res.verdict, "作废")
        self.assertEqual(res.tier, VerificationTier.VOID)
        self.assertIn("目录为空", res.reason)

    def test_expanded_format_violation_brackets(self):
        # 各种括号与关键词并置违约
        violations = [
            "【前】第一句【后】第二句",
            "[前]第一句[后]第二句",
            "〔前〕第一句〔后〕第二句",
            "［前］第一句［后］第二句",
            "（上）第一句（下）第二句",
            "【上】第一句【下】第二句",
            "（后）第二句（前）第一句",
            "前段：第一句后段：第二句",
            "句一：第一句句二：第二句",
            "引文1: 第一句引文2: 第二句",
        ]
        for v in violations:
            self.assertTrue(has_multi_quote_format_violation(v), f"Failed for {v}")
            res = verify_one(v, self.sample_text, None, target_kind="text")
            self.assertEqual(res.verdict, "作废")
            self.assertIn("格式违约", res.reason)

    def test_non_string_quote_and_seat_inputs(self):
        # 传入数字、None、布尔等非字符串类型时不应崩溃
        res_int = verify_one(12345, "记录于12345号档案", None, target_kind="text", seat=1, cid=2)
        self.assertEqual(res_int.verdict, "通过")
        self.assertEqual(res_int.seat, "1")
        self.assertEqual(res_int.id, "2")

        res_none = verify_one(None, self.sample_text, None, target_kind="text")
        self.assertEqual(res_none.verdict, "跳过")
        self.assertEqual(res_none.quote, "")

    def test_unknown_target_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "target"):
            verify_one("只在正文出现", "只在正文出现", None, target_kind="soruce")


class TestSourceDirectoryHandling(unittest.TestCase):
    """--source 多文件目录加载与核验测试"""

    def test_load_source_targets_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "file1.txt").write_text("访谈记录一：张红芳出生地为苏州。", encoding="utf-8")
            (tmppath / "file2.md").write_text("访谈记录二：不会烧饭是明确陈述。", encoding="utf-8")
            # 创建一个二进制文件
            (tmppath / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")

            targets = load_source_targets(str(tmppath))
            self.assertIsInstance(targets, dict)
            self.assertIn("file1.txt", targets)
            self.assertIn("file2.md", targets)
            self.assertNotIn("image.png", targets)

            # 核验位于不同文件中的引文
            res1 = verify_one("张红芳出生地为苏州", "正文", targets, target_kind="source")
            self.assertEqual(res1.verdict, "通过")
            self.assertEqual(res1.source_file, "file1.txt")

            res2 = verify_one("不会烧饭是明确陈述", "正文", targets, target_kind="source")
            self.assertEqual(res2.verdict, "通过")
            self.assertEqual(res2.source_file, "file2.md")

            res_fail = verify_one("完全不存在的来源引文", "正文", targets, target_kind="source")
            self.assertEqual(res_fail.verdict, "作废")

    def test_load_source_targets_gbk_and_bom(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # GB18030 / GBK 编码文件
            (tmppath / "gbk.txt").write_bytes("访谈材料：张红芳自述生活经历。".encode("gb18030"))
            # UTF-8 with BOM 文件
            (tmppath / "bom.txt").write_bytes("\ufeff访谈记录：另一段补充说明。".encode("utf-8"))

            targets = load_source_targets(str(tmppath))
            self.assertIn("gbk.txt", targets)
            self.assertIn("bom.txt", targets)
            self.assertIn("张红芳自述生活经历", targets["gbk.txt"])
            self.assertIn("另一段补充说明", targets["bom.txt"])

    def test_nested_subdirectories_no_collision(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "sub1").mkdir()
            (tmppath / "sub2").mkdir()
            (tmppath / "sub1" / "notes.txt").write_text("第一部分访谈记录", encoding="utf-8")
            (tmppath / "sub2" / "notes.txt").write_text("第二部分补充资料", encoding="utf-8")

            targets = load_source_targets(str(tmppath))
            self.assertEqual(len(targets), 2)
            self.assertIn(os.path.join("sub1", "notes.txt"), targets)
            self.assertIn(os.path.join("sub2", "notes.txt"), targets)

    def test_empty_source_dir_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            targets = load_source_targets(tmpdir)
            self.assertEqual(targets, {})

    def test_read_file_safely_utf16_bom(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            utf16_file = tmppath / "utf16_sample.txt"
            sample_content = "访谈记录：张红芳自述生活经历。"
            # 写入 UTF-16 包含 BOM
            utf16_file.write_bytes(sample_content.encode("utf-16"))

            decoded = read_file_safely(utf16_file)
            self.assertEqual(decoded, sample_content)

            targets = load_source_targets(str(tmppath))
            self.assertIn("utf16_sample.txt", targets)
            self.assertEqual(targets["utf16_sample.txt"], sample_content)

    def test_read_file_safely_binary_and_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            bin_file = tmppath / "test.bin"
            bin_file.write_bytes(b"\x00\x01\x02\x03\x04\x05")
            self.assertIsNone(read_file_safely(bin_file))
            self.assertIsNone(read_file_safely(tmppath / "missing.txt"))


class TestMaxTierLimiting(unittest.TestCase):
    """--max-tier 阶段限制测试"""

    def setUp(self):
        self.sample_text = "两件事挤在一盏灯下面，谁也不能替谁让开太多。"

    def test_max_tier_1_blocks_normalized(self):
        # 归一化引文在 max_tier=1 下被拦截
        quote = "两件事挤在一盏灯下面,谁也不能替谁让开太多."
        res1 = verify_one(quote, self.sample_text, None, target_kind="text", max_tier=1)
        self.assertEqual(res1.verdict, "作废")

        res2 = verify_one(quote, self.sample_text, None, target_kind="text", max_tier=2)
        self.assertEqual(res2.verdict, "通过")
        self.assertEqual(res2.tier, VerificationTier.NORMALIZED)

    def test_max_tier_2_blocks_span_ellipsis(self):
        # 省略号跨度引文在 max_tier=2 下被拦截作废，在 max_tier=3 下通过
        text_with_span = "志愿已经递交。考试已经结束。接下来要等。"
        quote = "志愿已经递交……接下来要等。"
        res1 = verify_one(quote, text_with_span, None, target_kind="text", max_tier=2)
        self.assertEqual(res1.verdict, "作废")
        self.assertEqual(res1.tier, VerificationTier.VOID)

        res2 = verify_one(quote, text_with_span, None, target_kind="text", max_tier=3)
        self.assertEqual(res2.verdict, "通过")
        self.assertEqual(res2.tier, VerificationTier.SPAN_ELLIPSIS)

    def test_max_tier_3_blocks_fuzzy(self):
        # 模糊引文在 max_tier=3 下被拦截
        quote = "两件事挤在一盏灯下面，谁也不能替谁让开很多。"
        res1 = verify_one(quote, self.sample_text, None, target_kind="text", max_tier=3)
        self.assertEqual(res1.verdict, "作废")

        res2 = verify_one(quote, self.sample_text, None, target_kind="text", max_tier=4)
        self.assertEqual(res2.verdict, "作废")
        self.assertEqual(res2.tier, VerificationTier.FUZZY)

    def test_max_tier_transitions_full_matrix(self):
        # 针对同一文本测试 4 种类型引文在 max_tier=1..5 下的阶梯表现
        sample = "至少一个月，夜晚被这样切开。离高考只剩两星期，她改了志愿。接下来要等。"
        q_exact = "至少一个月，夜晚被这样切开。"
        q_norm = "至少一个月,夜晚被这样切开."
        q_ellipsis = "至少一个月……接下来要等。"
        q_fuzzy = "至少一个月，夜幕被这样切开。"

        # max_tier = 1
        self.assertEqual(verify_one(q_exact, sample, None, max_tier=1).verdict, "通过")
        self.assertEqual(verify_one(q_norm, sample, None, max_tier=1).verdict, "作废")
        self.assertEqual(verify_one(q_ellipsis, sample, None, max_tier=1).verdict, "作废")
        self.assertEqual(verify_one(q_fuzzy, sample, None, max_tier=1).verdict, "作废")

        # max_tier = 2
        self.assertEqual(verify_one(q_exact, sample, None, max_tier=2).verdict, "通过")
        self.assertEqual(verify_one(q_norm, sample, None, max_tier=2).verdict, "通过")
        self.assertEqual(verify_one(q_ellipsis, sample, None, max_tier=2).verdict, "作废")
        self.assertEqual(verify_one(q_fuzzy, sample, None, max_tier=2).verdict, "作废")

        # max_tier = 3
        self.assertEqual(verify_one(q_exact, sample, None, max_tier=3).verdict, "通过")
        self.assertEqual(verify_one(q_norm, sample, None, max_tier=3).verdict, "通过")
        self.assertEqual(verify_one(q_ellipsis, sample, None, max_tier=3).verdict, "通过")
        self.assertEqual(verify_one(q_fuzzy, sample, None, max_tier=3).verdict, "作废")

        # max_tier = 4 / 5
        for mt in (4, 5):
            self.assertEqual(verify_one(q_exact, sample, None, max_tier=mt).verdict, "通过")
            self.assertEqual(verify_one(q_norm, sample, None, max_tier=mt).verdict, "通过")
            self.assertEqual(verify_one(q_ellipsis, sample, None, max_tier=mt).verdict, "通过")
            fuzzy_result = verify_one(q_fuzzy, sample, None, max_tier=mt)
            self.assertEqual(fuzzy_result.verdict, "作废")
            self.assertEqual(fuzzy_result.tier, VerificationTier.FUZZY)


class TestTupleUnpackingCompatibility(unittest.TestCase):
    """向后兼容性测试：(result, reason) 解构与字段访问"""

    def test_tuple_unpacking(self):
        res = verify_one("测试引文", "测试引文在此处出现", None, target_kind="text")
        result, reason = res
        self.assertEqual(result, "通过")
        self.assertIn("精确子串命中", reason)

    def test_index_access(self):
        res = verify_one("-", "正文", None, target_kind="text")
        self.assertEqual(res[0], "跳过")
        self.assertIn("无需核验", res[1])

    def test_len_and_indexing_and_slicing(self):
        res = verify_one("测试引文", "测试引文在此处出现", None, target_kind="text")
        self.assertEqual(len(res), 2)
        self.assertEqual(res[-1], res.reason)
        self.assertEqual(res[-2], res.verdict)
        self.assertEqual(list(res[:]), [res.verdict, res.reason])

    def test_to_dict_primitive_tier(self):
        res = verify_one("测试引文", "测试引文在此处出现", None, target_kind="text")
        d = res.to_dict()
        self.assertIsInstance(d["tier"], int)
        self.assertEqual(d["tier"], 1)
        self.assertEqual(d["tier_name"], "Exact")
        # 确保 JSON 序列化无异常
        dumped = json.dumps(d)
        self.assertIn('"tier": 1', dumped)


class TestCLIFeaturesAndOutputs(unittest.TestCase):
    """CLI 命令行调用与输出格式测试 (text, markdown, json, 退出码)"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmppath = Path(self.temp_dir.name)

        self.text_file = self.tmppath / "text.txt"
        self.text_file.write_text(
            "第一段：至少一个月，夜晚被这样切开。\n"
            "第二段：就在这段日子里，离高考只剩两星期，她改了志愿。\n"
            "第三段：服从分配几个字并不写在她的题本上，却在升学去向的秩序里压着。",
            encoding="utf-8",
        )

        self.source_file = self.tmppath / "source.txt"
        self.source_file.write_text("来源素材：张红芳反复说自己不会烧饭。", encoding="utf-8")

        self.quotes_pass_file = self.tmppath / "quotes_pass.json"
        self.quotes_pass_file.write_text(
            json.dumps([
                {"seat": "lit-continuity", "id": "C1", "quote": "至少一个月，夜晚被这样切开。", "target": "text"},
                {"seat": "lit-fidelity", "id": "F1", "quote": "张红芳反复说自己不会烧饭", "target": "source"},
                {"seat": "lit-structure", "id": "N1", "quote": "-", "target": "text"},
            ], ensure_ascii=False),
            encoding="utf-8",
        )

        self.quotes_fail_file = self.tmppath / "quotes_fail.json"
        self.quotes_fail_file.write_text(
            json.dumps([
                {"seat": "lit-slop", "id": "A1", "quote": "这是一条完全伪造的不存在引文", "target": "text"},
            ], ensure_ascii=False),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_exit_code_success(self):
        code = main([
            str(self.quotes_pass_file),
            str(self.text_file),
            "--source", str(self.source_file),
            "--format", "text",
        ])
        self.assertEqual(code, 0)

    def test_cli_exit_code_failure(self):
        code = main([
            str(self.quotes_fail_file),
            str(self.text_file),
            "--format", "text",
        ])
        self.assertEqual(code, 1)

    def test_cli_exit_code_io_error(self):
        code = main([
            "non_existent_quotes.json",
            str(self.text_file),
        ])
        self.assertEqual(code, 2)

    def test_cli_fuzzy_threshold_out_of_bounds(self):
        # 阈值超出文档约定的 [0.5, 1.0] 应返回退出码 2
        code_high = main([
            str(self.quotes_pass_file),
            str(self.text_file),
            "--fuzzy-threshold", "1.5",
        ])
        self.assertEqual(code_high, 2)

        code_low = main([
            str(self.quotes_pass_file),
            str(self.text_file),
            "--fuzzy-threshold", "-0.1",
        ])
        self.assertEqual(code_low, 2)

        for threshold in ("0", "0.49"):
            with self.subTest(threshold=threshold):
                code_below_floor = main([
                    str(self.quotes_pass_file),
                    str(self.text_file),
                    "--fuzzy-threshold", threshold,
                ])
                self.assertEqual(code_below_floor, 2)

    def test_cli_format_json_output(self):
        captured_out = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_out
        try:
            code = main([
                str(self.quotes_pass_file),
                str(self.text_file),
                "--source", str(self.source_file),
                "--format", "json",
            ])
        finally:
            sys.stdout = old_stdout

        self.assertEqual(code, 0)
        output_str = captured_out.getvalue()
        data = json.loads(output_str)
        self.assertEqual(data["schema_version"], "lit-panel.quote-verification/v1")
        self.assertIn("summary", data)
        self.assertEqual(data["summary"]["total"], 3)
        self.assertEqual(data["summary"]["passed"], 2)
        self.assertEqual(data["summary"]["skipped"], 1)
        self.assertEqual(data["summary"]["failed"], 0)
        self.assertEqual(data["summary"]["tier_breakdown"]["tier_1_exact"], 2)
        self.assertEqual(len(data["results"]), 3)

    def test_cli_format_markdown_output(self):
        captured_out = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_out
        try:
            code = main([
                str(self.quotes_pass_file),
                str(self.text_file),
                "--source", str(self.source_file),
                "--format", "markdown",
            ])
        finally:
            sys.stdout = old_stdout

        self.assertEqual(code, 0)
        output_str = captured_out.getvalue()
        self.assertIn("| 席位 | id | 结果 | 引文 | 说明 |", output_str)
        self.assertNotIn("| Tier |", output_str)
        self.assertIn("| lit-continuity | C1 | 通过 | “至少一个月，夜晚被这样切开。” |", output_str)

    def test_cli_include_tier_opt_in(self):
        captured_out = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured_out
        try:
            code = main([
                str(self.quotes_pass_file),
                str(self.text_file),
                "--source", str(self.source_file),
                "--format", "markdown",
                "--include-tier",
            ])
        finally:
            sys.stdout = old_stdout

        self.assertEqual(code, 0)
        self.assertIn("| 席位 | id | 结果 | Tier | 引文 | 说明 |", captured_out.getvalue())

    def test_malformed_entries_handling(self):
        malformed_batches = [
            ["invalid_entry"],
            [{}],
            [{"quote": None}],
            [{"quote": 12345}],
            [{"quote": "正文", "target": "soruce"}],
        ]
        for entries in malformed_batches:
            with self.subTest(entries=entries):
                with self.assertRaises(ValueError):
                    verify_entries(entries, "至少一个月，夜晚被这样切开。", None)

    def test_cli_malformed_entries_exit_two(self):
        malformed_file = self.tmppath / "quotes_malformed.json"
        malformed_file.write_text("[{}]", encoding="utf-8")
        code = main([str(malformed_file), str(self.text_file), "--format", "json"])
        self.assertEqual(code, 2)

    def test_cli_directory_as_text_path_error(self):
        # 被评文本传入目录而非文件应返回退出码 2
        code = main([
            str(self.quotes_pass_file),
            str(self.tmppath),
        ])
        self.assertEqual(code, 2)

    def test_tsv_and_markdown_escaping(self):
        # 测试包含特殊符号（管道符 |、制表符 \t、换行符 \n、回车 \r）的条目安全格式化
        results = [
            VerificationResult(
                seat="lit|custom\t1",
                id="C|1\nsub",
                verdict="通过",
                tier=VerificationTier.EXACT,
                tier_name="Exact",
                quote="引用包含|管道符\t制表符\n换行",
                target_kind="text",
                reason="说明包含|管道符\r回车\n换行",
                score=1.0,
            )
        ]
        tsv_out = format_output_text(results)
        self.assertNotIn("\r", tsv_out)
        self.assertNotIn("\n", tsv_out)
        self.assertEqual(len(tsv_out.split("\t")), 5)
        self.assertEqual(len(format_output_text(results, include_tier=True).split("\t")), 6)

        md_out = format_output_markdown(results)
        # 表格应该只有2行表头 + 1行数据行 = 3行
        md_lines = md_out.strip().split("\n")
        self.assertEqual(len(md_lines), 3)
        # 默认维持旧版 5 列；Tier 列只在显式 opt-in 时添加。
        import re
        self.assertEqual(len(re.split(r"(?<!\\)\|", md_lines[2])), 7)
        self.assertIn(r"\|", md_lines[2])
        md_with_tier = format_output_markdown(results, include_tier=True)
        self.assertEqual(len(re.split(r"(?<!\\)\|", md_with_tier.strip().split("\n")[2])), 8)

    def test_json_schema_distinguishes_fuzzy_candidates_from_tier_5_void(self):
        fuzzy_candidate = VerificationResult(
            seat="lit-continuity",
            id="C1",
            verdict="作废",
            tier=VerificationTier.FUZZY,
            tier_name="Fuzzy Alignment",
            quote="候选引文",
            target_kind="text",
            reason="Tier 4: 待人工仲裁",
            score=0.9,
        )
        hard_void = VerificationResult(
            seat="lit-continuity",
            id="C2",
            verdict="作废",
            tier=VerificationTier.VOID,
            tier_name="Void",
            quote="伪造引文",
            target_kind="text",
            reason="Tier 5: 作废",
            score=0.0,
        )
        data = json.loads(format_output_json([fuzzy_candidate, hard_void]))
        breakdown = data["summary"]["tier_breakdown"]
        self.assertEqual(data["schema_version"], "lit-panel.quote-verification/v1")
        self.assertEqual(data["summary"]["failed"], 2)
        self.assertEqual(breakdown["tier_4_fuzzy_candidates"], 1)
        self.assertEqual(breakdown["tier_5_void"], 1)

    def test_cli_max_tier_argument(self):
        # 测试 CLI 传入 --max-tier 选项对判定的影响
        quotes_ellipsis = self.tmppath / "quotes_ellipsis.json"
        quotes_ellipsis.write_text(
            json.dumps([
                {"seat": "lit-continuity", "id": "C1", "quote": "至少一个月……离高考只剩两星期", "target": "text"},
            ], ensure_ascii=False),
            encoding="utf-8",
        )
        # 在 max-tier 2 下省略号跨度失败退出码为 1
        code_t2 = main([
            str(quotes_ellipsis),
            str(self.text_file),
            "--max-tier", "2",
        ])
        self.assertEqual(code_t2, 1)

        # 在 max-tier 3 下省略号跨度成功退出码为 0
        code_t3 = main([
            str(quotes_ellipsis),
            str(self.text_file),
            "--max-tier", "3",
        ])
        self.assertEqual(code_t3, 0)

    def test_cli_default_runs_all_verification_tiers(self):
        quotes_normalized = self.tmppath / "quotes_normalized.json"
        quotes_normalized.write_text(
            json.dumps([
                {
                    "seat": "lit-continuity",
                    "id": "C1",
                    "quote": "第一段:至少一个月,夜晚被这样切开.",
                    "target": "text",
                },
            ], ensure_ascii=False),
            encoding="utf-8",
        )

        self.assertEqual(main([str(quotes_normalized), str(self.text_file)]), 0)
        self.assertEqual(
            main([str(quotes_normalized), str(self.text_file), "--max-tier", "1"]),
            1,
        )


class TestPackagedSkillVerifier(unittest.TestCase):
    """技能目录被单独复制后仍应自包含机械核验 CLI。"""

    def test_copied_skill_runs_outside_repository(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            installed_skill = temp_path / "installed" / "lit-panel"
            installed_skill.parent.mkdir()
            shutil.copytree(REPO_ROOT / "skills" / "lit-panel", installed_skill)

            text_path = temp_path / "chapter.md"
            text_path.write_text("至少一个月，夜晚被这样切开。", encoding="utf-8")
            quotes_path = temp_path / "quotes.json"
            verifier = installed_skill / "scripts" / "verify-quotes.py"

            quotes_path.write_text(
                json.dumps([{"quote": "至少一个月，夜晚被这样切开。"}], ensure_ascii=False),
                encoding="utf-8",
            )
            good = subprocess.run(
                [
                    sys.executable,
                    str(verifier),
                    str(quotes_path),
                    str(text_path),
                    "--format",
                    "json",
                    "--max-tier",
                    "5",
                ],
                cwd=temp_path,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertEqual(json.loads(good.stdout)["summary"]["passed"], 1)

            quotes_path.write_text(
                json.dumps([{"quote": "这是一条完全伪造的引文"}], ensure_ascii=False),
                encoding="utf-8",
            )
            bad = subprocess.run(
                [
                    sys.executable,
                    str(verifier),
                    str(quotes_path),
                    str(text_path),
                    "--format",
                    "json",
                    "--max-tier",
                    "5",
                ],
                cwd=temp_path,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(bad.returncode, 1, bad.stderr)
            self.assertEqual(json.loads(bad.stdout)["summary"]["failed"], 1)


if __name__ == "__main__":
    unittest.main()
