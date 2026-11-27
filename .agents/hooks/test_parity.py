#!/usr/bin/env python3
"""Tests for the four-runtime parity judge."""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RUNTIMES = ("claude", "codex", "antigravity", "deepseek")
CLASS_C = {"vault-boundary-guard.py", "git-scope-guard.py"}
WIRING = (
    ".claude/settings.json",
    ".codex/hooks.json",
    ".agents/hooks/antigravity-adapter.py",
    ".agents/hooks/deepseek-adapter.py",
)


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / "lib" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(**extra):
    """Every runtime dispatches the Class C guards plus its named extras."""
    return {r: CLASS_C | set(extra.get(r, ())) for r in RUNTIMES}


def live_exemptions():
    return json.loads((HERE / "parity-exemptions.json").read_text(encoding="utf-8"))["hooks"]


class ParityJudgeTest(unittest.TestCase):
    def setUp(self):
        self.parity = load("parity")

    def test_full_parity_yields_no_findings(self):
        snap = snapshot(**{r: {"incident-gate.py"} for r in RUNTIMES})
        self.assertEqual([], self.parity.findings(snap, exemptions={}))

    def test_undeclared_absence_is_a_finding(self):
        snap = snapshot(claude={"incident-gate.py"}, antigravity={"incident-gate.py"}, deepseek={"incident-gate.py"})
        found = self.parity.findings(snap, exemptions={})
        self.assertEqual(1, len(found))
        self.assertIn("incident-gate.py", found[0])
        self.assertIn("codex", found[0])

    def test_declared_exemption_suppresses_the_finding(self):
        exemptions = {"wire-skills.py": {"runtimes": ["claude"], "reason": "installer, not a gate"}}
        self.assertEqual([], self.parity.findings(snapshot(claude={"wire-skills.py"}), exemptions=exemptions))

    def test_exemption_without_a_reason_is_rejected(self):
        exemptions = {"wire-skills.py": {"runtimes": ["claude"], "reason": ""}}
        found = self.parity.findings(snapshot(claude={"wire-skills.py"}), exemptions=exemptions)
        self.assertEqual(1, len(found))
        self.assertIn("reason", found[0])
        self.assertIn("wire-skills.py", found[0])

    def test_exemption_narrower_than_reality_still_reports(self):
        exemptions = {"wire-skills.py": {"runtimes": ["claude"], "reason": "installer"}}
        snap = snapshot(claude={"wire-skills.py"}, codex={"wire-skills.py"})
        found = self.parity.findings(snap, exemptions=exemptions)
        self.assertEqual(1, len(found))
        self.assertIn("codex", found[0])
        self.assertIn("widen or remove", found[0])

    def test_exemption_broader_than_reality_is_reported(self):
        exemptions = {"wire-skills.py": {"runtimes": ["claude", "codex"], "reason": "installer"}}
        found = self.parity.findings(snapshot(claude={"wire-skills.py"}), exemptions=exemptions)
        self.assertEqual(1, len(found))
        self.assertIn("codex", found[0])
        self.assertIn("does not dispatch it", found[0])

    def test_exemption_both_narrower_and_broader_reports_both(self):
        exemptions = {"wire-skills.py": {"runtimes": ["codex"], "reason": "installer"}}
        found = self.parity.findings(snapshot(claude={"wire-skills.py"}), exemptions=exemptions)
        self.assertEqual(2, len(found))
        self.assertIn("claude", [f for f in found if "widen or remove" in f][0])
        self.assertIn("codex", [f for f in found if "narrow the exemption" in f][0])

    def test_malformed_exemptions_are_rejected(self):
        snap = snapshot(claude={"wire-skills.py"})
        for bad_rule in (
            None, "text", 42, ["claude"],
            {"runtimes": "claude", "reason": "installer"},
            {"runtimes": [123], "reason": "installer"},
        ):
            found = self.parity.findings(snap, exemptions={"wire-skills.py": bad_rule})
            self.assertEqual(1, len(found), f"bad_rule={bad_rule}")
            self.assertIn("malformed", found[0])

    def test_class_c_guard_removed_from_every_runtime_is_a_finding(self):
        snap = {r: {"git-scope-guard.py", "incident-gate.py"} for r in RUNTIMES}
        found = self.parity.findings(snap, exemptions={})
        self.assertEqual(1, len(found))
        self.assertIn("vault-boundary-guard.py", found[0])
        self.assertIn("mandatory", found[0])

    def test_exemption_cannot_waive_a_class_c_guard(self):
        snap = snapshot()
        snap["deepseek"].discard("git-scope-guard.py")
        exemptions = {"git-scope-guard.py": {"runtimes": ["claude", "codex", "antigravity"], "reason": "x"}}
        found = self.parity.findings(snap, exemptions=exemptions)
        self.assertEqual(1, len(found))
        self.assertIn("git-scope-guard.py", found[0])
        self.assertIn("deepseek", found[0])

    def test_live_vault_has_parity(self):
        snap = load("registry").runtime_hooks(ROOT)
        self.assertEqual([], self.parity.findings(snap, exemptions=live_exemptions()))

    def test_live_vault_negative_control_detects_removed_guard(self):
        broken = {r: set(h) for r, h in load("registry").runtime_hooks(ROOT).items()}
        broken["deepseek"].remove("vault-boundary-guard.py")
        found = self.parity.findings(broken, exemptions=live_exemptions())
        self.assertEqual(1, len(found))
        self.assertIn("vault-boundary-guard.py", found[0])
        self.assertIn("deepseek", found[0])


class ActivationIntegrationTest(unittest.TestCase):
    def verify_clone(self, files, old, new):
        """Rewrite `old` to `new` in the named files of a vault copy and run the verifier."""
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "vault"
            shutil.copytree(
                ROOT,
                clone,
                symlinks=True,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "handoff", "raw-kb", "work"),
            )
            for rel in files:
                path = clone / rel
                path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(clone / "scripts" / "verify_activation.py"), str(clone)],
                capture_output=True,
                text=True,
            )

    def test_verifier_reports_a_parity_break(self):
        result = self.verify_clone([".agents/hooks/deepseek-adapter.py"], '"vault-boundary-guard.py"', '"incident-gate.py"')
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("vault-boundary-guard.py", result.stdout)
        self.assertIn("deepseek", result.stdout)

    def test_verifier_reports_class_c_guard_removed_from_every_runtime(self):
        # Swap for an existing hook so only the Class C rule, not a missing file, can fire.
        result = self.verify_clone(WIRING, "vault-boundary-guard.py", "frontmatter-reminder.py")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("Class C guard vault-boundary-guard.py", result.stdout)

    def test_verifier_reports_missing_direct_form_target(self):
        result = self.verify_clone([".codex/hooks.json"], "direct incident-gate.py stop", "direct absent-gate.py stop")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("absent-gate.py", result.stdout)


if __name__ == "__main__":
    unittest.main()
