from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class CompareContractTests(unittest.TestCase):
    def test_command_usage_and_parameter_table_expose_fast_compare(self) -> None:
        command = (ROOT / "commands" / "lit-compare.md").read_text(encoding="utf-8")
        usage = next(
            line for line in command.splitlines() if line.startswith("/lit-compare ")
        )
        self.assertIn("[--fast-compare]", usage)
        self.assertIn("| `--fast-compare` |", command)
        self.assertIn("位置偏差未防护", command)

    def test_skill_freezes_swap_order_tie_and_non_numeric_output(self) -> None:
        skill = (ROOT / "core" / "lit-panel" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        for claim in (
            "A→B 与 B→A",
            "记 TIE",
            "--fast-compare",
            "不用于发布门禁",
            "不宣布数值胜率或加权冠军",
        ):
            self.assertIn(claim, skill)

    def test_compare_command_is_copied_into_claude_distribution(self) -> None:
        source = (ROOT / "commands" / "lit-compare.md").read_bytes()
        generated = (ROOT / "dist" / "claude" / "commands" / "lit-compare.md")
        self.assertEqual(generated.read_bytes(), source)


if __name__ == "__main__":
    unittest.main()
