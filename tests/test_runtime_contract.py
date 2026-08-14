from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "core" / "lit-panel"
SCRIPTS = SKILL / "scripts"
TEXT = ROOT / "tests" / "synthetic" / "text.md"
SOURCE = ROOT / "tests" / "synthetic" / "source.md"
BRIEF = ROOT / "tests" / "synthetic" / "brief.md"

sys.path.insert(0, str(SCRIPTS))
from lit_panel_common import parse_criteria  # noqa: E402

METADATA = parse_criteria(SKILL / "references" / "criteria")


def run(*args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != expected:
        raise AssertionError(
            f"returncode={result.returncode}, expected={expected}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


def prepare(
    root: Path,
    preset: str,
    *,
    run_id: str = "run-contract",
    readers: int = 1,
    source: Path | None = None,
    brief: Path | None = None,
    genre: str = "other",
) -> tuple[Path, dict[str, Any]]:
    run_dir = root / "run"
    command = [
        sys.executable,
        str(SCRIPTS / "prepare_run.py"),
        str(TEXT),
        "--preset",
        preset,
        "--genre",
        genre,
        "--readers",
        str(readers),
        "--run-id",
        run_id,
        "--output",
        str(run_dir),
    ]
    if source is not None:
        command.extend(["--source", str(source)])
    if brief is not None:
        command.extend(["--brief", str(brief)])
    run(*command)
    return run_dir, json.loads((run_dir / "run.json").read_text(encoding="utf-8"))


def write_outputs(
    root: Path,
    manifest: dict[str, Any],
    *,
    problem: tuple[str, str] | None = None,
    bad_quote: tuple[str, str] | None = None,
    omit: tuple[str, str] | None = None,
    omit_recommendation: bool = False,
    abstain_all: bool = False,
) -> Path:
    seats = root / "seats"
    seats.mkdir()
    for expected in manifest["expected_outputs"]:
        criteria: list[dict[str, Any]] = []
        for criterion_id in expected["criteria_ids"]:
            if omit == (expected["seat"], criterion_id):
                continue
            polarity = METADATA[(expected["seat"], criterion_id)]["polarity"]
            verdict = "YES" if polarity == "[通过]" else "NO"
            severity = "none"
            is_problem = problem == (expected["seat"], criterion_id)
            if abstain_all:
                verdict = "ABSTAIN"
            if is_problem:
                verdict = "NO" if polarity == "[通过]" else "YES"
                severity = "high"
            quote = (
                "原文中不存在的逐字引文"
                if bad_quote == (expected["seat"], criterion_id)
                else "那年冬天"
            )
            quotes = (
                []
                if abstain_all
                else [{"text": quote, "target": "text", "location": "第1段"}]
            )
            item: dict[str, Any] = {
                "id": criterion_id,
                "verdict": verdict,
                "severity": severity,
                "quotes": quotes,
                "note": "合成测试判定",
            }
            if expected["seat"] == "lit-fidelity":
                item["fidelity_state"] = (
                    "UNVERIFIABLE"
                    if abstain_all
                    else "UNSUPPORTED" if is_problem else "SUPPORTED"
                )
                if not abstain_all:
                    item["quotes"].append({
                        "text": "母亲第一次独自去县城是在冬天",
                        "target": "source",
                        "location": "来源第1行",
                    })
            if is_problem and not omit_recommendation:
                item["recommendation"] = "按来源或叙事证据修订"
            criteria.append(item)
        output: dict[str, Any] = {
            "schema_version": "1.0",
            "run_id": manifest["run_id"],
            "seat": expected["seat"],
            "phase": expected["phase"],
            "criteria": criteria,
            "free_view": "分席独立质性观点。",
        }
        if expected["reader_id"] is not None:
            output["reader_id"] = expected["reader_id"]
            output["reader"] = {
                "experience": f"{expected['reader_id']} 的自然首读体验",
                "required_answers": ["最亮处", "最闷处", "一句话转述"],
                "willing_to_share": "愿意",
            }
        identity = expected["seat"] + (
            f"-{expected['reader_id']}" if expected["reader_id"] else ""
        )
        (seats / f"{identity}.json").write_text(
            json.dumps(output, ensure_ascii=False), encoding="utf-8"
        )
    return seats


def write_execution(
    root: Path,
    manifest: dict[str, Any],
    outputs: Path,
    *,
    native: bool = True,
    gaps: list[str] | None = None,
    sealed_naive: bool = False,
) -> Path:
    gaps = gaps or []
    expected_by_packet = {item["packet"]: item for item in manifest["expected_outputs"]}
    dispatches: list[dict[str, Any]] = []
    naive_readers: list[dict[str, Any]] = []
    for packet in manifest["packets"]:
        expected = expected_by_packet.get(packet)
        if expected is None and "step-1.json" in packet:
            expected = expected_by_packet[packet.replace("step-1.json", "step-2.json")]
        assert expected is not None
        reader_id = expected["reader_id"]
        if reader_id and sealed_naive:
            step = "step-1" if "step-1.json" in packet else "step-2"
            context_id = f"ctx-{reader_id}-{step}"
        else:
            context_id = f"ctx-{reader_id}" if reader_id else f"ctx-{expected['seat']}"
        dispatches.append({
            "packet": packet,
            "packet_sha256": hashlib.sha256(
                (root / "run" / "packets" / packet).read_bytes()
            ).hexdigest(),
            "seat": expected["seat"],
            "reader_id": reader_id,
            "context_id": context_id,
            "isolated": native,
            "status": "completed",
        })
    for expected in manifest["expected_outputs"]:
        if expected["reader_id"] is None:
            continue
        output_path = outputs / f"{expected['seat']}-{expected['reader_id']}.json"
        output = json.loads(output_path.read_text(encoding="utf-8"))
        if sealed_naive:
            step1_context = f"ctx-{expected['reader_id']}-step-1"
            step2_context = f"ctx-{expected['reader_id']}-step-2"
            step2_mode = "sealed-new-context"
        else:
            step1_context = f"ctx-{expected['reader_id']}"
            step2_context = step1_context
            step2_mode = "follow-up"
        naive_readers.append({
            "reader_id": expected["reader_id"],
            "step_1_context_id": step1_context,
            "step_2_context_id": step2_context,
            "step_2_mode": step2_mode,
            "step_1_receipt_sha256": hashlib.sha256(
                output["reader"]["experience"].encode("utf-8")
            ).hexdigest(),
        })
    receipt = {
        "schema_version": "1.0",
        "run_id": manifest["run_id"],
        "host": {"name": "codex", "version": "0.147.0"},
        "native_subagents": native,
        "degraded": not native or bool(gaps),
        "dispatches": dispatches,
        "naive_readers": naive_readers,
        "coverage_gaps": gaps,
    }
    path = root / "execution.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False), encoding="utf-8")
    return path


def verify(root: Path, seats: Path, *, source: Path | None = None, expected: int = 0) -> Path:
    receipt = root / "verification.json"
    command = [
        sys.executable,
        str(SCRIPTS / "verify_quotes.py"),
        str(seats),
        str(TEXT),
    ]
    if source is not None:
        command.extend(["--source", str(source)])
    command.extend(["--output", str(receipt)])
    run(*command, expected=expected)
    return receipt


def derive(
    root: Path,
    seats: Path,
    verification: Path,
    run_dir: Path,
    execution: Path,
    *,
    source: Path | None = None,
    brief: Path | None = None,
    expected: int = 0,
) -> Path:
    result = root / "derived.json"
    command = [
        sys.executable,
        str(SCRIPTS / "derive_report.py"),
        str(seats),
        str(verification),
        str(run_dir / "run.json"),
        str(execution),
        str(SKILL / "references" / "criteria"),
        "--text",
        str(TEXT),
    ]
    if source is not None:
        command.extend(["--source", str(source)])
    if brief is not None:
        command.extend(["--brief", str(brief)])
    command.extend([
        "--output-json",
        str(result),
        "--output-markdown",
        str(root / "report.md"),
    ])
    run(*command, expected=expected)
    return result


class RuntimeContractTests(unittest.TestCase):
    def test_validate_rejects_quote_free_yes_and_naive_review_bypass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ordinary = {
                "schema_version": "1.0",
                "run_id": "run-contract",
                "seat": "lit-structure",
                "phase": "review",
                "criteria": [{
                    "id": "N2", "verdict": "YES", "severity": "none", "quotes": [],
                    "note": "结构判定",
                }],
                "free_view": "观点",
            }
            bad_quote = root / "bad-quote.json"
            bad_quote.write_text(json.dumps(ordinary, ensure_ascii=False), encoding="utf-8")
            run(
                sys.executable, str(SCRIPTS / "validate_seat_output.py"), str(bad_quote),
                expected=1,
            )
            ordinary["seat"] = "lit-naive-reader"
            ordinary["criteria"][0]["quotes"] = [{
                "text": "那年冬天", "target": "text", "location": "第1段",
            }]
            bypass = root / "bypass.json"
            bypass.write_text(json.dumps(ordinary, ensure_ascii=False), encoding="utf-8")
            run(
                sys.executable, str(SCRIPTS / "validate_seat_output.py"), str(bypass),
                expected=1,
            )

    def test_prepare_is_closed_blind_and_supports_multiple_readers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "custom(03,04,08)", readers=2)
            packets = run_dir / "packets"
            seat03 = json.loads((packets / "03.json").read_text(encoding="utf-8"))
            seat04 = json.loads((packets / "04.json").read_text(encoding="utf-8"))
            step1 = json.loads(
                (packets / "08-reader-01-step-1.json").read_text(encoding="utf-8")
            )
            step2 = json.loads(
                (packets / "08-reader-01-step-2.json").read_text(encoding="utf-8")
            )
            self.assertNotEqual(seat03["persona_path"], seat04["persona_path"])
            self.assertNotEqual(seat03["criteria_path"], seat04["criteria_path"])
            self.assertNotIn("A7", seat03["active_criteria_ids"])
            self.assertNotIn("criteria_path", step1)
            self.assertNotIn("contract_path", step1)
            self.assertNotIn("persona_path", step1)
            self.assertEqual(step2["depends_on"], "08-reader-01-step-1.json")
            self.assertEqual(step2["text_path"], step1["text_path"])
            self.assertEqual(
                step2["step_1_receipt_contract"]["output_field"], "reader.experience"
            )
            self.assertEqual(manifest["readers"], 2)
            self.assertEqual(len(manifest["expected_outputs"]), 4)
            run(
                sys.executable,
                str(SCRIPTS / "prepare_run.py"),
                str(TEXT),
                "--preset",
                "custom(03,04,08)",
                "--output",
                str(run_dir),
                expected=2,
            )

    def test_prepare_memoir_quick_adds_ethics_and_activates_cross_chapter_a7(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, quick = prepare(root / "quick", "quick", genre="memoir")
            self.assertIn("11", quick["selected_seats"])
            sources = root / "chapters"
            sources.mkdir()
            (sources / "one.md").write_text("第一章", encoding="utf-8")
            (sources / "two.md").write_text("第二章", encoding="utf-8")
            run_dir, manifest = prepare(root / "cross", "custom(03)", source=sources)
            packet = json.loads((run_dir / "packets" / "03.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["cross_chapter_source"])
            self.assertIn("A7", packet["active_criteria_ids"])

    def test_complete_native_chain_can_form_literary_a(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "custom(04,05,06,07)")
            seats = write_outputs(root, manifest)
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )
            self.assertTrue(result["formal"])
            self.assertEqual(result["bands"]["literary"], "A")
            self.assertEqual(result["recommendation"], "交付")

    def test_degraded_execution_is_diagnostic_with_null_bands(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "custom(04,05,06,07)")
            seats = write_outputs(root, manifest)
            receipt = verify(root, seats)
            execution = write_execution(
                root, manifest, seats, native=False,
                gaps=["宿主未提供可核验的原生 subagent 隔离"],
            )
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )
            self.assertFalse(result["formal"])
            self.assertEqual(result["bands"], {"fidelity": None, "literary": None})
            self.assertEqual(result["recommendation"], "仅诊断")

    def test_forged_receipt_and_undisclosed_partial_criteria_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "custom(04)")
            seats = write_outputs(root, manifest)
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
            receipt_data["summary"]["verified"] += 1
            receipt.write_text(json.dumps(receipt_data, ensure_ascii=False), encoding="utf-8")
            derive(root, seats, receipt, run_dir, execution, expected=2)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "custom(04)")
            manifest["expected_outputs"][0]["criteria_ids"] = manifest["expected_outputs"][0][
                "criteria_ids"
            ][:1]
            (run_dir / "run.json").write_text(
                json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
            )
            seats = write_outputs(root, manifest)
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            derive(root, seats, receipt, run_dir, execution, expected=2)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "custom(04)")
            missing_id = manifest["expected_outputs"][0]["criteria_ids"][-1]
            seats = write_outputs(root, manifest, omit=("lit-structure", missing_id))
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            derive(root, seats, receipt, run_dir, execution, expected=2)

    def test_invalid_quote_becomes_diagnostic_and_problem_needs_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "custom(04)")
            criterion_id = manifest["expected_outputs"][0]["criteria_ids"][0]
            seats = write_outputs(root, manifest, bad_quote=("lit-structure", criterion_id))
            receipt = verify(root, seats, expected=1)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )
            self.assertFalse(result["formal"])
            self.assertTrue(any("引文作废" in gap for gap in result["coverage_gaps"]))

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "custom(04)")
            criterion_id = manifest["expected_outputs"][0]["criteria_ids"][0]
            seats = write_outputs(
                root, manifest, problem=("lit-structure", criterion_id),
                omit_recommendation=True,
            )
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            derive(root, seats, receipt, run_dir, execution, expected=2)

    def test_fidelity_redline_uses_structured_state_not_note_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "custom(01)", source=SOURCE)
            criterion_id = manifest["expected_outputs"][0]["criteria_ids"][0]
            seats = write_outputs(root, manifest, problem=("lit-fidelity", criterion_id))
            receipt = verify(root, seats, source=SOURCE)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(
                    root, seats, receipt, run_dir, execution, source=SOURCE
                ).read_text(encoding="utf-8")
            )
            self.assertTrue(result["formal"])
            self.assertEqual(result["bands"]["fidelity"], "C")
            self.assertEqual(len(result["red_flags"]), 1)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, manifest = prepare(root, "custom(01)", source=SOURCE)
            seats = write_outputs(root, manifest)
            output_path = next(seats.glob("*.json"))
            output = json.loads(output_path.read_text(encoding="utf-8"))
            output["criteria"][0]["fidelity_state"] = "CONTRADICTED"
            output["criteria"][0]["severity"] = "high"
            output_path.write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8")
            receipt = verify(root, seats, source=SOURCE)
            execution = write_execution(root, manifest, seats)
            derive(root, seats, receipt, root / "run", execution, source=SOURCE, expected=2)

            unverifiable_root = root / "unverifiable"
            unverifiable_root.mkdir()
            unverifiable = write_outputs(unverifiable_root, manifest)
            unverifiable_path = next(unverifiable.glob("*.json"))
            payload = json.loads(unverifiable_path.read_text(encoding="utf-8"))
            criterion = next(item for item in payload["criteria"] if item["id"] == "F6")
            criterion.update({
                "fidelity_state": "UNVERIFIABLE",
                "verdict": "NA",
                "severity": "none",
            })
            unverifiable_path.write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
            run(
                sys.executable,
                str(SCRIPTS / "validate_seat_output.py"),
                str(unverifiable_path),
                expected=1,
            )

    def test_abstentions_cannot_form_a_and_brief_is_digest_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "custom(04,05,06,07)")
            seats = write_outputs(root, manifest, abstain_all=True)
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )
            self.assertFalse(result["formal"])
            self.assertEqual(result["bands"], {"fidelity": None, "literary": None})
            self.assertEqual(result["recommendation"], "仅诊断")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "custom(10)", brief=BRIEF)
            seats = write_outputs(root, manifest)
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(
                    root, seats, receipt, run_dir, execution, brief=BRIEF
                ).read_text(encoding="utf-8")
            )
            self.assertTrue(result["formal"])
            derive(root, seats, receipt, run_dir, execution, expected=2)

    def test_brief_activation_respects_preset_scope(self) -> None:
        cases = (
            ("quick", False),
            ("standard", True),
            ("full", True),
            ("custom(04)", False),
            ("custom(10)", True),
        )
        for preset, expected in cases:
            with self.subTest(preset=preset), tempfile.TemporaryDirectory() as temporary:
                _, manifest = prepare(Path(temporary), preset, brief=BRIEF)
                selected = {
                    item["seat"] for item in manifest["expected_outputs"]
                }
                self.assertEqual("lit-brief" in selected, expected)

    def test_multiple_naive_readers_have_distinct_quote_and_two_step_proofs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "custom(08)", readers=2)
            seats = write_outputs(root, manifest)
            receipt = verify(root, seats)
            receipt_data = json.loads(receipt.read_text(encoding="utf-8"))
            identities = {
                (item["seat"], item["reader_id"])
                for item in receipt_data["inputs"]["seat_outputs"]
            }
            self.assertEqual(
                identities,
                {("lit-naive-reader", "reader-01"), ("lit-naive-reader", "reader-02")},
            )
            execution = write_execution(root, manifest, seats, sealed_naive=True)
            run(
                sys.executable,
                str(SCRIPTS / "validate_execution_receipt.py"),
                str(execution),
            )
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )
            self.assertTrue(result["formal"])
            self.assertEqual(len(result["seat_views"]), 2)

            execution_data = json.loads(execution.read_text(encoding="utf-8"))
            execution_data["dispatches"][2]["context_id"] = execution_data["dispatches"][0][
                "context_id"
            ]
            execution.write_text(json.dumps(execution_data, ensure_ascii=False), encoding="utf-8")
            run(
                sys.executable,
                str(SCRIPTS / "validate_execution_receipt.py"),
                str(execution),
                expected=1,
            )

    def test_structured_receipt_records_tiers_and_rejects_fuzzy_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, manifest = prepare(root, "custom(04)")
            seats = write_outputs(root, manifest)
            output_path = next(seats.glob("*.json"))
            output = json.loads(output_path.read_text(encoding="utf-8"))
            output["criteria"][0]["quotes"][0]["text"] = "那年，冬天"
            output["criteria"][1]["quotes"][0]["text"] = "母亲第一次独自坐汽车去县城"
            output_path.write_text(
                json.dumps(output, ensure_ascii=False), encoding="utf-8"
            )

            receipt = verify(root, seats, expected=1)
            data = json.loads(receipt.read_text(encoding="utf-8"))
            normalized = next(
                item for item in data["items"] if item["criterion_id"] == output["criteria"][0]["id"]
            )
            fuzzy = next(
                item for item in data["items"] if item["criterion_id"] == output["criteria"][1]["id"]
            )
            self.assertEqual((normalized["status"], normalized["tier"]), ("verified", 2))
            self.assertEqual((fuzzy["status"], fuzzy["tier"]), ("invalidated", 4))
            self.assertIn(
                f"lit-structure:{output['criteria'][1]['id']}",
                data["invalidated_criteria"],
            )


if __name__ == "__main__":
    unittest.main()
