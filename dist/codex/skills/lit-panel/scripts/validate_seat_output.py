#!/usr/bin/env python3
"""Validate one lit-panel seat result against the frozen runtime contract."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lit_panel_common import ContractError, read_json, validate_seat_output


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 lit-panel 席位 JSON 输出")
    parser.add_argument("seat_output", type=Path)
    parser.add_argument("--expected-seat")
    args = parser.parse_args()
    try:
        data = validate_seat_output(read_json(args.seat_output), args.expected_seat)
    except ContractError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print(f"VALID: {data['seat']} ({len(data['criteria'])} criteria)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
