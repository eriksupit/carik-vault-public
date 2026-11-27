#!/usr/bin/env python3
"""Tests for artifact-preview-gate.py."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GATE = ROOT / ".agents" / "hooks" / "artifact-preview-gate.py"

class TestArtifactPreviewGate(unittest.TestCase):
    def test_extension_prefilter_ignores_python_files(self):
        payload = {"tool_name": "Write", "tool_input": {"file_path": "scripts/test.py"}}
        res = subprocess.run([sys.executable, str(GATE)], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stderr, "")

    def test_preview_triggered_on_markdown(self):
        payload = {"tool_name": "Write", "tool_input": {"file_path": "README.md"}}
        res = subprocess.run([sys.executable, str(GATE)], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Artifact preview generated:", res.stderr)

if __name__ == "__main__":
    unittest.main()
