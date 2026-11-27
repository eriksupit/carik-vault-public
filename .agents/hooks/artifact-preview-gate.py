#!/usr/bin/env python3
"""PostToolUse hook: trigger local HTML preview compilation on Markdown or Canvas writes.

Class B advisory hook: emits clickable URI and absolute filesystem path to stderr.
Never blocks file operations (always exits 0).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "preview_artifact.py"

PREVIEW_EXTENSIONS = (".md", ".canvas")
WRITE_TOOLS = {
    "write", "edit", "write_to_file", "replace_file_content",
    "multi_replace_file_content", "notebookedit", "apply_patch"
}


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_name = str(payload.get("tool_name") or "").lower()
    tool_input = payload.get("tool_input") or {}
    file_path = str(
        tool_input.get("file_path")
        or tool_input.get("path")
        or tool_input.get("TargetFile")
        or ""
    )

    if not file_path:
        return 0

    # Pre-filter: only process file writing/editing tools
    if tool_name and tool_name not in WRITE_TOOLS:
        return 0

    # Pre-filter: extension must be .md or .canvas
    target = Path(file_path)
    if target.suffix.lower() not in PREVIEW_EXTENSIONS:
        return 0

    target_abs = (ROOT / target).resolve() if not target.is_absolute() else target.resolve()
    if not target_abs.is_file():
        return 0

    if not SCRIPT.is_file():
        return 0

    try:
        res = subprocess.run(
            [sys.executable, str(SCRIPT), str(target_abs)],
            capture_output=True,
            text=True,
            timeout=5.0,
            check=False,
            cwd=str(ROOT),
        )
        if res.returncode == 0 and res.stdout.strip():
            sys.stderr.write(f"Artifact preview generated:\n{res.stdout.strip()}\n")
        elif res.stderr.strip():
            sys.stderr.write(f"Preview advisory: {res.stderr.strip()}\n")
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
        sys.stderr.write(f"Preview advisory (timeout or execution error): {e}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
