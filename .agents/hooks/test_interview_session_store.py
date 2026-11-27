#!/usr/bin/env python3
"""Behavior tests for the canonical Interview Protocol session store."""

from __future__ import annotations

import importlib.util
import json
import multiprocessing
import os
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

HOOKS_DIR = Path(__file__).resolve().parent
MODULE_PATH = HOOKS_DIR / "interview_session_store.py"
SPEC = importlib.util.spec_from_file_location("interview_session_store", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("session store module is unavailable")
store = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = store
SPEC.loader.exec_module(store)


def _competing_lease(vault: str, queue: multiprocessing.Queue) -> None:
    module_spec = importlib.util.spec_from_file_location("child_store", MODULE_PATH)
    assert module_spec and module_spec.loader
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    try:
        lease = module.acquire_writer_lease(Path(vault), "child", stale_after=60)
    except module.SessionStoreError as exc:
        queue.put(exc.code)
    else:
        lease.release()
        queue.put("acquired")


class SessionIdentityTest(unittest.TestCase):
    def test_identity_is_repeatable_runtime_bound_and_collision_resistant(self) -> None:
        first = store.canonical_session_id("Claude Code", "a/b")
        self.assertEqual(first, store.canonical_session_id("Claude Code", "a/b"))
        self.assertNotEqual(first, store.canonical_session_id("Claude Code", "a_b"))
        self.assertNotEqual(first, store.canonical_session_id("Codex", "a/b"))
        self.assertRegex(first, r"^claude-code-[a-z0-9-]+-[a-f0-9]{16}$")
        self.assertLessEqual(len(first), 144)

    def test_identity_rejects_unusable_raw_ids(self) -> None:
        for value in ("", "unknown", "UNKNOWN", "unavailable", "x\x00y", "x" * 4097):
            with self.subTest(value=value[:20]):
                with self.assertRaises(store.SessionStoreError):
                    store.canonical_session_id("codex", value)

    def test_unicode_variants_do_not_collide(self) -> None:
        self.assertNotEqual(
            store.canonical_session_id("codex", "é"),
            store.canonical_session_id("codex", "e\u0301"),
        )


class PathContainmentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name).resolve()
        (self.vault / ".agents" / "sessions").mkdir(parents=True)
        self.sid = store.canonical_session_id("codex", "session-alpha")
        self.session_dir = self.vault / ".agents" / "sessions" / self.sid
        self.session_dir.mkdir()
        self.scratch = self.session_dir / "scratch-pad.md"
        self.scratch.write_text(f"---\nsession_id: {self.sid}\n---\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_accepts_exact_canonical_path_from_nested_cwd(self) -> None:
        nested = self.vault / "a" / "b"
        nested.mkdir(parents=True)
        relative = f".agents/sessions/{self.sid}/scratch-pad.md"
        self.assertEqual(
            store.resolve_scratch_pad(self.vault, relative, expected_session_id=self.sid),
            self.scratch.resolve(),
        )

    def test_rejects_lexical_escape_and_alternate_forms(self) -> None:
        invalid = (
            str(self.scratch), "../scratch-pad.md", ".agents/../scratch-pad.md",
            f".agents\\sessions\\{self.sid}\\scratch-pad.md",
            f".agents/sessions/%2e%2e/{self.sid}/scratch-pad.md",
            f"C:/vault/.agents/sessions/{self.sid}/scratch-pad.md",
            f".agents/sessions/{self.sid}/other.md",
        )
        for path in invalid:
            with self.subTest(path=path):
                with self.assertRaises(store.SessionStoreError):
                    store.resolve_scratch_pad(self.vault, path, expected_session_id=self.sid)

    def test_rejects_symlinked_directory_and_scratch_pad(self) -> None:
        outside = Path(self.tmp.name).parent / f"outside-{os.getpid()}"
        outside.mkdir(exist_ok=True)
        try:
            other_sid = store.canonical_session_id("codex", "other")
            link_dir = self.vault / ".agents" / "sessions" / other_sid
            link_dir.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(store.SessionStoreError):
                store.resolve_scratch_pad(
                    self.vault,
                    f".agents/sessions/{other_sid}/scratch-pad.md",
                    expected_session_id=other_sid,
                )
            self.scratch.unlink()
            target = outside / "scratch-pad.md"
            target.write_text("---\n---\n", encoding="utf-8")
            self.scratch.symlink_to(target)
            with self.assertRaises(store.SessionStoreError):
                store.resolve_scratch_pad(
                    self.vault,
                    f".agents/sessions/{self.sid}/scratch-pad.md",
                    expected_session_id=self.sid,
                )
        finally:
            for child in outside.iterdir():
                child.unlink()
            outside.rmdir()

    def test_rejects_pointer_and_frontmatter_identity_mismatch(self) -> None:
        wrong = store.canonical_session_id("codex", "wrong")
        with self.assertRaises(store.SessionStoreError):
            store.resolve_scratch_pad(
                self.vault,
                f".agents/sessions/{self.sid}/scratch-pad.md",
                expected_session_id=wrong,
            )
        self.scratch.write_text(f"---\nsession_id: {wrong}\n---\n", encoding="utf-8")
        with self.assertRaises(store.SessionStoreError):
            store.resolve_scratch_pad(
                self.vault,
                f".agents/sessions/{self.sid}/scratch-pad.md",
                expected_session_id=self.sid,
            )


class AtomicWriteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.target = self.root / "state.json"
        self.old = b'{"version":"old"}\n'
        self.new = b'{"version":"new"}\n'
        self.target.write_bytes(self.old)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_atomic_write_replaces_bytes_with_restrictive_permissions(self) -> None:
        store.atomic_write_bytes(self.target, self.new)
        self.assertEqual(self.target.read_bytes(), self.new)
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o600)
        self.assertFalse(any(p.name.startswith(".state.json.") for p in self.root.iterdir()))

    def test_failures_leave_old_or_complete_new_state(self) -> None:
        fault_points = ("open", "flush", "file_fsync", "replace", "directory_fsync")
        for point in fault_points:
            with self.subTest(point=point):
                self.target.write_bytes(self.old)
                with self.assertRaises(store.SessionStoreError):
                    store.atomic_write_bytes(self.target, self.new, fault_at=point)
                self.assertIn(self.target.read_bytes(), (self.old, self.new))
                self.assertFalse(any(p.name.startswith(".state.json.") for p in self.root.iterdir()))

    def test_atomic_json_is_canonical_and_scanned_before_write(self) -> None:
        scanner = mock.Mock()
        store.atomic_write_json(self.target, {"b": 2, "a": 1}, scanner=scanner)
        self.assertEqual(self.target.read_bytes(), b'{"a":1,"b":2}\n')
        scanner.assert_called_once_with(b'{"a":1,"b":2}\n')


class WriterLeaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name)
        (self.vault / ".agents" / "sessions").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_two_processes_cannot_own_writer_lease(self) -> None:
        lease = store.acquire_writer_lease(self.vault, "parent", stale_after=60)
        queue: multiprocessing.Queue = multiprocessing.Queue()
        proc = multiprocessing.Process(target=_competing_lease, args=(str(self.vault), queue))
        proc.start()
        proc.join(10)
        self.assertEqual(proc.exitcode, 0)
        self.assertEqual(queue.get(timeout=2), "conflict")
        lease.release()

    def test_stale_lease_requires_explicit_takeover(self) -> None:
        lease = store.acquire_writer_lease(self.vault, "old", stale_after=0)
        lease.close_lock_only_for_test()
        with self.assertRaises(store.SessionStoreError) as caught:
            store.acquire_writer_lease(self.vault, "new", stale_after=0)
        self.assertEqual(caught.exception.code, "stale-lease")
        replacement = store.acquire_writer_lease(
            self.vault, "new", stale_after=0, allow_stale_takeover=True
        )
        replacement.release()


class TurnTransactionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sid = store.canonical_session_id("codex", "turn-session")
        self.state = {
            "protocol_version": 1,
            "session_id": self.sid,
            "lifecycle": "active",
            "turn_state": "active",
            "pending_turn": None,
            "event_nonce": None,
            "lease": None,
        }

    @staticmethod
    def redact(value: str) -> tuple[str, tuple[str, ...]]:
        return value.replace("secret", "[REDACTED-CREDENTIAL]"), ()

    @staticmethod
    def scan(value: bytes) -> None:
        if b"secret" in value:
            raise ValueError("unsafe")

    def prepare(self, number: int = 1, nonce: str = "nonce-1"):
        pending = store.open_turn(self.state, self.sid, nonce, number - 1)
        return store.prepare_turn(
            pending, self.sid, number, nonce, ("owner secret",), ("agent summary",),
            redact=self.redact, scanner=self.scan,
        )

    def test_active_pending_prepared_sealed_active_and_idempotent_events(self) -> None:
        prepared_state, prepared = self.prepare()
        self.assertEqual(prepared_state["turn_state"], "prepared")
        sealed_state, body, digest = store.seal_turn(prepared_state, b"", prepared)
        self.assertEqual(sealed_state["turn_state"], "active")
        self.assertNotIn(b"secret", body)
        self.assertEqual(store.verify_event_chain(body), (digest, 1))
        repeated_state, repeated_body, repeated_digest = store.seal_turn(
            sealed_state, body, prepared
        )
        self.assertEqual((repeated_state, repeated_body, repeated_digest), (sealed_state, body, digest))

    def test_rejects_wrong_missing_duplicate_replayed_and_skipped_events(self) -> None:
        pending = store.open_turn(self.state, self.sid, "nonce-1", 0)
        self.assertEqual(pending, store.open_turn(pending, self.sid, "nonce-1", 0))
        cases = (("wrong", 1, "nonce-1"), (self.sid, 2, "nonce-1"), (self.sid, 1, "other"))
        for sid, number, nonce in cases:
            with self.subTest(sid=sid, number=number, nonce=nonce):
                with self.assertRaises(store.SessionStoreError):
                    store.prepare_turn(pending, sid, number, nonce, ("u",), ("a",), redact=self.redact, scanner=self.scan)

    def test_detects_every_immutable_body_mutation(self) -> None:
        prepared_state, prepared = self.prepare()
        _, body, _ = store.seal_turn(prepared_state, b"", prepared)
        mutations = (
            body.replace(b"owner", b"other"), body[:-1], body.replace(b"User: ", b""),
            b"injected\n" + body, body.replace(b"Agent: agent summary\n", b""),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation[:20]):
                with self.assertRaises((store.SessionStoreError, UnicodeError)):
                    store.verify_event_chain(mutation)

    def test_limits_count_only_content_lines(self) -> None:
        pending = store.open_turn(self.state, self.sid, "nonce", 0)
        with self.assertRaises(store.SessionStoreError):
            store.prepare_turn(pending, self.sid, 1, "nonce", ("1", "2", "3"), ("4", "5", "6"), redact=self.redact, scanner=self.scan)
        with self.assertRaises(store.SessionStoreError):
            store.prepare_turn(pending, self.sid, 1, "nonce", ("x" * 155,), ("a",), redact=self.redact, scanner=self.scan)

    def test_correction_and_routing_are_append_only_and_latest_digest_wins(self) -> None:
        prepared_state, prepared = self.prepare()
        _, original, _ = store.seal_turn(prepared_state, b"", prepared)
        corrected, correction_digest = store.append_chain_event(
            original, "Correction to Turn 001", (("Correct meaning", "new meaning"),)
        )
        routed, routing_digest = store.append_chain_event(
            corrected,
            "Routing Resolution for Turn 001",
            (("Agent proposal", "concept/x"), ("Owner resolution", "concept/y"), ("Disposition", "active")),
        )
        self.assertTrue(corrected.startswith(original))
        self.assertTrue(routed.startswith(corrected))
        self.assertNotEqual(correction_digest, routing_digest)
        self.assertEqual(store.verify_event_chain(routed)[0], routing_digest)
        projection = store.project_event_chain(routed)
        self.assertEqual(projection[1]["meaning"], "new meaning")
        self.assertEqual(projection[1]["address"], "concept/y")
        self.assertEqual(projection[1]["disposition"], "active")


class SessionRecoveryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name)
        self.sessions = self.vault / ".agents" / "sessions"
        self.sessions.mkdir(parents=True)
        self.old_sid = store.canonical_session_id("codex", "old-session")
        self.new_sid = store.canonical_session_id("codex", "new-session")
        self.old_relative = f".agents/sessions/{self.old_sid}/scratch-pad.md"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def reset_sessions(self) -> None:
        for child in self.sessions.iterdir():
            if child.is_dir():
                for nested in child.iterdir():
                    nested.unlink()
                child.rmdir()
            else:
                child.unlink()

    def write_session(self, sid: str, lifecycle: str, heartbeat: datetime) -> bytes:
        directory = self.sessions / sid
        directory.mkdir(parents=True, exist_ok=True)
        scratch = (
            "---\n"
            f"title: Session Interview Scratch-Pad — {sid}\n"
            "date: 2026-09-11\nupdated: 2026-09-11\n"
            "type: session-interview-scratchpad\n"
            f"status: {lifecycle}\n"
            "tags:\n  - session\n  - interview\n  - continuity\n"
            f"session_id: {sid}\nscope_ref: SCOPE.md\ncontext_ref: .agents/Context.md\n"
            "previous_scratch_pad: null\nprotocol_version: 1\n---\n"
        ).encode()
        (directory / "scratch-pad.md").write_bytes(scratch)
        timestamp = heartbeat.isoformat().replace("+00:00", "Z")
        state = {
            "protocol_version": 1, "session_id": sid, "lifecycle": lifecycle,
            "turn_state": "active", "pending_turn": None, "event_nonce": None,
            "lease": {"owner": sid, "acquired_at": timestamp, "heartbeat_at": timestamp},
        }
        (directory / "state.json").write_bytes(store.canonical_json_bytes(state))
        return scratch

    def write_pointer(self, sid: str, lifecycle: str) -> None:
        pointer = {
            "session_id": sid,
            "scratch_pad": f".agents/sessions/{sid}/scratch-pad.md",
            "status": lifecycle,
            "last_turn": 0,
            "updated_at": "2026-09-11T00:00:00Z",
        }
        (self.sessions / "active.json").write_bytes(store.canonical_json_bytes(pointer))

    def test_recovery_matrix_no_pointer_and_unknown_identity(self) -> None:
        no_active = store.recover_session(self.vault, "codex", "new-session")
        self.assertEqual(no_active.action, "no-active")
        self.assertIsNone(no_active.scratch_pad_bytes)
        unavailable = store.recover_session(self.vault, "codex", "unknown")
        self.assertEqual(unavailable.action, "unavailable")
        self.assertFalse((self.sessions / "active.json").exists())

    def test_same_identity_live_lease_continues_with_full_readback(self) -> None:
        scratch = self.write_session(self.old_sid, "active", datetime.now(UTC))
        self.write_pointer(self.old_sid, "active")
        result = store.recover_session(self.vault, "codex", "old-session", stale_after=60)
        self.assertEqual(result.action, "continued")
        self.assertEqual(result.scratch_pad_bytes, scratch)
        self.assertEqual(result.session_id, self.old_sid)

    def test_same_identity_requires_live_lease_and_matching_pointer_state(self) -> None:
        stale = datetime.now(UTC) - timedelta(hours=1)
        self.write_session(self.old_sid, "active", stale)
        self.write_pointer(self.old_sid, "active")
        result = store.recover_session(self.vault, "codex", "old-session", stale_after=1)
        self.assertEqual(result.action, "faulted")
        self.assertEqual(result.diagnostic, "stale-lease-continuity")
        state_path = self.sessions / self.old_sid / "state.json"
        state = json.loads(state_path.read_text())
        state["lifecycle"] = "closing"
        state_path.write_bytes(store.canonical_json_bytes(state))
        mismatch = store.recover_session(self.vault, "codex", "old-session")
        self.assertEqual(mismatch.action, "faulted")
        self.assertEqual(mismatch.diagnostic, "pointer-state-mismatch")

    def test_crashed_closing_session_recovers_as_interrupted(self) -> None:
        stale = datetime.now(UTC) - timedelta(hours=1)
        scratch = self.write_session(self.old_sid, "closing", stale)
        self.write_pointer(self.old_sid, "closing")
        result = store.recover_session(self.vault, "codex", "old-session", stale_after=1)
        self.assertEqual(result.action, "interrupted")
        self.assertEqual(result.predecessor_bytes, scratch)
        state = json.loads((self.sessions / self.old_sid / "state.json").read_text())
        pointer = json.loads((self.sessions / "active.json").read_text())
        self.assertEqual((state["lifecycle"], pointer["status"]), ("interrupted", "interrupted"))

    def test_different_identity_live_lease_conflicts_without_pointer_change(self) -> None:
        self.write_session(self.old_sid, "active", datetime.now(UTC))
        self.write_pointer(self.old_sid, "active")
        before = (self.sessions / "active.json").read_bytes()
        result = store.recover_session(self.vault, "codex", "new-session", stale_after=60)
        self.assertEqual(result.action, "conflict")
        self.assertEqual((self.sessions / "active.json").read_bytes(), before)
        old_state = json.loads((self.sessions / self.old_sid / "state.json").read_text())
        self.assertEqual(old_state["lifecycle"], "active")

    def test_stale_active_or_closing_predecessor_is_interrupted_and_succeeded(self) -> None:
        stale = datetime.now(UTC) - timedelta(hours=1)
        for lifecycle in ("active", "closing"):
            with self.subTest(lifecycle=lifecycle):
                self.reset_sessions()
                predecessor = self.write_session(self.old_sid, lifecycle, stale)
                self.write_pointer(self.old_sid, lifecycle)
                result = store.recover_session(self.vault, "codex", "new-session", stale_after=1)
                self.assertEqual(result.action, "succeeded")
                self.assertEqual(result.predecessor_bytes, predecessor)
                self.assertEqual(result.session_id, self.new_sid)
                pointer = json.loads((self.sessions / "active.json").read_text())
                self.assertEqual(pointer["session_id"], self.new_sid)
                old_state = json.loads((self.sessions / self.old_sid / "state.json").read_text())
                self.assertEqual(old_state["lifecycle"], "interrupted")

    def test_closed_or_interrupted_predecessor_reads_without_successor(self) -> None:
        for lifecycle in ("closed", "interrupted"):
            with self.subTest(lifecycle=lifecycle):
                self.reset_sessions()
                scratch = self.write_session(self.old_sid, lifecycle, datetime.now(UTC))
                self.write_pointer(self.old_sid, lifecycle)
                result = store.recover_session(self.vault, "codex", "new-session")
                self.assertEqual(result.action, "predecessor-only")
                self.assertEqual(result.predecessor_bytes, scratch)
                self.assertFalse((self.sessions / self.new_sid).exists())

    def test_missing_target_and_malformed_pointer_fail_closed(self) -> None:
        self.write_pointer(self.old_sid, "active")
        result = store.recover_session(self.vault, "codex", "new-session")
        self.assertEqual(result.action, "faulted")
        (self.sessions / "active.json").write_text("{bad json", encoding="utf-8")
        result = store.recover_session(self.vault, "codex", "new-session")
        self.assertEqual(result.action, "faulted")

    def test_malformed_state_or_lease_never_triggers_guessed_interruption(self) -> None:
        for mutation in (
            lambda state: state.pop("lease"),
            lambda state: state["lease"].update(heartbeat_at="not-a-date"),
            lambda state: state.update(extra=True),
        ):
            with self.subTest(mutation=mutation):
                self.reset_sessions()
                self.write_session(self.old_sid, "active", datetime.now(UTC))
                self.write_pointer(self.old_sid, "active")
                state_path = self.sessions / self.old_sid / "state.json"
                original_pointer = (self.sessions / "active.json").read_bytes()
                state = json.loads(state_path.read_text())
                mutation(state)
                state_path.write_bytes(store.canonical_json_bytes(state))
                result = store.recover_session(self.vault, "codex", "new-session")
                self.assertEqual(result.action, "faulted")
                self.assertEqual((self.sessions / "active.json").read_bytes(), original_pointer)

    def test_multifile_transition_recovers_idempotently_from_every_boundary(self) -> None:
        stale = datetime.now(UTC) - timedelta(hours=1)
        for fault in ("predecessor", "successor-scratch", "successor-state", "pointer"):
            with self.subTest(fault=fault):
                self.reset_sessions()
                old_body = self.write_session(self.old_sid, "active", stale)
                self.write_pointer(self.old_sid, "active")
                first = store.recover_session(
                    self.vault, "codex", "new-session", stale_after=1, fault_at=fault
                )
                self.assertEqual(first.action, "faulted")
                transaction_path = self.sessions / self.new_sid / "transaction.json"
                self.assertEqual(json.loads(transaction_path.read_text())["phase"], "applying")
                second = store.recover_session(self.vault, "codex", "new-session", stale_after=1)
                self.assertEqual(second.action, "succeeded")
                snapshot = {p.relative_to(self.sessions).as_posix(): p.read_bytes() for p in self.sessions.rglob("*") if p.is_file()}
                third = store.recover_session(self.vault, "codex", "new-session", stale_after=1)
                self.assertEqual(third.action, "continued")
                self.assertEqual(snapshot, {p.relative_to(self.sessions).as_posix(): p.read_bytes() for p in self.sessions.rglob("*") if p.is_file()})
                self.assertEqual(old_body, first.predecessor_bytes)

    def assert_closed(self) -> None:
        state = json.loads((self.sessions / self.old_sid / "state.json").read_text())
        pointer = json.loads((self.sessions / "active.json").read_text())
        self.assertEqual((state["lifecycle"], pointer["status"]), ("closed", "closed"))

    def test_malformed_recovery_transaction_fails_closed(self) -> None:
        stale = datetime.now(UTC) - timedelta(hours=1)
        self.write_session(self.old_sid, "active", stale)
        self.write_pointer(self.old_sid, "active")
        first = store.recover_session(
            self.vault, "codex", "new-session", stale_after=1, fault_at="predecessor"
        )
        self.assertEqual(first.action, "faulted")
        transaction = self.sessions / self.new_sid / "transaction.json"
        transaction.write_text('{"phase":"invented"}\n', encoding="utf-8")
        pointer_before = (self.sessions / "active.json").read_bytes()
        recovered = store.recover_session(self.vault, "codex", "new-session", stale_after=1)
        self.assertEqual(recovered.action, "faulted")
        self.assertEqual(recovered.diagnostic, "malformed-transaction")
        self.assertEqual((self.sessions / "active.json").read_bytes(), pointer_before)

    def test_begin_close_recovers_at_every_boundary(self) -> None:
        for fault in ("state", "scratch", "pointer"):
            with self.subTest(fault=fault):
                self.reset_sessions()
                self.write_session(self.old_sid, "active", datetime.now(UTC))
                self.write_pointer(self.old_sid, "active")
                with self.assertRaises(store.SessionStoreError):
                    store.close_session(self.vault, self.old_sid, final=False, fault_at=fault)
                store.close_session(self.vault, self.old_sid, final=False)
                store.close_session(self.vault, self.old_sid, final=True)
                self.assert_closed()

    def test_final_close_recovers_at_every_boundary_and_is_idempotent(self) -> None:
        for fault in ("state", "scratch", "pointer"):
            with self.subTest(fault=fault):
                self.reset_sessions()
                self.write_session(self.old_sid, "active", datetime.now(UTC))
                self.write_pointer(self.old_sid, "active")
                store.close_session(self.vault, self.old_sid, final=False)
                with self.assertRaises(store.SessionStoreError):
                    store.close_session(self.vault, self.old_sid, final=True, fault_at=fault)
                store.close_session(self.vault, self.old_sid, final=True)
                store.close_session(self.vault, self.old_sid, final=True)
                self.assert_closed()


if __name__ == "__main__":
    unittest.main()
