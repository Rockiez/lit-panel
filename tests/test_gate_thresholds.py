#!/usr/bin/env python3
"""craft 门阈值的行为等价类。

`CRAFT_GATE_RATIO` 与 `CRAFT_OVERALL_GATE_RATIO` 是连续参数，但它们比较的量是
**量化**的——门用子集只有 2/1/3/3 条判据，比例只能落在有限个格点上。因此阈值落在
相邻格点之间时行为完全相同：真正可选的不是一个实数，而是**有限个等价类**。

这改变了 docs/SCORING_0_7_DESIGN.md §1.5「阈值落在观测空洞里」的处置方式：
问题不是「该取 0.6 还是 0.61」（这两个是同一个类，行为一模一样），而是
「该选哪一类」。选类需要语料证据；本测试只负责把**当前选的是哪一类**钉住，
使类内的改动是已知的空操作、跨类的改动一定被抓到。
"""

from __future__ import annotations

import sys
import unittest
from fractions import Fraction
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "core" / "lit-panel" / "scripts"
CRITERIA = ROOT / "core" / "lit-panel" / "references" / "criteria"
sys.path.insert(0, str(SCRIPTS))

import band_lattice  # noqa: E402

LATTICE = band_lattice.BandLattice(band_lattice.Rubric.from_criteria_dir(CRITERIA))
SEATS = sorted(band_lattice.LITERARY_SEATS)


def gate_sizes() -> dict[str, int]:
    return {seat: len(LATTICE.rubric.craft_gate_set(seat)) for seat in SEATS}


def per_seat_grid() -> list[Fraction]:
    """逐席 craft 门比例的全部可取值。"""
    return sorted({
        Fraction(k, size)
        for size in gate_sizes().values()
        for k in range(size + 1)
    })


def overall_grid() -> list[Fraction]:
    """craft_overall（四席门比例的算术平均）的全部可取值。"""
    sizes = gate_sizes()
    return sorted({
        sum(Fraction(k, sizes[seat]) for seat, k in zip(SEATS, combo)) / len(SEATS)
        for combo in product(*[range(sizes[seat] + 1) for seat in SEATS])
    })


def equivalence_class(threshold: float, grid: list[Fraction]) -> Fraction:
    """阈值实际生效的格点：满足 `值 >= 阈值` 的最小格点。"""
    above = [point for point in grid if point >= Fraction(threshold).limit_denominator(10**6)]
    return above[0] if above else Fraction(10**9)


class GateThresholdClasses(unittest.TestCase):
    def test_gate_sets_are_what_the_design_says(self) -> None:
        """门用子集＝craft 全集剔除被红线强制为 YES 的成员（§4.3）。"""
        self.assertEqual(
            {seat: sorted(LATTICE.rubric.craft_gate_set(seat)) for seat in SEATS},
            {
                "lit-character": ["P7"],
                "lit-prose": ["L5", "L7", "TW3"],
                "lit-resonance": ["E6", "E7", "TW14"],
                "lit-structure": ["SC1", "TW2"],
            },
        )

    def test_per_seat_threshold_class_is_two_thirds(self) -> None:
        """现值 0.6 生效为「各席 >= 2/3」；类内任意取值行为相同。"""
        grid = per_seat_grid()
        self.assertEqual(
            [str(point) for point in grid], ["0", "1/3", "1/2", "2/3", "1"]
        )
        effective = equivalence_class(band_lattice.CRAFT_GATE_RATIO, grid)
        self.assertEqual(effective, Fraction(2, 3))
        # 同类内的任意阈值必须产出同一个生效格点——这正是「0.6 与 0.61 无差别」的形式陈述。
        for inside in (0.51, 0.6, 0.65, 2 / 3):
            self.assertEqual(equivalence_class(inside, grid), Fraction(2, 3), inside)
        # 跨类必须改变生效格点，否则本测试挡不住任何东西。
        self.assertEqual(equivalence_class(0.5, grid), Fraction(1, 2))
        self.assertEqual(equivalence_class(0.7, grid), Fraction(1, 1))

    def test_overall_threshold_class_is_one_third(self) -> None:
        """现值 0.3 生效为「craft_overall >= 1/3」。"""
        grid = overall_grid()
        effective = equivalence_class(band_lattice.CRAFT_OVERALL_GATE_RATIO, grid)
        self.assertEqual(effective, Fraction(1, 3))
        for inside in (0.2918, 0.3, 1 / 3):
            self.assertEqual(equivalence_class(inside, grid), Fraction(1, 3), inside)
        self.assertNotEqual(equivalence_class(0.29, grid), Fraction(1, 3))

    def test_thresholds_do_not_sit_on_a_grid_point(self) -> None:
        """阈值压在格点上会让浮点误差决定带位，必须留在格点之间。"""
        for name, value, grid in (
            ("CRAFT_GATE_RATIO", band_lattice.CRAFT_GATE_RATIO, per_seat_grid()),
            (
                "CRAFT_OVERALL_GATE_RATIO",
                band_lattice.CRAFT_OVERALL_GATE_RATIO,
                overall_grid(),
            ),
        ):
            for point in grid:
                self.assertNotAlmostEqual(
                    value, float(point), places=9,
                    msg=f"{name}={value} 正好压在格点 {point} 上",
                )


if __name__ == "__main__":
    unittest.main()
