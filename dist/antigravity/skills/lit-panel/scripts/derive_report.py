#!/usr/bin/env python3
"""Deterministically derive a formal or explicitly diagnostic lit-panel report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from lit_panel_common import (
    ContractError,
    criterion_key,
    digest_path,
    is_problem,
    iter_seat_output_paths,
    output_identity,
    parse_criteria,
    read_json,
    sha256_text,
    validate_execution_receipt,
    validate_run_manifest,
    validate_seat_output,
    validate_verification_receipt,
    write_json,
)
from prepare_run import build_packet_payloads, has_cross_chapter_source, parse_registry, plan_run

LITERARY_SEATS = {"lit-structure", "lit-character", "lit-prose", "lit-resonance"}
SCORING_SEATS = LITERARY_SEATS | {"lit-slop", "lit-naive-reader", "lit-originality"}
LITERARY_DIMENSIONS = {
    "structure": "lit-structure",
    "character": "lit-character",
    "prose": "lit-prose",
    "resonance": "lit-resonance",
}
SCORE_FORMULA_VERSION = "0.4.1-closed"
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "none": 3}


def finding(output: dict[str, Any], criterion: dict[str, Any]) -> dict[str, Any]:
    first_text_quote = next(
        (quote["text"] for quote in criterion["quotes"] if quote["target"] == "text"), ""
    )
    value: dict[str, Any] = {
        "seat": output["seat"],
        "reader_id": output.get("reader_id"),
        "criterion_id": criterion["id"],
        "severity": criterion["severity"],
        "reason": criterion["note"],
    }
    if first_text_quote:
        value["quote"] = first_text_quote
    if criterion.get("recommendation"):
        value["recommendation"] = criterion["recommendation"]
    return value


def fidelity_band(valid: list[tuple[dict[str, Any], dict[str, Any], dict[str, str]]]) -> str:
    rows = [row for row in valid if row[0]["seat"] == "lit-fidelity"]
    if not rows:
        return "N/A"
    if any(
        row[1]["fidelity_state"] == "CONTRADICTED"
        or (
            row[1]["fidelity_state"] == "UNSUPPORTED"
            and row[1]["severity"] == "high"
        )
        for row in rows
    ):
        return "C"
    return "B" if any(row[1]["fidelity_state"] == "UNSUPPORTED" for row in rows) else "A"


def validate_fidelity_semantics(
    output: dict[str, Any],
    criterion: dict[str, Any],
    metadata: dict[str, str],
) -> None:
    if output["seat"] != "lit-fidelity":
        return
    state = criterion["fidelity_state"]
    verdict = criterion["verdict"]
    severity = criterion["severity"]
    problem = is_problem(metadata["polarity"], verdict)
    key = criterion_key(output, criterion["id"])
    if state in {"SUPPORTED", "PERMISSIBLE_INFERENCE"}:
        if problem or verdict not in {"YES", "NO"} or severity != "none":
            raise ContractError(f"{key} 的正向 fidelity_state 与 verdict/severity 矛盾")
        if state == "PERMISSIBLE_INFERENCE" and criterion["id"] != "F6":
            raise ContractError(f"{key} 仅 F6 可使用 PERMISSIBLE_INFERENCE")
    elif state == "UNSUPPORTED":
        if not problem or severity == "none":
            raise ContractError(f"{key} 的 UNSUPPORTED 必须是有严重度的问题判定")
    elif state == "CONTRADICTED":
        if not problem or severity != "high":
            raise ContractError(f"{key} 的 CONTRADICTED 必须是 high 问题判定")
    elif state == "UNVERIFIABLE":
        if verdict != "ABSTAIN" or severity != "none":
            raise ContractError(f"{key} 的 UNVERIFIABLE 必须是 ABSTAIN 且 severity=none")


def validate_canonical_run(
    manifest: dict[str, Any],
    execution: dict[str, Any],
    *,
    manifest_path: Path,
    criteria_dir: Path,
    metadata: dict[tuple[str, str], dict[str, str]],
    text: Path,
    source: Path | None,
    brief: Path | None,
) -> None:
    """Rebuild the run plan and bind every executed packet to its canonical bytes."""
    skill_root = criteria_dir.resolve().parent.parent
    registry = parse_registry(skill_root / "references" / "registry.md")
    cross_chapter = has_cross_chapter_source(source)
    require_cross = manifest["cross_chapter_source"] == cross_chapter
    if not require_cross:
        raise ContractError("cross_chapter_source 与当前来源不一致")
    canonical = plan_run(
        registry,
        metadata,
        preset=manifest["preset"],
        genre=manifest["genre"],
        readers=manifest["readers"],
        source_provided=source is not None,
        brief_provided=brief is not None,
        cross_chapter_source=cross_chapter,
    )
    for field in ("selected_seats", "skipped_seats", "expected_outputs", "packets"):
        if manifest[field] != canonical[field]:
            raise ContractError(f"运行清单 {field} 与 canonical 计划不一致")

    run_dir = manifest_path.resolve().parent
    text_copy = run_dir / "text.txt"
    if digest_path(text_copy) != manifest["inputs"]["text_sha256"]:
        raise ContractError("派发正文副本与运行清单摘要不一致")
    payloads = build_packet_payloads(
        canonical,
        registry,
        run_id=manifest["run_id"],
        skill_root=skill_root,
        text_path=text_copy,
        source=source,
        brief=brief,
    )
    packets_dir = run_dir / "packets"
    if not packets_dir.is_dir():
        raise ContractError("运行清单旁缺少 packets 目录")
    actual_names = sorted(item.name for item in packets_dir.iterdir())
    if actual_names != manifest["packets"]:
        raise ContractError("packets 目录内容与运行清单不一致")
    dispatches = {item["packet"]: item for item in execution["dispatches"]}
    for packet_name, canonical_payload in payloads.items():
        packet_path = packets_dir / packet_name
        if not packet_path.is_file() or read_json(packet_path) != canonical_payload:
            raise ContractError(f"派发包内容不符合 canonical 计划: {packet_name}")
        dispatch = dispatches.get(packet_name)
        if dispatch is not None and dispatch["packet_sha256"] != digest_path(packet_path):
            raise ContractError(f"执行回执 packet_sha256 不匹配: {packet_name}")


def literary_band(
    valid: list[tuple[dict[str, Any], dict[str, Any], dict[str, str]]],
    covered_seats: set[str],
    naive_unwilling: bool,
) -> str:
    if not LITERARY_SEATS.issubset(covered_seats):
        return "N/A"
    rows = [row for row in valid if row[0]["seat"] in LITERARY_SEATS]
    problems = [row for row in rows if is_problem(row[2]["polarity"], row[1]["verdict"])]
    if any(row[2]["tier"] == "veto" and row[1]["severity"] == "high" for row in problems):
        return "C"
    if any(row[2]["tier"] in {"veto", "core"} for row in problems):
        return "B"
    return "A候选（待人工确认）" if naive_unwilling else "A"


def recommendation(fidelity: str, literary: str) -> str:
    if fidelity == "N/A" and literary == "N/A":
        return "仅诊断"
    if fidelity == "C" or literary == "C":
        return "重写建议"
    if literary == "A候选（待人工确认）":
        return "待人工确认"
    if fidelity in {"A", "N/A"} and literary == "A":
        return "交付"
    return "修订后交付"


def normalized_score(value: float) -> int | float:
    rounded = float(round(max(0.0, min(100.0, value)), 2))
    return int(rounded) if rounded.is_integer() else rounded


def score_grade(value: int | float) -> str:
    if value >= 90:
        return "A"
    if value >= 85:
        return "A-"
    if value >= 80:
        return "B+"
    if value >= 70:
        return "B"
    if value >= 60:
        return "C+"
    if value >= 45:
        return "C"
    return "D"


def scored_dimension(
    seat: str,
    valid: list[tuple[dict[str, Any], dict[str, Any], dict[str, str]]],
) -> dict[str, int | float | str]:
    rows = [row for row in valid if row[0]["seat"] == seat]
    problems = [row for row in rows if is_problem(row[2]["polarity"], row[1]["verdict"])]
    value = 90
    cap = 100
    for _, criterion, metadata in problems:
        if metadata["tier"] == "veto":
            cap = min(cap, 45 if criterion["severity"] == "high" else 65)
        elif metadata["tier"] == "core":
            value -= 12
        elif metadata["tier"] == "extended":
            value -= 5
    score = normalized_score(min(value, cap))
    return {"score": score, "grade": score_grade(score)}


def originality_bonus(
    valid: list[tuple[dict[str, Any], dict[str, Any], dict[str, str]]],
) -> int:
    rows = [row for row in valid if row[0]["seat"] == "lit-originality"]
    if any(is_problem(row[2]["polarity"], row[1]["verdict"]) for row in rows):
        return 0
    positive_ids = {"O2", "O3", "O5", "O6"}
    positive_yes = {
        criterion["id"]
        for _, criterion, _ in rows
        if criterion["id"] in positive_ids and criterion["verdict"] == "YES"
    }
    if positive_yes == positive_ids:
        return 5
    return 3 if len(positive_yes) >= 3 else 0


def derive_scores(
    valid: list[tuple[dict[str, Any], dict[str, Any], dict[str, str]]],
    outputs: list[dict[str, Any]],
    *,
    formal: bool,
    fidelity: str | None,
    reader_warning: bool,
) -> dict[str, Any]:
    covered_seats = {output["seat"] for output in outputs}
    dimensions: dict[str, dict[str, int | float | str] | None] = {
        "structure": None,
        "character": None,
        "prose": None,
        "resonance": None,
        "ai_cleanliness": None,
        "reader_experience": None,
        "fidelity": None,
    }
    available = formal and SCORING_SEATS.issubset(covered_seats)
    if not available:
        return {
            "available": False,
            "formula_version": SCORE_FORMULA_VERSION,
            "total": None,
            "grade": None,
            "originality_bonus": None,
            "reader_warning": reader_warning,
            "dimensions": dimensions,
        }

    for dimension, seat in LITERARY_DIMENSIONS.items():
        dimensions[dimension] = scored_dimension(seat, valid)

    slop_problems = sum(
        output["seat"] == "lit-slop"
        and is_problem(metadata["polarity"], criterion["verdict"])
        for output, criterion, metadata in valid
    )
    slop_penalty = min(10, slop_problems * 3)
    ai_score = normalized_score(100 - slop_penalty)
    dimensions["ai_cleanliness"] = {"score": ai_score, "grade": score_grade(ai_score)}

    reader_scores: list[int | float] = []
    for output in outputs:
        if output["seat"] != "lit-naive-reader":
            continue
        problems = sum(
            row_output is output
            and is_problem(metadata["polarity"], criterion["verdict"])
            for row_output, criterion, metadata in valid
        )
        reader_scores.append(normalized_score(85 - problems * 10))
    reader_score = normalized_score(sum(reader_scores) / len(reader_scores))
    dimensions["reader_experience"] = {
        "score": reader_score,
        "grade": score_grade(reader_score),
    }

    if fidelity in {"A", "B", "C"}:
        fidelity_score = {"A": 90, "B": 65, "C": 45}[fidelity]
        dimensions["fidelity"] = {
            "score": fidelity_score,
            "grade": score_grade(fidelity_score),
        }

    bonus = originality_bonus(valid)
    literary_scores = [
        dimensions[name]["score"]
        for name in LITERARY_DIMENSIONS
        if dimensions[name] is not None
    ]
    total = sum(literary_scores) / len(literary_scores) - slop_penalty + bonus
    if fidelity == "C":
        total = min(total, 45)
    elif fidelity == "B":
        total = min(total, 75)
    total_score = normalized_score(total)
    return {
        "available": True,
        "formula_version": SCORE_FORMULA_VERSION,
        "total": total_score,
        "grade": score_grade(total_score),
        "originality_bonus": bonus,
        "reader_warning": reader_warning,
        "dimensions": dimensions,
    }


def display_finding(item: dict[str, Any]) -> str:
    identity = item["seat"] + (f"@{item['reader_id']}" if item.get("reader_id") else "")
    return f"{identity} / {item['criterion_id']}：{item['reason']}"


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    host = report["execution"]["host"]
    lines = [
        "# lit-panel 评审报告",
        "",
        f"- run_id: `{report['run_id']}`",
        f"- 报告性质：{'正式评审' if report['formal'] else '诊断性结果（不得作为正式带位）'}",
        f"- 宿主：{host['name']} {host['version']}",
        f"- preset / genre / readers：{report['run']['preset']} / {report['run']['genre']} / {report['run']['readers']}",
        f"- 原生 subagents：{'是' if report['execution']['native_subagents'] else '否'}",
        f"- 降级执行：{'是' if report['execution']['degraded'] else '否'}",
        f"- 忠实带：{report['bands']['fidelity'] or '未形成'}",
        f"- 文学带：{report['bands']['literary'] or '未形成'}",
        f"- 决策建议：{report['recommendation']}",
        f"- 引文核验：通过 {report['verification']['verified']}，作废 {report['verification']['invalidated']}",
        "",
        "## 总分卡",
        "",
    ]
    scores = report["scores"]
    if scores["available"]:
        warning = " ⚠ 读者预警" if scores["reader_warning"] else ""
        lines.extend([
            f"**{scores['total']}/100 · {scores['grade']}{warning}**",
            "",
            "分数由判据向量机械导出，评审席不产生任何数字。",
            "",
            "## 多维评分",
            "",
            "| 维度 | 分数 | 等级 |",
            "|---|---:|---|",
        ])
        labels = {
            "fidelity": "忠实度",
            "structure": "结构",
            "character": "人物",
            "prose": "语言",
            "resonance": "情感",
            "ai_cleanliness": "AI 洁净度",
            "reader_experience": "读者体验",
        }
        for key in (
            "fidelity", "structure", "character", "prose", "resonance",
            "ai_cleanliness", "reader_experience",
        ):
            dimension = scores["dimensions"][key]
            if dimension is not None:
                lines.append(
                    f"| {labels[key]} | {dimension['score']} | {dimension['grade']} |"
                )
        lines.append(f"| 原创加分 | +{scores['originality_bonus']} | — |")
    else:
        lines.extend([
            "未形成：数值视图只在运行正式闭合且覆盖席 03/04/05/06/07/08/09 时生成。",
            "",
            "分数由判据向量机械导出，评审席不产生任何数字。",
        ])
    lines.extend(["", "## 覆盖与降级披露", ""])
    lines.extend([f"- {gap}" for gap in report["coverage_gaps"]] or ["- 无"])
    lines.extend(["", "### 跳过席位", ""])
    lines.extend(
        [
            f"- {item['number']} / {item['seat']}：{item['reason']}"
            + ("（警告）" if item["warning"] else "")
            for item in report["run"]["skipped_seats"]
        ]
        or ["- 无"]
    )
    lines.extend(["", "## 红线", ""])
    lines.extend([f"- {display_finding(item)}" for item in report["red_flags"]] or ["- 无"])
    lines.extend(["", "## 修订包", ""])
    lines.extend(
        [f"- [{item['severity']}] {display_finding(item)}" for item in report["revisions"]]
        or ["- 无"]
    )
    lines.extend(["", "## 人工仲裁", ""])
    lines.extend([f"- {display_finding(item)}" for item in report["arbitration"]] or ["- 无"])
    lines.extend(["", "## 分席自由观点", ""])
    for view in report["seat_views"]:
        identity = view["seat"] + (f"@{view['reader_id']}" if view["reader_id"] else "")
        lines.extend([f"### {identity}", "", view["free_view"] or "（未提供）", ""])
        if view["reader"] is not None:
            lines.extend(
                [
                    f"- 素读体验：{view['reader']['experience']}",
                    f"- 传播意愿：{view['reader']['willing_to_share']}",
                    "- 三必答：" + " / ".join(view["reader"]["required_answers"]),
                    "",
                ]
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def correlate_run(
    manifest: dict[str, Any],
    execution: dict[str, Any],
    outputs: list[dict[str, Any]],
) -> list[str]:
    gaps: list[str] = []
    expected = {
        (f"{item['seat']}@{item['reader_id']}" if item["reader_id"] else item["seat"]): item
        for item in manifest["expected_outputs"]
    }
    actual = {output_identity(output): output for output in outputs}
    if len(actual) != len(outputs):
        raise ContractError("席位输出身份重复")
    extra_outputs = sorted(set(actual) - set(expected))
    if extra_outputs:
        raise ContractError(f"出现运行清单未授权的席位输出: {extra_outputs}")
    for identity in sorted(set(expected) - set(actual)):
        gaps.append(f"缺少席位输出: {identity}")
    for identity in sorted(set(actual) & set(expected)):
        output = actual[identity]
        wanted = expected[identity]
        if output["phase"] != wanted["phase"]:
            raise ContractError(f"{identity} phase 与运行清单不一致")
        wanted_ids = set(wanted["criteria_ids"])
        actual_ids = {item["id"] for item in output["criteria"]}
        extra_ids = sorted(actual_ids - wanted_ids)
        if extra_ids:
            raise ContractError(f"{identity} 输出未授权判据: {extra_ids}")
        missing_ids = sorted(wanted_ids - actual_ids)
        if missing_ids:
            gaps.append(f"{identity} 缺少判据: {','.join(missing_ids)}")

    dispatches = {item["packet"]: item for item in execution["dispatches"]}
    extra_packets = sorted(set(dispatches) - set(manifest["packets"]))
    if extra_packets:
        raise ContractError(f"执行回执包含运行清单外 packet: {extra_packets}")
    for packet in sorted(set(manifest["packets"]) - set(dispatches)):
        gaps.append(f"缺少 packet 执行回执: {packet}")
    for item in manifest["expected_outputs"]:
        dispatch = dispatches.get(item["packet"])
        if dispatch is None:
            continue
        if dispatch["seat"] != item["seat"] or dispatch["reader_id"] != item["reader_id"]:
            raise ContractError(f"packet 身份与运行清单不一致: {item['packet']}")
        if dispatch["status"] != "completed":
            gaps.append(f"packet 执行失败: {item['packet']}")
        if not dispatch["isolated"]:
            gaps.append(f"packet 未使用隔离上下文: {item['packet']}")

    naive_receipts = {item["reader_id"]: item for item in execution["naive_readers"]}
    expected_readers = {
        item["reader_id"] for item in manifest["expected_outputs"] if item["reader_id"] is not None
    }
    extra_readers = sorted(set(naive_receipts) - expected_readers)
    if extra_readers:
        raise ContractError(f"执行回执包含未授权素读者: {extra_readers}")
    for reader_id in sorted(expected_readers - set(naive_receipts)):
        gaps.append(f"缺少素读者两步执行证明: {reader_id}")
    for reader_id in sorted(expected_readers & set(naive_receipts)):
        expected_item = next(
            item for item in manifest["expected_outputs"] if item["reader_id"] == reader_id
        )
        step2_packet = expected_item["packet"]
        step1_packet = step2_packet.replace("step-2.json", "step-1.json")
        step1_dispatch = dispatches.get(step1_packet)
        step2_dispatch = dispatches.get(step2_packet)
        proof = naive_receipts[reader_id]
        if step1_dispatch is None or step2_dispatch is None:
            continue
        if step1_dispatch["seat"] != "lit-naive-reader" or step1_dispatch["reader_id"] != reader_id:
            raise ContractError(f"{reader_id} Step 1 身份不一致")
        if proof["step_1_context_id"] != step1_dispatch["context_id"]:
            raise ContractError(f"{reader_id} Step 1 context 不一致")
        if proof["step_2_context_id"] != step2_dispatch["context_id"]:
            raise ContractError(f"{reader_id} Step 2 context 不一致")
        output = actual.get(f"lit-naive-reader@{reader_id}")
        if output is not None and proof["step_1_receipt_sha256"] != sha256_text(
            output["reader"]["experience"]
        ):
            raise ContractError(f"{reader_id} Step 1 体验哈希与最终输出不一致")
    return gaps


def main() -> int:
    parser = argparse.ArgumentParser(description="从闭合执行证据机械导出 lit-panel 报告")
    parser.add_argument("seat_outputs", type=Path)
    parser.add_argument("verification_receipt", type=Path)
    parser.add_argument("run_manifest", type=Path)
    parser.add_argument("execution_receipt", type=Path)
    parser.add_argument("criteria_dir", type=Path)
    parser.add_argument("--text", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--brief", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    args = parser.parse_args()

    try:
        records = [
            (path, validate_seat_output(read_json(path)))
            for path in iter_seat_output_paths(args.seat_outputs)
        ]
        outputs = [output for _, output in records]
        run_ids = {output["run_id"] for output in outputs}
        if len(run_ids) != 1:
            raise ContractError(f"席位输出 run_id 不一致: {sorted(run_ids)}")
        run_id = next(iter(run_ids))
        manifest = validate_run_manifest(read_json(args.run_manifest))
        execution = validate_execution_receipt(read_json(args.execution_receipt))
        if manifest["run_id"] != run_id or execution["run_id"] != run_id:
            raise ContractError("运行清单、执行回执与席位输出 run_id 不一致")
        if manifest["inputs"]["text_sha256"] != digest_path(args.text):
            raise ContractError("正文与运行清单摘要不一致")
        if manifest["inputs"]["source_sha256"] != digest_path(args.source):
            raise ContractError("来源与运行清单摘要不一致")
        if manifest["inputs"]["brief_sha256"] != digest_path(args.brief):
            raise ContractError("brief 与运行清单摘要不一致")
        receipt = validate_verification_receipt(
            read_json(args.verification_receipt), records, args.text, args.source
        )
        metadata = parse_criteria(args.criteria_dir)
        validate_canonical_run(
            manifest,
            execution,
            manifest_path=args.run_manifest,
            criteria_dir=args.criteria_dir,
            metadata=metadata,
            text=args.text,
            source=args.source,
            brief=args.brief,
        )
        mechanical_gaps = correlate_run(manifest, execution, outputs)
        if mechanical_gaps and not execution["coverage_gaps"]:
            raise ContractError(
                "运行产物存在未披露覆盖缺口: " + "; ".join(mechanical_gaps)
            )
    except (ContractError, OSError, UnicodeError, ValueError) as exc:
        print(f"DERIVE ERROR: {exc}", file=sys.stderr)
        return 2

    invalidated = set(receipt["invalidated_criteria"])
    valid: list[tuple[dict[str, Any], dict[str, Any], dict[str, str]]] = []
    arbitration: list[dict[str, Any]] = []
    try:
        for output in outputs:
            for criterion in output["criteria"]:
                key = criterion_key(output, criterion["id"])
                meta = metadata.get((output["seat"], criterion["id"]))
                if meta is None:
                    raise ContractError(f"未注册判据 {key}")
                validate_fidelity_semantics(output, criterion, meta)
                if key in invalidated:
                    item = finding(output, criterion)
                    item["reason"] = f"引文核验失败，判定作废：{criterion['note']}"
                    arbitration.append(item)
                    continue
                valid.append((output, criterion, meta))
                if criterion["verdict"] == "ABSTAIN" or (
                    criterion["verdict"] == "NA" and meta["tier"] == "veto"
                ):
                    arbitration.append(finding(output, criterion))

        problems = [row for row in valid if is_problem(row[2]["polarity"], row[1]["verdict"])]
        for output, criterion, _ in problems:
            if not isinstance(criterion.get("recommendation"), str) or not criterion["recommendation"]:
                raise ContractError(
                    f"问题判据必须给出 recommendation: {criterion_key(output, criterion['id'])}"
                )
    except ContractError as exc:
        print(f"DERIVE ERROR: {exc}", file=sys.stderr)
        return 2

    revisions = [finding(output, criterion) for output, criterion, _ in problems]
    revisions.sort(
        key=lambda item: (
            SEVERITY_ORDER[item["severity"]], item["seat"], item.get("reader_id") or "",
            item["criterion_id"],
        )
    )
    red_flags = [
        finding(output, criterion)
        for output, criterion, _ in problems
        if (
            output["seat"] == "lit-fidelity"
            and criterion["severity"] == "high"
            and criterion.get("fidelity_state") in {"CONTRADICTED", "UNSUPPORTED"}
        )
        or (output["seat"] == "lit-continuity" and criterion["severity"] == "high")
    ]
    arbitration.extend(
        finding(output, criterion)
        for output, criterion, criterion_metadata in problems
        if output["seat"] == "lit-ethics"
        or (criterion_metadata["tier"] == "veto" and criterion["severity"] in {"medium", "low"})
    )

    naive_unwilling_outputs = [
        output for output in outputs
        if output["seat"] == "lit-naive-reader"
        and output.get("reader", {}).get("willing_to_share") == "不愿意"
    ]
    for output in naive_unwilling_outputs:
        arbitration.append({
            "seat": output["seat"],
            "reader_id": output["reader_id"],
            "criterion_id": "SHARE",
            "severity": "none",
            "reason": "素读者明确表示不愿意把这篇讲给别人听",
            "recommendation": "人工复核传播意愿报警及其阅读体验",
        })

    unresolved_gaps = [
        f"未决判据不能形成正式带位: {criterion_key(output, criterion['id'])}"
        for output, criterion, meta in valid
        if criterion["verdict"] == "ABSTAIN"
        or (criterion["verdict"] == "NA" and meta["tier"] in {"veto", "core"})
    ]
    coverage_gaps = list(dict.fromkeys(
        execution["coverage_gaps"]
        + mechanical_gaps
        + unresolved_gaps
        + [f"引文作废导致判据覆盖缺口: {key}" for key in sorted(invalidated)]
        + [
            f"{item['number']} / {item['seat']}: {item['reason']}"
            for item in manifest["skipped_seats"] if item["warning"]
        ]
    ))
    formal = (
        execution["native_subagents"]
        and not execution["degraded"]
        and not coverage_gaps
    )
    covered_seats = {output["seat"] for output in outputs}
    if formal:
        fidelity: str | None = fidelity_band(valid)
        literary: str | None = literary_band(valid, covered_seats, bool(naive_unwilling_outputs))
        final_recommendation = recommendation(fidelity, literary)
    else:
        fidelity = None
        literary = None
        final_recommendation = "仅诊断"

    scores = derive_scores(
        valid,
        outputs,
        formal=formal,
        fidelity=fidelity,
        reader_warning=bool(naive_unwilling_outputs),
    )

    report = {
        "schema_version": "1.1",
        "run_id": run_id,
        "formal": formal,
        "run": {
            "preset": manifest["preset"],
            "genre": manifest["genre"],
            "readers": manifest["readers"],
            "cross_chapter_source": manifest["cross_chapter_source"],
            "selected_seats": manifest["selected_seats"],
            "skipped_seats": manifest["skipped_seats"],
        },
        "execution": {
            "host": execution["host"],
            "native_subagents": execution["native_subagents"],
            "degraded": execution["degraded"],
            "completed_dispatches": sum(
                item["status"] == "completed" for item in execution["dispatches"]
            ),
            "total_dispatches": len(execution["dispatches"]),
        },
        "coverage_gaps": coverage_gaps,
        "bands": {"fidelity": fidelity, "literary": literary},
        "scores": scores,
        "recommendation": final_recommendation,
        "red_flags": red_flags,
        "revisions": revisions,
        "arbitration": arbitration,
        "seat_views": [
            {
                "seat": output["seat"],
                "reader_id": output.get("reader_id"),
                "free_view": output["free_view"],
                "reader": output.get("reader"),
            }
            for output in sorted(outputs, key=output_identity)
        ],
        "verification": {
            "verified": int(receipt["summary"]["verified"]),
            "invalidated": int(receipt["summary"]["invalidated"]),
        },
    }
    write_json(args.output_json, report)
    write_markdown(args.output_markdown, report)
    print(
        f"REPORT: formal={str(formal).lower()} fidelity={fidelity or 'none'} "
        f"literary={literary or 'none'} recommendation={final_recommendation} "
        f"json={args.output_json} markdown={args.output_markdown}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
