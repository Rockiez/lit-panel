from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "core" / "lit-panel" / "scripts"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def run(*args: str, expected: int) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"returncode={result.returncode}, expected={expected}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


class TestQuoteOnlyRepair(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.text = self.root / "text.md"
        self.text.write_text(
            "那年冬天，母亲第一次独自坐火车去县城。\n"
            "回来后，她只说县城的灯比村里亮。\n",
            encoding="utf-8",
        )
        self.outputs = self.root / "outputs"
        self.outputs.mkdir()
        self.original = {
            "schema_version": "1.0",
            "run_id": "run-quote-repair",
            "seat": "lit-structure",
            "phase": "review",
            "criteria": [
                {
                    "id": "S1",
                    "verdict": "NO",
                    "severity": "low",
                    "quotes": [
                        {
                            "text": "母亲第一次独自坐汽车去县城",
                            "target": "text",
                            "location": "第1段",
                        }
                    ],
                    "note": "交通工具的叙述需要核对。",
                    "recommendation": "保持事实和判断，只校正逐字引文。",
                }
            ],
            "free_view": "结构判断保持不变。",
        }
        self.output_path = self.outputs / "lit-structure.json"
        write_json(self.output_path, self.original)
        self.initial_receipt = self.root / "initial-verification.json"
        self.repair_request = self.root / "quote-repair-request.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def verify_initial(self) -> dict[str, Any]:
        run(
            sys.executable,
            str(SCRIPTS / "verify_quotes.py"),
            str(self.outputs),
            str(self.text),
            "--output",
            str(self.initial_receipt),
            "--repair-request",
            str(self.repair_request),
            expected=1,
        )
        return json.loads(self.repair_request.read_text(encoding="utf-8"))

    def write_patch(self, quote_text: str, **criterion_extras: Any) -> Path:
        patch = {
            "schema_version": "1.0",
            "run_id": self.original["run_id"],
            "seat": self.original["seat"],
            "reader_id": None,
            "criteria": [
                {
                    "id": "S1",
                    "quotes": [
                        {
                            "text": quote_text,
                            "target": "text",
                            "location": "第1段",
                        }
                    ],
                    **criterion_extras,
                }
            ],
        }
        path = self.root / "patch.json"
        write_json(path, patch)
        return path

    def run_repair(self, patch: Path, *, expected: int) -> tuple[Path, Path, Path]:
        repaired_outputs = self.root / "repaired-outputs"
        final_receipt = self.root / "final-verification.json"
        repair_receipt = self.root / "quote-repair-receipt.json"
        run(
            sys.executable,
            str(SCRIPTS / "repair_quotes.py"),
            str(self.outputs),
            str(patch),
            str(self.initial_receipt),
            str(self.text),
            "--output-dir",
            str(repaired_outputs),
            "--verification-output",
            str(final_receipt),
            "--repair-receipt",
            str(repair_receipt),
            expected=expected,
        )
        return repaired_outputs, final_receipt, repair_receipt

    def test_verifier_emits_auditable_request_for_invalidated_criterion(self) -> None:
        request = self.verify_initial()

        self.assertEqual(request["run_id"], self.original["run_id"])
        self.assertEqual(request["attempt"], 1)
        self.assertEqual(len(request["requests"]), 1)
        item = request["requests"][0]
        self.assertEqual(
            (item["seat"], item["reader_id"], item["criterion_id"]),
            ("lit-structure", None, "S1"),
        )
        self.assertEqual(item["original_quotes"], self.original["criteria"][0]["quotes"])
        self.assertEqual(item["failures"][0]["tier"], 4)
        self.assertIn("火车", item["failures"][0]["matched_snippet"])

    def test_verifier_does_not_leave_a_partial_receipt_when_request_write_fails(self) -> None:
        blocker = self.root / "not-a-directory"
        blocker.write_text("block", encoding="utf-8")

        run(
            sys.executable,
            str(SCRIPTS / "verify_quotes.py"),
            str(self.outputs),
            str(self.text),
            "--output",
            str(self.initial_receipt),
            "--repair-request",
            str(blocker / "quote-repair-request.json"),
            expected=2,
        )

        self.assertFalse(self.initial_receipt.exists())

    def test_valid_patch_repairs_quotes_and_freezes_every_non_quote_field(self) -> None:
        self.verify_initial()
        patch = self.write_patch("母亲第一次独自坐火车去县城")
        repaired_outputs, final_receipt, repair_receipt = self.run_repair(patch, expected=0)

        repaired = json.loads(
            (repaired_outputs / self.output_path.name).read_text(encoding="utf-8")
        )
        expected = copy.deepcopy(self.original)
        expected["criteria"][0]["quotes"] = json.loads(patch.read_text(encoding="utf-8"))[
            "criteria"
        ][0]["quotes"]
        self.assertEqual(repaired, expected)
        verification = json.loads(final_receipt.read_text(encoding="utf-8"))
        self.assertEqual(verification["invalidated_criteria"], [])
        audit = json.loads(repair_receipt.read_text(encoding="utf-8"))
        self.assertEqual(audit["attempt"], 1)
        self.assertEqual(audit["status"], "repaired")
        self.assertEqual(audit["repaired_criteria"], ["lit-structure:S1"])
        self.assertEqual(audit["outputs"]["seat_outputs"], verification["inputs"]["seat_outputs"])
        self.assertEqual(
            audit["outputs"]["verification_sha256"],
            hashlib.sha256(final_receipt.read_bytes()).hexdigest(),
        )

    def test_patch_cannot_change_verdict_or_other_review_fields(self) -> None:
        self.verify_initial()
        patch = self.write_patch(
            "母亲第一次独自坐火车去县城",
            verdict="YES",
        )

        self.run_repair(patch, expected=2)
        self.assertFalse((self.root / "repaired-outputs").exists())

    def test_retry_is_still_fail_closed_when_replacement_is_not_verbatim(self) -> None:
        self.verify_initial()
        patch = self.write_patch("母亲第一次独自坐客车去县城")
        _, final_receipt, repair_receipt = self.run_repair(patch, expected=1)

        verification = json.loads(final_receipt.read_text(encoding="utf-8"))
        self.assertEqual(verification["invalidated_criteria"], ["lit-structure:S1"])
        self.assertEqual(verification["items"][0]["tier"], 4)
        audit = json.loads(repair_receipt.read_text(encoding="utf-8"))
        self.assertEqual(audit["attempt"], 1)
        self.assertEqual(audit["status"], "failed")

    def test_patch_cannot_target_a_criterion_that_was_not_invalidated(self) -> None:
        self.verify_initial()
        patch = self.write_patch("母亲第一次独自坐火车去县城")
        payload = json.loads(patch.read_text(encoding="utf-8"))
        payload["criteria"][0]["id"] = "S2"
        write_json(patch, payload)

        self.run_repair(patch, expected=2)
        self.assertFalse((self.root / "repaired-outputs").exists())

    def test_receipt_write_failure_does_not_publish_partial_repaired_outputs(self) -> None:
        self.verify_initial()
        patch = self.write_patch("母亲第一次独自坐火车去县城")
        blocker = self.root / "not-a-directory"
        blocker.write_text("block", encoding="utf-8")
        repaired_outputs = self.root / "repaired-outputs"
        repair_receipt = self.root / "quote-repair-receipt.json"

        run(
            sys.executable,
            str(SCRIPTS / "repair_quotes.py"),
            str(self.outputs),
            str(patch),
            str(self.initial_receipt),
            str(self.text),
            "--output-dir",
            str(repaired_outputs),
            "--verification-output",
            str(blocker / "verification.json"),
            "--repair-receipt",
            str(repair_receipt),
            expected=2,
        )

        self.assertFalse(repaired_outputs.exists())
        self.assertFalse(repair_receipt.exists())


if __name__ == "__main__":
    unittest.main()
