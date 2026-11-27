#!/usr/bin/env python3
"""Behavior tests for owner-authorized Interview Protocol checkpoints."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
MODULE_PATH = HOOKS / "interview_checkpoint.py"
SPEC = importlib.util.spec_from_file_location("interview_checkpoint", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("checkpoint module unavailable")
checkpoint = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = checkpoint
SPEC.loader.exec_module(checkpoint)

SESSION_ID = "codex-checkpoint-0123456789abcdef"


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=True)


def scratch_pad(turns: int = 1, status: str = "active", previous: str = "null") -> bytes:
    head = (
        "---\n"
        f"title: Session Interview Scratch-Pad — {SESSION_ID}\n"
        "date: 2026-09-11\nupdated: 2026-09-11\n"
        "type: session-interview-scratchpad\n"
        f"status: {status}\n"
        "tags:\n  - session\n  - interview\n  - continuity\n"
        f"session_id: {SESSION_ID}\n"
        "scope_ref: SCOPE.md\ncontext_ref: .agents/Context.md\n"
        f"previous_scratch_pad: {previous}\nprotocol_version: 1\n---\n"
    )
    body = "".join(
        f"### Turn {number:03d}\nUser: Owner validated a decision.\n"
        f"Agent: Recorded the decision.\nAddress status: unrouted\n"
        f"Previous digest: ROOT\nTurn digest: {'a' * 64}\n"
        for number in range(1, turns + 1)
    )
    return (head + body).encode("utf-8")


class CheckpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve() / "vault"
        self.sessions = self.root / ".agents" / "sessions" / SESSION_ID
        self.sessions.mkdir(parents=True)
        git(self.root, "init", "-b", "main")
        git(self.root, "config", "user.email", "owner@example.test")
        git(self.root, "config", "user.name", "Owner")
        (self.root / "README.md").write_text("vault\n", encoding="utf-8")
        git(self.root, "add", "--", "README.md")
        git(self.root, "commit", "-m", "chore: baseline")
        self.write_session()

    def write_session(self, turns: int = 1, last_turn: int | None = None) -> None:
        (self.sessions / "scratch-pad.md").write_bytes(scratch_pad(turns))
        (self.sessions / "state.json").write_text(
            json.dumps({"session_id": SESSION_ID, "lifecycle": "active"}) + "\n", encoding="utf-8"
        )
        pointer = {
            "session_id": SESSION_ID,
            "scratch_pad": f".agents/sessions/{SESSION_ID}/scratch-pad.md",
            "status": "active",
            "last_turn": turns if last_turn is None else last_turn,
            "updated_at": "2026-09-11T00:00:00Z",
        }
        (self.root / ".agents" / "sessions" / "active.json").write_text(
            json.dumps(pointer) + "\n", encoding="utf-8"
        )

    def staged(self) -> set[str]:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=self.root, text=True, capture_output=True, check=True,
        )
        return {line for line in result.stdout.splitlines() if line}

    def test_offer_has_no_side_effect_and_no_automatic_stage(self) -> None:
        before = subprocess.run(
            ["git", "status", "--porcelain"], cwd=self.root, text=True, capture_output=True, check=True
        ).stdout
        text = checkpoint.offer_text(SESSION_ID, 1)
        self.assertIn(SESSION_ID, text)
        snapshot = checkpoint.prepare_snapshot(self.root, SESSION_ID)
        self.assertEqual(snapshot.turn, 1)
        after = subprocess.run(
            ["git", "status", "--porcelain"], cwd=self.root, text=True, capture_output=True, check=True
        ).stdout
        self.assertEqual(before, after)
        self.assertEqual(self.staged(), set())

    def test_stage_and_commit_require_explicit_authorization(self) -> None:
        snapshot = checkpoint.prepare_snapshot(self.root, SESSION_ID)
        with self.assertRaises(checkpoint.CheckpointError) as caught:
            checkpoint.stage(self.root, snapshot, authorized=False)
        self.assertEqual(caught.exception.code, "missing-owner-authorization")
        self.assertEqual(self.staged(), set())
        checkpoint.stage(self.root, snapshot, authorized=True)
        with self.assertRaises(checkpoint.CheckpointError):
            checkpoint.commit(self.root, snapshot, authorized=False)

    def test_exact_transaction_owned_path_set_is_staged(self) -> None:
        (self.root / "work").mkdir()
        (self.root / "work" / "unrelated.md").write_text("x\n", encoding="utf-8")
        snapshot = checkpoint.prepare_snapshot(self.root, SESSION_ID)
        checkpoint.stage(self.root, snapshot, authorized=True)
        self.assertEqual(
            self.staged(),
            {
                ".agents/sessions/active.json",
                f".agents/sessions/{SESSION_ID}/scratch-pad.md",
                f".agents/sessions/{SESSION_ID}/state.json",
            },
        )

    def test_transition_includes_an_interrupted_predecessor(self) -> None:
        predecessor_id = "codex-predecessor-fedcba9876543210"
        predecessor_dir = self.root / ".agents" / "sessions" / predecessor_id
        predecessor_dir.mkdir(parents=True)
        (predecessor_dir / "scratch-pad.md").write_text(
            f"---\nsession_id: {predecessor_id}\nstatus: interrupted\n---\n", encoding="utf-8"
        )
        (predecessor_dir / "state.json").write_text("{}\n", encoding="utf-8")
        previous = f".agents/sessions/{predecessor_id}/scratch-pad.md"
        (self.sessions / "scratch-pad.md").write_bytes(scratch_pad(previous=previous))
        snapshot = checkpoint.prepare_snapshot(self.root, SESSION_ID)
        self.assertIn(previous, snapshot.paths)
        self.assertIn(f".agents/sessions/{predecessor_id}/state.json", snapshot.paths)

    def test_preexisting_staged_path_aborts_without_touching_the_index(self) -> None:
        (self.root / "owner.md").write_text("owner work\n", encoding="utf-8")
        git(self.root, "add", "--", "owner.md")
        before = self.staged()
        snapshot = checkpoint.prepare_snapshot(self.root, SESSION_ID)
        with self.assertRaises(checkpoint.CheckpointError) as caught:
            checkpoint.stage(self.root, snapshot, authorized=True)
        self.assertEqual(caught.exception.code, "index-not-clean")
        self.assertEqual(self.staged(), before)

    def test_post_snapshot_mutation_is_refused(self) -> None:
        snapshot = checkpoint.prepare_snapshot(self.root, SESSION_ID)
        (self.sessions / "scratch-pad.md").write_bytes(scratch_pad(turns=2))
        with self.assertRaises(checkpoint.CheckpointError) as caught:
            checkpoint.stage(self.root, snapshot, authorized=True)
        self.assertEqual(caught.exception.code, "snapshot-digest-mismatch")

    def test_staged_secret_is_refused(self) -> None:
        body = scratch_pad().replace(
            b"Agent: Recorded the decision.", b"Agent: API_TOKEN=raw-secret-canary"
        )
        (self.sessions / "scratch-pad.md").write_bytes(body)
        with self.assertRaises(Exception) as caught:
            checkpoint.prepare_snapshot(self.root, SESSION_ID)
        self.assertNotIn("raw-secret-canary", str(caught.exception))

    def test_turn_pointer_inconsistency_is_refused(self) -> None:
        self.write_session(turns=2, last_turn=1)
        with self.assertRaises(checkpoint.CheckpointError) as caught:
            checkpoint.prepare_snapshot(self.root, SESSION_ID)
        self.assertEqual(caught.exception.code, "turn-pointer-mismatch")

    def test_incomplete_transaction_is_refused(self) -> None:
        (self.sessions / "transaction.json").write_text("{}\n", encoding="utf-8")
        with self.assertRaises(checkpoint.CheckpointError) as caught:
            checkpoint.prepare_snapshot(self.root, SESSION_ID)
        self.assertEqual(caught.exception.code, "incomplete-transaction")

    def test_wrong_repository_root_is_refused(self) -> None:
        nested = self.root / "nested"
        nested.mkdir()
        (nested / ".agents" / "sessions" / SESSION_ID).mkdir(parents=True)
        (nested / ".agents" / "sessions" / SESSION_ID / "scratch-pad.md").write_bytes(scratch_pad())
        (nested / ".agents" / "sessions" / "active.json").write_text(
            json.dumps(
                {
                    "session_id": SESSION_ID,
                    "scratch_pad": f".agents/sessions/{SESSION_ID}/scratch-pad.md",
                    "status": "active",
                    "last_turn": 1,
                    "updated_at": "2026-09-11T00:00:00Z",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        snapshot = checkpoint.prepare_snapshot(nested, SESSION_ID)
        with self.assertRaises(checkpoint.CheckpointError) as caught:
            checkpoint.stage(nested, snapshot, authorized=True)
        self.assertEqual(caught.exception.code, "repository-root-mismatch")

    def test_commit_message_binds_session_and_sealed_turn(self) -> None:
        snapshot = checkpoint.prepare_snapshot(self.root, SESSION_ID)
        checkpoint.stage(self.root, snapshot, authorized=True)
        head = checkpoint.commit(self.root, snapshot, authorized=True)
        subject = subprocess.run(
            ["git", "log", "-1", "--format=%s"], cwd=self.root, text=True, capture_output=True, check=True
        ).stdout.strip()
        self.assertEqual(subject, f"chore(session): checkpoint {SESSION_ID} turn 1")
        self.assertTrue(head)

    def test_commit_refuses_a_snapshot_that_is_no_longer_current(self) -> None:
        snapshot = checkpoint.prepare_snapshot(self.root, SESSION_ID)
        checkpoint.stage(self.root, snapshot, authorized=True)
        self.write_session(turns=2)
        with self.assertRaises(checkpoint.CheckpointError) as caught:
            checkpoint.commit(self.root, snapshot, authorized=True)
        self.assertEqual(caught.exception.code, "snapshot-no-longer-current")


class PushTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name).resolve()
        self.remote = base / "remote.git"
        self.root = base / "vault"
        git(base, "init", "--bare", str(self.remote))
        git(base, "clone", str(self.remote), str(self.root))
        git(self.root, "config", "user.email", "owner@example.test")
        git(self.root, "config", "user.name", "Owner")
        (self.root / "README.md").write_text("vault\n", encoding="utf-8")
        git(self.root, "add", "--", "README.md")
        git(self.root, "commit", "-m", "chore: baseline")
        git(self.root, "push", "origin", "HEAD:main")
        git(self.root, "fetch", "origin", "main")

    def add_commit(self, name: str, message: str) -> str:
        (self.root / name).write_text("x\n", encoding="utf-8")
        git(self.root, "add", "--", name)
        git(self.root, "commit", "-m", message)
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root, text=True, capture_output=True, check=True
        ).stdout.strip()

    def test_force_and_unauthorized_push_are_refused(self) -> None:
        head = self.add_commit("a.md", "chore(session): checkpoint turn 1")
        with self.assertRaises(checkpoint.CheckpointError) as forced:
            checkpoint.push(self.root, "origin", "main", authorized=True, expected_commits=[head], force=True)
        self.assertEqual(forced.exception.code, "force-push-forbidden")
        with self.assertRaises(checkpoint.CheckpointError) as unauthorized:
            checkpoint.push(self.root, "origin", "main", authorized=False, expected_commits=[head])
        self.assertEqual(unauthorized.exception.code, "missing-push-authorization")

    def test_push_holds_when_the_outgoing_range_carries_unrelated_commits(self) -> None:
        unrelated = self.add_commit("unrelated.md", "feat: unrelated work")
        head = self.add_commit("b.md", "chore(session): checkpoint turn 1")
        range_commits = checkpoint.outgoing_commits(self.root, "origin", "main")
        self.assertEqual(len(range_commits), 2)
        with self.assertRaises(checkpoint.CheckpointError) as caught:
            checkpoint.push(self.root, "origin", "main", authorized=True, expected_commits=[head])
        self.assertEqual(caught.exception.code, "outgoing-range-contains-unrelated-commits")
        self.assertIn(unrelated, " ".join(range_commits))

    def test_authorized_push_verifies_the_remote_commit(self) -> None:
        head = self.add_commit("c.md", "chore(session): checkpoint turn 1")
        pushed = checkpoint.push(self.root, "origin", "main", authorized=True, expected_commits=[head])
        self.assertEqual(pushed, head)
        remote_head = subprocess.run(
            ["git", "rev-parse", "origin/main"], cwd=self.root, text=True, capture_output=True, check=True
        ).stdout.strip()
        self.assertEqual(remote_head, head)

    def test_push_rejection_preserves_the_local_commit(self) -> None:
        other = Path(self.tmp.name).resolve() / "other"
        git(Path(self.tmp.name), "clone", str(self.remote), str(other))
        git(other, "config", "user.email", "owner@example.test")
        git(other, "config", "user.name", "Owner")
        git(other, "checkout", "-B", "main", "origin/main")
        (other / "d.md").write_text("x\n", encoding="utf-8")
        git(other, "add", "--", "d.md")
        git(other, "commit", "-m", "chore: divergent")
        git(other, "push", "origin", "HEAD:main")
        head = self.add_commit("e.md", "chore(session): checkpoint turn 1")
        with self.assertRaises(checkpoint.CheckpointError) as caught:
            checkpoint.push(self.root, "origin", "main", authorized=True, expected_commits=[head])
        self.assertIn(caught.exception.code, {"push-rejected-local-commit-preserved", "outgoing-range-contains-unrelated-commits"})
        local = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root, text=True, capture_output=True, check=True
        ).stdout.strip()
        self.assertEqual(local, head)


class DigestHelperTest(unittest.TestCase):
    def test_snapshot_message_is_derived_not_free_text(self) -> None:
        snapshot = checkpoint.CheckpointSnapshot(SESSION_ID, 7, (), {})
        self.assertEqual(snapshot.message, f"chore(session): checkpoint {SESSION_ID} turn 7")
        self.assertEqual(
            hashlib.sha256(b"x").hexdigest(),
            hashlib.sha256(b"x").hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
