#!/usr/bin/env python3
"""Tests for git-scope-guard.py."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GUARD = ROOT / ".agents" / "hooks" / "git-scope-guard.py"

class TestGitScopeGuard(unittest.TestCase):
    def test_blocks_broad_add(self):
        commands = [
            "git add .",
            "git add -A",
            "git add --all",
            "git add -u",
            "git add -Av",
            "git add -- .",
            "git add :/",
            "git add 'docs/*.md'",
            "/usr/bin/git add -A",
            "git -C sub add .",
            "git status\ngit add -A",
        ]
        for cmd in commands:
            payload = {"tool_name": "Bash", "tool_input": {"command": cmd}}
            res = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(payload), capture_output=True, text=True)
            self.assertEqual(res.returncode, 2, f"Allowed broad add: {cmd}")
            self.assertIn("broad staging", res.stderr)

    def test_allows_explicit_add(self):
        commands = [
            "git add -- file.txt",
            "git add src/main.py",
            "git add .agents/sessions/sess-1.md",
            "git add -- -odd-name.md",
        ]
        for cmd in commands:
            payload = {"tool_name": "Bash", "tool_input": {"command": cmd}}
            res = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(payload), capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Blocked explicit add: {cmd}")

    def test_blocks_force_push_flags(self):
        commands = [
            "git push origin main -f",
            "git push --force",
            "git push origin main --force-with-lease",
            "git push origin main --force-with-lease=main",
            "git push -uf origin main",
            "git push origin +main",
            "/usr/bin/git push --force",
        ]
        for cmd in commands:
            payload = {"tool_name": "Bash", "tool_input": {"command": cmd}}
            res = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(payload), capture_output=True, text=True)
            self.assertEqual(res.returncode, 2, f"Allowed force push: {cmd}")
            self.assertIn("forced push is strictly prohibited", res.stderr)

    def test_blocks_session_path_mixing(self):
        commands = [
            "git add .agents/sessions/sess-1.md SCOPE.md",
            "git add -- .agents/sessions/sess-1.md work/task.md"
        ]
        for cmd in commands:
            payload = {"tool_name": "Bash", "tool_input": {"command": cmd}}
            res = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(payload), capture_output=True, text=True)
            self.assertEqual(res.returncode, 2, f"Allowed mixed session staging: {cmd}")
            self.assertIn("session continuity files cannot be staged together", res.stderr)

if __name__ == "__main__":
    unittest.main()
