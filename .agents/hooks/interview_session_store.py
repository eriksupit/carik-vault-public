#!/usr/bin/env python3
"""Canonical identity, containment, atomic-write, and writer-lease primitives."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import tempfile
import time
import unicodedata
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from types import TracebackType
from typing import BinaryIO, Callable, cast
from urllib.parse import unquote

MAX_RAW_SESSION_ID_BYTES = 4096
MAX_CANONICAL_ID_LENGTH = 144
UNKNOWN_SESSION_IDS = frozenset({"unknown", "unavailable", "none", "null"})
_CANONICAL_ID = re.compile(
    r"^[a-z0-9]+(?:-[a-z0-9]+)*-[a-z0-9]+(?:-[a-z0-9]+)*-[a-f0-9]{16}$"
)
SESSION_PATH_SAFE = re.compile(
    r"^\.agents/sessions/[a-z0-9]+(?:-[a-z0-9]+)*-[a-z0-9]+(?:-[a-z0-9]+)*-[a-f0-9]{16}"
    r"/scratch-pad\.md$"
)


class SessionStoreError(RuntimeError):
    """Bounded deterministic session-store failure."""

    __slots__ = ("code",)

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _slug(value: str, *, fallback: str, limit: int) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    rendered = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return (rendered or fallback)[:limit].rstrip("-") or fallback


def canonical_session_id(runtime: str, raw_session_id: str) -> str:
    """Return `<runtime>-<readable>-<sha256(raw)[:16]>` without storing raw ID."""

    if not isinstance(runtime, str) or not isinstance(raw_session_id, str):
        raise SessionStoreError("invalid-session-identity")
    if "\x00" in runtime or "\x00" in raw_session_id:
        raise SessionStoreError("invalid-session-identity")
    raw_bytes = raw_session_id.encode("utf-8", errors="strict")
    if (
        not raw_session_id.strip()
        or raw_session_id.strip().lower() in UNKNOWN_SESSION_IDS
        or len(raw_bytes) > MAX_RAW_SESSION_ID_BYTES
    ):
        raise SessionStoreError("invalid-session-identity")
    runtime_slug = _slug(runtime, fallback="runtime", limit=32)
    if (
        len(raw_session_id) <= MAX_CANONICAL_ID_LENGTH
        and _CANONICAL_ID.fullmatch(raw_session_id)
        and raw_session_id.startswith(f"{runtime_slug}-")
    ):
        return raw_session_id
    digest = hashlib.sha256(raw_bytes).hexdigest()[:16]
    room = MAX_CANONICAL_ID_LENGTH - len(runtime_slug) - len(digest) - 2
    readable = _slug(raw_session_id, fallback="session", limit=max(1, min(64, room)))
    identity = f"{runtime_slug}-{readable}-{digest}"
    if not _CANONICAL_ID.fullmatch(identity):
        raise SessionStoreError("invalid-session-identity")
    return identity


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _reject_symlink_components(root: Path, candidate: Path) -> None:
    relative = candidate.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise SessionStoreError("symlink-escape")


def _frontmatter_session_id(path: Path) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        raise SessionStoreError("malformed-scratch-pad") from None
    if not lines or lines[0] != "---":
        raise SessionStoreError("malformed-scratch-pad")
    for line in lines[1:]:
        if line == "---":
            break
        if line.startswith("session_id:"):
            return line.partition(":")[2].strip()
    raise SessionStoreError("missing-session-identity")


def resolve_scratch_pad(
    vault_root: Path | str,
    relative_path: str,
    *,
    expected_session_id: str,
) -> Path:
    """Resolve the sole canonical scratch-pad shape without lexical/symlink escape."""

    root = Path(vault_root).resolve(strict=True)
    if not isinstance(relative_path, str) or "\x00" in relative_path:
        raise SessionStoreError("invalid-session-path")
    decoded = unquote(relative_path)
    pure = PurePosixPath(relative_path)
    if (
        decoded != relative_path
        or "\\" in relative_path
        or pure.is_absolute()
        or ".." in pure.parts
        or re.match(r"^[A-Za-z]:", relative_path)
        or not _CANONICAL_ID.fullmatch(expected_session_id)
    ):
        raise SessionStoreError("invalid-session-path")
    expected = PurePosixPath(
        ".agents", "sessions", expected_session_id, "scratch-pad.md"
    )
    if pure != expected:
        raise SessionStoreError("session-path-identity-mismatch")
    candidate = root.joinpath(*pure.parts)
    _reject_symlink_components(root, candidate)
    resolved = candidate.resolve(strict=False)
    if not _inside(root, resolved):
        raise SessionStoreError("path-escape")
    if candidate.exists() and _frontmatter_session_id(candidate) != expected_session_id:
        raise SessionStoreError("scratch-pad-identity-mismatch")
    return resolved


def _fault(name: str, fault_at: str | None) -> None:
    if fault_at == name:
        raise OSError(f"injected-{name}")


def atomic_write_bytes(
    target: Path | str,
    data: bytes,
    *,
    scanner: Callable[[bytes], None] | None = None,
    fault_at: str | None = None,
) -> None:
    """Durably replace a file using a same-directory mode-0600 temporary file."""

    path = Path(target)
    if not isinstance(data, bytes):
        raise SessionStoreError("invalid-write-bytes")
    path.parent.mkdir(parents=True, exist_ok=True)
    if scanner is not None:
        scanner(data)
    fd: int | None = None
    temp_path: Path | None = None
    try:
        _fault("open", fault_at)
        fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temp_path = Path(raw_temp)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb", closefd=True) as stream:
            fd = None
            stream.write(data)
            _fault("flush", fault_at)
            stream.flush()
            _fault("file_fsync", fault_at)
            os.fsync(stream.fileno())
        _fault("replace", fault_at)
        os.replace(temp_path, path)
        temp_path = None
        os.chmod(path, 0o600)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            _fault("directory_fsync", fault_at)
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        if fd is not None:
            os.close(fd)
        if temp_path is not None:
            with suppress(FileNotFoundError):
                temp_path.unlink()
        raise SessionStoreError(f"atomic-write-{fault_at or 'failure'}") from None


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def atomic_write_json(
    target: Path | str,
    value: object,
    *,
    scanner: Callable[[bytes], None] | None = None,
    fault_at: str | None = None,
) -> None:
    atomic_write_bytes(target, canonical_json_bytes(value), scanner=scanner, fault_at=fault_at)


@dataclass
class WriterLease:
    lock_path: Path
    lease_path: Path
    owner: str
    _stream: BinaryIO | None

    def close_lock_only_for_test(self) -> None:
        if self._stream is not None:
            fcntl.flock(self._stream.fileno(), fcntl.LOCK_UN)
            self._stream.close()
            self._stream = None

    def release(self) -> None:
        if self._stream is None:
            return
        try:
            self.lease_path.unlink(missing_ok=True)
            directory_fd = os.open(self.lease_path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            fcntl.flock(self._stream.fileno(), fcntl.LOCK_UN)
            self._stream.close()
            self._stream = None

    def __enter__(self) -> "WriterLease":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()


@dataclass(frozen=True)
class PreparedTurn:
    session_id: str
    number: int
    nonce: str
    user_lines: tuple[str, ...]
    agent_lines: tuple[str, ...]
    address_status: str = "unrouted"


def _digest_event(previous_digest: str, event_without_digest: bytes) -> str:
    return hashlib.sha256(previous_digest.encode() + b"\n" + event_without_digest).hexdigest()


def _bounded_lines(lines: tuple[str, ...], prefix: str) -> tuple[str, ...]:
    if not lines or any(not isinstance(line, str) or not line for line in lines):
        raise SessionStoreError("incomplete-pair")
    rendered = tuple(f"{prefix}{line}" for line in lines)
    if any("\n" in line or "\r" in line or len(line) > 160 for line in rendered):
        raise SessionStoreError("content-limit")
    return rendered


def open_turn(state: dict[str, object], session_id: str, nonce: str, last_turn: int) -> dict[str, object]:
    """Move an active session to one monotonic pending turn without raw prompt data."""
    if state.get("session_id") != session_id or state.get("lifecycle") != "active":
        raise SessionStoreError("wrong-session")
    if state.get("turn_state") == "pending" and state.get("event_nonce") == nonce:
        return dict(state)
    if state.get("turn_state") != "active" or state.get("pending_turn") is not None:
        raise SessionStoreError("open-turn-exists")
    if not isinstance(nonce, str) or not nonce or len(nonce) > 256:
        raise SessionStoreError("invalid-event-nonce")
    updated = dict(state)
    updated.update(turn_state="pending", pending_turn=last_turn + 1, event_nonce=nonce)
    return updated


def prepare_turn(
    state: dict[str, object],
    session_id: str,
    turn_number: int,
    nonce: str,
    user_lines: tuple[str, ...],
    agent_lines: tuple[str, ...],
    *,
    redact: Callable[[str], tuple[str, tuple[str, ...]]],
    scanner: Callable[[bytes], None],
) -> tuple[dict[str, object], PreparedTurn]:
    """Redact and validate one in-memory pair; operational state stores no content."""
    if state.get("session_id") != session_id:
        raise SessionStoreError("wrong-session")
    if state.get("turn_state") != "pending" or state.get("pending_turn") != turn_number:
        raise SessionStoreError("wrong-turn-number")
    if state.get("event_nonce") != nonce:
        raise SessionStoreError("replayed-event-nonce")
    redacted_user = tuple(redact(line)[0] for line in user_lines)
    redacted_agent = tuple(redact(line)[0] for line in agent_lines)
    rendered_user = _bounded_lines(redacted_user, "User: ")
    rendered_agent = _bounded_lines(redacted_agent, "Agent: ")
    if len(rendered_user) + len(rendered_agent) > 5:
        raise SessionStoreError("content-limit")
    scanner(("\n".join(rendered_user + rendered_agent) + "\n").encode())
    updated = dict(state)
    updated["turn_state"] = "prepared"
    return updated, PreparedTurn(session_id, turn_number, nonce, redacted_user, redacted_agent)


def serialize_turn(prepared: PreparedTurn, previous_digest: str) -> tuple[bytes, str]:
    if previous_digest != "ROOT" and not re.fullmatch(r"[a-f0-9]{64}", previous_digest):
        raise SessionStoreError("invalid-previous-digest")
    lines = [f"### Turn {prepared.number:03d}"]
    lines.extend(_bounded_lines(prepared.user_lines, "User: "))
    lines.extend(_bounded_lines(prepared.agent_lines, "Agent: "))
    if len(prepared.user_lines) + len(prepared.agent_lines) > 5:
        raise SessionStoreError("content-limit")
    lines.extend((f"Address status: {prepared.address_status}", f"Previous digest: {previous_digest}"))
    event = ("\n".join(lines) + "\n").encode()
    digest = _digest_event(previous_digest, event)
    return event + f"Turn digest: {digest}\n".encode(), digest


def _event_chunks(body: bytes) -> list[bytes]:
    if not body:
        return []
    if b"\r" in body or not body.endswith(b"\n"):
        raise SessionStoreError("invalid-event-serialization")
    starts = [m.start() for m in re.finditer(rb"(?m)^### ", body)]
    if not starts or starts[0] != 0:
        raise SessionStoreError("invalid-event-serialization")
    return [body[starts[i] : starts[i + 1] if i + 1 < len(starts) else len(body)] for i in range(len(starts))]


def verify_event_chain(body: bytes) -> tuple[str, int]:
    """Verify immutable ordered turn/correction/routing event bytes."""
    previous = "ROOT"
    last_turn = 0
    for chunk in _event_chunks(body):
        lines = chunk.decode("utf-8", errors="strict").splitlines(keepends=True)
        if len(lines) < 4 or not lines[-2].startswith("Previous digest: "):
            raise SessionStoreError("invalid-event-grammar")
        digest_label = "Turn digest: " if lines[0].startswith("### Turn ") else "Event digest: "
        if not lines[-1].startswith(digest_label):
            raise SessionStoreError("invalid-event-grammar")
        recorded_previous = lines[-2].removeprefix("Previous digest: ").rstrip("\n")
        recorded_digest = lines[-1].removeprefix(digest_label).rstrip("\n")
        event = "".join(lines[:-1]).encode()
        if recorded_previous != previous or recorded_digest != _digest_event(previous, event):
            raise SessionStoreError("digest-chain-mismatch")
        if lines[0].startswith("### Turn "):
            header = re.fullmatch(r"### Turn ([0-9]{3})\n", lines[0])
            if header is None:
                raise SessionStoreError("invalid-turn-number")
            number = int(header.group(1))
            if number != last_turn + 1:
                raise SessionStoreError("invalid-turn-number")
            content = lines[1:-3]
            user_count = 0
            agent_count = 0
            in_agent = False
            for line in content:
                if len(line.rstrip("\n")) > 160 or not line.endswith("\n"):
                    raise SessionStoreError("content-limit")
                if line.startswith("User: ") and not in_agent and line != "User: \n":
                    user_count += 1
                elif line.startswith("Agent: ") and line != "Agent: \n":
                    in_agent = True
                    agent_count += 1
                else:
                    raise SessionStoreError("invalid-event-grammar")
            if not user_count or not agent_count or len(content) > 5:
                raise SessionStoreError("incomplete-pair")
            if lines[-3] != "Address status: unrouted\n":
                raise SessionStoreError("invalid-event-grammar")
            last_turn = number
        elif lines[0].startswith("### Correction to Turn "):
            if not re.fullmatch(r"### Correction to Turn [0-9]{3}\n", lines[0]):
                raise SessionStoreError("invalid-event-heading")
            if len(lines) != 4 or not lines[1].startswith("Correct meaning: "):
                raise SessionStoreError("invalid-event-grammar")
        elif lines[0].startswith("### Routing Resolution for Turn "):
            if not re.fullmatch(r"### Routing Resolution for Turn [0-9]{3}\n", lines[0]):
                raise SessionStoreError("invalid-event-heading")
            prefixes = ("Agent proposal: ", "Owner resolution: ", "Disposition: ")
            if len(lines) != 6 or any(not lines[index + 1].startswith(prefix) for index, prefix in enumerate(prefixes)):
                raise SessionStoreError("invalid-event-grammar")
            if lines[3] not in ("Disposition: active\n", "Disposition: carried-forward\n"):
                raise SessionStoreError("invalid-event-grammar")
        else:
            raise SessionStoreError("invalid-event-heading")
        previous = recorded_digest
    return previous, last_turn


def seal_turn(state: dict[str, object], body: bytes, prepared: PreparedTurn) -> tuple[dict[str, object], bytes, str]:
    previous, last_turn = verify_event_chain(body)
    if last_turn >= prepared.number:
        if last_turn == prepared.number and state.get("turn_state") == "active":
            return dict(state), body, previous
        raise SessionStoreError("duplicate-or-skipped-turn")
    if state.get("turn_state") != "prepared" or state.get("pending_turn") != prepared.number:
        raise SessionStoreError("missing-prepared-turn")
    if state.get("session_id") != prepared.session_id or state.get("event_nonce") != prepared.nonce:
        raise SessionStoreError("wrong-session")
    if prepared.number != last_turn + 1:
        raise SessionStoreError("invalid-turn-number")
    event, digest = serialize_turn(prepared, previous)
    updated = dict(state)
    updated.update(turn_state="active", pending_turn=None, event_nonce=None)
    return updated, body + event, digest


def project_event_chain(body: bytes) -> dict[int, dict[str, object]]:
    """Return the latest active meaning/address while preserving the source bytes."""
    verify_event_chain(body)
    projection: dict[int, dict[str, object]] = {}
    for chunk in _event_chunks(body):
        lines = chunk.decode().splitlines()
        turn_match = re.fullmatch(r"### Turn ([0-9]{3})", lines[0])
        correction_match = re.fullmatch(r"### Correction to Turn ([0-9]{3})", lines[0])
        routing_match = re.fullmatch(r"### Routing Resolution for Turn ([0-9]{3})", lines[0])
        if turn_match:
            number = int(turn_match.group(1))
            projection[number] = {
                "user": tuple(line.removeprefix("User: ") for line in lines if line.startswith("User: ")),
                "agent": tuple(line.removeprefix("Agent: ") for line in lines if line.startswith("Agent: ")),
                "meaning": None,
                "address": None,
                "disposition": "unrouted",
            }
        elif correction_match:
            number = int(correction_match.group(1))
            if number not in projection:
                raise SessionStoreError("unknown-correction-target")
            projection[number]["meaning"] = lines[1].removeprefix("Correct meaning: ")
        elif routing_match:
            number = int(routing_match.group(1))
            if number not in projection:
                raise SessionStoreError("unknown-routing-target")
            projection[number]["address"] = lines[2].removeprefix("Owner resolution: ")
            projection[number]["disposition"] = lines[3].removeprefix("Disposition: ")
    return projection


def append_chain_event(body: bytes, heading: str, fields: tuple[tuple[str, str], ...]) -> tuple[bytes, str]:
    previous, _ = verify_event_chain(body)
    if not heading.startswith(("Correction to Turn ", "Routing Resolution for Turn ")):
        raise SessionStoreError("invalid-event-heading")
    lines = [f"### {heading}"] + [f"{key}: {value}" for key, value in fields]
    if any("\n" in line or "\r" in line for line in lines):
        raise SessionStoreError("invalid-event-content")
    event = ("\n".join(lines + [f"Previous digest: {previous}"]) + "\n").encode()
    digest = _digest_event(previous, event)
    return body + event + f"Event digest: {digest}\n".encode(), digest


@dataclass(frozen=True)
class RecoveryResult:
    action: str
    session_id: str | None = None
    scratch_pad_bytes: bytes | None = None
    predecessor_bytes: bytes | None = None
    diagnostic: str | None = None


def _read_json_object(path: Path, code: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise SessionStoreError(code) from None
    if not isinstance(value, dict):
        raise SessionStoreError(code)
    return value


def _parse_timestamp(value: object, code: str) -> datetime:
    if not isinstance(value, str):
        raise SessionStoreError(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise SessionStoreError(code) from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SessionStoreError(code)
    return parsed


def _read_pointer(sessions: Path) -> dict[str, object] | None:
    path = sessions / "active.json"
    if not path.exists():
        return None
    pointer = _read_json_object(path, "malformed-active-pointer")
    if set(pointer) != {"session_id", "scratch_pad", "status", "last_turn", "updated_at"}:
        raise SessionStoreError("malformed-active-pointer")
    if (
        not isinstance(pointer["session_id"], str)
        or not _CANONICAL_ID.fullmatch(pointer["session_id"])
        or pointer["status"] not in {"initializing", "active", "closing", "closed", "interrupted", "faulted", "conflict"}
        or not isinstance(pointer["last_turn"], int)
        or pointer["last_turn"] < 0
        or not isinstance(pointer["scratch_pad"], str)
    ):
        raise SessionStoreError("malformed-active-pointer")
    _parse_timestamp(pointer["updated_at"], "malformed-active-pointer")
    return pointer


def _read_state(sessions: Path, session_id: str) -> dict[str, object]:
    state = _read_json_object(sessions / session_id / "state.json", "malformed-session-state")
    required = {"protocol_version", "session_id", "lifecycle", "turn_state", "pending_turn", "event_nonce", "lease"}
    if (
        set(state) != required
        or state.get("protocol_version") != 1
        or state.get("session_id") != session_id
        or state.get("lifecycle") not in {"initializing", "active", "closing", "closed", "interrupted", "faulted", "conflict"}
        or state.get("turn_state") not in {"inactive", "active", "pending", "prepared", "sealed"}
        or (state.get("pending_turn") is not None and (not isinstance(state["pending_turn"], int) or state["pending_turn"] < 1))
        or (state.get("event_nonce") is not None and (not isinstance(state["event_nonce"], str) or not state["event_nonce"] or len(state["event_nonce"]) > 256))
    ):
        raise SessionStoreError("malformed-session-state")
    lease = state["lease"]
    if lease is not None:
        if not isinstance(lease, dict) or set(lease) != {"owner", "acquired_at", "heartbeat_at"}:
            raise SessionStoreError("malformed-session-state")
        if not isinstance(lease["owner"], str) or not lease["owner"] or len(lease["owner"]) > 256:
            raise SessionStoreError("malformed-session-state")
        _parse_timestamp(lease["acquired_at"], "malformed-session-state")
        _parse_timestamp(lease["heartbeat_at"], "malformed-session-state")
    if state["lifecycle"] in {"active", "initializing", "closing"} and lease is None:
        raise SessionStoreError("malformed-session-state")
    return state


def _lease_live(state: dict[str, object], stale_after: float, now: datetime) -> bool:
    if stale_after < 0 or now.tzinfo is None or now.utcoffset() is None:
        raise SessionStoreError("invalid-lease-contract")
    lease = state.get("lease")
    if not isinstance(lease, dict):
        raise SessionStoreError("malformed-lease")
    heartbeat = _parse_timestamp(lease.get("heartbeat_at"), "malformed-lease")
    return (now - heartbeat).total_seconds() < stale_after


def _scratch_bytes(root: Path, pointer: dict[str, object]) -> bytes:
    path = resolve_scratch_pad(
        root,
        cast(str, pointer["scratch_pad"]),
        expected_session_id=cast(str, pointer["session_id"]),
    )
    try:
        return path.read_bytes()
    except OSError:
        raise SessionStoreError("missing-scratch-pad") from None


def _replace_frontmatter_status(content: bytes, lifecycle: str) -> bytes:
    try:
        text = content.decode("utf-8")
    except UnicodeError:
        raise SessionStoreError("malformed-scratch-pad") from None
    rendered, count = re.subn(r"(?m)^status: [a-z-]+$", f"status: {lifecycle}", text, count=1)
    if count != 1:
        raise SessionStoreError("malformed-scratch-pad")
    return rendered.encode()


def _new_scratch_pad(session_id: str, previous: str, day: str) -> bytes:
    return (
        "---\n"
        f"title: Session Interview Scratch-Pad — {session_id}\n"
        f"date: {day}\nupdated: {day}\n"
        "type: session-interview-scratchpad\nstatus: active\n"
        "tags:\n  - session\n  - interview\n  - continuity\n"
        f"session_id: {session_id}\n"
        "scope_ref: SCOPE.md\ncontext_ref: .agents/Context.md\n"
        f"previous_scratch_pad: {previous}\nprotocol_version: 1\n---\n"
    ).encode()


def _sha(value: bytes | None) -> str | None:
    return None if value is None else hashlib.sha256(value).hexdigest()


def _transition_marker(session_id: str, targets: tuple[tuple[str, bytes | None, bytes], ...], phase: str) -> dict[str, object]:
    return {
        "protocol_version": 1,
        "session_id": session_id,
        "phase": phase,
        "targets": [
            {"path": path, "expected_old_digest": _sha(old), "intended_new_digest": _sha(new)}
            for path, old, new in targets
        ],
    }


def _raise_transition_fault(name: str, fault_at: str | None) -> None:
    if name == fault_at:
        raise SessionStoreError(f"transition-{name}")


def _read_transaction(path: Path, expected_session_id: str) -> dict[str, object]:
    transaction = _read_json_object(path, "malformed-transaction")
    if (
        set(transaction) != {"protocol_version", "session_id", "phase", "targets"}
        or transaction.get("protocol_version") != 1
        or transaction.get("session_id") != expected_session_id
        or transaction.get("phase") not in {"prepared", "applying", "committed"}
        or not isinstance(transaction.get("targets"), list)
        or not transaction["targets"]
    ):
        raise SessionStoreError("malformed-transaction")
    path_pattern = re.compile(
        r"^\.agents/sessions/(?:active\.json|[a-z0-9]+(?:-[a-z0-9]+)*-[a-z0-9]+(?:-[a-z0-9]+)*-[a-f0-9]{16}/(?:scratch-pad\.md|state\.json))$"
    )
    digest_pattern = re.compile(r"^[a-f0-9]{64}$")
    for target in cast(list[object], transaction["targets"]):
        if not isinstance(target, dict) or set(target) != {"path", "expected_old_digest", "intended_new_digest"}:
            raise SessionStoreError("malformed-transaction")
        if not isinstance(target["path"], str) or not path_pattern.fullmatch(target["path"]):
            raise SessionStoreError("malformed-transaction")
        if target["expected_old_digest"] is not None and (
            not isinstance(target["expected_old_digest"], str)
            or not digest_pattern.fullmatch(target["expected_old_digest"])
        ):
            raise SessionStoreError("malformed-transaction")
        if not isinstance(target["intended_new_digest"], str) or not digest_pattern.fullmatch(target["intended_new_digest"]):
            raise SessionStoreError("malformed-transaction")
    return transaction


def _durable_unlink(path: Path) -> None:
    path.unlink(missing_ok=True)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _create_successor(
    root: Path,
    pointer: dict[str, object],
    predecessor_state: dict[str, object],
    predecessor_bytes: bytes,
    successor_id: str,
    now: datetime,
    fault_at: str | None,
) -> RecoveryResult:
    sessions = root / ".agents" / "sessions"
    predecessor_id = cast(str, pointer["session_id"])
    predecessor_dir = sessions / predecessor_id
    successor_dir = sessions / successor_id
    successor_dir.mkdir(parents=True, exist_ok=True)
    timestamp = now.isoformat().replace("+00:00", "Z")
    day = now.date().isoformat()
    successor_relative = f".agents/sessions/{successor_id}/scratch-pad.md"
    successor_scratch = _new_scratch_pad(successor_id, cast(str, pointer["scratch_pad"]), day)
    successor_state = {
        "protocol_version": 1, "session_id": successor_id, "lifecycle": "active",
        "turn_state": "active", "pending_turn": None, "event_nonce": None,
        "lease": {"owner": successor_id, "acquired_at": timestamp, "heartbeat_at": timestamp},
    }
    successor_state_bytes = canonical_json_bytes(successor_state)
    next_pointer = {
        "session_id": successor_id, "scratch_pad": successor_relative, "status": "active",
        "last_turn": 0, "updated_at": timestamp,
    }
    pointer_bytes = canonical_json_bytes(next_pointer)
    interrupted_state = dict(predecessor_state)
    interrupted_state["lifecycle"] = "interrupted"
    interrupted_state["lease"] = None
    interrupted_state_bytes = canonical_json_bytes(interrupted_state)
    interrupted_scratch = _replace_frontmatter_status(predecessor_bytes, "interrupted")
    targets = (
        (f".agents/sessions/{predecessor_id}/state.json", (predecessor_dir / "state.json").read_bytes(), interrupted_state_bytes),
        (f".agents/sessions/{predecessor_id}/scratch-pad.md", predecessor_bytes, interrupted_scratch),
        (successor_relative, (successor_dir / "scratch-pad.md").read_bytes() if (successor_dir / "scratch-pad.md").exists() else None, successor_scratch),
        (f".agents/sessions/{successor_id}/state.json", (successor_dir / "state.json").read_bytes() if (successor_dir / "state.json").exists() else None, successor_state_bytes),
        (".agents/sessions/active.json", (sessions / "active.json").read_bytes(), pointer_bytes),
    )
    transaction = successor_dir / "transaction.json"
    atomic_write_json(transaction, _transition_marker(successor_id, targets, "prepared"))
    try:
        atomic_write_json(transaction, _transition_marker(successor_id, targets, "applying"))
        atomic_write_bytes(predecessor_dir / "state.json", interrupted_state_bytes)
        atomic_write_bytes(predecessor_dir / "scratch-pad.md", interrupted_scratch)
        _raise_transition_fault("predecessor", fault_at)
        atomic_write_bytes(successor_dir / "scratch-pad.md", successor_scratch)
        _raise_transition_fault("successor-scratch", fault_at)
        atomic_write_bytes(successor_dir / "state.json", successor_state_bytes)
        _raise_transition_fault("successor-state", fault_at)
        atomic_write_bytes(sessions / "active.json", pointer_bytes)
        _raise_transition_fault("pointer", fault_at)
        atomic_write_json(transaction, _transition_marker(successor_id, targets, "committed"))
        _durable_unlink(transaction)
    except SessionStoreError:
        return RecoveryResult("faulted", successor_id, predecessor_bytes=predecessor_bytes, diagnostic="incomplete-transition")
    return RecoveryResult("succeeded", successor_id, successor_scratch, predecessor_bytes)


def _interrupt_current_session(
    root: Path,
    pointer: dict[str, object],
    state: dict[str, object],
    scratch: bytes,
) -> RecoveryResult:
    sessions = root / ".agents" / "sessions"
    session_id = cast(str, pointer["session_id"])
    directory = sessions / session_id
    next_state = dict(state)
    next_state["lifecycle"] = "interrupted"
    next_state["lease"] = None
    next_pointer = dict(pointer)
    next_pointer["status"] = "interrupted"
    next_pointer["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    next_scratch = _replace_frontmatter_status(scratch, "interrupted")
    targets = (
        (f".agents/sessions/{session_id}/state.json", canonical_json_bytes(state), canonical_json_bytes(next_state)),
        (f".agents/sessions/{session_id}/scratch-pad.md", scratch, next_scratch),
        (".agents/sessions/active.json", canonical_json_bytes(pointer), canonical_json_bytes(next_pointer)),
    )
    transaction = directory / "transaction.json"
    atomic_write_json(transaction, _transition_marker(session_id, targets, "prepared"))
    atomic_write_json(transaction, _transition_marker(session_id, targets, "applying"))
    atomic_write_json(directory / "state.json", next_state)
    atomic_write_bytes(directory / "scratch-pad.md", next_scratch)
    atomic_write_json(sessions / "active.json", next_pointer)
    atomic_write_json(transaction, _transition_marker(session_id, targets, "committed"))
    _durable_unlink(transaction)
    return RecoveryResult("interrupted", session_id, next_scratch, scratch)


def recover_session(
    vault_root: Path | str,
    runtime: str,
    raw_session_id: str,
    *,
    stale_after: float = 300,
    now: datetime | None = None,
    fault_at: str | None = None,
) -> RecoveryResult:
    """Apply the SessionStart recovery matrix without guessing a continuity source."""
    root = Path(vault_root).resolve(strict=True)
    sessions = root / ".agents" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    try:
        current_id = canonical_session_id(runtime, raw_session_id)
    except SessionStoreError:
        return RecoveryResult("unavailable", diagnostic="stable-session-identity-unavailable")
    try:
        pointer = _read_pointer(sessions)
        if pointer is None:
            return RecoveryResult("no-active", current_id)
        predecessor_bytes = _scratch_bytes(root, pointer)
        predecessor_state = _read_state(sessions, cast(str, pointer["session_id"]))
        lifecycle = predecessor_state["lifecycle"]
        current_time = now or datetime.now(UTC)
        pending_transaction = sessions / current_id / "transaction.json"
        if pending_transaction.exists():
            _read_transaction(pending_transaction, current_id)
            if pointer["session_id"] == current_id:
                marker = _read_transaction(pending_transaction, current_id)
                current_scratch = _scratch_bytes(root, pointer)
                current_state = _read_state(sessions, current_id)
                if current_state["lifecycle"] != "active":
                    return RecoveryResult("faulted", current_id, diagnostic="incomplete-transition")
                if marker["phase"] == "prepared" and current_state["turn_state"] == "prepared":
                    # A crash between preparation and sealing changed no durable body.
                    # Discard the unsealed preparation so the open turn can be reopened,
                    # rather than leaving the session permanently blocked.
                    reopened = dict(current_state)
                    reopened.update(turn_state="active", pending_turn=None, event_nonce=None)
                    atomic_write_json(sessions / current_id / "state.json", reopened)
                _durable_unlink(pending_transaction)
                return RecoveryResult("succeeded", current_id, current_scratch, predecessor_bytes)
            return _create_successor(
                root,
                pointer,
                predecessor_state,
                predecessor_bytes,
                current_id,
                current_time,
                fault_at,
            )
        if pointer["status"] != lifecycle:
            return RecoveryResult("faulted", current_id, predecessor_bytes=predecessor_bytes, diagnostic="pointer-state-mismatch")
        if pointer["session_id"] == current_id:
            if lifecycle == "active" and _lease_live(predecessor_state, stale_after, current_time):
                return RecoveryResult("continued", current_id, predecessor_bytes)
            if lifecycle == "active":
                return RecoveryResult("faulted", current_id, predecessor_bytes, diagnostic="stale-lease-continuity")
            if lifecycle == "closing" and not _lease_live(predecessor_state, stale_after, current_time):
                return _interrupt_current_session(root, pointer, predecessor_state, predecessor_bytes)
            return RecoveryResult("predecessor-only", current_id, predecessor_bytes)
        if lifecycle in {"closed", "interrupted"}:
            return RecoveryResult("predecessor-only", current_id, predecessor_bytes=predecessor_bytes)
        if lifecycle == "active" and _lease_live(predecessor_state, stale_after, current_time):
            return RecoveryResult("conflict", current_id, predecessor_bytes=predecessor_bytes, diagnostic="live-writer-lease")
        if lifecycle not in {"active", "closing", "initializing"}:
            return RecoveryResult("faulted", current_id, predecessor_bytes=predecessor_bytes, diagnostic="unsupported-lifecycle")
        return _create_successor(root, pointer, predecessor_state, predecessor_bytes, current_id, current_time, fault_at)
    except SessionStoreError as exc:
        return RecoveryResult("faulted", current_id, diagnostic=exc.code)


def close_session(vault_root: Path | str, session_id: str, *, final: bool, fault_at: str | None = None) -> None:
    """Idempotently begin or finalize normal closure through a transaction marker."""
    root = Path(vault_root).resolve(strict=True)
    sessions = root / ".agents" / "sessions"
    pointer = _read_pointer(sessions)
    if pointer is None or pointer["session_id"] != session_id:
        raise SessionStoreError("wrong-session")
    state_path = sessions / session_id / "state.json"
    scratch_path = sessions / session_id / "scratch-pad.md"
    state = _read_state(sessions, session_id)
    target = "closed" if final else "closing"
    transaction = sessions / session_id / "transaction.json"
    if transaction.exists():
        _read_transaction(transaction, session_id)
    if state["lifecycle"] == target and pointer["status"] == target:
        _durable_unlink(transaction)
        return
    allowed = {("active", "closing"), ("closing", "closed"), ("active", "closed")}
    if state["lifecycle"] != target and (state["lifecycle"], target) not in allowed:
        raise SessionStoreError("invalid-lifecycle-transition")
    next_state = dict(state)
    next_state["lifecycle"] = target
    if final:
        next_state["lease"] = None
    scratch = scratch_path.read_bytes()
    next_scratch = _replace_frontmatter_status(scratch, target)
    next_pointer = dict(pointer)
    next_pointer["status"] = target
    next_pointer["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    targets = (
        (f".agents/sessions/{session_id}/state.json", canonical_json_bytes(state), canonical_json_bytes(next_state)),
        (f".agents/sessions/{session_id}/scratch-pad.md", scratch, next_scratch),
        (".agents/sessions/active.json", canonical_json_bytes(pointer), canonical_json_bytes(next_pointer)),
    )
    atomic_write_json(transaction, _transition_marker(session_id, targets, "prepared"))
    atomic_write_json(transaction, _transition_marker(session_id, targets, "applying"))
    atomic_write_json(state_path, next_state)
    _raise_transition_fault("state", fault_at)
    atomic_write_bytes(scratch_path, next_scratch)
    _raise_transition_fault("scratch", fault_at)
    _raise_transition_fault("pointer", fault_at)
    atomic_write_json(sessions / "active.json", next_pointer)
    atomic_write_json(transaction, _transition_marker(session_id, targets, "committed"))
    _durable_unlink(transaction)


def _split_scratch_pad(content: bytes) -> tuple[bytes, bytes]:
    marker = b"---\n"
    if not content.startswith(marker):
        raise SessionStoreError("malformed-scratch-pad")
    end = content.find(marker, len(marker))
    if end < 0:
        raise SessionStoreError("malformed-scratch-pad")
    boundary = end + len(marker)
    return content[:boundary], content[boundary:]


def activate_session(
    vault_root: Path | str,
    runtime: str,
    raw_session_id: str,
    *,
    now: datetime | None = None,
) -> str:
    """Idempotently create the first active session through a transaction."""
    root = Path(vault_root).resolve(strict=True)
    sessions = root / ".agents" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    session_id = canonical_session_id(runtime, raw_session_id)
    pointer = _read_pointer(sessions)
    if pointer is not None:
        if pointer["session_id"] == session_id and pointer["status"] == "active":
            _read_state(sessions, session_id)
            _scratch_bytes(root, pointer)
            return session_id
        if pointer["status"] != "closed":
            raise SessionStoreError("active-session-conflict")
        predecessor_id = str(pointer["session_id"])
        previous_rel = f".agents/sessions/{predecessor_id}/scratch-pad.md"
        pred_tx = sessions / predecessor_id / "transaction.json"
        if pred_tx.exists():
            _durable_unlink(pred_tx)
    else:
        previous_rel = ""
    current = now or datetime.now(UTC)
    timestamp = current.isoformat().replace("+00:00", "Z")
    relative = f".agents/sessions/{session_id}/scratch-pad.md"
    directory = sessions / session_id
    directory.mkdir(parents=True, exist_ok=True)
    pending_tx = directory / "transaction.json"
    if pending_tx.exists():
        _durable_unlink(pending_tx)
    scratch = _new_scratch_pad(session_id, previous_rel, current.date().isoformat())
    state = {
        "protocol_version": 1,
        "session_id": session_id,
        "lifecycle": "active",
        "turn_state": "active",
        "pending_turn": None,
        "event_nonce": None,
        "lease": {"owner": session_id, "acquired_at": timestamp, "heartbeat_at": timestamp},
    }
    pointer_value = {
        "session_id": session_id,
        "scratch_pad": relative,
        "status": "active",
        "last_turn": 0,
        "updated_at": timestamp,
    }
    state_bytes = canonical_json_bytes(state)
    pointer_bytes = canonical_json_bytes(pointer_value)
    active_json = sessions / "active.json"
    active_old_bytes = active_json.read_bytes() if active_json.exists() else None
    targets = (
        (relative, None, scratch),
        (f".agents/sessions/{session_id}/state.json", None, state_bytes),
        (".agents/sessions/active.json", active_old_bytes, pointer_bytes),
    )
    transaction = directory / "transaction.json"
    atomic_write_json(transaction, _transition_marker(session_id, targets, "prepared"))
    atomic_write_json(transaction, _transition_marker(session_id, targets, "applying"))
    atomic_write_bytes(directory / "scratch-pad.md", scratch)
    atomic_write_bytes(directory / "state.json", state_bytes)
    atomic_write_bytes(active_json, pointer_bytes)
    atomic_write_json(transaction, _transition_marker(session_id, targets, "committed"))
    _durable_unlink(transaction)
    return session_id


def _active_material(root: Path, session_id: str) -> tuple[dict[str, object], dict[str, object], bytes]:
    sessions = root / ".agents" / "sessions"
    pointer = _read_pointer(sessions)
    if pointer is None or pointer["session_id"] != session_id:
        raise SessionStoreError("wrong-session")
    state = _read_state(sessions, session_id)
    scratch = _scratch_bytes(root, pointer)
    if pointer["status"] != state["lifecycle"]:
        raise SessionStoreError("pointer-state-mismatch")
    return pointer, state, scratch


def persist_open_turn(vault_root: Path | str, session_id: str, nonce: str) -> int:
    root = Path(vault_root).resolve(strict=True)
    pointer, state, _ = _active_material(root, session_id)
    if state["lifecycle"] != "active":
        raise SessionStoreError("inactive-session")
    updated = open_turn(state, session_id, nonce, cast(int, pointer["last_turn"]))
    atomic_write_json(root / ".agents" / "sessions" / session_id / "state.json", updated)
    return cast(int, updated["pending_turn"])


def persist_prepared_turn(
    vault_root: Path | str,
    session_id: str,
    turn: int,
    nonce: str,
    user_lines: tuple[str, ...],
    agent_lines: tuple[str, ...],
    *,
    redact: Callable[[str], tuple[str, tuple[str, ...]]],
    scanner: Callable[[bytes], None],
) -> None:
    root = Path(vault_root).resolve(strict=True)
    sessions = root / ".agents" / "sessions"
    _, state, scratch = _active_material(root, session_id)
    updated, prepared = prepare_turn(
        state,
        session_id,
        turn,
        nonce,
        user_lines,
        agent_lines,
        redact=redact,
        scanner=scanner,
    )
    frontmatter, body = _split_scratch_pad(scratch)
    previous, last_turn = verify_event_chain(body)
    if turn != last_turn + 1:
        raise SessionStoreError("invalid-turn-number")
    event, _ = serialize_turn(prepared, previous)
    intended_scratch = frontmatter + body + event
    scanner(intended_scratch)
    state_bytes = canonical_json_bytes(updated)
    targets = (
        (f".agents/sessions/{session_id}/scratch-pad.md", scratch, intended_scratch),
        (f".agents/sessions/{session_id}/state.json", canonical_json_bytes(state), state_bytes),
    )
    transaction = sessions / session_id / "transaction.json"
    atomic_write_json(transaction, _transition_marker(session_id, targets, "prepared"))
    atomic_write_bytes(sessions / session_id / "state.json", state_bytes)


def persist_sealed_turn(
    vault_root: Path | str,
    session_id: str,
    turn: int,
    nonce: str,
    user_lines: tuple[str, ...],
    agent_lines: tuple[str, ...],
    *,
    redact: Callable[[str], tuple[str, tuple[str, ...]]],
    scanner: Callable[[bytes], None],
) -> str:
    """Seal one prepared pair and atomically advance scratch, state, and pointer."""
    root = Path(vault_root).resolve(strict=True)
    sessions = root / ".agents" / "sessions"
    pointer, state, scratch = _active_material(root, session_id)
    transaction = sessions / session_id / "transaction.json"
    if state["turn_state"] == "active" and cast(int, pointer["last_turn"]) == turn:
        return "duplicate"
    if state["turn_state"] != "prepared" or state["pending_turn"] != turn or state["event_nonce"] != nonce:
        raise SessionStoreError("missing-prepared-pair")
    if not transaction.exists():
        raise SessionStoreError("missing-prepared-pair")
    prepared_transaction = _read_transaction(transaction, session_id)
    redacted_user = tuple(redact(line)[0] for line in user_lines)
    redacted_agent = tuple(redact(line)[0] for line in agent_lines)
    scanner(("\n".join(redacted_user + redacted_agent) + "\n").encode())
    prepared = PreparedTurn(session_id, turn, nonce, redacted_user, redacted_agent)
    frontmatter, body = _split_scratch_pad(scratch)
    next_state, next_body, _ = seal_turn(state, body, prepared)
    next_scratch = frontmatter + next_body
    scratch_target = next(
        (
            target
            for target in cast(list[object], prepared_transaction["targets"])
            if isinstance(target, dict)
            and target.get("path") == f".agents/sessions/{session_id}/scratch-pad.md"
        ),
        None,
    )
    if not isinstance(scratch_target, dict) or scratch_target.get("intended_new_digest") != _sha(next_scratch):
        raise SessionStoreError("prepared-pair-mismatch")
    next_pointer = dict(pointer)
    next_pointer["last_turn"] = turn
    next_pointer["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    scanner(next_scratch)
    state_bytes = canonical_json_bytes(next_state)
    pointer_bytes = canonical_json_bytes(next_pointer)
    targets = (
        (f".agents/sessions/{session_id}/scratch-pad.md", scratch, next_scratch),
        (f".agents/sessions/{session_id}/state.json", canonical_json_bytes(state), state_bytes),
        (".agents/sessions/active.json", canonical_json_bytes(pointer), pointer_bytes),
    )
    atomic_write_json(transaction, _transition_marker(session_id, targets, "applying"))
    atomic_write_bytes(sessions / session_id / "scratch-pad.md", next_scratch, scanner=scanner)
    atomic_write_bytes(sessions / session_id / "state.json", state_bytes)
    atomic_write_bytes(sessions / "active.json", pointer_bytes)
    atomic_write_json(transaction, _transition_marker(session_id, targets, "committed"))
    _durable_unlink(transaction)
    return "sealed"


def mark_session_faulted(vault_root: Path | str, session_id: str) -> None:
    root = Path(vault_root).resolve(strict=True)
    sessions = root / ".agents" / "sessions"
    pointer, state, scratch = _active_material(root, session_id)
    next_state = dict(state)
    next_state.update(lifecycle="faulted", turn_state="active", pending_turn=None, event_nonce=None, lease=None)
    next_pointer = dict(pointer)
    next_pointer["status"] = "faulted"
    next_pointer["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    next_scratch = _replace_frontmatter_status(scratch, "faulted")
    state_bytes = canonical_json_bytes(next_state)
    pointer_bytes = canonical_json_bytes(next_pointer)
    targets = (
        (f".agents/sessions/{session_id}/state.json", canonical_json_bytes(state), state_bytes),
        (f".agents/sessions/{session_id}/scratch-pad.md", scratch, next_scratch),
        (".agents/sessions/active.json", canonical_json_bytes(pointer), pointer_bytes),
    )
    transaction = sessions / session_id / "transaction.json"
    atomic_write_json(transaction, _transition_marker(session_id, targets, "prepared"))
    atomic_write_json(transaction, _transition_marker(session_id, targets, "applying"))
    atomic_write_bytes(sessions / session_id / "state.json", state_bytes)
    atomic_write_bytes(sessions / session_id / "scratch-pad.md", next_scratch)
    atomic_write_bytes(sessions / "active.json", pointer_bytes)
    atomic_write_json(transaction, _transition_marker(session_id, targets, "committed"))
    _durable_unlink(transaction)


def session_lifecycle(vault_root: Path | str, session_id: str) -> str:
    root = Path(vault_root).resolve(strict=True)
    _, state, _ = _active_material(root, session_id)
    return cast(str, state["lifecycle"])


def open_turn_metadata(vault_root: Path | str, session_id: str) -> tuple[str, int | None, str | None]:
    """Report the current turn state plus its pending number and nonce, if any."""
    root = Path(vault_root).resolve(strict=True)
    _, state, _ = _active_material(root, session_id)
    return (
        cast(str, state["turn_state"]),
        cast("int | None", state["pending_turn"]),
        cast("str | None", state["event_nonce"]),
    )


def acquire_writer_lease(
    vault_root: Path | str,
    owner: str,
    *,
    stale_after: float,
    allow_stale_takeover: bool = False,
) -> WriterLease:
    """Acquire the sole vault writer lock; stale records need explicit takeover."""

    if not isinstance(owner, str) or not owner or len(owner) > 256:
        raise SessionStoreError("invalid-lease-owner")
    sessions = Path(vault_root).resolve(strict=True) / ".agents" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    lock_path = sessions / ".writer.lock"
    lease_path = sessions / ".writer-lease.json"
    stream = lock_path.open("a+b")
    os.chmod(lock_path, 0o600)
    try:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        stream.close()
        raise SessionStoreError("conflict") from None

    try:
        if lease_path.exists():
            try:
                record = json.loads(lease_path.read_text(encoding="utf-8"))
                heartbeat = datetime.fromisoformat(record["heartbeat_at"].replace("Z", "+00:00"))
                age = time.time() - heartbeat.timestamp()
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                raise SessionStoreError("malformed-lease") from None
            if not allow_stale_takeover:
                raise SessionStoreError("stale-lease" if age >= stale_after else "conflict")
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        atomic_write_json(
            lease_path,
            {"owner": owner, "acquired_at": now, "heartbeat_at": now},
        )
        return WriterLease(lock_path, lease_path, owner, stream)
    except Exception:
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()
        raise
