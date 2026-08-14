#!/usr/bin/env python3
"""
E2E Multi-Language README Validation Suite for lit-panel repository.

Validates README.md, README.en.md, README.fr.md, and README.es.md across 4 Tiers:
- Tier 1: File Existence & Synchronized Navigation Header
- Tier 2: Structural & Heading Parity (1 H1, 11-12 H2, 9 H3, 11 seat IDs, 6 parameters, 16 fence markers, zero placeholders)
- Tier 3: Technical Terminology & CLI Preserved Syntax
- Tier 4: Relative Markdown Link & Path Reference Integrity
"""

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README_FILES = ["README.md", "README.en.md", "README.fr.md", "README.es.md"]

HEADER_NAV = "[简体中文](README.md) | [English](README.en.md) | [Français](README.fr.md) | [Español](README.es.md)"

SEAT_IDS = [
    "lit-fidelity",
    "lit-continuity",
    "lit-slop",
    "lit-structure",
    "lit-character",
    "lit-prose",
    "lit-resonance",
    "lit-naive-reader",
    "lit-originality",
    "lit-brief",
    "lit-ethics",
]

CLI_FLAGS = [
    "--preset",
    "--source",
    "--brief",
    "--stability",
    "--readers",
    "--fast-compare",
]

CLI_COMMANDS = [
    "/lit-review",
    "/lit-compare",
]

PRESET_NAMES = [
    "quick",
    "standard",
    "full",
    "custom",
]

FIVE_STATE_LABELS = [
    "SUPPORTED",
    "PERMISSIBLE_INFERENCE",
    "UNSUPPORTED",
    "CONTRADICTED",
    "UNVERIFIABLE",
]

PLACEHOLDER_PATTERNS = [
    r"\bTODO\b",
    r"\bTBD\b",
    r"\[TODO\]",
    r"<TODO>",
    r"\[TBD\]",
    r"<TBD>",
    r"PLACEHOLDER",
]


class TestReporter:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def log(self, tier: str, check_name: str, file_name: str, success: bool, detail: str = ""):
        status_str = "PASS" if success else "FAIL"
        if success:
            self.passed += 1
        else:
            self.failed += 1
        self.results.append((tier, check_name, file_name, success, detail))
        prefix = f"[{status_str}] [{tier}] {file_name} -> {check_name}"
        if detail:
            print(f"{prefix}: {detail}")
        else:
            print(prefix)


def strip_code_blocks(text: str) -> str:
    """Strips code fence blocks (```...```) to prevent code block comments from being counted as headings."""
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def test_tier_1(reporter: TestReporter):
    print("\n--- Running Tier 1 Checks: File Existence & Header Navigation ---")
    for file_name in README_FILES:
        file_path = REPO_ROOT / file_name
        # 1.1 File Existence
        if not file_path.exists():
            reporter.log("Tier 1", "File Existence", file_name, False, f"File missing at {file_path}")
            continue
        else:
            reporter.log("Tier 1", "File Existence", file_name, True)

        # 1.2 Header Navigation Switcher
        content = file_path.read_text(encoding="utf-8")
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        header_found = any(HEADER_NAV in line for line in lines[:15])
        if header_found:
            reporter.log("Tier 1", "Header Navigation", file_name, True)
        else:
            reporter.log("Tier 1", "Header Navigation", file_name, False, f"Header nav line not found in top 15 lines")


def test_tier_2(reporter: TestReporter):
    print("\n--- Running Tier 2 Checks: Structural & Heading Parity ---")
    for file_name in README_FILES:
        file_path = REPO_ROOT / file_name
        if not file_path.exists():
            reporter.log("Tier 2", "Structural Checks", file_name, False, "File missing")
            continue

        content = file_path.read_text(encoding="utf-8")
        content_no_code = strip_code_blocks(content)

        # 2.1 Heading Counts (1 H1, 11-12 H2, 9 H3 outside code blocks)
        h1_count = len(re.findall(r"^# ", content_no_code, re.MULTILINE))
        h2_count = len(re.findall(r"^## ", content_no_code, re.MULTILINE))
        h3_count = len(re.findall(r"^### ", content_no_code, re.MULTILINE))

        h1_ok = (h1_count == 1)
        h2_ok = (h2_count in (11, 12))
        h3_ok = (h3_count == 9)

        if h1_ok and h2_ok and h3_ok:
            reporter.log("Tier 2", "Heading Hierarchy Count", file_name, True, f"H1: {h1_count}, H2: {h2_count}, H3: {h3_count}")
        else:
            reporter.log("Tier 2", "Heading Hierarchy Count", file_name, False, f"Expected H1=1, H2=11-12, H3=9; Found H1={h1_count}, H2={h2_count}, H3={h3_count}")

        # 2.2 11 Seat Identifiers
        missing_seats = [seat for seat in SEAT_IDS if seat not in content]
        if not missing_seats:
            reporter.log("Tier 2", "Seat Identifiers (11 Seats)", file_name, True)
        else:
            reporter.log("Tier 2", "Seat Identifiers (11 Seats)", file_name, False, f"Missing seat IDs: {missing_seats}")

        # 2.3 Parameter Reference Table (6 Flags)
        missing_flags = [flag for flag in CLI_FLAGS if flag not in content]
        if not missing_flags:
            reporter.log("Tier 2", "Parameter Reference Flags (6 Flags)", file_name, True)
        else:
            reporter.log("Tier 2", "Parameter Reference Flags (6 Flags)", file_name, False, f"Missing parameter flags: {missing_flags}")

        # 2.4 Total Code Block Fence Markers (16 fence lines = 8 code blocks)
        fence_lines = len(re.findall(r"^```", content, re.MULTILINE))
        if fence_lines == 16:
            reporter.log("Tier 2", "Code Block Fence Markers (16 markers)", file_name, True)
        else:
            reporter.log("Tier 2", "Code Block Fence Markers (16 markers)", file_name, False, f"Expected 16 fence markers (8 blocks), found {fence_lines}")

        # 2.5 Zero Placeholder Tokens
        found_placeholders = []
        for pattern in PLACEHOLDER_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                found_placeholders.extend(matches)
        if not found_placeholders:
            reporter.log("Tier 2", "Zero Placeholder Tokens", file_name, True)
        else:
            reporter.log("Tier 2", "Zero Placeholder Tokens", file_name, False, f"Found placeholder tokens: {found_placeholders}")


