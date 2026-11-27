#!/usr/bin/env python3
"""Tests for the four-runtime hook registry reader."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_registry():
    spec = importlib.util.spec_from_file_location("registry", HERE / "lib" / "registry.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RegistryReaderTest(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".claude").mkdir()
        (self.root / ".codex").mkdir()
        (self.root / ".agents" / "hooks" / "lib").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write_claude(self, hook_names):
        entries = [
            {"hooks": [{"type": "command", "command": f'python3 "$ROOT/.agents/hooks/{name}"'}]}
            for name in hook_names
        ]
        (self.root / ".claude" / "settings.json").write_text(
            json.dumps({"hooks": {"PreToolUse": entries}}), encoding="utf-8"
        )

    def test_claude_reads_path_form_commands(self):
        self.write_claude(["git-scope-guard.py", "menu-guard.py"])
        found = self.registry.runtime_hooks(self.root)
        self.assertEqual({"git-scope-guard.py", "menu-guard.py"}, found["claude"])

    def test_codex_reads_bare_direct_arguments(self):
        (self.root / ".codex" / "hooks.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "Stop": [
                            {
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": 'python3 "$H" direct menu-guard.py',
                                    }
                                ]
                            }
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        found = self.registry.runtime_hooks(self.root)
        self.assertIn("menu-guard.py", found["codex"])

    def test_codex_also_reads_adapter_hardcoded_names(self):
        (self.root / ".codex" / "hooks.json").write_text(json.dumps({"hooks": {}}), encoding="utf-8")
        (self.root / ".agents" / "hooks" / "codex-adapter.py").write_text(
            'for script in ("goal-contract-gate.py", "prose-language-gate.py"):\n    pass\n',
            encoding="utf-8",
        )
        found = self.registry.runtime_hooks(self.root)
        self.assertEqual({"goal-contract-gate.py", "prose-language-gate.py"}, found["codex"])

    def test_adapter_only_runtimes_read_their_own_source(self):
        (self.root / ".agents" / "hooks" / "deepseek-adapter.py").write_text(
            'GATES = ("incident-gate.py",)\n', encoding="utf-8"
        )
        found = self.registry.runtime_hooks(self.root)
        self.assertEqual({"incident-gate.py"}, found["deepseek"])

    def test_missing_wiring_yields_empty_set_not_error(self):
        found = self.registry.runtime_hooks(self.root)
        self.assertEqual({"claude", "codex", "antigravity", "deepseek"}, set(found))
        self.assertEqual(set(), found["antigravity"])

    def test_library_imports_are_not_reported_as_dispatched(self):
        (self.root / ".agents" / "hooks" / "antigravity-adapter.py").write_text(
            'spec_from_file_location("t", parent / "lib" / "telemetry.py")\n'
            'GATES = ("menu-guard.py",)\n',
            encoding="utf-8",
        )
        found = self.registry.runtime_hooks(self.root)
        self.assertEqual({"menu-guard.py"}, found["antigravity"])

    def test_live_vault_reports_every_runtime_nonempty(self):
        root = HERE.parent.parent
        found = self.registry.runtime_hooks(root)
        for runtime, hooks in found.items():
            self.assertTrue(hooks, f"{runtime} reported no dispatched hooks in the live vault")
        common = set.intersection(*found.values())
        expected_common = {
            "artifact-preview-gate.py",
            "artifact-research-gate.py",
            "discussion-intake-gate.py",
            "frontmatter-reminder.py",
            "git-scope-guard.py",
            "goal-contract-gate.py",
            "governance-reminder.py",
            "incident-gate.py",
            "prose-language-gate.py",
            "vault-boundary-guard.py",
        }
        self.assertEqual(expected_common, common)

if __name__ == "__main__":
    unittest.main()
