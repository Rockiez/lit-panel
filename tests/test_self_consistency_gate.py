#!/usr/bin/env python3
"""自洽性门禁：文档声称的东西必须与代码实际做的东西对得上。

docs/SCORING_0_7_DESIGN.md §6。规则一写的是「不等时文档必须显式记录差额（禁止
沉默）」——门禁因此不是「必须没有背离」，而是「背离必须与已登记的账目完全一致」。
这样它今天就是绿的、就能挡住**新增**的背离，而阶段 2 的任务是把账目缩到空。

登记账目：tests/golden/self_consistency_ledger.json
重新生成（只在有意改动公式后）：

    LIT_PANEL_REGENERATE_LEDGER=1 python3 -m unittest tests.test_self_consistency_gate
"""

from __future__ import annotations

import json
import os
import re
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "core" / "lit-panel" / "scripts"
CRITERIA = ROOT / "core" / "lit-panel" / "references" / "criteria"
SKILL_MD = ROOT / "core" / "lit-panel" / "SKILL.md"
sys.path.insert(0, str(SCRIPTS))

import band_lattice  # noqa: E402
import derive_report  # noqa: E402

LEDGER = Path(__file__).resolve().parent / "golden" / "self_consistency_ledger.json"

# 机械带位能形成窗口的全部 (band, demoted) 组合。
BANDS: tuple[tuple[str, bool], ...] = (
    ("A", False),
    ("B", False),
    ("B", True),
    ("C", False),
)


def grade_bands() -> tuple[tuple[str, float, float], ...]:
    """从 `score_grade` 本身探测出档位区间，**不复制一份阈值表**。

    这里曾经硬编码过一份区间表，于是改 score_grade 的阈值门禁毫无反应——
    门禁自己犯了它要防的「第二真源」错误，由变异测试抓出。分数经
    normalized_score 后是两位小数，按 0.01 步长扫描即可穷尽定义域。
    """
    bounds: dict[str, list[float]] = {}
    for step in range(0, 10001):
        value = round(step / 100, 2)
        label = band_lattice.score_grade(value)
        span = bounds.setdefault(label, [value, value])
        span[0] = min(span[0], value)
        span[1] = max(span[1], value)
    return tuple(
        (label, span[0], span[1])
        for label, span in sorted(bounds.items(), key=lambda item: -item[1][1])
    )


def lattice() -> band_lattice.BandLattice:
    return band_lattice.BandLattice(band_lattice.Rubric.from_criteria_dir(CRITERIA))


def audit() -> dict[str, Any]:
    """跑完五条检查，返回实际观察到的背离账目。"""
    engine = lattice()
    reaches = []
    feedback_failures: list[str] = []
    for band, demoted in BANDS:
        reach = engine.reachable(band, demoted=demoted, modifiers=False)
        if reach is None:
            feedback_failures.append(f"{band}(demoted={demoted}) 无可达配置")
            continue
        problems = engine.verify(reach)
        if problems:
            feedback_failures.extend(f"{reach.label}: {item}" for item in problems)
        reaches.append(reach)

    # 检查一：窗口声称 vs 实际可达
    window_divergences = []
    for reach in reaches:
        low, high = reach.window
        if round(reach.low, 2) != low or round(reach.high, 2) != high:
            window_divergences.append({
                "band": reach.label,
                "declared_window": [low, high],
                "reachable": [round(reach.low, 2), round(reach.high, 2)],
                "unreachable_span": round((reach.low - low) + (high - reach.high), 2),
                "utilisation": round(reach.utilisation, 4),
            })

    # 检查二：每个对外分档标签是否至少有一个可达分数（限满覆盖的窗口投影路径）
    unreachable_labels = []
    for label, low, high in grade_bands():
        if not any(reach.low <= high and reach.high >= low for reach in reaches):
            unreachable_labels.append(label)

    # 检查二之二：同一个标签是否被多个带位共用（读者无法从标签反推带位）
    overloaded = {}
    for label, low, high in grade_bands():
        owners = sorted(
            reach.label
            for reach in reaches
            if reach.low <= high and reach.high >= low
        )
        if len(owners) > 1:
            overloaded[label] = owners

    return {
        "scope": (
            "全判定配置（每条判据均为 YES/NO）下的窗口投影路径；"
            "不含 ABSTAIN/NA 与未覆盖文学维度时的回退链，"
            "两者只会让实际区间更宽。modifiers=False：不含原创性奖励与 slop 惩罚。"
        ),
        "window_divergences": window_divergences,
        "unreachable_grade_labels": unreachable_labels,
        "overloaded_grade_labels": overloaded,
        "feedback_failures": feedback_failures,
    }


class SelfConsistencyGate(unittest.TestCase):
    def test_divergences_match_the_documented_ledger(self) -> None:
        observed = audit()
        if os.environ.get("LIT_PANEL_REGENERATE_LEDGER"):
            LEDGER.parent.mkdir(parents=True, exist_ok=True)
            LEDGER.write_text(
                json.dumps(observed, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            self.skipTest(f"账目已重新生成：{LEDGER}")
        self.assertTrue(LEDGER.exists(), f"缺少自洽性账目 {LEDGER}")
        documented = json.loads(LEDGER.read_text(encoding="utf-8"))
        for key in ("window_divergences", "unreachable_grade_labels", "overloaded_grade_labels"):
            self.assertEqual(
                observed[key],
                documented[key],
                f"{key} 与已登记账目不一致——出现了未登记的背离，"
                f"或已登记的背离被修好却没有更新账目",
            )

    def test_extrema_feed_back_into_the_real_functions(self) -> None:
        """可达性模型不得与实现各说各话——这是死区当初逃脱门禁的机制。"""
        self.assertEqual(audit()["feedback_failures"], [])

    def test_craft_set_has_no_second_source(self) -> None:
        """判据表是 craft set 的唯一真源；代码里不得再出现硬编码副本。"""
        self.assertFalse(
            hasattr(derive_report, "CRAFT_SETS"),
            "derive_report.CRAFT_SETS 又出现了；craft set 只能来自判据表",
        )
        engine = lattice()
        for seat in sorted(band_lattice.LITERARY_SEATS):
            self.assertTrue(
                engine.rubric.craft_set(seat),
                f"{seat} 的判据表缺少 `## craft set 判据集` 小节",
            )

    def test_formula_version_matches_the_published_contract(self) -> None:
        text = SKILL_MD.read_text(encoding="utf-8")
        declared = set(re.findall(r"formula_version=([0-9a-z.\-]+)", text))
        self.assertIn(
            derive_report.SCORE_FORMULA_VERSION,
            declared,
            f"SKILL.md 声明的 formula_version {sorted(declared)} 与代码中的 "
            f"{derive_report.SCORE_FORMULA_VERSION} 不一致",
        )


if __name__ == "__main__":
    unittest.main()
