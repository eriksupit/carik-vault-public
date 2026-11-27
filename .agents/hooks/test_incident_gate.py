#!/usr/bin/env python3
"""Tests for incident-gate.py."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GATE = ROOT / ".agents" / "hooks" / "incident-gate.py"
INC_DIR = ROOT / ".agents" / "incidents"

class TestIncidentGate(unittest.TestCase):
    def setUp(self):
        INC_DIR.mkdir(parents=True, exist_ok=True)
        self.created_files = []

    def tearDown(self):
        for f in self.created_files:
            if f.exists():
                f.unlink(missing_ok=True)

    def test_ignores_readme_file_in_incidents_directory(self):
        readme = INC_DIR / "README.md"
        readme.write_text("# Incident Registry Documentation\nNo YAML frontmatter.", encoding="utf-8")
        payload = {"tool_name": "Bash", "tool_input": {"command": "ls -la"}}
        res = subprocess.run([sys.executable, str(GATE)], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

    def test_pre_tool_blocks_matching_token_with_exit_2(self):
        inc_file = INC_DIR / "INC-9001-block-test.md"
        inc_file.write_text(
            "---\n"
            "id: INC-9001\n"
            "trigger_class: bash_command\n"
            "activation_predicate:\n"
            "  token: 'forbidden_script_token'\n"
            "status: active\n"
            "---\n",
            encoding="utf-8"
        )
        self.created_files.append(inc_file)
        payload = {"tool_name": "Bash", "tool_input": {"command": "sh forbidden_script_token.sh"}}
        res = subprocess.run([sys.executable, str(GATE)], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(res.returncode, 2)
        self.assertIn("Blocked by incident gate [INC-9001]", res.stderr)

    def test_pre_tool_allows_unmatched(self):
        inc_file = INC_DIR / "INC-9002-unmatched-test.md"
        inc_file.write_text(
            "---\n"
            "id: INC-9002\n"
            "trigger_class: bash_command\n"
            "activation_predicate:\n"
            "  token: 'other_token'\n"
            "status: active\n"
            "---\n",
            encoding="utf-8"
        )
        self.created_files.append(inc_file)
        payload = {"tool_name": "Bash", "tool_input": {"command": "echo safe"}}
        res = subprocess.run([sys.executable, str(GATE)], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

    def test_corrupted_incident_fails_closed_with_exit_2(self):
        inc_file = INC_DIR / "INC-9003-corrupt.md"
        inc_file.write_text("No frontmatter delimiters at all", encoding="utf-8")
        self.created_files.append(inc_file)
        payload = {"tool_name": "Bash", "tool_input": {"command": "echo test"}}
        res = subprocess.run([sys.executable, str(GATE)], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(res.returncode, 2)
        self.assertIn("corrupted incident registry", res.stderr.lower())

    def test_stop_token_is_advisory_only(self):
        inc_file = INC_DIR / "INC-9004-stop-advisory.md"
        inc_file.write_text(
            "---\n"
            "id: INC-9004\n"
            "trigger_class: stop_token\n"
            "activation_predicate:\n"
            "  token: 'forbidden_stop_pattern'\n"
            "status: active\n"
            "---\n",
            encoding="utf-8"
        )
        self.created_files.append(inc_file)
        payload = {
            "session_id": "test-session-stop-1",
            "last_assistant_message": "forbidden_stop_pattern in closing"
        }
        res = subprocess.run([sys.executable, str(GATE), "stop"], input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "", "stop must never emit a block decision")
        self.assertIn("INC-9004", res.stderr)

if __name__ == "__main__":
    unittest.main()
