#!/usr/bin/env python3
"""PreToolUse gate: enforce ## Goal Contract before modifying engineering surfaces.

Scope is an explicit ALLOWLIST of engineering surfaces (docs/, profiles/, scripts/,
.agents/hooks/, .agents/skills/, .agents/commands/). work/ is deliberately ungated:
drafting is exploratory. Anchor files, handoff/, and telemetry are never gated.

The oracle is STRUCTURED, not a raw-transcript substring: only text authored by the
assistant in transcript message entries counts. A raw substring scan would let
writing this gate file, define-goal/SKILL.md, or a design document open the gate
permanently for the session (self-poisoning oracle).

Fail-open semantics: a missing transcript path, an inaccessible transcript, or
malformed plumbing exits 0 so a governance gate can never lock a session. Denial
happens ONLY when the transcript is readable and provably lacks the header.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

GOAL_CONTRACT_HEADER = "## Goal Contract"

GATED_PREFIXES = (
    "docs/",
    "profiles/",
    "scripts/",
    ".agents/hooks/",
    ".agents/skills/",
    ".agents/commands/",
)
EXEMPT_PREFIXES = (
    ".agents/telemetry/",
)

DENY_MESSAGE = (
    "Blocked: Goal Contract missing.\n"
    "Per AGENTS.md and define-goal/SKILL.md, you must post the '## Goal Contract' block "
    "visibly in chat (Objective, Completion condition, Evaluator, Out of scope, Ultimate goal) "
    "before performing mutating actions on substantive files.\n"
)


def relative_path(path_str: str, root: Path) -> str | None:
    p = Path(path_str.replace("\\", "/"))
    if not p.is_absolute():
        return str(p).removeprefix("./") or None
    try:
        return p.resolve().relative_to(root).as_posix()
    except (ValueError, OSError):
        return None


def is_gated_path(rel_path: str) -> bool:
    if not rel_path:
        return False
    for exempt in EXEMPT_PREFIXES:
        if rel_path == exempt or rel_path.startswith(exempt):
            return False
    return any(rel_path.startswith(p) for p in GATED_PREFIXES)


def transcript_text(transcript_path: Path) -> str | None:
    try:
        return transcript_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        pass
    except OSError:
        return None
    try:
        result = subprocess.run(
            ["zstd", "-dc", str(transcript_path)],
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def assistant_text(raw: str) -> str:
    pieces: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        entry_type = str(entry.get("type") or "")
        if "assistant" not in entry_type.lower() and "response" not in entry_type.lower():
            continue
        content = (entry.get("message") or {}).get("content") or entry.get("content")
        if isinstance(content, str):
            pieces.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    pieces.append(block["text"])
    return "\n".join(pieces)


def has_goal_contract_in_transcript(transcript_path: Path) -> bool:
    text = transcript_text(transcript_path)
    if text is None:
        return False
    if not any(line.strip().startswith("{") for line in text.splitlines()):
        return True
    return GOAL_CONTRACT_HEADER in assistant_text(text)


def extract_gated_targets(payload: dict, root: Path) -> list[str]:
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return []
    targets: list[str] = []
    for key in ("file_path", "path", "target_file", "TargetFile", "destination"):
        val = tool_input.get(key)
        if isinstance(val, str) and val.strip():
            rel = relative_path(val.strip(), root)
            if rel and is_gated_path(rel) and rel not in targets:
                targets.append(rel)

    command = tool_input.get("command")
    if isinstance(command, str) and command:
        for m in re.finditer(r"(?:>|>>|\b(?:touch|rm|cp|mv|tee)\s+)\s*([^\s;&|]+)", command):
            token = m.group(1).strip().strip("'\"")
            if token.startswith("&"):
                continue
            rel = relative_path(token, root)
            if rel and is_gated_path(rel) and rel not in targets:
                targets.append(rel)
    return targets


def transcript_accessible(transcript_path: Path) -> bool:
    if not transcript_path.is_file():
        return False
    return transcript_text(transcript_path) is not None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
        targets = extract_gated_targets(payload, root)
        if not targets:
            return 0

        transcript_str = payload.get("transcript_path", "")
        if not transcript_str:
            return 0

        t_path = Path(transcript_str)
        if not transcript_accessible(t_path):
            return 0

        if not has_goal_contract_in_transcript(t_path):
            sys.stderr.write(DENY_MESSAGE)
            return 2

        return 0
    except Exception:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
