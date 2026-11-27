#!/usr/bin/env python3
"""SessionStart hook: enforce the runtime-neutral project skill layout.

Project skills and commands remain exclusively under <vault>/.agents/. This hook
runs scripts/sync-skills.py at session start to remove obsolete managed
<vault>/.claude/skills and <vault>/.claude/commands adapters.

Idempotent. Claude-only by activation location; sync-skills without
--apply-codex never writes the global ~/.codex/config.toml, so Codex registration
stays an explicit opt-in.

Never blocks a session: a missing script or any failure exits 0 silently. Output
is suppressed so maintenance does not spam session context.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    script = Path(root) / "scripts" / "sync-skills.py"
    if not script.is_file():
        return 0
    try:
        subprocess.run(
            [sys.executable, str(script), "--wire-project", "--apply"],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )
    except Exception:  # ponytail: wiring is best-effort; never break a session over it
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
