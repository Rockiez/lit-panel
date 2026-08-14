#!/usr/bin/env python3
"""Fail-closed release gates for manifests, distributions and privacy hygiene."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
HOSTS = ("codex", "claude", "antigravity")
AGENT_PLUGIN_KEYS = {
    "$schema", "name", "version", "description", "author", "homepage",
    "repository", "license", "keywords", "extensions",
}
FORBIDDEN_RUNTIME_CLAIMS = (
    "Codex 没有并行 subagent",
    "Codex 顺序路径",
    "语义等价的顺序模拟",
    "单个 tool call 中通过 `Subagents` 数组",
    "使用 Task 工具派发",
    "Claude Code Task",
    "independent Task tools",
)


def fail(message: str) -> None:
    raise ValueError(message)


def read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"JSON 无效: {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"JSON root 必须是 object: {path}")
    return value


def check_generated_copies() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/build_dist.py", "--check"],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        fail(f"dist/root mirror 已过期: {detail}")


def check_agent_plugin_manifest() -> None:
    manifest = read_json(ROOT / "plugin.json")
    if manifest.get("$schema") != "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json":
        fail("plugin.json 未声明 Agent Plugins 1.0.0 schema")
    if not manifest.get("name"):
        fail("plugin.json 缺少 name")
    unknown = set(manifest) - AGENT_PLUGIN_KEYS
    if unknown:
        fail(f"Agent Plugin manifest 含非标准顶层字段: {sorted(unknown)}")
    extension = manifest.get("extensions", {}).get("com.anamnese.lit-panel", {})
    expected = {
        "codex": ">=0.147.0",
        "claude-code": ">=2.1.63",
        "antigravity-cli": ">=1.1.12",
    }
    if extension.get("supportedHosts") != expected:
        fail("最低宿主版本矩阵缺失或漂移")
    if extension.get("requiresNativeSubagents") is not True:
        fail("manifest 必须声明 native subagent 闸门")


def check_versions() -> None:
    expected = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    paths = (
        ROOT / "plugin.json",
        ROOT / ".codex-plugin" / "plugin.json",
        ROOT / ".claude-plugin" / "plugin.json",
        ROOT / "adapters" / "codex" / ".codex-plugin" / "plugin.json",
        ROOT / "adapters" / "claude" / ".claude-plugin" / "plugin.json",
        DIST / "codex" / "plugin.json",
        DIST / "codex" / ".codex-plugin" / "plugin.json",
        DIST / "claude" / ".claude-plugin" / "plugin.json",
    )
    for path in paths:
        if read_json(path).get("version") != expected:
            fail(f"版本不一致: {path}")


def check_self_contained() -> None:
    required = (
        "SKILL.md",
        "agents",
        "references/registry.md",
        "references/report-template.md",
        "schema/seat-output.schema.json",
        "schema/run-manifest.schema.json",
        "schema/execution-receipt.schema.json",
        "schema/verification-receipt.schema.json",
        "schema/derived-report.schema.json",
        "scripts/validate_seat_output.py",
        "scripts/validate_execution_receipt.py",
        "scripts/verify_quotes.py",
        "scripts/derive_report.py",
        "scripts/prepare_run.py",
    )
    for host in HOSTS:
        skill = DIST / host / "skills" / "lit-panel"
        for relative in required:
            if not (skill / relative).exists():
                fail(f"{host} 分发包缺少 {relative}")
    if len(list((DIST / "codex" / ".codex" / "agents").glob("*.toml"))) != 11:
        fail("Codex adapter 未生成 11 个 Agent TOML")
    if len(list((DIST / "claude" / "agents").glob("*.md"))) != 11:
        fail("Claude adapter 未携带 11 个 Agent")
    if len(list((DIST / "antigravity" / "agents").glob("*.md"))) != 11:
        fail("Antigravity adapter 未携带 11 个 Agent")


def check_privacy() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "tests/fixtures", "tests/runs"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    if tracked:
        fail(f"真实/运行 fixture 被 Git 跟踪: {tracked}")
    for path in DIST.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(DIST)
        if "fixtures" in relative.parts or "runs" in relative.parts:
            fail(f"分发包包含 fixture/run: {relative}")
        if path.suffix.lower() not in {".md", ".json", ".py", ".toml", ".txt"}:
            continue
        content = path.read_text(encoding="utf-8")
        if "/Users/" in content or "tests/fixtures/" in content or "tests/runs/" in content:
            fail(f"分发包泄漏机器路径或运行数据指针: {relative}")
        for claim in FORBIDDEN_RUNTIME_CLAIMS:
            if claim in content:
                fail(f"分发包含过时运行事实 {claim!r}: {relative}")


def main() -> int:
    try:
        check_generated_copies()
        check_agent_plugin_manifest()
        check_versions()
        check_self_contained()
        check_privacy()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"RELEASE CHECK FAILED: {exc}", file=sys.stderr)
        return 1
    print("RELEASE CHECK PASSED: manifests, versions, self-contained assets, privacy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
