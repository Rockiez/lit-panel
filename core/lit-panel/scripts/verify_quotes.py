#!/usr/bin/env python3
"""Verify every structured quote and emit a machine-readable receipt."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lit_panel_common import (
    build_verification_receipt,
    ContractError,
    iter_seat_output_paths,
    read_json,
    validate_seat_output,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="逐字核验 lit-panel 席位 JSON 中的全部引文")
    parser.add_argument("seat_outputs", type=Path, help="单个席位 JSON 或包含多个 JSON 的目录")
    parser.add_argument("text", type=Path, help="已剥离元数据的被评正文")
    parser.add_argument("--source", type=Path, help="席 01 来源文件或目录")
    parser.add_argument("--output", type=Path, required=True, help="核验回执 JSON")
    args = parser.parse_args()

    try:
        records = [
            (path, validate_seat_output(read_json(path)))
            for path in iter_seat_output_paths(args.seat_outputs)
        ]
        receipt = build_verification_receipt(records, args.text, args.source)
    except (ContractError, OSError, UnicodeError, ValueError) as exc:
        print(f"VERIFY ERROR: {exc}", file=sys.stderr)
        return 2

    write_json(args.output, receipt)
    verified_count = receipt["summary"]["verified"]
    invalid_count = receipt["summary"]["invalidated"]
    print(
        f"RECEIPT: verified={verified_count} invalidated={invalid_count} "
        f"criteria_invalidated={len(receipt['invalidated_criteria'])} output={args.output}"
    )
    return 1 if receipt["invalidated_criteria"] else 0


if __name__ == "__main__":
    sys.exit(main())
