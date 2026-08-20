from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class DistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, "scripts/build_dist.py"], cwd=ROOT, check=True)

    def test_all_dist_skills_are_self_contained(self) -> None:
        for host in ("codex", "claude", "antigravity"):
            skill = ROOT / "dist" / host / "skills" / "lit-panel"
            for path in (
                "SKILL.md", "agents", "references/registry.md",
                "schema/seat-output.schema.json", "schema/run-manifest.schema.json",
                "schema/execution-receipt.schema.json",
                "schema/verification-receipt.schema.json",
                "schema/quote-repair-request.schema.json",
                "schema/quote-repair-patch.schema.json",
                "schema/quote-repair-receipt.schema.json",
                "schema/derived-report.schema.json",
                "scripts/prepare_run.py", "scripts/validate_execution_receipt.py",
                "scripts/verify-quotes.py", "scripts/verify_quotes.py",
                "scripts/quote_repair.py", "scripts/repair_quotes.py",
                "scripts/derive_report.py",
            ):
                self.assertTrue((skill / path).exists(), f"{host} missing {path}")

    def test_agent_plugin_declares_current_codex_floor(self) -> None:
        manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        extension = manifest["extensions"]["com.anamnese.lit-panel"]
        self.assertEqual(extension["supportedHosts"]["codex"], ">=0.147.0")
        self.assertTrue(extension["requiresNativeSubagents"])

    def test_each_host_has_eleven_native_or_enhanced_agents(self) -> None:
        self.assertEqual(len(list((ROOT / "dist/codex/.codex/agents").glob("*.toml"))), 11)
        self.assertEqual(len(list((ROOT / "dist/claude/agents").glob("*.md"))), 11)
        self.assertEqual(len(list((ROOT / "dist/antigravity/agents").glob("*.md"))), 11)

    def test_repository_marketplaces_route_to_host_specific_distributions(self) -> None:
        codex = json.loads(
            (ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
        )
        claude = json.loads(
            (ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8")
        )

        self.assertEqual(codex["plugins"][0]["source"]["path"], "./dist/codex")
        self.assertEqual(claude["plugins"][0]["source"], "./dist/claude")

    def test_distribution_marketplaces_are_self_relative(self) -> None:
        codex = json.loads(
            (ROOT / "dist/codex/.agents/plugins/marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        claude = json.loads(
            (ROOT / "dist/claude/.claude-plugin/marketplace.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(codex["plugins"][0]["source"]["path"], "./")
        self.assertEqual(claude["plugins"][0]["source"], "./")


if __name__ == "__main__":
    unittest.main()
