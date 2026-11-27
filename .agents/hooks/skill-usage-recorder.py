#!/usr/bin/env python3
"""PreToolUse recorder: log which skills a session actually invoked.

The vault mandates fifteen-odd governance skills but measures none of them, so
nobody — owner or agent — can see the compliance rate. This hook is the missing
instrument: it appends one line per `Skill` tool call to a per-session log under
.agents/telemetry/, from which "which skills never fire" becomes a countable fact
instead of an impression.

Why PreToolUse on the `Skill` matcher rather than a Stop hook reading the
transcript: the transcript "is written asynchronously and may lag the in-memory
conversation" (Claude Code hooks reference), so a turn-end reader sees an
incomplete turn. A PreToolUse hook sees each call as it happens. And because the
harness — not the agent — decides when this fires, the record cannot be fabricated
by an agent that skipped the skill, unlike a marker the agent writes for itself.

Records only, never blocks: always exit 0, no stdout. Whether to gate on this data
is a later decision that belongs to the owner, taken once the numbers exist.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Load shared telemetry writer via spec to avoid package-relative import issues
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("hook_telemetry", Path(__file__).resolve().parent / "lib" / "telemetry.py")
_telemetry = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_telemetry)
record_skill_usage = _telemetry.record_skill_usage


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        skill = (payload.get("tool_input") or {}).get("skill")
        if not isinstance(skill, str) or not skill:
            return 0
        session = str(payload.get("session_id") or "unknown")
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
        record_skill_usage(root, session, skill)
    except Exception:  # ponytail: telemetry must never break a session
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
