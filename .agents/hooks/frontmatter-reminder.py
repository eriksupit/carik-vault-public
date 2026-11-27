#!/usr/bin/env python3
"""PostToolUse reminder: warn when an agent-written .md note lacks required frontmatter.

Non-blocking. Reads the Claude Code hook JSON from stdin. If a Write/Edit touched a
.md file (outside raw-kb/user-provided/) whose frontmatter is missing any of the six
required properties, print a warning so the agent fixes it. Exit 0 always.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REQUIRED = ("title", "date", "updated", "type", "status", "tags")


def missing_properties(text: str) -> list[str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return list(REQUIRED)
    try:
        close = lines.index("---", 1)
    except ValueError:
        return list(REQUIRED)
    keys = set()
    for line in lines[1:close]:
        m = re.match(r"^([A-Za-z0-9_-]+):", line)
        if m:
            keys.add(m.group(1))
    return [k for k in REQUIRED if k not in keys]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path", "")
    if not isinstance(path, str) or not path.endswith(".md"):
        return 0
    if "raw-kb/user-provided/" in path.replace("\\", "/"):
        return 0
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return 0
    missing = missing_properties(text)
    if missing:
        sys.stderr.write(
            f"Frontmatter reminder: {path} is missing {', '.join(missing)}. "
            "Every agent-created .md needs title, date, updated, type, status, tags "
            "(see WORKFLOW.md).\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
