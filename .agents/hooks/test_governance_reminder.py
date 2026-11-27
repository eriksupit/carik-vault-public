#!/usr/bin/env python3
import json
import subprocess
import sys
import unittest
from pathlib import Path

HOOK = Path(__file__).with_name("governance-reminder.py")


class GovernanceReminderTests(unittest.TestCase):
    def test_prompt_reminds_agent_of_mandatory_governance(self) -> None:
        result = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps({"prompt": "continue", "session_id": "test-session"}),
            text=True,
            capture_output=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Governance active", context)
        self.assertIn("anti-sycophancy", context)
        self.assertIn("recommend skill", context)
        self.assertIn("brave", context)
        self.assertIn("goal-contract-gate.py", context)
        self.assertIn("closers must be declarative statements", context)
        self.assertIn("convene debate", context)

    def test_reminder_does_not_depend_on_prompt_wording(self) -> None:
        contexts = {
            subprocess.run(
                [sys.executable, str(HOOK)],
                input=json.dumps({"prompt": prompt, "session_id": "test-session"}),
                text=True,
                capture_output=True,
            ).stdout
            for prompt in ("continue normal work", "kamu salah lagi")
        }
        self.assertEqual(1, len(contexts))


if __name__ == "__main__":
    unittest.main()
