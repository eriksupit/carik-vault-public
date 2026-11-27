#!/usr/bin/env python3
"""Thin lifecycle command entry point for the Interview Protocol.

Storage, identity, redaction, containment, and transaction mechanics remain owned by
``interview_session_store`` and ``interview_credential_redactor``.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

HOOKS_DIR = Path(__file__).resolve().parent
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

import interview_credential_redactor as redactor  # noqa: E402
import interview_session_store as store  # noqa: E402


CAPABILITY_PATH = HOOKS_DIR / "interview-capability.json"


def _unavailable() -> dict[str, object]:
    return {"status": "unavailable"}


def capability_report() -> dict[str, object]:
    """Report each capability independently; wiring alone never yields `proven`."""

    registry = json.loads(CAPABILITY_PATH.read_text(encoding="utf-8"))
    capabilities = list(registry["capabilities"])
    report: dict[str, object] = {"status": "capability-report", "runtimes": {}}
    runtimes = report["runtimes"]
    assert isinstance(runtimes, dict)
    for runtime, declared in registry["runtimes"].items():
        probes = declared.get("probes") or {}
        measured = {}
        for capability in capabilities:
            status = declared["capability_status"].get(capability, "unavailable")
            if status == "proven" and not probes.get(capability):
                status = "partial"
            measured[capability] = status
        runtimes[runtime] = {"posture": declared["posture"], "capability_status": measured}
    return report


def _blocked(code: str, session_id: str | None = None) -> dict[str, object]:
    suffix = f":.agents/sessions/{session_id}" if session_id else ""
    return {
        "decision": "block",
        "reason": f"{code}{suffix}",
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "additionalContext": "Interview continuity is blocked until the named condition is repaired.",
        },
    }


def _common(payload: dict[str, object]) -> tuple[str, str]:
    runtime = payload.get("runtime")
    raw_session_id = payload.get("session_id")
    if not isinstance(runtime, str) or not runtime or not isinstance(raw_session_id, str) or not raw_session_id:
        raise store.SessionStoreError("unavailable-session-identity")
    return runtime, raw_session_id


def _canonical(payload: dict[str, object]) -> tuple[str, str, str]:
    runtime, raw_session_id = _common(payload)
    return runtime, raw_session_id, store.canonical_session_id(runtime, raw_session_id)


def _nonce(payload: dict[str, object]) -> str:
    nonce = payload.get("event_nonce")
    if isinstance(nonce, str) and nonce:
        return nonce
    prompt = payload.get("prompt")
    if isinstance(prompt, str) and prompt:
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:32]
        return f"prompt-{digest}"
    raise store.SessionStoreError("missing-event-nonce")


def _turn(payload: dict[str, object]) -> int:
    turn = payload.get("turn")
    if not isinstance(turn, int) or isinstance(turn, bool) or turn < 1:
        raise store.SessionStoreError("missing-turn-number")
    return turn


def _lines(payload: dict[str, object], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not value or any(not isinstance(line, str) for line in value):
        raise store.SessionStoreError("missing-prepared-pair")
    return tuple(value)


def _is_proven_active(root: Path) -> bool:
    pointer = root / ".agents" / "sessions" / "active.json"
    if not pointer.is_file():
        return False
    try:
        value = json.loads(pointer.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return True
    return isinstance(value, dict) and value.get("status") in {
        "initializing", "active", "closing", "faulted", "conflict"
    }


def _recovery_response(result: store.RecoveryResult) -> dict[str, object]:
    if result.action == "unavailable":
        return _unavailable()
    if result.action in {"faulted", "conflict"}:
        return _blocked(result.diagnostic or result.action, result.session_id)
    response: dict[str, object] = {"status": result.action}
    if result.session_id is not None:
        response["session_id"] = result.session_id
    continuity = result.scratch_pad_bytes or result.predecessor_bytes
    if continuity is not None:
        response["additionalContext"] = continuity.decode("utf-8", errors="strict")
    return response


def handle(mode: str, payload: dict[str, object], *, root: Path) -> dict[str, object]:
    """Translate one lifecycle event into a bounded runtime-neutral response."""

    root = root.resolve(strict=True)
    bounded_session_id: str | None = None
    try:
        if mode == "session-start":
            runtime, raw_session_id = _common(payload)
            return _recovery_response(store.recover_session(root, runtime, raw_session_id))

        if mode == "activate":
            runtime, raw_session_id, session_id = _canonical(payload)
            store.activate_session(root, runtime, raw_session_id)
            nonce = payload.get("event_nonce")
            if nonce is not None:
                if not isinstance(nonce, str) or not nonce:
                    raise store.SessionStoreError("missing-event-nonce")
                turn = store.persist_open_turn(root, session_id, nonce)
                return {"status": "pending", "session_id": session_id, "turn": turn}
            return {"status": "active", "session_id": session_id}

        runtime, raw_session_id, session_id = _canonical(payload)
        bounded_session_id = session_id
        del runtime, raw_session_id
        lifecycle = store.session_lifecycle(root, session_id)

        if mode == "prompt":
            if lifecycle == "faulted":
                return _blocked("faulted-session", session_id)
            turn = store.persist_open_turn(root, session_id, _nonce(payload))
            return {"status": "pending", "session_id": session_id, "turn": turn}

        if mode == "verify":
            if lifecycle == "faulted":
                return {"status": "faulted", "session_id": session_id}
            turn_state, pending, _ = store.open_turn_metadata(root, session_id)
            if turn_state in {"pending", "prepared"}:
                return _blocked(f"unsealed-turn-{pending}", session_id)
            return {"status": "verified", "session_id": session_id}

        if mode == "prepare":
            store.persist_prepared_turn(
                root,
                session_id,
                _turn(payload),
                _nonce(payload),
                _lines(payload, "user_lines"),
                _lines(payload, "agent_lines"),
                redact=redactor.redact_text,
                scanner=redactor.assert_destination_safe,
            )
            return {"status": "prepared", "session_id": session_id, "turn": payload["turn"]}

        if mode == "stop":
            if lifecycle == "faulted":
                return {"status": "faulted", "session_id": session_id}
            _, pending_turn, pending_nonce = store.open_turn_metadata(root, session_id)
            if payload.get("turn") is None and pending_turn is not None:
                payload["turn"] = pending_turn
            if payload.get("event_nonce") is None and pending_nonce is not None:
                payload["event_nonce"] = pending_nonce
            try:
                status = store.persist_sealed_turn(
                    root,
                    session_id,
                    _turn(payload),
                    _nonce(payload),
                    _lines(payload, "user_lines"),
                    _lines(payload, "agent_lines"),
                    redact=redactor.redact_text,
                    scanner=redactor.assert_destination_safe,
                )
            except store.SessionStoreError as exc:
                if exc.code in {
                    "missing-prepared-pair",
                    "missing-turn-number",
                    "missing-event-nonce",
                    "prepared-pair-mismatch",
                }:
                    return _blocked(exc.code, session_id)
                try:
                    store.mark_session_faulted(root, session_id)
                except Exception:
                    return _blocked("fault-transition-failed", session_id)
                return {
                    "status": "faulted",
                    "session_id": session_id,
                    "diagnostic": "interview-session:faulted",
                    "semantic": False,
                }
            return {"status": status, "session_id": session_id, "turn": payload["turn"]}

        return _unavailable()
    except Exception as exc:
        if _is_proven_active(root):
            if isinstance(exc, (store.SessionStoreError, redactor.CredentialSafetyError)):
                return _blocked(str(exc), bounded_session_id)
            return _blocked("malformed-protected-state", bounded_session_id)
        return _unavailable()


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload: Any = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            return 0
        mode = sys.argv[1].lower() if len(sys.argv) > 1 else str(payload.get("hook_event_name") or "").lower()
        if len(sys.argv) > 2 and sys.argv[2]:
            payload.setdefault("runtime", sys.argv[2])
        else:
            payload.setdefault("runtime", os.environ.get("HARNESS_RUNTIME", "codex"))
        if len(sys.argv) > 3 and sys.argv[3]:
            payload.setdefault("session_id", sys.argv[3])
        elif not payload.get("session_id"):
            env_sid = os.environ.get("SESSION_ID") or os.environ.get("CLAUDE_CONVERSATION_ID") or os.environ.get("CODEX_SESSION_ID")
            if env_sid:
                payload["session_id"] = env_sid
            elif mode == "activate":
                import uuid
                payload["session_id"] = f"auto-{uuid.uuid4().hex[:16]}"
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
        if mode == "capability":
            json.dump(capability_report(), sys.stdout, separators=(",", ":"))
            return 0
        response = handle(mode, payload, root=root)
        json.dump(response, sys.stdout, separators=(",", ":"))
        return 0
    except Exception:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
