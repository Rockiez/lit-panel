#!/usr/bin/env python3
"""Build deterministic, self-contained distributions for all supported hosts."""

from __future__ import annotations

import argparse
import filecmp
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "core" / "lit-panel"
ADAPTERS = ROOT / "adapters"
DIST = ROOT / "dist"


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def split_agent(path: Path) -> tuple[dict[str, str], str]:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        raise ValueError(f"agent 缺少 frontmatter: {path}")
    _, frontmatter, body = content.split("---\n", 2)
    meta: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    for key in ("name", "description"):
        if not meta.get(key):
            raise ValueError(f"agent frontmatter 缺少 {key}: {path}")
    return meta, body.lstrip()


def generate_codex_agents(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for path in sorted((CORE / "agents").glob("*.md")):
        meta, body = split_agent(path)
        content = "\n".join(
            [
                f"name = {json.dumps(meta['name'], ensure_ascii=False)}",
                f"description = {json.dumps(meta['description'], ensure_ascii=False)}",
                f"developer_instructions = {json.dumps(body, ensure_ascii=False)}",
                'sandbox_mode = "read-only"',
                "",
            ]
        )
        target = destination / f"{meta['name']}.toml"
        target.write_text(content, encoding="utf-8")


def generate_antigravity_agents(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for path in sorted((CORE / "agents").glob("*.md")):
        meta, body = split_agent(path)
        frontmatter = "\n".join(
            [
                "---",
                f"name: {meta['name']}",
                f"description: {json.dumps(meta['description'], ensure_ascii=False)}",
                "tools: []",
                "mainAgent: false",
                "subagent: true",
                "model: inherit",
                "---",
                "",
            ]
        )
        (destination / path.name).write_text(frontmatter + body, encoding="utf-8")


def make_executable_scripts(skill_root: Path) -> None:
    for path in (skill_root / "scripts").glob("*.py"):
        path.chmod(0o755)


def build_into(destination: Path) -> None:
    codex = destination / "codex"
    shutil.copytree(CORE, codex / "skills" / "lit-panel", dirs_exist_ok=True)
    shutil.copytree(
        ADAPTERS / "codex" / ".codex-plugin", codex / ".codex-plugin", dirs_exist_ok=True
    )
    shutil.copy2(ROOT / "plugin.json", codex / "plugin.json")
    shutil.copy2(ADAPTERS / "codex" / "README.md", codex / "README.md")
    codex_marketplace = load_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    codex_marketplace["plugins"][0]["source"]["path"] = "./"
    write_json(codex / ".agents" / "plugins" / "marketplace.json", codex_marketplace)
    generate_codex_agents(codex / ".codex" / "agents")
    make_executable_scripts(codex / "skills" / "lit-panel")

    claude = destination / "claude"
    shutil.copytree(CORE, claude / "skills" / "lit-panel", dirs_exist_ok=True)
    shutil.copytree(CORE / "agents", claude / "agents", dirs_exist_ok=True)
    shutil.copytree(ROOT / "commands", claude / "commands", dirs_exist_ok=True)
    shutil.copytree(
        ADAPTERS / "claude" / ".claude-plugin", claude / ".claude-plugin", dirs_exist_ok=True
    )
    claude_marketplace = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    claude_marketplace["plugins"][0]["source"] = "./"
    write_json(
        claude / ".claude-plugin" / "marketplace.json",
        claude_marketplace,
    )
    make_executable_scripts(claude / "skills" / "lit-panel")

    antigravity = destination / "antigravity"
    shutil.copytree(CORE, antigravity / "skills" / "lit-panel", dirs_exist_ok=True)
    shutil.copy2(ADAPTERS / "antigravity" / "plugin.json", antigravity / "plugin.json")
    shutil.copy2(ADAPTERS / "antigravity" / "README.md", antigravity / "README.md")
    generate_antigravity_agents(antigravity / "agents")
    make_executable_scripts(antigravity / "skills" / "lit-panel")


def same_tree(left: Path, right: Path) -> bool:
    comparison = filecmp.dircmp(left, right)
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        return False
    for name in comparison.common_files:
        left_file = left / name
        right_file = right / name
        if not filecmp.cmp(left_file, right_file, shallow=False):
            return False
        if stat.S_IMODE(left_file.stat().st_mode) != stat.S_IMODE(right_file.stat().st_mode):
            return False
    return all(same_tree(left / name, right / name) for name in comparison.common_dirs)


def _move_tree(source: Path, destination: Path) -> None:
    """Rename a directory on the same filesystem."""
    os.replace(source, destination)


def replace_tree(candidate: Path, destination: Path) -> None:
    """Swap a completed sibling tree into place and restore the old tree on failure."""
    backup: Path | None = None
    if destination.exists():
        backup = Path(
            tempfile.mkdtemp(
                prefix=f".{destination.name}.backup-",
                dir=destination.parent,
            )
        )
        backup.rmdir()
        _move_tree(destination, backup)

    try:
        _move_tree(candidate, destination)
    except OSError as swap_error:
        if backup is not None:
            try:
                _move_tree(backup, destination)
            except OSError as restore_error:
                raise OSError(
                    f"分发包替换失败，旧产物保留在 {backup}；"
                    f"替换错误: {swap_error}；恢复错误: {restore_error}"
                ) from swap_error
        raise

    if backup is not None:
        try:
            shutil.rmtree(backup)
        except OSError as exc:
            print(f"BUILD WARNING: 旧分发包备份未能清理: {backup}: {exc}", file=sys.stderr)


def sync_tree(source: Path, destination: Path) -> None:
    """Copy a source tree completely before swapping a stale destination."""
    if destination.exists() and same_tree(source, destination):
        return
    with tempfile.TemporaryDirectory(
        prefix=f".{destination.name}.staging-",
        dir=destination.parent,
    ) as temporary:
        candidate = Path(temporary)
        shutil.copytree(source, candidate, dirs_exist_ok=True)
        replace_tree(candidate, destination)


def sync_root_compatibility() -> None:
    for source, destination in (
        (CORE, ROOT / "skills" / "lit-panel"),
        (CORE / "agents", ROOT / "agents"),
        (ADAPTERS / "codex" / ".codex-plugin", ROOT / ".codex-plugin"),
    ):
        sync_tree(source, destination)
    (ROOT / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        ADAPTERS / "claude" / ".claude-plugin" / "plugin.json",
        ROOT / ".claude-plugin" / "plugin.json",
    )
    make_executable_scripts(ROOT / "skills" / "lit-panel")


def validate_versions() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    manifests = [
        ROOT / "plugin.json",
        ADAPTERS / "codex" / ".codex-plugin" / "plugin.json",
        ADAPTERS / "claude" / ".claude-plugin" / "plugin.json",
        ROOT / ".claude-plugin" / "marketplace.json",
    ]
    for manifest in manifests:
        data = load_json(manifest)
        found = data.get("version") or data.get("metadata", {}).get("version")
        if found != version:
            raise ValueError(f"版本不一致: {manifest}={found}, VERSION={version}")
    if load_json(ROOT / "plugin.json").get("$schema") != "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json":
        raise ValueError("root plugin.json 不是 Agent Plugins 1.0.0 manifest")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只检查 dist 与源码是否同步")
    args = parser.parse_args()
    try:
        validate_versions()
        with tempfile.TemporaryDirectory(prefix=".dist.staging-", dir=DIST.parent) as temporary:
            candidate = Path(temporary)
            build_into(candidate)
            candidate.chmod((DIST.stat().st_mode & 0o777) if DIST.is_dir() else 0o755)
            if args.check:
                if not DIST.exists() or not same_tree(candidate, DIST):
                    print("DIST OUT OF DATE: 请运行 scripts/build_dist.py", file=sys.stderr)
                    return 1
                compatibility_pairs = (
                    (CORE, ROOT / "skills" / "lit-panel"),
                    (CORE / "agents", ROOT / "agents"),
                    (ADAPTERS / "codex" / ".codex-plugin", ROOT / ".codex-plugin"),
                )
                if any(not destination.exists() or not same_tree(source, destination) for source, destination in compatibility_pairs):
                    print("ROOT COMPATIBILITY COPY OUT OF DATE: 请运行 scripts/build_dist.py", file=sys.stderr)
                    return 1
                claude_source = ADAPTERS / "claude" / ".claude-plugin" / "plugin.json"
                claude_destination = ROOT / ".claude-plugin" / "plugin.json"
                if not claude_destination.is_file() or not filecmp.cmp(
                    claude_source, claude_destination, shallow=False
                ):
                    print("ROOT COMPATIBILITY COPY OUT OF DATE: 请运行 scripts/build_dist.py", file=sys.stderr)
                    return 1
                print("DIST CURRENT: codex, claude, antigravity")
                return 0
            if not DIST.exists() or not same_tree(candidate, DIST):
                replace_tree(candidate, DIST)
        sync_root_compatibility()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"BUILD ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"BUILT: {DIST}/{{codex,claude,antigravity}}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
