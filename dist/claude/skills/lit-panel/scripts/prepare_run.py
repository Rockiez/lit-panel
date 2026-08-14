#!/usr/bin/env python3
"""Create isolated per-seat dispatch packets and a closed run manifest."""

from __future__ import annotations

import argparse
import re
import sys
import uuid
from pathlib import Path

from lit_panel_common import ContractError, digest_path, parse_criteria, write_json

PRESETS = {
    "quick": ["01", "02", "03", "08"],
    "standard": [f"{number:02d}" for number in range(1, 10)] + ["11"],
    "full": [f"{number:02d}" for number in range(1, 12)],
}
NAIVE_STEP_1_PROMPT = (
    "请以普通读者身份首读正文，只输出自然体验原文；不要读取判据、其他席位输出，"
    "也不要使用评审术语。执行器必须保存该 UTF-8 原文的 SHA-256。"
)
STEP_1_RECEIPT_CONTRACT = {
    "format": "utf-8-text",
    "required": True,
    "sha256_algorithm": "sha256",
    "output_field": "reader.experience",
}


def parse_registry(path: Path) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not re.match(r"^\|\s*\d{2}\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        number, agent_file, agent_name, criteria_file = cells[:4]
        result[number] = {
            "agent_file": agent_file,
            "agent_name": agent_name,
            "criteria_file": criteria_file,
        }
    if len(result) != 11:
        raise ContractError(f"注册表应有 11 席，实际 {len(result)}")
    return result


def parse_preset(value: str, registry: dict[str, dict[str, str]]) -> tuple[list[str], bool]:
    if value in PRESETS:
        return list(PRESETS[value]), False
    match = re.fullmatch(r"custom\(([^)]+)\)", value)
    if match is None:
        raise ContractError(f"未知 preset: {value}")
    seats = [part.strip() for part in match.group(1).split(",") if part.strip()]
    if len(seats) != len(set(seats)):
        raise ContractError("custom 席位不得重复")
    unknown = sorted(set(seats) - set(registry))
    if unknown:
        raise ContractError(f"custom 包含未注册席位: {unknown}")
    return seats, True


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是正整数") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("必须是正整数")
    return parsed


def has_cross_chapter_source(path: Path | None) -> bool:
    return path is not None and path.is_dir() and sum(
        1 for candidate in path.rglob("*") if candidate.is_file()
    ) >= 2


def expected_criteria(
    criteria: dict[tuple[str, str], dict[str, str]],
    seat: str,
    cross_chapter_source: bool,
) -> list[str]:
    ids = [criterion_id for (criterion_seat, criterion_id) in criteria if criterion_seat == seat]
    if seat == "lit-slop" and not cross_chapter_source:
        ids = [criterion_id for criterion_id in ids if criterion_id != "A7"]
    if not ids:
        raise ContractError(f"席位没有注册判据: {seat}")
    return ids


def plan_run(
    registry: dict[str, dict[str, str]],
    criteria: dict[tuple[str, str], dict[str, str]],
    *,
    preset: str,
    genre: str,
    readers: int,
    source_provided: bool,
    brief_provided: bool,
    cross_chapter_source: bool,
) -> dict[str, object]:
    """Return the canonical seat/output/packet layout for one run."""
    requested, is_custom = parse_preset(preset, registry)
    if genre == "memoir" and not is_custom and "11" not in requested:
        requested.append("11")
    if brief_provided and not is_custom and preset in {"standard", "full"}:
        if "10" not in requested:
            requested.append("10")

    selected: list[str] = []
    skipped: list[dict[str, object]] = []
    for number in sorted(registry):
        seat = registry[number]
        if number not in requested:
            warning = number == "11" and genre == "memoir" and is_custom
            reason = (
                "custom 显式排除回忆录默认伦理席，正式报告将披露覆盖缺口"
                if warning
                else "当前 preset 未选择"
            )
            skipped.append({
                "number": number,
                "seat": seat["agent_name"],
                "reason": reason,
                "warning": warning,
            })
            continue
        if number == "01" and not source_provided:
            skipped.append({
                "number": number,
                "seat": seat["agent_name"],
                "reason": "未提供 --source，忠实席按条件跳过",
                "warning": preset == "full",
            })
            continue
        if number == "10" and not brief_provided:
            skipped.append({
                "number": number,
                "seat": seat["agent_name"],
                "reason": "未提供 --brief，编辑意图席按条件跳过",
                "warning": preset == "full",
            })
            continue
        selected.append(number)

    expected_outputs: list[dict[str, object]] = []
    packets: list[str] = []
    for number in selected:
        seat_name = registry[number]["agent_name"]
        criteria_ids = expected_criteria(criteria, seat_name, cross_chapter_source)
        if number == "08":
            for reader_number in range(1, readers + 1):
                reader_id = f"reader-{reader_number:02d}"
                if readers == 1:
                    step1_name = "08-step-1.json"
                    step2_name = "08-step-2.json"
                else:
                    step1_name = f"08-{reader_id}-step-1.json"
                    step2_name = f"08-{reader_id}-step-2.json"
                packets.extend([step1_name, step2_name])
                expected_outputs.append({
                    "packet": step2_name,
                    "seat": seat_name,
                    "reader_id": reader_id,
                    "phase": "naive-reader-step-2",
                    "criteria_ids": criteria_ids,
                })
            continue
        packet_name = f"{number}.json"
        packets.append(packet_name)
        expected_outputs.append({
            "packet": packet_name,
            "seat": seat_name,
            "reader_id": None,
            "phase": "review",
            "criteria_ids": criteria_ids,
        })
    return {
        "selected_seats": selected,
        "skipped_seats": skipped,
        "expected_outputs": expected_outputs,
        "packets": sorted(packets),
    }


def build_packet_payloads(
    plan: dict[str, object],
    registry: dict[str, dict[str, str]],
    *,
    run_id: str,
    skill_root: Path,
    text_path: Path,
    source: Path | None,
    brief: Path | None,
) -> dict[str, dict[str, object]]:
    """Build the canonical JSON payload for every packet in a planned run."""
    seat_numbers = {item["agent_name"]: number for number, item in registry.items()}
    result: dict[str, dict[str, object]] = {}
    for expected in plan["expected_outputs"]:
        seat_name = expected["seat"]
        number = seat_numbers[seat_name]
        criteria_ids = expected["criteria_ids"]
        if expected["reader_id"] is not None:
            reader_id = expected["reader_id"]
            step2_name = expected["packet"]
            step1_name = step2_name.replace("step-2.json", "step-1.json")
            result[step1_name] = {
                "run_id": run_id,
                "seat": seat_name,
                "reader_id": reader_id,
                "phase": "naive-reader-step-1",
                "text_path": str(text_path),
                "prompt": NAIVE_STEP_1_PROMPT,
            }
            result[step2_name] = {
                "run_id": run_id,
                "seat": seat_name,
                "reader_id": reader_id,
                "phase": "naive-reader-step-2",
                "text_path": str(text_path),
                "criteria_path": str(
                    skill_root / "references" / registry[number]["criteria_file"]
                ),
                "active_criteria_ids": criteria_ids,
                "contract_path": str(skill_root / "schema" / "seat-output.schema.json"),
                "depends_on": step1_name,
                "step_1_receipt_contract": STEP_1_RECEIPT_CONTRACT,
            }
            continue

        packet: dict[str, object] = {
            "run_id": run_id,
            "seat": seat_name,
            "phase": "review",
            "text_path": str(text_path),
            "persona_path": str(skill_root / "agents" / registry[number]["agent_file"]),
            "criteria_path": str(
                skill_root / "references" / registry[number]["criteria_file"]
            ),
            "active_criteria_ids": criteria_ids,
            "contract_path": str(skill_root / "schema" / "seat-output.schema.json"),
        }
        if number == "01" and source is not None:
            packet["source_path"] = str(source.resolve())
        if number == "10" and brief is not None:
            packet["brief_path"] = str(brief.resolve())
        if number == "03":
            packet["slop_patterns_path"] = str(
                skill_root / "references" / "slop-patterns-zh.md"
            )
        result[expected["packet"]] = packet
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="生成互盲 lit-panel 席位派发包")
    parser.add_argument("text", type=Path)
    parser.add_argument("--preset", default="standard")
    parser.add_argument("--genre", choices=("memoir", "other"), default="memoir")
    parser.add_argument("--readers", type=positive_int, default=1)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--brief", type=Path)
    parser.add_argument("--run-id", default=f"run-{uuid.uuid4().hex[:12]}")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parent.parent
    try:
        if args.output.exists() and (not args.output.is_dir() or any(args.output.iterdir())):
            raise ContractError(f"输出目录必须不存在或为空: {args.output}")
        registry = parse_registry(skill_root / "references" / "registry.md")
        text = args.text.read_text(encoding="utf-8")
        text_digest = digest_path(args.text)
        source_digest = digest_path(args.source)
        brief_digest = digest_path(args.brief)
        cross_chapter = has_cross_chapter_source(args.source)
        criteria = parse_criteria(skill_root / "references" / "criteria")
        plan = plan_run(
            registry,
            criteria,
            preset=args.preset,
            genre=args.genre,
            readers=args.readers,
            source_provided=args.source is not None,
            brief_provided=args.brief is not None,
            cross_chapter_source=cross_chapter,
        )
    except (ContractError, OSError, UnicodeError) as exc:
        print(f"PREPARE ERROR: {exc}", file=sys.stderr)
        return 2

    selected = plan["selected_seats"]
    skipped = plan["skipped_seats"]

    try:
        args.output.mkdir(parents=True, exist_ok=True)
        text_path = (args.output / "text.txt").resolve()
        text_path.write_text(text, encoding="utf-8")
        packets_dir = args.output / "packets"
        packets_dir.mkdir()
        expected_outputs = plan["expected_outputs"]
        payloads = build_packet_payloads(
            plan,
            registry,
            run_id=args.run_id,
            skill_root=skill_root,
            text_path=text_path,
            source=args.source,
            brief=args.brief,
        )
        for packet_name, packet in payloads.items():
            write_json(packets_dir / packet_name, packet)

        packets = [path.name for path in sorted(packets_dir.glob("*.json"))]
        if expected_outputs != plan["expected_outputs"] or packets != plan["packets"]:
            raise ContractError("内部错误：实际派发包与 canonical 运行计划不一致")
        manifest = {
            "schema_version": "1.0",
            "run_id": args.run_id,
            "preset": args.preset,
            "genre": args.genre,
            "readers": args.readers,
            "inputs": {
                "text_sha256": text_digest,
                "source_sha256": source_digest,
                "brief_sha256": brief_digest,
            },
            "cross_chapter_source": cross_chapter,
            "selected_seats": selected,
            "skipped_seats": skipped,
            "expected_outputs": expected_outputs,
            "packets": packets,
        }
        write_json(args.output / "run.json", manifest)
    except (ContractError, OSError, UnicodeError) as exc:
        print(f"PREPARE ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        f"RUN: {args.run_id} seats={','.join(selected)} readers={args.readers} "
        f"output={args.output}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
