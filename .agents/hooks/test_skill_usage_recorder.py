#!/usr/bin/env python3
"""Regression tests for the skill-usage-recorder PreToolUse hook."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("skill-usage-recorder.py")


def run(root: Path, payload: dict | None, raw: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=raw if raw is not None else json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=10,
        env={"CLAUDE_PROJECT_DIR": str(root), "PATH": "/usr/bin:/bin"},
    )


class SkillUsageRecorderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.log = self.root / ".agents" / "telemetry" / "skill-usage.jsonl"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def records(self) -> list[dict]:
        if not self.log.is_file():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines() if line]

    def test_records_a_skill_call_and_never_blocks(self) -> None:
        result = run(self.root, {"session_id": "s1", "tool_input": {"skill": "session-anchors"}})
        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual(["session-anchors"], [r["skill"] for r in self.records()])
        self.assertEqual("s1", self.records()[0]["session_id"])
        self.assertIn("T", self.records()[0]["at"])

    def test_appends_rather_than_overwrites(self) -> None:
        for name in ("brave", "confidence", "brave"):
            run(self.root, {"session_id": "s1", "tool_input": {"skill": name}})
        self.assertEqual(["brave", "confidence", "brave"], [r["skill"] for r in self.records()])

    def test_missing_skill_name_records_nothing(self) -> None:
        result = run(self.root, {"session_id": "s1", "tool_input": {"args": "no skill key"}})
        self.assertEqual(0, result.returncode)
        self.assertEqual([], self.records())

    def test_malformed_json_fails_open(self) -> None:
        result = run(self.root, None, raw="not json{{{")
        self.assertEqual(0, result.returncode)
        self.assertEqual([], self.records())


if __name__ == "__main__":
    unittest.main()
