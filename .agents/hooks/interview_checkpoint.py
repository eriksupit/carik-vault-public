#!/usr/bin/env python3
"""Owner-authorized session checkpoint operations for the Interview Protocol.

Preparation is read-only. Stage, commit, push, and remote verification are separate
operations, each requiring its own explicit authorization. Nothing here runs from a
sealed turn, an agent offer, or a closing session.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import sys

HOOKS_DIR = Path(__file__).resolve().parent
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

import interview_credential_redactor as redactor  # noqa: E402
import interview_session_store as store  # noqa: E402

COMMIT_MESSAGE = "chore(session): checkpoint {session_id} turn {turn}"
PERMITTED_SUFFIXES = ("scratch-pad.md", "state.json")


class CheckpointError(RuntimeError):
    """Bounded checkpoint refusal naming the exact unmet condition."""

    __slots__ = ("code",)

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class CheckpointSnapshot:
    session_id: str
    turn: int
    paths: tuple[str, ...]
    digests: dict[str, str] = field(default_factory=dict)

    @property
    def message(self) -> str:
        return COMMIT_MESSAGE.format(session_id=self.session_id, turn=self.turn)


def offer_text(session_id: str, turn: int) -> str:
    """Return the offer wording. Reading this performs no Git or filesystem action."""

    return (
        f"I can checkpoint session continuity for {session_id} at turn {turn}. "
        "Authorize it explicitly if you want the local commit."
    )


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False
    )
    if check and result.returncode != 0:
        raise CheckpointError("git-command-failed")
    return result


def _repository_root(root: Path) -> Path:
    result = _git(root, "rev-parse", "--show-toplevel")
    return Path(result.stdout.strip()).resolve()


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_snapshot(vault_root: Path | str, session_id: str) -> CheckpointSnapshot:
    """Freeze the transaction-owned path set and digests without touching Git."""

    root = Path(vault_root).resolve(strict=True)
    sessions = root / ".agents" / "sessions"
    pointer_path = sessions / "active.json"
    if not pointer_path.is_file():
        raise CheckpointError("no-active-session")
    try:
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise CheckpointError("malformed-active-pointer") from None
    if pointer.get("session_id") != session_id:
        raise CheckpointError("wrong-session")
    if (sessions / session_id / "transaction.json").exists():
        raise CheckpointError("incomplete-transaction")

    scratch = sessions / session_id / "scratch-pad.md"
    if not scratch.is_file():
        raise CheckpointError("missing-scratch-pad")
    body = scratch.read_bytes()
    sealed = re.findall(rb"(?m)^### Turn (\d{3})$", body)
    turn = int(sealed[-1]) if sealed else 0
    if pointer.get("last_turn") != turn:
        raise CheckpointError("turn-pointer-mismatch")

    paths = [
        ".agents/sessions/active.json",
        f".agents/sessions/{session_id}/scratch-pad.md",
    ]
    state = sessions / session_id / "state.json"
    if state.is_file():
        paths.append(f".agents/sessions/{session_id}/state.json")

    previous = next(
        (
            line.partition(":")[2].strip()
            for line in body.decode("utf-8", errors="replace").splitlines()
            if line.startswith("previous_scratch_pad:")
        ),
        "null",
    )
    if previous and previous != "null":
        predecessor = root / previous
        if not store.SESSION_PATH_SAFE.fullmatch(previous) or not predecessor.is_file():
            raise CheckpointError("malformed-predecessor-reference")
        predecessor_status = next(
            (
                line.partition(":")[2].strip()
                for line in predecessor.read_text(encoding="utf-8").splitlines()
                if line.startswith("status:")
            ),
            "",
        )
        if predecessor_status in {"interrupted", "closed"}:
            paths.append(previous)
            predecessor_state = predecessor.parent / "state.json"
            if predecessor_state.is_file():
                paths.append(str(predecessor_state.relative_to(root).as_posix()))

    ordered = tuple(dict.fromkeys(paths))
    digests = {path: _digest(root / path) for path in ordered}
    for path in ordered:
        redactor.assert_destination_safe((root / path).read_bytes())
    return CheckpointSnapshot(session_id, turn, ordered, digests)


def stage(vault_root: Path | str, snapshot: CheckpointSnapshot, *, authorized: bool) -> None:
    """Stage exactly the frozen path set after explicit owner authorization."""

    if not authorized:
        raise CheckpointError("missing-owner-authorization")
    root = Path(vault_root).resolve(strict=True)
    if _repository_root(root) != root:
        raise CheckpointError("repository-root-mismatch")
    if _git(root, "diff", "--cached", "--name-only").stdout.strip():
        raise CheckpointError("index-not-clean")
    for path in snapshot.paths:
        target = root / path
        if not target.is_file():
            raise CheckpointError("missing-checkpoint-path")
        if _digest(target) != snapshot.digests[path]:
            raise CheckpointError("snapshot-digest-mismatch")
        redactor.assert_destination_safe(target.read_bytes())
    _git(root, "add", "--", *snapshot.paths)
    staged = tuple(
        line for line in _git(root, "diff", "--cached", "--name-only").stdout.splitlines() if line
    )
    if set(staged) != set(snapshot.paths):
        _git(root, "reset", check=False)
        raise CheckpointError("staged-path-set-mismatch")
    for path in snapshot.paths:
        blob = _git(root, "show", f":{path}").stdout.encode("utf-8")
        if hashlib.sha256(blob).hexdigest() != snapshot.digests[path]:
            _git(root, "reset", check=False)
            raise CheckpointError("staged-byte-digest-mismatch")


def commit(vault_root: Path | str, snapshot: CheckpointSnapshot, *, authorized: bool) -> str:
    """Commit the staged snapshot; the message's turn must be the sealed turn."""

    if not authorized:
        raise CheckpointError("missing-owner-authorization")
    root = Path(vault_root).resolve(strict=True)
    verification = prepare_snapshot(root, snapshot.session_id)
    if verification.turn != snapshot.turn or verification.digests != snapshot.digests:
        raise CheckpointError("snapshot-no-longer-current")
    _git(root, "commit", "-m", snapshot.message)
    return _git(root, "rev-parse", "HEAD").stdout.strip()


