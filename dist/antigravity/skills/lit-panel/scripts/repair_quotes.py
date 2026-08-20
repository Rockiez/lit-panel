#!/usr/bin/env python3
"""Apply one auditable quote-only repair attempt and re-run Tier 1-5 verification."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from lit_panel_common import (
    ContractError,
    build_verification_receipt,
    digest_path,
    iter_seat_output_paths,
    output_identity,
    read_json,
    require,
    sha256_bytes,
    validate_seat_output,
    validate_verification_receipt,
    write_json,
)
from quote_repair import apply_quote_repair_patches, validate_quote_repair_patch


def iter_patch_paths(path: Path):
    if path.is_file():
        yield path
        return
    require(path.is_dir(), f"引文修复补丁路径不存在: {path}")
    files = sorted(path.glob("*.json"))
    require(bool(files), f"目录中没有引文修复补丁 JSON: {path}")
    yield from files


def stage_json(destination: Path, value) -> Path:
    """Write a complete sibling temp file without publishing the destination."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{destination.name}.staging-",
        dir=destination.parent,
    )
    os.close(descriptor)
    path = Path(temporary)
    write_json(path, value)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("seat_outputs", type=Path, help="原始席位 JSON 或目录")
    parser.add_argument("repair_patches", type=Path, help="引文修复补丁 JSON 或目录")
    parser.add_argument("initial_verification", type=Path, help="初次核验回执")
    parser.add_argument("text", type=Path, help="已剥离元数据的被评正文")
    parser.add_argument("--source", type=Path, help="席 01 来源文件或目录")
    parser.add_argument("--output-dir", type=Path, required=True, help="修复后的席位输出目录")
    parser.add_argument(
        "--verification-output", type=Path, required=True, help="重验回执 JSON"
    )
    parser.add_argument("--repair-receipt", type=Path, required=True, help="修复审计回执 JSON")
    args = parser.parse_args()

    staging: Path | None = None
    staged_files: list[Path] = []
    published: list[Path] = []
    try:
        require(not args.output_dir.exists(), f"输出目录已存在: {args.output_dir}")
        require(
            not args.verification_output.exists(),
            f"重验回执已存在: {args.verification_output}",
        )
        require(not args.repair_receipt.exists(), f"修复回执已存在: {args.repair_receipt}")

        records = [
            (path, validate_seat_output(read_json(path)))
            for path in iter_seat_output_paths(args.seat_outputs)
        ]
        initial_receipt = validate_verification_receipt(
            read_json(args.initial_verification),
            records,
            args.text,
            args.source,
        )
        patch_records = [
            (path, validate_quote_repair_patch(read_json(path)))
            for path in iter_patch_paths(args.repair_patches)
        ]
        repaired_records, repaired_criteria = apply_quote_repair_patches(
            records,
            patch_records,
            initial_receipt,
        )

        args.output_dir.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(
            tempfile.mkdtemp(
                prefix=f".{args.output_dir.name}.staging-",
                dir=args.output_dir.parent,
            )
        )
        staged_records = []
        for original_path, output in repaired_records:
            destination = staging / original_path.name
            require(not destination.exists(), f"席位输出文件名重复: {original_path.name}")
            write_json(destination, output)
            staged_records.append((destination, output))

        final_receipt = build_verification_receipt(staged_records, args.text, args.source)
        status = "repaired" if not final_receipt["invalidated_criteria"] else "failed"
        final_receipt_sha256 = sha256_bytes(
            (
                json.dumps(final_receipt, ensure_ascii=False, indent=2, sort_keys=False)
                + "\n"
            ).encode("utf-8")
        )
        repair_receipt = {
            "schema_version": "1.0",
            "run_id": initial_receipt["run_id"],
            "attempt": 1,
            "inputs": {
                "initial_verification_sha256": digest_path(args.initial_verification),
                "repair_patches": [
                    {
                        "seat": patch["seat"],
                        "reader_id": patch["reader_id"],
                        "sha256": digest_path(path),
                    }
                    for path, patch in sorted(
                        patch_records, key=lambda item: output_identity(item[1])
                    )
                ],
            },
            "repaired_criteria": repaired_criteria,
            "status": status,
            "remaining_invalidated_criteria": final_receipt["invalidated_criteria"],
            "outputs": {
                "seat_outputs": final_receipt["inputs"]["seat_outputs"],
                "verification_sha256": final_receipt_sha256,
            },
        }

        staged_verification = stage_json(args.verification_output, final_receipt)
        staged_files.append(staged_verification)
        staged_repair_receipt = stage_json(args.repair_receipt, repair_receipt)
        staged_files.append(staged_repair_receipt)

        os.replace(staged_verification, args.verification_output)
        staged_files.remove(staged_verification)
        published.append(args.verification_output)
        os.replace(staged_repair_receipt, args.repair_receipt)
        staged_files.remove(staged_repair_receipt)
        published.append(args.repair_receipt)
        os.replace(staging, args.output_dir)
        staging = None
        published.append(args.output_dir)
    except (ContractError, OSError, UnicodeError, ValueError) as exc:
        for path in reversed(published):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
        for path in staged_files:
            path.unlink(missing_ok=True)
        if staging is not None and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        print(f"REPAIR ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        f"REPAIR: status={status} repaired={len(repaired_criteria)} "
        f"remaining={len(final_receipt['invalidated_criteria'])} "
        f"outputs={args.output_dir} verification={args.verification_output} "
        f"receipt={args.repair_receipt}"
    )
    return 0 if status == "repaired" else 1


if __name__ == "__main__":
    sys.exit(main())
