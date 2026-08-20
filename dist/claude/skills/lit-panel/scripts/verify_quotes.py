#!/usr/bin/env python3
"""Verify every structured quote and emit a machine-readable receipt."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from lit_panel_common import (
    build_verification_receipt,
    ContractError,
    iter_seat_output_paths,
    read_json,
    require,
    validate_seat_output,
    write_json,
)
from quote_repair import build_quote_repair_request


def publish_json_artifacts(artifacts: list[tuple[Path, Any]]) -> None:
    """Publish a fresh set of JSON artifacts together or leave none behind."""
    destinations = [path for path, _ in artifacts]
    require(len(destinations) == len(set(destinations)), "输出 JSON 路径重复")
    for destination in destinations:
        require(not destination.exists(), f"输出 JSON 已存在: {destination}")

    staged: list[tuple[Path, Path]] = []
    published: list[Path] = []
    try:
        for destination, value in artifacts:
            destination.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(
                prefix=f".{destination.name}.staging-",
                dir=destination.parent,
            )
            os.close(descriptor)
            temporary_path = Path(temporary)
            write_json(temporary_path, value)
            staged.append((temporary_path, destination))
        for temporary_path, destination in staged:
            os.replace(temporary_path, destination)
            published.append(destination)
    except (OSError, UnicodeError, ValueError):
        for destination in reversed(published):
            destination.unlink(missing_ok=True)
        for temporary_path, _ in staged:
            temporary_path.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="逐字核验 lit-panel 席位 JSON 中的全部引文")
    parser.add_argument("seat_outputs", type=Path, help="单个席位 JSON 或包含多个 JSON 的目录")
    parser.add_argument("text", type=Path, help="已剥离元数据的被评正文")
    parser.add_argument("--source", type=Path, help="席 01 来源文件或目录")
    parser.add_argument("--output", type=Path, required=True, help="核验回执 JSON")
    parser.add_argument(
        "--repair-request",
        type=Path,
        help="写出一次性、仅允许替换 quotes 的重取请求 JSON",
    )
    args = parser.parse_args()

    try:
        records = [
            (path, validate_seat_output(read_json(path)))
            for path in iter_seat_output_paths(args.seat_outputs)
        ]
        receipt = build_verification_receipt(records, args.text, args.source)
        repair_request = build_quote_repair_request(records, receipt)
        artifacts = [(args.output, receipt)]
        if args.repair_request is not None:
            artifacts.append((args.repair_request, repair_request))
        publish_json_artifacts(artifacts)
    except (ContractError, OSError, UnicodeError, ValueError) as exc:
        print(f"VERIFY ERROR: {exc}", file=sys.stderr)
        return 2
    verified_count = receipt["summary"]["verified"]
    invalid_count = receipt["summary"]["invalidated"]
    print(
        f"RECEIPT: verified={verified_count} invalidated={invalid_count} "
        f"criteria_invalidated={len(receipt['invalidated_criteria'])} output={args.output}"
        + (
            f" repair_request={args.repair_request}"
            if args.repair_request is not None
            else ""
        )
    )
    return 1 if receipt["invalidated_criteria"] else 0


if __name__ == "__main__":
    sys.exit(main())