def test_tier_3(reporter: TestReporter):
    print("\n--- Running Tier 3 Checks: Technical Terminology & Preserved Syntax ---")
    for file_name in README_FILES:
        file_path = REPO_ROOT / file_name
        if not file_path.exists():
            reporter.log("Tier 3", "Terminology Checks", file_name, False, "File missing")
            continue

        content = file_path.read_text(encoding="utf-8")

        # 3.1 Preserved Commands & Flags
        missing_commands = [cmd for cmd in CLI_COMMANDS if cmd not in content]
        if not missing_commands:
            reporter.log("Tier 3", "Preserved CLI Commands", file_name, True)
        else:
            reporter.log("Tier 3", "Preserved CLI Commands", file_name, False, f"Missing CLI commands: {missing_commands}")

        # 3.2 Preserved Presets
        missing_presets = [preset for preset in PRESET_NAMES if preset not in content]
        if not missing_presets:
            reporter.log("Tier 3", "Preserved Presets", file_name, True)
        else:
            reporter.log("Tier 3", "Preserved Presets", file_name, False, f"Missing preset names: {missing_presets}")

        # 3.3 Preserved 5-State Labels
        missing_labels = [label for label in FIVE_STATE_LABELS if label not in content]
        if not missing_labels:
            reporter.log("Tier 3", "Preserved 5-State Labels", file_name, True)
        else:
            reporter.log("Tier 3", "Preserved 5-State Labels", file_name, False, f"Missing 5-state labels: {missing_labels}")


def resolve_link_target(target: str) -> bool:
    """Helper to resolve link target against repo root or canonical reference directories."""
    target_clean = target.split("#")[0].strip()
    if not target_clean:
        return True  # Anchor link within same document

    if target_clean.startswith(("http://", "https://", "mailto:")):
        return True  # External URL

    # 1. Direct path check relative to repo root
    path_direct = REPO_ROOT / target_clean
    if path_direct.exists():
        return True

    # 2. Canonical reference directory fallback
    path_ref = REPO_ROOT / "skills" / "lit-panel" / "references" / target_clean
    if path_ref.exists():
        return True

    # 3. Handle optional user private files (e.g. criteria/99-private.md)
    if "99-private.md" in target_clean:
        return True

    return False


def test_tier_4(reporter: TestReporter):
    print("\n--- Running Tier 4 Checks: Relative Link & Path Reference Integrity ---")
    for file_name in README_FILES:
        file_path = REPO_ROOT / file_name
        if not file_path.exists():
            reporter.log("Tier 4", "Link Integrity", file_name, False, "File missing")
            continue

        content = file_path.read_text(encoding="utf-8")

        # 4.1 Markdown Hyperlinks Parsing: [text](target)
        markdown_links = re.findall(r"\[.*?\]\((.*?)\)", content)
        broken_links = []
        for target in markdown_links:
            if not resolve_link_target(target):
                broken_links.append(target)

        if not broken_links:
            reporter.log("Tier 4", "Markdown Link Resolution", file_name, True, f"Total links checked: {len(markdown_links)}")
        else:
            reporter.log("Tier 4", "Markdown Link Resolution", file_name, False, f"Broken relative links: {broken_links}")

        # 4.2 Explicit Key Path References Check
        key_paths = [
            "skills/lit-panel/SKILL.md",
            "docs/DESIGN.md",
            "scripts/install-codex.sh",
            ".claude-plugin/marketplace.json",
            "docs/criteria-pool.md",
            "LICENSE",
        ]
        missing_key_paths = []
        for kp in key_paths:
            if kp not in content and f"./{kp}" not in content:
                missing_key_paths.append(kp)

        if not missing_key_paths:
            reporter.log("Tier 4", "Key Repository Path References", file_name, True)
        else:
            reporter.log("Tier 4", "Key Repository Path References", file_name, False, f"Missing key path references in text: {missing_key_paths}")


def main():
    print("================================================================")
    print("  lit-panel README E2E Multi-Language Test Suite Execution")
    print("================================================================")

    reporter = TestReporter()

    test_tier_1(reporter)
    test_tier_2(reporter)
    test_tier_3(reporter)
    test_tier_4(reporter)

    print("\n================================================================")
    print("  TEST SUMMARY")
    print("================================================================")
    print(f"Total Checks Executed : {reporter.passed + reporter.failed}")
    print(f"Checks Passed        : {reporter.passed}")
    print(f"Checks Failed        : {reporter.failed}")
    print("----------------------------------------------------------------")

    if reporter.failed > 0:
        print("RESULT: FAIL (One or more validation checks failed)")
        sys.exit(1)
    else:
        print("RESULT: PASS (All multi-language README checks passed successfully!)")
        sys.exit(0)


if __name__ == "__main__":
    main()
