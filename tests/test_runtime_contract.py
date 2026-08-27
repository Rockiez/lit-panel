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
import derive_report  # noqa: E402
from lit_panel_common import ContractError, parse_criteria, validate_seat_output  # noqa: E402

METADATA = parse_criteria(SKILL / "references" / "criteria")
CRAFT_SETS = {
    "lit-structure": ("N3", "TW2", "TW4", "SC1"),
    "lit-character": ("P2", "P3", "P4", "P7"),
    "lit-prose": ("L5", "L7", "TW3"),
    "lit-resonance": ("E3", "E6", "E7", "TW14"),
}
ALL_CRAFT_IDS = {
    (seat, criterion_id)
    for seat, criterion_ids in CRAFT_SETS.items()
    for criterion_id in criterion_ids
}
CORE_SEATS = set(CRAFT_SETS)


def selection(value: tuple[str, str] | set[tuple[str, str]] | None) -> set[tuple[str, str]]:
    """Accept either a single (seat, criterion) pair or a set of them."""
    if value is None:
        return set()
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], str):
        return {value}
    return set(value)


def core_judgments(
    overrides: dict[tuple[str, str], tuple[str, str]] | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, str]]]:
    """Judgment rows for the four core seats, clean everywhere except the overrides.

    An override maps (seat, criterion_id) to (verdict, severity), letting a test state a
    band-lattice combination directly instead of steering it through a whole run.
    """
    overrides = overrides or {}
    outputs = {seat: {"seat": seat, "reader_id": None} for seat in CORE_SEATS}
    rows = []
    for (seat, criterion_id), metadata in sorted(METADATA.items()):
        if seat not in CORE_SEATS:
            continue
        clean = "YES" if metadata["polarity"] == "[通过]" else "NO"
        verdict, severity = overrides.get((seat, criterion_id), (clean, "none"))
        rows.append((
            outputs[seat],
            {"id": criterion_id, "verdict": verdict, "severity": severity},
            metadata,
        ))
    return rows


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
    problem: tuple[str, str] | set[tuple[str, str]] | None = None,
    bad_quote: tuple[str, str] | None = None,
    omit: tuple[str, str] | None = None,
    na: tuple[str, str] | set[tuple[str, str]] | None = None,
    omit_recommendation: bool = False,
    abstain_all: bool = False,
    problem_severity: str = "high",
    anchor: dict[str, dict[str, Any]] | None = None,
) -> Path:
    problems = selection(problem)
    nas = selection(na)
    anchor = anchor or {}
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
            is_problem = (expected["seat"], criterion_id) in problems
            is_na = (expected["seat"], criterion_id) in nas
            if abstain_all:
                verdict = "ABSTAIN"
            elif is_na:
                verdict = "NA"
            if is_problem:
                verdict = "NO" if polarity == "[通过]" else "YES"
                severity = problem_severity
            quote = (
                "原文中不存在的逐字引文"
                if bad_quote == (expected["seat"], criterion_id)
                else "那年冬天"
            )
            quotes = (
                []
                if abstain_all or is_na
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
        if expected["seat"] in anchor:
            output["anchor_comparison"] = anchor[expected["seat"]]
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

    def test_complete_standard_chain_derives_restored_scorecard(self) -> None:
        """Break caught: a formal standard run drops the v0.4.1 score view again.

        Band A [85,94] with every craft row affirmed and no defects: p_i = 1 for all
        four seats, so each dimension is 85+9*1 = 94 and the total saturates at 94
        (the +0.05 originality lift is clamped away at the top of the window).
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "standard")
            seats = write_outputs(root, manifest)
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )
            self.assertEqual(result["schema_version"], "1.2")
            self.assertEqual(
                result["scores"],
                {
                    "available": True,
                    "status": "verified",
                    "status_reasons": [],
                    "formula_version": "0.6.0-band-anchored",
                    "total": 94,
                    "grade": "A",
                    "originality_bonus": 5,
                    "reader_warning": False,
                    "dimensions": {
                        "structure": {"score": 94, "grade": "A"},
                        "character": {"score": 94, "grade": "A"},
                        "prose": {"score": 94, "grade": "A"},
                        "resonance": {"score": 94, "grade": "A"},
                        "ai_cleanliness": {"score": 100, "grade": "A"},
                        "reader_experience": {"score": 85, "grade": "A-"},
                        "fidelity": None,
                    },
                },
            )
            markdown = (root / "report.md").read_text(encoding="utf-8")
            self.assertIn("## 总分卡", markdown)
            self.assertIn("**94/100 · A**", markdown)
            self.assertIn("分数由判据向量机械导出，评审席不产生任何数字。", markdown)

    def test_invalid_quotes_keep_provisional_scores_from_frozen_judgments(self) -> None:
        """Break caught: a bad quote erases a score instead of degrading its evidence status.

        The frozen N1 problem still lands the run in band B [75,84]; structure keeps its
        full craft ratio and carries one core defect out of 14 tier-weighted non-craft
        units, so p = 0.5+0.5*(1-2/14) = 0.9286 → 75+9*0.9286 = 83.36.
        """
        cases = (
            ("lit-structure", "N1", "lit-structure:N1", "structure", {"score": 83.36, "grade": "B+"}),
            ("lit-slop", "A1", "lit-slop:A1", "ai_cleanliness", {"score": 97, "grade": "A"}),
            (
                "lit-naive-reader", "R2", "lit-naive-reader@reader-01:R2",
                "reader_experience", {"score": 75, "grade": "B"},
            ),
        )
        for seat, criterion_id, expected_key, dimension, expected_dimension in cases:
            with self.subTest(seat=seat), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                run_dir, manifest = prepare(root, "standard")
                seats = write_outputs(
                    root,
                    manifest,
                    problem=(seat, criterion_id),
                    bad_quote=(seat, criterion_id),
                )
                receipt = verify(root, seats, expected=1)
                execution = write_execution(root, manifest, seats)
                result = json.loads(
                    derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
                )

                self.assertFalse(result["formal"])
                self.assertTrue(result["scores"]["available"])
                self.assertEqual(result["scores"]["status"], "provisional")
                self.assertEqual(
                    result["scores"]["status_reasons"],
                    [f"引文核验失败: {expected_key}"],
                )
                self.assertEqual(result["scores"]["dimensions"][dimension], expected_dimension)
                markdown = (root / "report.md").read_text(encoding="utf-8")
                self.assertIn("评分状态：暂定（判定、覆盖或证据降级）", markdown)
                self.assertIn(f"引文核验失败: {expected_key}", markdown)

    def test_non_applicable_core_p4_does_not_block_band_or_numeric_score(self) -> None:
        """Short prose without two speakers must not lose its band or score.

        P4 is a craft criterion, so an NA only withholds positive evidence: character
        craft is 3/4, keeping the seat above the 0.6 A-gate, so the band stays A [85,94].
        Character sits at p=0.5*0.75+0.5=0.875 → 85+9*0.875 = 92.88, and the total at
        p=0.7*0.9688+0.3*0.875+0.05 = 0.9906 → 93.92.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "standard")
            seats = write_outputs(root, manifest, na=("lit-character", "P4"))
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )

            self.assertTrue(result["formal"])
            self.assertEqual(result["bands"]["literary"], "A")
            self.assertTrue(result["scores"]["available"])
            self.assertEqual(result["scores"]["status"], "verified")
            self.assertEqual(
                result["scores"]["dimensions"]["character"], {"score": 92.88, "grade": "A"}
            )
            self.assertEqual(result["scores"]["total"], 93.92)
            self.assertEqual(result["scores"]["status_reasons"], [])
            self.assertEqual(result["arbitration"], [])

    def test_quick_and_non_scoring_custom_runs_always_emit_numeric_scores(self) -> None:
        """Every successfully derived report needs a transparent numerical fallback."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "quick")
            seats = write_outputs(root, manifest)
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )
            self.assertTrue(result["scores"]["available"])
            self.assertEqual(result["scores"]["status"], "provisional")
            self.assertEqual(result["scores"]["total"], 85)
            self.assertIsNone(result["scores"]["dimensions"]["structure"])
            self.assertTrue(
                any("读者体验基线" in reason for reason in result["scores"]["status_reasons"])
            )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "custom(02)")
            seats = write_outputs(root, manifest)
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )
            self.assertTrue(result["scores"]["available"])
            self.assertEqual(result["scores"]["status"], "provisional")
            self.assertEqual(result["scores"]["total"], 50)
            self.assertTrue(
                any("固定诊断基线 50" in reason for reason in result["scores"]["status_reasons"])
            )

    def test_invalid_originality_quote_still_removes_the_bonus_provisionally(self) -> None:
        """Break caught: an unverified originality judgment is dropped from the score vector.

        The bonus must be gone from the reported field; the total stays 94 because the
        core seats are already at the top of band A [85,94], where the +0.05 lift the
        bonus would have added is clamped away anyway.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "standard")
            seats = write_outputs(
                root,
                manifest,
                problem=("lit-originality", "O1"),
                bad_quote=("lit-originality", "O1"),
            )
            receipt = verify(root, seats, expected=1)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )

            self.assertTrue(result["scores"]["available"])
            self.assertEqual(result["scores"]["status"], "provisional")
            self.assertEqual(result["scores"]["originality_bonus"], 0)
            self.assertEqual(result["scores"]["total"], 94)

    def test_invalid_fidelity_quote_keeps_provisional_fidelity_score_when_source_exists(self) -> None:
        """Break caught: a fidelity quote error clears a score despite the source being present."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "standard", source=SOURCE)
            seats = write_outputs(
                root,
                manifest,
                problem=("lit-fidelity", "F1"),
                bad_quote=("lit-fidelity", "F1"),
            )
            receipt = verify(root, seats, source=SOURCE, expected=1)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(
                    root, seats, receipt, run_dir, execution, source=SOURCE
                ).read_text(encoding="utf-8")
            )

            self.assertTrue(result["scores"]["available"])
            self.assertEqual(result["scores"]["status"], "provisional")
            self.assertEqual(
                result["scores"]["dimensions"]["fidelity"],
                {"score": 45, "grade": "C"},
            )
            self.assertEqual(result["scores"]["total"], 45)

    def test_full_run_without_source_still_scores_every_non_fidelity_dimension(self) -> None:
        """Break caught: missing source clears literary scores instead of only fidelity."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "full")
            seats = write_outputs(root, manifest)
            receipt = verify(root, seats)
            execution = write_execution(
                root,
                manifest,
                seats,
                gaps=[
                    f"{item['number']} / {item['seat']}: {item['reason']}"
                    for item in manifest["skipped_seats"]
                    if item["warning"]
                ],
            )
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )

            self.assertFalse(result["formal"])
            self.assertTrue(result["scores"]["available"])
            self.assertEqual(result["scores"]["status"], "verified")
            self.assertIsNone(result["scores"]["dimensions"]["fidelity"])
            for dimension in (
                "structure", "character", "prose", "resonance",
                "ai_cleanliness", "reader_experience",
            ):
                self.assertIsNotNone(result["scores"]["dimensions"][dimension])

    def test_missing_one_of_multiple_scoring_readers_keeps_a_provisional_score(self) -> None:
        """A partial reader panel must not erase the score or masquerade as verified."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "standard", readers=2)
            seats = write_outputs(root, manifest)
            receipt = verify(root, seats)
            execution = write_execution(
                root,
                manifest,
                seats,
                gaps=["缺少席位输出: lit-naive-reader@reader-02"],
            )
            (seats / "lit-naive-reader-reader-02.json").unlink()
            receipt.unlink()
            receipt = verify(root, seats)
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )

            self.assertTrue(result["scores"]["available"])
            self.assertEqual(result["scores"]["status"], "provisional")
            self.assertIsInstance(result["scores"]["total"], (int, float))
            self.assertTrue(
                any("reader-02" in reason for reason in result["scores"]["status_reasons"])
            )

    def test_scorecard_deducts_an_ordinary_core_problem(self) -> None:
        """Break caught: ordinary core failures stop reducing their literary dimension.

        N1 is deliberately a non-craft core row, so it lands in the defect ledger: it
        drops the defect ceiling to B [75,84] and raises structure's defect density to
        2/14, giving p=0.9286 → 83.36 while the other three seats stay at 84.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "standard")
            seats = write_outputs(root, manifest, problem=("lit-structure", "N1"))
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )

            self.assertEqual(
                result["scores"]["dimensions"]["structure"],
                {"score": 83.36, "grade": "B+"},
            )
            self.assertEqual(result["scores"]["total"], 84)
            self.assertEqual(result["bands"]["literary"], "B")

    def test_scorecard_applies_ai_penalty_without_double_counting(self) -> None:
        """Break caught: one slop finding is omitted or charged more than once.

        The ai_cleanliness dimension keeps its absolute scale (100−3 per finding). The
        total charges 0.02 of the band position per finding, so against a run held just
        below the top of band A (one prose craft row withheld, total 93.74) one finding
        costs 9*0.02 = 0.18 and two cost exactly twice that.
        """
        for problem, expected_ai, expected_total in (
            (("lit-slop", "A1"), {"score": 97, "grade": "A"}, 93.56),
            (
                {("lit-slop", "A1"), ("lit-slop", "A2")},
                {"score": 94, "grade": "A"},
                93.38,
            ),
        ):
            with self.subTest(problem=problem), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                run_dir, manifest = prepare(root, "standard")
                seats = write_outputs(
                    root, manifest, na={("lit-prose", "TW3")}, problem=problem
                )
                receipt = verify(root, seats)
                execution = write_execution(root, manifest, seats)
                result = json.loads(
                    derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
                )

                self.assertEqual(result["bands"]["literary"], "A")
                self.assertEqual(result["scores"]["dimensions"]["ai_cleanliness"], expected_ai)
                self.assertEqual(result["scores"]["total"], expected_total)

    def test_scorecard_keeps_originality_bonus_positive_only(self) -> None:
        """Break caught: an originality problem deducts points instead of only removing bonus.

        Measured against the same run without the problem (total 93.74), losing the bonus
        must cost exactly the 0.05 position lift it bought — 9*0.05 = 0.45 — and nothing
        more, so the total is 93.29 rather than anything lower.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "standard")
            seats = write_outputs(root, manifest, na={("lit-prose", "TW3")})
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            baseline = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )
            self.assertEqual(baseline["scores"]["originality_bonus"], 5)
            self.assertEqual(baseline["scores"]["total"], 93.74)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "standard")
            seats = write_outputs(
                root,
                manifest,
                na={("lit-prose", "TW3")},
                problem=("lit-originality", "O1"),
            )
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )

            self.assertEqual(result["scores"]["originality_bonus"], 0)
            self.assertEqual(result["scores"]["total"], 93.29)
            self.assertAlmostEqual(
                baseline["scores"]["total"] - result["scores"]["total"], 0.45, places=2
            )

    def test_scorecard_applies_fidelity_cap_last(self) -> None:
        """Break caught: a fidelity C no longer caps a high literary score at 45."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "standard", source=SOURCE)
            seats = write_outputs(root, manifest, problem=("lit-fidelity", "F1"))
            receipt = verify(root, seats, source=SOURCE)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(
                    root, seats, receipt, run_dir, execution, source=SOURCE
                ).read_text(encoding="utf-8")
            )

            self.assertEqual(
                result["scores"]["dimensions"]["fidelity"],
                {"score": 45, "grade": "C"},
            )
            self.assertEqual(result["scores"]["total"], 45)
            self.assertEqual(result["scores"]["grade"], "C")
            self.assertEqual(result["recommendation"], "重写建议")

    def test_record_type_run_without_craft_evidence_is_demoted_to_b(self) -> None:
        """A flawless run that never affirms positive craft cannot buy an A.

        craft_overall is 0, below the 0.3 overall gate, so the craft ceiling is 记录型
        and the window is [68,74]. Every seat sits at p=0.5*0+0.5*1 = 0.5 → 71, and the
        total adds the 0.05 originality lift: 68+6*0.55 = 71.3.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "standard")
            seats = write_outputs(root, manifest, na=ALL_CRAFT_IDS)
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )

            self.assertTrue(result["formal"])
            self.assertEqual(result["revisions"], [])
            self.assertEqual(result["bands"]["literary"], "B")
            self.assertEqual(result["recommendation"], "修订后交付")
            for dimension in ("structure", "character", "prose", "resonance"):
                self.assertEqual(
                    result["scores"]["dimensions"][dimension],
                    {"score": 71, "grade": "B"},
                    dimension,
                )
            self.assertEqual(result["scores"]["status"], "verified")
            self.assertEqual(result["scores"]["total"], 71.3)
            markdown = (root / "report.md").read_text(encoding="utf-8")
            self.assertIn(
                "- 文学带：B（记录型：正向工艺证据未达 A 门）", markdown
            )

    def test_total_follows_the_weakest_literary_dimension_not_the_mean(self) -> None:
        """Break caught: three strong dimensions average away one collapsed dimension.

        Three non-craft core defects put structure at defect density 6/14, so p=0.7857
        → 75+9*0.7857 = 82.07 inside band B [75,84]. The 0.3 min term then has to pull
        the total below what the weighted mean alone would give: 0.7*0.9464+0.3*0.7857
        +0.05 = 0.9482 → 83.53, against 83.97 for a mean-only projection.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "standard")
            seats = write_outputs(
                root,
                manifest,
                problem={("lit-structure", "N1"), ("lit-structure", "N4"),
                         ("lit-structure", "N5")},
            )
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )

            dimensions = result["scores"]["dimensions"]
            self.assertEqual(dimensions["structure"], {"score": 82.07, "grade": "B+"})
            for dimension in ("character", "prose", "resonance"):
                self.assertEqual(dimensions[dimension], {"score": 84, "grade": "B+"}, dimension)
            self.assertEqual(result["scores"]["originality_bonus"], 5)
            self.assertEqual(result["scores"]["total"], 83.53)
            self.assertEqual(result["bands"]["literary"], "B")
            mean_only = sum(
                dimensions[name]["score"]
                for name in ("structure", "character", "prose", "resonance")
            ) / 4 + 0.45
            self.assertLess(result["scores"]["total"], mean_only)

    def test_dimension_steps_down_with_the_share_of_affirmed_craft(self) -> None:
        """The craft share and the 0.6 A-gate must move together.

        Prose has three craft rows. Withholding one leaves 2/3 = 0.667, still above the
        per-seat gate, so the band stays A [85,94] and prose sits at 0.5*0.667+0.5 =
        0.833 → 92.5. Withholding two drops prose to 1/3, failing the gate: the band
        falls to B [75,84] and prose to 0.667 → 81. Withholding all three gives 0.5 →
        79.5, still B because craft_overall (0.75) clears the 0.3 record-type line.
        """
        cases = (
            ({("lit-prose", "TW3")}, {"score": 92.5, "grade": "A"}, "A"),
            ({("lit-prose", "L7"), ("lit-prose", "TW3")}, {"score": 81, "grade": "B+"}, "B"),
            (
                {("lit-prose", "L5"), ("lit-prose", "L7"), ("lit-prose", "TW3")},
                {"score": 79.5, "grade": "B"},
                "B",
            ),
        )
        for withheld, expected_dimension, expected_band in cases:
            with self.subTest(withheld=sorted(withheld)), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                run_dir, manifest = prepare(root, "standard")
                seats = write_outputs(root, manifest, na=withheld)
                receipt = verify(root, seats)
                execution = write_execution(root, manifest, seats)
                result = json.loads(
                    derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
                )

                self.assertEqual(result["revisions"], [])
                self.assertEqual(result["scores"]["dimensions"]["prose"], expected_dimension)
                self.assertEqual(result["bands"]["literary"], expected_band)

    def test_medium_veto_problem_costs_more_than_an_ordinary_core_problem(self) -> None:
        """Break caught: only the high-severity veto cap is enforced.

        A medium-severity veto stops short of the C red line, so the band is B [75,84]
        like any core defect — but the veto tier weighs 3 against core's 2, so structure
        lands at 0.5+0.5*(1-3/14) = 0.8929 → 83.04, strictly below the 83.36 the same
        seat scores for a core defect. It still has to reach human arbitration.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "standard")
            seats = write_outputs(
                root, manifest, problem=("lit-structure", "N2"), problem_severity="medium"
            )
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )

            self.assertEqual(
                result["scores"]["dimensions"]["structure"], {"score": 83.04, "grade": "B+"}
            )
            self.assertEqual(result["scores"]["total"], 83.99)
            self.assertEqual(result["bands"]["literary"], "B")
            self.assertLess(result["scores"]["dimensions"]["structure"]["score"], 83.36)
            self.assertIn(
                ("lit-structure", "N2"),
                {(item["seat"], item["criterion_id"]) for item in result["arbitration"]},
            )

    def test_band_is_the_stricter_of_the_craft_and_defect_ceilings(self) -> None:
        """The lattice must take min(craft ceiling, defect ceiling), order A > B > 记录型 > C."""
        cases = (
            ("clean", {}, "A", "A", ("A", False)),
            (
                "craft A, defect B",
                {("lit-structure", "N1"): ("NO", "high")},
                "A", "B", ("B", False),
            ),
            (
                "craft 记录型, defect A",
                {pair: ("NA", "none") for pair in ALL_CRAFT_IDS},
                "记录型", "A", ("B", True),
            ),
            (
                "craft 记录型, defect C",
                {
                    **{pair: ("NA", "none") for pair in ALL_CRAFT_IDS},
                    ("lit-structure", "N2"): ("NO", "high"),
                },
                "记录型", "C", ("C", False),
            ),
            (
                "craft B, defect A",
                {(seat, cid): ("NA", "none")
                 for seat, cid in ALL_CRAFT_IDS if seat == "lit-prose"},
                "B", "A", ("B", False),
            ),
        )
        for label, overrides, craft, defect, expected in cases:
            with self.subTest(case=label):
                rows = core_judgments(overrides)
                self.assertEqual(derive_report.craft_ceiling(rows), craft)
                self.assertEqual(derive_report.defect_ceiling(rows), defect)
                self.assertEqual(
                    derive_report.literary_band_detail(rows, CORE_SEATS, False), expected
                )

    def test_record_type_window_opens_only_below_the_overall_craft_gate(self) -> None:
        """记录型 is B's sub-level at [68,74], reached only when craft_overall < 0.3."""
        self.assertEqual(derive_report.band_window("B", True), (68, 74))
        self.assertEqual(derive_report.band_window("B", False), (75, 84))
        self.assertIsNone(derive_report.band_window("N/A", False))

        # One core seat's craft withheld leaves craft_overall at 0.75 — plain B.
        partial = core_judgments(
            {(seat, cid): ("NA", "none") for seat, cid in ALL_CRAFT_IDS if seat == "lit-prose"}
        )
        self.assertAlmostEqual(derive_report.craft_overall(partial), 0.75)
        self.assertFalse(derive_report.literary_band_detail(partial, CORE_SEATS, False)[1])

        # All craft withheld puts craft_overall at 0, under the 0.3 gate.
        none_affirmed = core_judgments({pair: ("NA", "none") for pair in ALL_CRAFT_IDS})
        self.assertEqual(derive_report.craft_overall(none_affirmed), 0.0)
        band, demoted = derive_report.literary_band_detail(none_affirmed, CORE_SEATS, False)
        self.assertEqual((band, demoted), ("B", True))
        self.assertEqual(derive_report.band_window(band, demoted), (68, 74))

    def test_craft_criteria_never_enter_the_defect_ledger(self) -> None:
        """A craft NO must cost only its positive evidence, never a second tier deduction.

        N3 and N1 are both non-veto core rows on lit-structure; only N1 is in the craft
        set. Failing N3 leaves defect density at 0 and shows up solely as a craft ratio
        of 3/4, while failing N1 charges 2 of the seat's 14 tier-weighted non-craft units.
        """
        craft_no = core_judgments({("lit-structure", "N3"): ("NO", "high")})
        plain_no = core_judgments({("lit-structure", "N1"): ("NO", "high")})

        self.assertEqual(derive_report.defect_density("lit-structure", craft_no), 0.0)
        self.assertAlmostEqual(
            derive_report.defect_density("lit-structure", plain_no), 2 / 14
        )
        self.assertEqual(derive_report.craft_ratio("lit-structure", craft_no), 0.75)
        self.assertEqual(derive_report.craft_ratio("lit-structure", plain_no), 1.0)
        self.assertNotEqual(
            derive_report.position("lit-structure", craft_no),
            derive_report.position("lit-structure", plain_no),
        )

        # A craft NO and a craft NA are indistinguishable to the score: both are simply
        # absent positive evidence, which is the whole point of the 0.6.0 correction.
        craft_na = core_judgments({("lit-structure", "N3"): ("NA", "none")})
        self.assertEqual(
            derive_report.position("lit-structure", craft_no),
            derive_report.position("lit-structure", craft_na),
        )

    def test_total_stays_inside_its_band_window_unless_fidelity_caps_it(self) -> None:
        """The score is a projection of the band, so only the fidelity cap may escape it."""
        cases = (
            ("A", {}, "A"),
            ("B", {"problem": ("lit-structure", "N1")}, "B"),
            ("C", {"problem": ("lit-structure", "N2")}, "C"),
            ("记录型", {"na": ALL_CRAFT_IDS}, "B"),
        )
        for label, kwargs, expected_band in cases:
            with self.subTest(band=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                run_dir, manifest = prepare(root, "standard")
                seats = write_outputs(root, manifest, **kwargs)
                receipt = verify(root, seats)
                execution = write_execution(root, manifest, seats)
                result = json.loads(
                    derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
                )

                self.assertEqual(result["bands"]["literary"], expected_band)
                low, high = derive_report.BAND_WINDOWS[label]
                self.assertGreaterEqual(result["scores"]["total"], low)
                self.assertLessEqual(result["scores"]["total"], high)
                for dimension in ("structure", "character", "prose", "resonance"):
                    score = result["scores"]["dimensions"][dimension]["score"]
                    self.assertGreaterEqual(score, low, dimension)
                    self.assertLessEqual(score, high, dimension)

        # The pre-existing fidelity cap is applied last and may legitimately push the
        # total below the band window — band A here, but capped to 45 by a fidelity C.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "standard", source=SOURCE)
            seats = write_outputs(root, manifest, problem=("lit-fidelity", "F1"))
            receipt = verify(root, seats, source=SOURCE)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(
                    root, seats, receipt, run_dir, execution, source=SOURCE
                ).read_text(encoding="utf-8")
            )

            self.assertEqual(result["bands"]["literary"], "A")
            self.assertEqual(result["bands"]["fidelity"], "C")
            self.assertEqual(result["scores"]["total"], 45)
            self.assertLess(result["scores"]["total"], derive_report.BAND_WINDOWS["A"][0])

    def test_anchor_comparison_is_validated_and_flags_divergence_for_arbitration(self) -> None:
        """An anchor placement two ranks away from the derived band needs a human."""
        base = {
            "schema_version": "1.0",
            "run_id": "run-contract",
            "seat": "lit-structure",
            "phase": "review",
            "criteria": [],
            "free_view": "观点",
            "anchor_comparison": {
                "placement": "低于C",
                "rationale": "关键转折只以概述交代，低于 C 档锚文的场景密度。",
                "quote": {"text": "那年冬天", "target": "text", "location": "第1段"},
            },
        }
        self.assertEqual(
            validate_seat_output(json.loads(json.dumps(base)))["anchor_comparison"]["placement"],
            "低于C",
        )
        rejected = json.loads(json.dumps(base))
        rejected["anchor_comparison"]["placement"] = "接近A+"
        with self.assertRaises(ContractError):
            validate_seat_output(rejected)
        non_core = json.loads(json.dumps(base))
        non_core["seat"] = "lit-slop"
        with self.assertRaises(ContractError):
            validate_seat_output(non_core)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "custom(04,05,06,07)")
            seats = write_outputs(
                root,
                manifest,
                anchor={"lit-structure": base["anchor_comparison"]},
            )
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )

            self.assertEqual(result["bands"]["literary"], "A")
            flagged = [
                item for item in result["arbitration"] if item["criterion_id"] == "ANCHOR"
            ]
            self.assertEqual(len(flagged), 1)
            self.assertEqual(flagged[0]["seat"], "lit-structure")
            self.assertEqual(
                flagged[0]["reason"],
                "席位 lit-structure 锚定对比背离：对照带位 低于C 与机导文学带 A 偏差 ≥2 档",
            )
            self.assertIn("锚定对比背离", (root / "report.md").read_text(encoding="utf-8"))

    def test_anchor_comparison_within_one_rank_is_not_arbitrated(self) -> None:
        """Break caught: every anchor placement is escalated regardless of distance."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, manifest = prepare(root, "custom(04,05,06,07)")
            seats = write_outputs(
                root,
                manifest,
                anchor={
                    "lit-structure": {
                        "placement": "介于A-B",
                        "rationale": "转折已场景化，但铺垫密度弱于 A 档锚文。",
                        "quote": {"text": "那年冬天", "target": "text", "location": "第1段"},
                    }
                },
            )
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )

            self.assertEqual(result["bands"]["literary"], "A")
            self.assertEqual(result["arbitration"], [])

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
            self.assertTrue(result["scores"]["available"])
            self.assertEqual(result["scores"]["status"], "provisional")
            # No formal band, but the frozen judgments still project into A [85,94] at
            # p=1 for the provisional score view.
            self.assertEqual(result["scores"]["total"], 94)
            self.assertTrue(
                any("原生 subagent 隔离" in reason for reason in result["scores"]["status_reasons"])
            )

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
            run_dir, manifest = prepare(root, "standard")
            seats = write_outputs(root, manifest, abstain_all=True)
            receipt = verify(root, seats)
            execution = write_execution(root, manifest, seats)
            result = json.loads(
                derive(root, seats, receipt, run_dir, execution).read_text(encoding="utf-8")
            )
            self.assertFalse(result["formal"])
            self.assertEqual(result["bands"], {"fidelity": None, "literary": None})
            self.assertEqual(result["recommendation"], "仅诊断")
            self.assertTrue(result["scores"]["available"])
            self.assertEqual(result["scores"]["status"], "provisional")
            # Abstaining everywhere affirms no craft and decides no defect: the score
            # view falls to the 记录型 window [68,74] at p=0.5 → 71.
            self.assertEqual(result["scores"]["total"], 71)
            self.assertTrue(
                any("评分判据未决" in reason for reason in result["scores"]["status_reasons"])
            )

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
