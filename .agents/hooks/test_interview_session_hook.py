#!/usr/bin/env python3
"""Lifecycle behavior tests for the Interview Protocol hook entry point."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HOOKS = Path(__file__).resolve().parent
HOOK_PATH = HOOKS / "interview_session_hook.py"
SPEC = importlib.util.spec_from_file_location("interview_session_hook", HOOK_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("interview session hook unavailable")
hook = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = hook
SPEC.loader.exec_module(hook)
store = hook.store


class InterviewSessionHookTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".agents" / "sessions").mkdir(parents=True)
        self.common = {"runtime": "codex", "session_id": "hook-session"}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def call(self, mode: str, **extra: object) -> dict[str, object]:
        return hook.handle(mode, {**self.common, **extra}, root=self.root)

    def activate(self, **extra: object) -> dict[str, object]:
        return self.call("activate", **extra)

    def open_and_prepare(self) -> None:
        self.activate()
        opened = self.call("prompt", event_nonce="nonce-1")
        self.assertEqual(opened["status"], "pending")
        prepared = self.call(
            "prepare",
            turn=1,
            event_nonce="nonce-1",
            user_lines=["Owner supplies API_TOKEN=raw-secret"],
            agent_lines=["Agent records the validated choice"],
        )
        self.assertEqual(prepared["status"], "prepared")

    def test_activation_and_session_start_recovery_are_idempotent(self) -> None:
        first = self.activate()
        second = self.activate()
        self.assertEqual(first["session_id"], second["session_id"])
        self.assertEqual(second["status"], "active")
        recovered = self.call("session-start")
        self.assertEqual(recovered["status"], "continued")
        self.assertIn("Session Interview Scratch-Pad", str(recovered["additionalContext"]))

    def test_prompt_prepare_stop_and_duplicate_stop_seal_once(self) -> None:
        self.open_and_prepare()
        payload = {
            "turn": 1,
            "event_nonce": "nonce-1",
            "user_lines": ["Owner supplies API_TOKEN=raw-secret"],
            "agent_lines": ["Agent records the validated choice"],
        }
        sealed = self.call("stop", **payload)
        duplicate = self.call("stop", **payload)
        self.assertEqual(sealed["status"], "sealed")
        self.assertEqual(duplicate["status"], "duplicate")
        pointer = json.loads((self.root / ".agents/sessions/active.json").read_text())
        scratch = (self.root / pointer["scratch_pad"]).read_text()
        self.assertEqual(scratch.count("### Turn 001"), 1)
        self.assertNotIn("raw-secret", scratch)

    def test_current_turn_activation_opens_the_activation_turn(self) -> None:
        activated = self.activate(event_nonce="activation-nonce")
        self.assertEqual(activated["status"], "pending")
        prepared = self.call(
            "prepare", turn=1, event_nonce="activation-nonce",
            user_lines=["Activate now"], agent_lines=["Activation captured"],
        )
        self.assertEqual(prepared["status"], "prepared")

    def test_stop_must_match_the_pair_that_was_prepared(self) -> None:
        self.open_and_prepare()
        mismatch = self.call(
            "stop", turn=1, event_nonce="nonce-1",
            user_lines=["Different owner meaning"],
            agent_lines=["Agent records the validated choice"],
        )
        self.assertTrue(str(mismatch["reason"]).startswith("prepared-pair-mismatch"))
        correct = self.call(
            "stop", turn=1, event_nonce="nonce-1",
            user_lines=["Owner supplies API_TOKEN=raw-secret"],
            agent_lines=["Agent records the validated choice"],
        )
        self.assertEqual(correct["status"], "sealed")

    def test_missing_pair_block_is_satisfiable_on_retry(self) -> None:
        self.activate()
        self.call("prompt", event_nonce="nonce-1")
        blocked = self.call("stop", turn=1, event_nonce="nonce-1")
        self.assertEqual(blocked["decision"], "block")
        self.assertTrue(str(blocked["reason"]).startswith("missing-prepared-pair:.agents/sessions/"))
        self.call(
            "prepare", turn=1, event_nonce="nonce-1",
            user_lines=["Owner summary"], agent_lines=["Agent summary"],
        )
        released = self.call(
            "stop", turn=1, event_nonce="nonce-1",
            user_lines=["Owner summary"], agent_lines=["Agent summary"],
        )
        self.assertEqual(released["status"], "sealed")

    def test_wrong_session_and_malformed_protected_payload_block(self) -> None:
        self.activate()
        wrong = hook.handle(
            "prompt", {"runtime": "codex", "session_id": "other", "event_nonce": "n"}, root=self.root
        )
        self.assertEqual(wrong["decision"], "block")
        self.assertIn(".agents/sessions/codex-other-", str(wrong["reason"]))
        malformed = self.call("prompt")
        self.assertEqual(malformed["decision"], "block")

    def test_unavailable_identity_and_inactive_malformed_plumbing_fail_open(self) -> None:
        unavailable = hook.handle(
            "session-start", {"runtime": "codex", "session_id": "unknown"}, root=self.root
        )
        self.assertEqual(unavailable["status"], "unavailable")
        malformed = hook.handle("prompt", {"garbage": True}, root=self.root)
        self.assertEqual(malformed["status"], "unavailable")
        self.assertNotIn("decision", malformed)

    def test_malformed_active_state_fails_closed(self) -> None:
        activated = self.activate()
        state_path = self.root / ".agents" / "sessions" / str(activated["session_id"]) / "state.json"
        state_path.write_text("{bad json", encoding="utf-8")
        result = self.call("prompt", event_nonce="n")
        self.assertEqual(result["decision"], "block")
        self.assertIn("malformed-session-state", str(result["reason"]))

    def test_permanent_stop_failure_faults_once_without_stop_loop(self) -> None:
        self.open_and_prepare()
        payload = {
            "turn": 1, "event_nonce": "nonce-1",
            "user_lines": ["Owner summary"], "agent_lines": ["Agent summary"],
        }
        with mock.patch.object(
            hook.store, "persist_sealed_turn", side_effect=hook.store.SessionStoreError("atomic-write-failure")
        ):
            first = self.call("stop", **payload)
        self.assertEqual(first["status"], "faulted")
        self.assertEqual(first["diagnostic"], "interview-session:faulted")
        directory = self.root / ".agents" / "sessions" / str(first["session_id"])
        self.assertFalse((directory / "transaction.json").exists())
        self.assertIn("status: faulted", (directory / "scratch-pad.md").read_text())
        later_prompt = self.call("prompt", event_nonce="nonce-2")
        self.assertEqual(later_prompt["decision"], "block")
        repeated_stop = self.call("stop", **payload)
        self.assertEqual(repeated_stop["status"], "faulted")
        self.assertNotIn("decision", repeated_stop)
        self.assertNotIn("diagnostic", repeated_stop)

    def test_crash_between_prepare_and_stop_recovers_to_a_usable_turn(self) -> None:
        self.open_and_prepare()
        session_id = str(self.call("session-start")["session_id"])
        directory = self.root / ".agents" / "sessions" / session_id
        self.assertFalse((directory / "transaction.json").exists())
        state = json.loads((directory / "state.json").read_text())
        self.assertEqual((state["turn_state"], state["pending_turn"]), ("active", None))
        reopened = self.call("prompt", event_nonce="nonce-2")
        self.assertEqual(reopened["status"], "pending")
        self.assertEqual(reopened["turn"], 1)
        self.call(
            "prepare", turn=1, event_nonce="nonce-2",
            user_lines=["Owner repeats the decision"], agent_lines=["Agent records it"],
        )
        sealed = self.call(
            "stop", turn=1, event_nonce="nonce-2",
            user_lines=["Owner repeats the decision"], agent_lines=["Agent records it"],
        )
        self.assertEqual(sealed["status"], "sealed")

    def test_new_scratch_pad_declares_an_empty_predecessor(self) -> None:
        activated = self.activate()
        scratch = (
            self.root / ".agents" / "sessions" / str(activated["session_id"]) / "scratch-pad.md"
        ).read_text()
        self.assertIn("previous_scratch_pad: \n", scratch + "\n")
        self.assertNotIn("previous_scratch_pad: null", scratch)

    def test_activate_from_closed_predecessor_binds_predecessor_and_activates(self) -> None:
        # 1. Activate session 1, seal a turn, and close normally
        s1 = self.activate(event_nonce="n1")
        sid1 = str(s1["session_id"])
        self.call("prepare", turn=1, event_nonce="n1", user_lines=["Hello"], agent_lines=["Proposal"])
        self.call("stop", turn=1, event_nonce="n1")
        store.close_session(self.root, sid1, final=True)

        pointer = json.loads((self.root / ".agents" / "sessions" / "active.json").read_text(encoding="utf-8"))
        self.assertEqual(pointer["status"], "closed")

        # 2. Activate session 2 using a new raw session id
        s2 = self.call("activate", session_id="codex-successor-0123456789abcdef", runtime="codex")
        self.assertEqual(s2["status"], "active")

        # Verify active.json advanced to session 2 with status: active
        new_pointer = json.loads((self.root / ".agents" / "sessions" / "active.json").read_text(encoding="utf-8"))
        self.assertEqual(new_pointer["session_id"], "codex-successor-0123456789abcdef")
        self.assertEqual(new_pointer["status"], "active")
        self.assertEqual(new_pointer["last_turn"], 0)

        # Verify new scratch-pad frontmatter carries previous_scratch_pad
        scratch_text = (
            self.root / ".agents" / "sessions" / "codex-successor-0123456789abcdef" / "scratch-pad.md"
        ).read_text(encoding="utf-8")
        self.assertIn(f"previous_scratch_pad: .agents/sessions/{sid1}/scratch-pad.md", scratch_text)

    def test_cli_malformed_json_exits_zero_without_output(self) -> None:
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.root)}
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH), "prompt"],
            input="{bad", text=True, capture_output=True, env=env, check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
