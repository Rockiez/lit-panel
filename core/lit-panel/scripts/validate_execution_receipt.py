#!/usr/bin/env python3
"""Validate a lit-panel host execution receipt without third-party dependencies."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lit_panel_common import ContractError, read_json, validate_execution_receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 lit-panel 执行回执")
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    try:
        receipt = validate_execution_receipt(read_json(args.receipt))
    except ContractError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print(
        f"VALID: host={receipt['host']['name']} native={str(receipt['native_subagents']).lower()} "
        f"degraded={str(receipt['degraded']).lower()} dispatches={len(receipt['dispatches'])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
