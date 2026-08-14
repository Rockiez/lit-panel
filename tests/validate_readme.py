#!/usr/bin/env python3
"""Validate current, cross-language README runtime claims."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = ("README.md", "README.en.md", "README.fr.md", "README.es.md")
NAV = "[简体中文](README.md) | [English](README.en.md) | [Français](README.fr.md) | [Español](README.es.md)"

REQUIRED_LITERAL = (
    "0.5.0",
    "Codex",
    "0.147.0",
    "Claude Code",
    "2.1.63",
    "Antigravity",
    "1.1.12",
    "Agent Plugins",
    "lit-naive-reader",
    "A/B/C/N/A",
    "scripts/release_check.py",
)

FORBIDDEN = (
    "Version: 0.4.1",
    "version-0.4.1",
    "Claude Code Task",
    "independent Task tools",
    "Codex sequential path",
    "Codex 顺序路径",
    "Subagents` array",
    "derived score adjustments",
    "puntuaciones multidimensionales",
    "scores multidimensionnels",
)


def main() -> int:
    failures: list[str] = []
    for name in FILES:
        path = ROOT / name
        if not path.is_file():
            failures.append(f"missing {name}")
            continue
        content = path.read_text(encoding="utf-8")
        if content.splitlines()[0].strip() != NAV:
            failures.append(f"{name}: language navigation must be first line")
        for claim in REQUIRED_LITERAL:
            if claim not in content:
                failures.append(f"{name}: missing {claim!r}")
        for claim in FORBIDDEN:
            if claim in content:
                failures.append(f"{name}: stale claim {claim!r}")
        if "spawn_agent" not in content and "Agent tool" not in content and "invoke_subagent" not in content:
            failures.append(f"{name}: missing native-subagent execution disclosure")
        if "two-step" not in content and "两步" not in content and "deux étapes" not in content and "dos pasos" not in content:
            failures.append(f"{name}: missing seat 08 two-step disclosure")
    if failures:
        print("README VALIDATION FAILED", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("README VALIDATION PASSED: versions, native subagents, seat 08, qualitative output")
    return 0


if __name__ == "__main__":
    sys.exit(main())
