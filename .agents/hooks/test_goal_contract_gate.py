#!/usr/bin/env python3
"""Unit tests for goal-contract-gate.py PreToolUse gate."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
VAULT_ROOT = HOOKS_DIR.parent.parent
GATE = HOOKS_DIR / "goal-contract-gate.py"


def run_gate(payload: dict, env_extra: dict | None = None) -> tuple[int, str, str]:
    """Helper to run goal-contract-gate.py with JSON payload on stdin."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(VAULT_ROOT)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(GATE)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=VAULT_ROOT,
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


class TestGoalContractGate(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.transcript_path = Path(self.temp_dir.name) / "transcript.jsonl"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_allows_exempt_or_telemetry_files(self):
        payload = {
            "session_id": "test-session",
            "tool_input": {
                "file_path": str(VAULT_ROOT / ".agents" / "telemetry" / "skill-usage.jsonl"),
                "content": "test",
            },
        }
        rc, _, stderr = run_gate(payload)
        self.assertEqual(rc, 0)
        self.assertEqual(stderr, "")

    def test_denies_substantive_write_when_transcript_has_no_goal_contract(self):
        self.transcript_path.write_text(
            json.dumps({"type": "PLANNER_RESPONSE", "content": "I will edit the file now."}) + "\n",
            encoding="utf-8",
        )
        payload = {
            "session_id": "test-session",
            "transcript_path": str(self.transcript_path),
            "tool_input": {
                "file_path": str(VAULT_ROOT / "docs" / "test.md"),
                "content": "# Test content",
            },
        }
        rc, _, stderr = run_gate(payload)
        self.assertEqual(rc, 2)
        self.assertIn("Goal Contract missing", stderr)

    def test_allows_substantive_write_when_transcript_contains_goal_contract(self):
        self.transcript_path.write_text(
            json.dumps({
                "type": "PLANNER_RESPONSE",
                "content": "## Goal Contract\n- **Objective:** Fix bug\n- **Completion condition:** passes tests",
            }) + "\n",
            encoding="utf-8",
        )
        payload = {
            "session_id": "test-session",
            "transcript_path": str(self.transcript_path),
            "tool_input": {
                "file_path": str(VAULT_ROOT / "docs" / "test.md"),
                "content": "# Test content",
            },
        }
        rc, _, stderr = run_gate(payload)
        self.assertEqual(rc, 0)
        self.assertEqual(stderr, "")

    def test_fails_open_on_missing_transcript_or_empty_payload(self):
        payload = {}
        rc, _, stderr = run_gate(payload)
        self.assertEqual(rc, 0)
        self.assertEqual(stderr, "")

    def test_denies_bash_mutation_without_goal_contract(self):
        self.transcript_path.write_text(
            json.dumps({"type": "PLANNER_RESPONSE", "content": "I will run bash now."}) + "\n",
            encoding="utf-8",
        )
        payload = {
            "session_id": "test-session",
            "transcript_path": str(self.transcript_path),
            "tool_input": {
                "command": "echo '# plan' > docs/plans/new-plan.md",
            },
        }
        rc, _, stderr = run_gate(payload)
        self.assertEqual(rc, 2)
        self.assertIn("Goal Contract missing", stderr)


if __name__ == "__main__":
    unittest.main()
