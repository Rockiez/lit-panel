#!/usr/bin/env python3
"""评分格的黄金基线：证明重构前后逐位相同。

本测试存在的唯一目的是给「阶段 0 行为严格等价」提供实证。它用真实判据表构造
确定性的判定向量样本，快照评分格每一个函数的输出，并与已提交的基线逐位比对。

任何**有意**的公式改动都必须同时重新生成基线，并在提交信息中说明为什么分数变了；
无意的改动会在这里失败。重新生成：

    LIT_PANEL_REGENERATE_GOLDEN=1 python3 -m unittest tests.test_scoring_lattice_golden

`LATTICE` 映射表是为跨重构存活而设的：评分格的函数从 derive_report 迁往
band_lattice 时只改这一处，基线 JSON 的键保持不变。
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import unittest
import zlib
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "core" / "lit-panel" / "scripts"
CRITERIA = ROOT / "core" / "lit-panel" / "references" / "criteria"
sys.path.insert(0, str(SCRIPTS))

import band_lattice  # noqa: E402
import derive_report  # noqa: E402
from lit_panel_common import parse_criteria  # noqa: E402

BASELINE = Path(__file__).resolve().parent / "golden" / "scoring_lattice_baseline.json"

_LATTICE = band_lattice.BandLattice(band_lattice.Rubric.from_criteria_dir(CRITERIA))

# 重构时只改这张表；基线 JSON 的键不变。
# 评分格已迁入 band_lattice（阶段 0）；fidelity_band 与 originality_bonus 留在
# derive_report——它们不依赖 rubric，属报告层而非带位格。
LATTICE: dict[str, Callable[..., Any]] = {
    "craft_ratio": _LATTICE.craft_ratio,
    "craft_overall": _LATTICE.craft_overall,
    "defect_density": _LATTICE.defect_density,
    "position": _LATTICE.position,
    "craft_ceiling": _LATTICE.craft_ceiling,
    "defect_ceiling": _LATTICE.defect_ceiling,
    "literary_band_detail": _LATTICE.band_detail,
    "band_window": _LATTICE.window,
    "scored_dimension": _LATTICE.scored_dimension,
    "originality_bonus": derive_report.originality_bonus,
    "fidelity_band": derive_report.fidelity_band,
    "score_grade": band_lattice.score_grade,
    "normalized_score": band_lattice.normalized_score,
    "derive_scores": lambda *a, **kw: derive_report.derive_scores(
        *a, lattice=_LATTICE, **kw
    ),
}

LITERARY_SEATS = sorted(derive_report.LITERARY_SEATS)
VERDICTS = ("YES", "NO", "ABSTAIN", "NA")
SEVERITIES = ("high", "medium", "low", "none")
FIDELITY_STATES = (
    "SUPPORTED",
    "PERMISSIBLE_INFERENCE",
    "UNSUPPORTED",
    "CONTRADICTED",
    "UNVERIFIABLE",
)


def rubric() -> dict[tuple[str, str], dict[str, str]]:
    return parse_criteria(CRITERIA)


def seat_criteria(meta: dict[tuple[str, str], dict[str, str]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for seat, cid in meta:
        out.setdefault(seat, []).append(cid)
    return {seat: sorted(ids) for seat, ids in sorted(out.items())}


def build_case(
    meta: dict[tuple[str, str], dict[str, str]],
    by_seat: dict[str, list[str]],
    *,
    seats: list[str],
    pick: Callable[[str, str], tuple[str, str]],
    readers: int = 1,
) -> tuple[list[dict[str, Any]], list[tuple[dict, dict, dict]]]:
    """构造 (outputs, judgments)。

    judgments 的第一元必须与 outputs 中的对象**同一**——derive_scores 用 `is`
    做素读者归属判断，复制一份 dict 会静默改变行为。
    """
    outputs: list[dict[str, Any]] = []
    judgments: list[tuple[dict, dict, dict]] = []
    for seat in seats:
        count = readers if seat == "lit-naive-reader" else 1
        for index in range(count):
            output: dict[str, Any] = {"seat": seat}
            if seat == "lit-naive-reader":
                output["reader_id"] = f"r{index + 1}"
            criteria: list[dict[str, Any]] = []
            for cid in by_seat[seat]:
                verdict, severity = pick(seat, cid)
                criterion: dict[str, Any] = {
                    "id": cid,
                    "verdict": verdict,
                    "severity": severity,
                    "quotes": [],
                    "note": f"{seat}:{cid}",
                }
                if seat == "lit-fidelity":
                    # 不能用内建 hash()：字符串哈希逐进程随机化，基线会不可复现。
                    criterion["fidelity_state"] = FIDELITY_STATES[
                        zlib.crc32(f"{seat}:{cid}:{verdict}".encode()) % len(FIDELITY_STATES)
                    ]
                criteria.append(criterion)
                judgments.append((output, criterion, meta[(seat, cid)]))
            output["criteria"] = criteria
            outputs.append(output)
    return outputs, judgments


def snapshot(outputs: list[dict[str, Any]], judgments: list[tuple]) -> dict[str, Any]:
    """记录评分格每一个可观测输出。"""
    covered = {output["seat"] for output in outputs}
    result: dict[str, Any] = {"covered_seats": sorted(covered)}

    per_seat: dict[str, dict[str, Any]] = {}
    for seat in LITERARY_SEATS:
        per_seat[seat] = {
            "craft_ratio": LATTICE["craft_ratio"](seat, judgments),
            "defect_density": LATTICE["defect_density"](seat, judgments),
            "position": LATTICE["position"](seat, judgments),
        }
    result["per_seat"] = per_seat
    result["craft_overall"] = LATTICE["craft_overall"](judgments)
    result["craft_ceiling"] = LATTICE["craft_ceiling"](judgments)
    result["defect_ceiling"] = LATTICE["defect_ceiling"](judgments)
    result["originality_bonus"] = LATTICE["originality_bonus"](judgments)
    result["fidelity_band"] = LATTICE["fidelity_band"](judgments)

    for warning in (False, True):
        band, demoted = LATTICE["literary_band_detail"](judgments, covered, warning)
        window = LATTICE["band_window"](band, demoted)
        entry: dict[str, Any] = {
            "band": band,
            "demoted": demoted,
            "window": list(window) if window else None,
        }
        if window is not None:
            entry["dimensions"] = {
                seat: LATTICE["scored_dimension"](seat, judgments, window)
                for seat in LITERARY_SEATS
            }
        result[f"band_warning_{warning}"] = entry

    for label, kwargs in (
        ("current", {"blockers": [], "provisional_reasons": [], "formal": None}),
        ("legacy_formal", {"formal": True}),
        ("legacy_diagnostic", {"formal": False}),
    ):
        for fidelity in (None, "A", "B", "C", "N/A"):
            key = f"scores_{label}_fidelity_{fidelity}"
            result[key] = LATTICE["derive_scores"](
                judgments,
                outputs,
                fidelity=fidelity,
                reader_warning=False,
                **kwargs,
            )
    return result


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def record(snap: dict[str, Any], *, full: bool) -> dict[str, Any]:
    """手工边界存全量（便于定位漂移），伪随机用例存摘要 + digest（控制基线体积）。

    digest 覆盖快照的每一位，所以任何漂移都会被抓到；摘要让覆盖度断言与失败信息
    仍然可读，不必展开 2.9MB 的全量数据。
    """
    entry: dict[str, Any] = {
        "summary": {
            "band": snap["band_warning_False"]["band"],
            "demoted": snap["band_warning_False"]["demoted"],
            "window": snap["band_warning_False"]["window"],
            "craft_ceiling": snap["craft_ceiling"],
            "defect_ceiling": snap["defect_ceiling"],
            "fidelity_band": snap["fidelity_band"],
            "total": snap["scores_current_fidelity_None"]["total"],
        },
        "digest": hashlib.sha256(canonical(snap).encode()).hexdigest(),
    }
    if full:
        entry["full"] = snap
    return entry


def all_cases() -> dict[str, Any]:
    meta = rubric()
    by_seat = seat_criteria(meta)
    every_seat = sorted(by_seat)
    cases: dict[str, Any] = {}

    # 手工边界：把带位格的每一个分支都点到。
    fixed: list[tuple[str, Callable[[str, str], tuple[str, str]], list[str], int]] = [
        ("all_yes", lambda s, c: ("YES", "none"), every_seat, 1),
        ("all_no_high", lambda s, c: ("NO", "high"), every_seat, 1),
        ("all_no_medium", lambda s, c: ("NO", "medium"), every_seat, 1),
        ("all_no_low", lambda s, c: ("NO", "low"), every_seat, 1),
        ("all_abstain", lambda s, c: ("ABSTAIN", "none"), every_seat, 1),
        ("all_na", lambda s, c: ("NA", "none"), every_seat, 1),
        ("literary_only_yes", lambda s, c: ("YES", "none"), LITERARY_SEATS, 1),
        ("no_literary_seats", lambda s, c: ("YES", "none"),
         [s for s in every_seat if s not in derive_report.LITERARY_SEATS], 1),
        ("two_naive_readers", lambda s, c: ("YES", "none"), every_seat, 2),
        ("three_naive_readers", lambda s, c: ("NO", "low"), every_seat, 3),
        # craft 恰好压线与恰好不足
        ("craft_yes_others_no",
         lambda s, c: ("YES", "none")
         if c in _LATTICE.rubric.craft_set(s) else ("NO", "low"),
         every_seat, 1),
        ("craft_no_others_yes",
         lambda s, c: ("NO", "low")
         if c in _LATTICE.rubric.craft_set(s) else ("YES", "none"),
         every_seat, 1),
        # 只让一条 veto 失败
        ("single_veto_high",
         lambda s, c: ("NO", "high") if (s, c) in {("lit-structure", "N2")} else ("YES", "none"),
         every_seat, 1),
        ("single_veto_medium",
         lambda s, c: ("NO", "medium") if (s, c) in {("lit-prose", "L1")} else ("YES", "none"),
         every_seat, 1),
        ("single_core",
         lambda s, c: ("NO", "low") if (s, c) in {("lit-character", "P5")} else ("YES", "none"),
         every_seat, 1),
        ("single_extended",
         lambda s, c: ("NO", "low") if (s, c) in {("lit-structure", "N6")} else ("YES", "none"),
         every_seat, 1),
        ("veto_na",
         lambda s, c: ("NA", "none") if c in {"N2", "P1", "L1", "E1", "E2"} else ("YES", "none"),
         every_seat, 1),
    ]
    for name, pick, seats, readers in fixed:
        outputs, judgments = build_case(
            meta, by_seat, seats=seats, pick=pick, readers=readers
        )
        cases[name] = record(snapshot(outputs, judgments), full=True)

    # 确定性伪随机：覆盖手工边界够不到的组合空间。
    for seed in range(240):
        rng = random.Random(seed)
        weights = rng.choice([
            (0.70, 0.25, 0.03, 0.02),
            (0.30, 0.60, 0.05, 0.05),
            (0.50, 0.50, 0.00, 0.00),
            (0.90, 0.10, 0.00, 0.00),
        ])
        seats = every_seat if seed % 5 else sorted(
            rng.sample(every_seat, rng.randint(4, len(every_seat)))
        )
        table = {
            (seat, cid): (
                rng.choices(VERDICTS, weights=weights)[0],
                rng.choice(SEVERITIES),
            )
            for seat in by_seat
            for cid in by_seat[seat]
        }
        outputs, judgments = build_case(
            meta,
            by_seat,
            seats=seats,
            pick=lambda s, c: table[(s, c)],
            readers=1 + (seed % 3),
        )
        cases[f"seed_{seed:03d}"] = record(snapshot(outputs, judgments), full=False)
    return cases


class ScoringLatticeGolden(unittest.TestCase):
    def test_lattice_output_matches_committed_baseline(self) -> None:
        produced = all_cases()
        if os.environ.get("LIT_PANEL_REGENERATE_GOLDEN"):
            BASELINE.parent.mkdir(parents=True, exist_ok=True)
            BASELINE.write_text(
                json.dumps(produced, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            self.skipTest(f"基线已重新生成：{BASELINE}")
        self.assertTrue(
            BASELINE.exists(),
            f"缺少黄金基线 {BASELINE}；用 LIT_PANEL_REGENERATE_GOLDEN=1 生成",
        )
        expected = json.loads(BASELINE.read_text(encoding="utf-8"))
        self.assertEqual(
            sorted(expected), sorted(produced), "黄金基线的用例集合发生变化"
        )
        drifted = [
            name
            for name in sorted(expected)
            if expected[name]["digest"] != produced[name]["digest"]
        ]
        detail = ""
        if drifted:
            first = drifted[0]
            detail = (
                f"\n首个漂移用例 {first}："
                f"\n  基线 summary = {canonical(expected[first]['summary'])}"
                f"\n  当前 summary = {canonical(produced[first]['summary'])}"
            )
        self.assertEqual(
            drifted,
            [],
            f"评分格输出与黄金基线不一致，共 {len(drifted)} 个用例漂移，"
            f"前若干：{drifted[:8]}{detail}",
        )

    def test_baseline_actually_exercises_every_band(self) -> None:
        """基线若只覆盖一两个带位，它就挡不住回归。"""
        expected = json.loads(BASELINE.read_text(encoding="utf-8"))
        bands = {case["summary"]["band"] for case in expected.values()}
        for required in ("A", "B", "C", "N/A"):
            self.assertIn(required, bands, f"黄金基线未覆盖带位 {required}")
        self.assertIn(
            True,
            {case["summary"]["demoted"] for case in expected.values()},
            "黄金基线未覆盖记录型（craft 天花板封顶）",
        )
        candidate = {
            case["full"]["band_warning_True"]["band"]
            for case in expected.values()
            if "full" in case
        }
        self.assertIn(
            "A候选（待人工确认）", candidate, "黄金基线未覆盖素读者预警路径"
        )


if __name__ == "__main__":
    unittest.main()
