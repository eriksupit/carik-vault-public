#!/usr/bin/env python3
"""PreToolUse gate: no prose document is written before `anti-translationese` runs.

The vault mandates the skill for Indonesian prose, but a mandate in prose is a
cognitive rule, and AGENTS.md states that a cognitive rule cannot be gated. What CAN
be gated is a filesystem fact: `skill-usage-recorder.py` appends every `Skill` call to
.agents/telemetry/skill-usage.jsonl with its session_id, so "was the skill invoked in
this session" is on disk and cannot be fabricated by an agent that skipped it.

So: a Write/Edit to a prose-bearing path is DENIED until this session's log carries an
`anti-translationese` entry. The agent's route past the gate is to actually invoke the
skill — there is no self-report to accept.

Scope is the vault's author-facing Indonesian prose (.md under work/, raw-kb/, and
writing-style/), excluding structured registries (raw-kb/SOURCES.md) and raw acquired
derivatives (raw-kb/agent-acquired/).

Fails open on any error or if declared language is not Indonesian.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

GATED_SKILL = "anti-translationese"
TELEMETRY = Path(".agents") / "telemetry" / "skill-usage.jsonl"

PROSE_ROOTS = ("work/", "writing-style/")
PROSE_SUFFIXES = (".md",)


def declared_prose_language(root: Path) -> str:
    """The vault's declared prose language from .agents/policy.json; '' when absent."""
    try:
        data = json.loads((root / Path(".agents") / "policy.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    lang = data.get("prose_language")
    return lang if isinstance(lang, str) else ""


def is_prose_target(root: Path, file_path: str) -> bool:
    if not file_path:
        return False
    if not declared_prose_language(root).startswith("id"):
        return False
    candidate = Path(file_path)
    if candidate.suffix.lower() not in PROSE_SUFFIXES:
        return False
    try:
        relative = candidate.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return False
    return any(relative.startswith(prefix) for prefix in PROSE_ROOTS)


def skill_used(root: Path, session_id: str) -> bool:
    log = root / TELEMETRY
    if not log.is_file():
        return False
    try:
        for line in log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get("session_id") == session_id and record.get("skill") == GATED_SKILL:
                return True
    except OSError:
        return False
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not isinstance(file_path, str):
        return 0

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    if not is_prose_target(root, file_path):
        return 0

    session_id = str(payload.get("session_id") or "unknown")
    if skill_used(root, session_id):
        return 0

    sys.stderr.write(
        f"Advisory (Class B): prose write to {file_path} before `{GATED_SKILL}` ran in this session.\n"
        f".agents/telemetry/skill-usage.jsonl carries no `{GATED_SKILL}` entry for this "
        "session_id.\n"
        f"Recommendation: invoke `{GATED_SKILL}` to audit prose style and natural Indonesian syntax.\n"
        "This check is diagnostic and non-blocking under the Reasoning-Over-Mechanic doctrine.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
