from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent


def load_script_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DistributionSwapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.build_dist = load_script_module("lit_panel_build_dist_test", "scripts/build_dist.py")

    def test_completed_candidate_replaces_old_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "dist"
            candidate = root / ".dist.staging-test"
            destination.mkdir()
            candidate.mkdir()
            (destination / "marker").write_text("old", encoding="utf-8")
            (candidate / "marker").write_text("new", encoding="utf-8")

            self.build_dist.replace_tree(candidate, destination)

            self.assertEqual((destination / "marker").read_text(encoding="utf-8"), "new")
            self.assertFalse(candidate.exists())
            self.assertEqual(list(root.glob(".dist.backup-*")), [])

    def test_tree_comparison_detects_executable_mode_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            left = root / "left"
            right = root / "right"
            left.mkdir()
            right.mkdir()
            (left / "runner.py").write_text("print('ok')\n", encoding="utf-8")
            (right / "runner.py").write_text("print('ok')\n", encoding="utf-8")
            (left / "runner.py").chmod(0o755)
            (right / "runner.py").chmod(0o644)

            self.assertFalse(self.build_dist.same_tree(left, right))

    def test_failed_candidate_swap_restores_last_known_good_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "dist"
            candidate = root / ".dist.staging-test"
            destination.mkdir()
            candidate.mkdir()
            (destination / "marker").write_text("old", encoding="utf-8")
            (candidate / "marker").write_text("new", encoding="utf-8")
            real_move = self.build_dist._move_tree
            call_count = 0

            def fail_candidate_move(source: Path, target: Path) -> None:
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise OSError("injected swap failure")
                real_move(source, target)

            with mock.patch.object(self.build_dist, "_move_tree", side_effect=fail_candidate_move):
                with self.assertRaises(OSError):
                    self.build_dist.replace_tree(candidate, destination)

            self.assertEqual((destination / "marker").read_text(encoding="utf-8"), "old")
            self.assertEqual((candidate / "marker").read_text(encoding="utf-8"), "new")
            self.assertEqual(list(root.glob(".dist.backup-*")), [])


class InstallerShellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "scripts").mkdir()
        (self.root / "bin").mkdir()
        (self.root / "VERSION").write_text("0.5.0\n", encoding="utf-8")
        build = self.root / "scripts" / "build_dist.py"
        build.write_text(
            "#!/usr/bin/env python3\n"
            "import os, pathlib\n"
            "marker = os.environ.get('FAKE_BUILD_MARKER')\n"
            "pathlib.Path(marker).write_text('called') if marker else None\n"
            "root = pathlib.Path(__file__).resolve().parent.parent\n"
            "for host in ('codex', 'claude', 'antigravity'):\n"
            "    scripts = root / 'dist' / host / 'skills' / 'lit-panel' / 'scripts'\n"
            "    scripts.mkdir(parents=True, exist_ok=True)\n"
            "    for name in ('verify_quotes.py', 'verify-quotes.py', 'repair_quotes.py'):\n"
            "        (scripts / name).write_text('import argparse; argparse.ArgumentParser().parse_args()\\n')\n",
            encoding="utf-8",
        )
        build.chmod(0o755)
        for host in ("codex", "claude", "antigravity"):
            scripts = self.root / "dist" / host / "skills" / "lit-panel" / "scripts"
            scripts.mkdir(parents=True, exist_ok=True)
            for name in ("verify_quotes.py", "verify-quotes.py", "repair_quotes.py"):
                (scripts / name).write_text(
                    "import argparse; argparse.ArgumentParser().parse_args()\n",
                    encoding="utf-8",
                )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def copy_installer(self, name: str) -> Path:
        target = self.root / "scripts" / name
        shutil.copy2(ROOT / "scripts" / name, target)
        target.chmod(0o755)
        return target

    def environment(self, **extra: str) -> dict[str, str]:
        return {
            **os.environ,
            "PATH": f"{self.root / 'bin'}:{os.environ['PATH']}",
            **extra,
        }

    def write_executable(self, name: str, content: str) -> None:
        path = self.root / "bin" / name
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)

    def install_fake_codex(self) -> Path:
        state = self.root / "codex-marketplace.json"
        self.write_executable(
            "codex",
            """#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
state = pathlib.Path(os.environ['FAKE_MARKETPLACE_STATE'])
current = json.loads(state.read_text()).get('path', '')
if args == ['--version']:
    print('codex-cli 0.147.0')
elif args == ['plugin', 'marketplace', 'list', '--json']:
    items = [{'name': 'lit-panel', 'root': current}] if current else []
    print(json.dumps({'marketplaces': items}))
elif args[:3] == ['plugin', 'marketplace', 'remove']:
    state.write_text(json.dumps({'path': ''}))
elif args[:3] == ['plugin', 'marketplace', 'add']:
    source = args[3]
    if source == os.environ['FAKE_DIST'] and os.environ.get('FAKE_FAIL_TARGET') == '1':
        raise SystemExit(7)
    state.write_text(json.dumps({'path': source}))
elif args == ['plugin', 'list', '--json']:
    print(json.dumps({'installed': [{'pluginId': 'lit-panel@lit-panel', 'version': '0.5.0'}]}))
elif args[:3] == ['plugin', 'add', 'lit-panel@lit-panel']:
    pass
else:
    print(f'unexpected codex args: {args}', file=sys.stderr)
    raise SystemExit(9)
""",
        )
        return state

    def prepare_codex_distribution(self) -> Path:
        dist = self.root / "dist" / "codex"
        agents = dist / ".codex" / "agents"
        agents.mkdir(parents=True)
        (agents / "lit-test.toml").write_text("new\n", encoding="utf-8")
        return dist

    def test_project_agents_require_force_and_backup_only_conflicts(self) -> None:
        installer = self.copy_installer("install-codex.sh")
        dist = self.prepare_codex_distribution()
        state = self.install_fake_codex()
        state.write_text(json.dumps({"path": str(dist)}), encoding="utf-8")
        project = self.root / "project"
        agents = project / ".codex" / "agents"
        agents.mkdir(parents=True)
        conflict = agents / "lit-test.toml"
        conflict.write_text("old\n", encoding="utf-8")
        unrelated = agents / "custom.toml"
        unrelated.write_text("custom\n", encoding="utf-8")
        marker = self.root / "build-called"
        env = self.environment(
            FAKE_MARKETPLACE_STATE=str(state),
            FAKE_DIST=str(dist),
            FAKE_BUILD_MARKER=str(marker),
        )

        blocked = subprocess.run(
            [str(installer), "--project-agents"],
            cwd=project,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertEqual(conflict.read_text(encoding="utf-8"), "old\n")
        self.assertEqual(list(agents.glob(".lit-panel-backup-*")), [])

        forced = subprocess.run(
            [str(installer), "--project-agents", "--force"],
            cwd=project,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(forced.returncode, 0, forced.stderr)
        backups = list(agents.glob(".lit-panel-backup-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "lit-test.toml").read_text(encoding="utf-8"), "old\n")
        self.assertFalse((backups[0] / "custom.toml").exists())
        self.assertEqual(conflict.read_text(encoding="utf-8"), "new\n")
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "custom\n")
        self.assertIn(str(backups[0]), forced.stdout)
        self.assertFalse(marker.exists(), "default Codex install must not rebuild dist")

    def test_failed_forced_marketplace_switch_restores_previous_path(self) -> None:
        installer = self.copy_installer("install-codex.sh")
        dist = self.prepare_codex_distribution()
        state = self.install_fake_codex()
        old_path = str(self.root / "old-marketplace")
        state.write_text(json.dumps({"path": old_path}), encoding="utf-8")
        env = self.environment(
            FAKE_MARKETPLACE_STATE=str(state),
            FAKE_DIST=str(dist),
            FAKE_FAIL_TARGET="1",
        )

        result = subprocess.run(
            [str(installer), "--force"],
            cwd=self.root,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(state.read_text(encoding="utf-8"))["path"], old_path)
        self.assertIn("已恢复原 marketplace", result.stderr)

    def install_fake_claude(
        self, version: str, mutation_log: Path, marketplace_path: Path | None = None
    ) -> None:
        marketplace_path = marketplace_path or (self.root / "dist" / "claude")
        self.write_executable(
            "claude",
            f"""#!/usr/bin/env python3
import json, pathlib, sys
args = sys.argv[1:]
log = pathlib.Path({str(mutation_log)!r})
if args == ['--version']:
    print({(version + ' (Claude Code)')!r})
elif args[:2] == ['plugin', 'validate']:
    pass
elif args == ['plugin', 'marketplace', 'list', '--json']:
    print(json.dumps([{{'name': 'lit-panel', 'source': 'directory', 'path': {str(marketplace_path)!r}}}]))
elif args == ['plugin', 'list', '--json']:
    print(json.dumps([{{'id': 'lit-panel@lit-panel', 'version': '0.5.0'}}]))
else:
    log.write_text(' '.join(args))
    raise SystemExit(8)
""",
        )

    def test_claude_installer_is_idempotent_from_json_state(self) -> None:
        installer = self.copy_installer("install-claude.sh")
        mutation_log = self.root / "claude-mutation"
        self.install_fake_claude("2.1.195", mutation_log)

        result = subprocess.run(
            [str(installer)],
            cwd=self.root,
            env=self.environment(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(mutation_log.exists())
        self.assertIn("跳过重复注册", result.stdout)
        self.assertIn("跳过重复安装", result.stdout)

    def test_installers_use_committed_distributions_without_rebuilding(self) -> None:
        installer = self.copy_installer("install-claude.sh")
        mutation_log = self.root / "claude-mutation"
        marker = self.root / "build-called"
        self.install_fake_claude("2.1.195", mutation_log)

        result = subprocess.run(
            [str(installer)],
            cwd=self.root,
            env=self.environment(FAKE_BUILD_MARKER=str(marker)),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists(), "default install must not rebuild dist")

    def test_rebuild_is_explicit_and_unknown_options_are_rejected(self) -> None:
        installer = self.copy_installer("install-claude.sh")
        mutation_log = self.root / "claude-mutation"
        marker = self.root / "build-called"
        self.install_fake_claude("2.1.195", mutation_log)

        rejected = subprocess.run(
            [str(installer), "--unexpected"],
            cwd=self.root,
            env=self.environment(FAKE_BUILD_MARKER=str(marker)),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertFalse(marker.exists())

        rebuilt = subprocess.run(
            [str(installer), "--rebuild"],
            cwd=self.root,
            env=self.environment(FAKE_BUILD_MARKER=str(marker)),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(rebuilt.returncode, 0, rebuilt.stderr)
        self.assertTrue(marker.exists(), "--rebuild must refresh dist explicitly")

    def test_claude_installer_rejects_same_name_marketplace_from_other_source(self) -> None:
        installer = self.copy_installer("install-claude.sh")
        mutation_log = self.root / "claude-mutation"
        self.install_fake_claude(
            "2.1.195", mutation_log, marketplace_path=self.root / "old-marketplace"
        )

        result = subprocess.run(
            [str(installer)],
            cwd=self.root,
            env=self.environment(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(mutation_log.exists())
        self.assertIn("来源不是当前", result.stderr)

    def test_minimum_versions_fail_before_distribution_build(self) -> None:
        marker = self.root / "build-called"
        mutation_log = self.root / "claude-mutation"
        claude = self.copy_installer("install-claude.sh")
        self.install_fake_claude("2.1.62", mutation_log)
        claude_result = subprocess.run(
            [str(claude)],
            cwd=self.root,
            env=self.environment(FAKE_BUILD_MARKER=str(marker)),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(claude_result.returncode, 0)
        self.assertFalse(marker.exists())

        antigravity = self.copy_installer("install-antigravity.sh")
        self.write_executable(
            "agy",
            "#!/usr/bin/env bash\nif [ \"$1\" = \"--version\" ]; then echo '1.1.11'; else exit 9; fi\n",
        )
        antigravity_result = subprocess.run(
            [str(antigravity)],
            cwd=self.root,
            env=self.environment(FAKE_BUILD_MARKER=str(marker)),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(antigravity_result.returncode, 0)
        self.assertFalse(marker.exists())

    def test_antigravity_workspace_copy_does_not_require_cli(self) -> None:
        installer = self.copy_installer("install-antigravity.sh")
        dist = self.root / "dist" / "antigravity"
        dist.mkdir(parents=True, exist_ok=True)
        (dist / "plugin.json").write_text("{}\n", encoding="utf-8")
        workspace = self.root / "workspace"
        workspace.mkdir()
        marker = self.root / "build-called"

        result = subprocess.run(
            [str(installer), "--workspace", str(workspace)],
            cwd=self.root,
            env=self.environment(FAKE_BUILD_MARKER=str(marker)),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((workspace / ".agents/plugins/lit-panel/plugin.json").is_file())
        self.assertFalse(marker.exists(), "default Antigravity install must not rebuild dist")

        repeated = subprocess.run(
            [str(installer), "--workspace", str(workspace)],
            cwd=self.root,
            env=self.environment(FAKE_BUILD_MARKER=str(marker)),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertIn("已是当前分发", repeated.stdout)

    def test_missing_committed_distribution_fails_without_rebuilding(self) -> None:
        installer = self.copy_installer("install-claude.sh")
        mutation_log = self.root / "claude-mutation"
        marker = self.root / "build-called"
        self.install_fake_claude("2.1.195", mutation_log)
        shutil.rmtree(self.root / "dist" / "claude")

        result = subprocess.run(
            [str(installer)],
            cwd=self.root,
            env=self.environment(FAKE_BUILD_MARKER=str(marker)),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(marker.exists())
        self.assertIn("完整 release checkout", result.stderr)

    def test_antigravity_failed_force_copy_preserves_existing_plugin(self) -> None:
        installer = self.copy_installer("install-antigravity.sh")
        dist = self.root / "dist" / "antigravity"
        dist.mkdir(parents=True, exist_ok=True)
        (dist / "plugin.json").write_text("{\"new\": true}\n", encoding="utf-8")
        workspace = self.root / "workspace"
        existing = workspace / ".agents/plugins/lit-panel"
        existing.mkdir(parents=True)
        marker = existing / "plugin.json"
        marker.write_text("{\"old\": true}\n", encoding="utf-8")
        self.write_executable("cp", "#!/usr/bin/env bash\nexit 7\n")

        result = subprocess.run(
            [str(installer), "--workspace", str(workspace), "--force"],
            cwd=self.root,
            env=self.environment(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(encoding="utf-8"), "{\"old\": true}\n")


class ReleaseCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.release_check = load_script_module("lit_panel_release_check_test", "scripts/release_check.py")

    def test_stale_generated_copies_fail_release_check(self) -> None:
        result = subprocess.CompletedProcess([], 1, stdout="", stderr="DIST OUT OF DATE")
        with mock.patch.object(self.release_check.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(ValueError, "DIST OUT OF DATE"):
                self.release_check.check_generated_copies()


if __name__ == "__main__":
    unittest.main()