def outgoing_commits(vault_root: Path | str, remote: str, branch: str) -> tuple[str, ...]:
    """Return the complete outgoing range, not merely the staged files."""

    root = Path(vault_root).resolve(strict=True)
    result = _git(root, "log", "--format=%H %s", f"{remote}/{branch}..HEAD", check=False)
    if result.returncode != 0:
        raise CheckpointError("outgoing-range-unavailable")
    return tuple(line for line in result.stdout.splitlines() if line)


def push(
    vault_root: Path | str,
    remote: str,
    branch: str,
    *,
    authorized: bool,
    expected_commits: Sequence[str],
    force: bool = False,
) -> str:
    """Push only the inspected range, never forced, and only when authorized."""

    if force:
        raise CheckpointError("force-push-forbidden")
    if not authorized:
        raise CheckpointError("missing-push-authorization")
    root = Path(vault_root).resolve(strict=True)
    range_commits = outgoing_commits(root, remote, branch)
    if [line.split(" ", 1)[0] for line in range_commits] != list(expected_commits):
        raise CheckpointError("outgoing-range-contains-unrelated-commits")
    result = _git(root, "push", remote, f"HEAD:{branch}", check=False)
    if result.returncode != 0:
        raise CheckpointError("push-rejected-local-commit-preserved")
    local = _git(root, "rev-parse", "HEAD").stdout.strip()
    _git(root, "fetch", remote, branch, check=False)
    remote_head = _git(root, "rev-parse", f"{remote}/{branch}", check=False)
    if remote_head.returncode != 0 or remote_head.stdout.strip() != local:
        raise CheckpointError("remote-verification-mismatch")
    return local
