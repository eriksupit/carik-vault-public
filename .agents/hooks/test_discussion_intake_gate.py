#!/usr/bin/env python3
"""Tests for discussion-intake-gate.py."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GATE = ROOT / ".agents" / "hooks" / "discussion-intake-gate.py"

class TestDiscussionIntakeGate(unittest.TestCase):
    def test_blocks_downstream_drafting_without_entry_artifact(self):
        payload = {"tool_name": "Write", "tool_input": {"file_path": "work/drafts/sample.md", "content": "draft text"}}
        res = subprocess.run([sys.executable, str(GATE)], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(res.returncode, 2)
        self.assertIn("Blocked by discussion intake discipline", res.stderr)

    def test_permits_writes_outside_work_directory(self):
        payload = {"tool_name": "Write", "tool_input": {"file_path": "docs/plans/sample.md", "content": "plan text"}}
        res = subprocess.run([sys.executable, str(GATE)], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

    def test_permits_root_work_files(self):
        payload = {"tool_name": "Write", "tool_input": {"file_path": "work/WORKFLOW.md", "content": "workflow text"}}
        res = subprocess.run([sys.executable, str(GATE)], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

    def test_honors_bypass_env_var(self):
        payload = {"tool_name": "Write", "tool_input": {"file_path": "work/drafts/sample.md", "content": "draft text"}}
        env = dict(os.environ, VAULT_BYPASS_INTAKE="1")
        res = subprocess.run([sys.executable, str(GATE)], input=json.dumps(payload), capture_output=True, text=True, env=env)
        self.assertEqual(res.returncode, 0)

    def test_honors_intake_exempt_frontmatter(self):
        payload = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "work/drafts/sample.md",
                "content": "---\ntitle: Sample\nintake_exempt: true\n---\ntext"
            }
        }
        res = subprocess.run([sys.executable, str(GATE)], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

if __name__ == "__main__":
    unittest.main()
