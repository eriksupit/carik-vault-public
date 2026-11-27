#!/usr/bin/env python3
"""PreToolUse gate: block an ungrounded write to a pipeline artifact under work/.

Replaces the former PostToolUse `artifact-research-reminder.py`, which could only
regret a write that had already happened. That file's own docstring gave the reason
a gate was rejected: browsing cannot be verified deterministically. True — but the
*grounding* can. WORKFLOW.md (Per-Artifact Research Loop) requires the artifact to
cite its registered `source_id`s, and requires the `raw-kb/SOURCES.md` row to
exist BEFORE the source is used as evidence. So the checkable fact is not "did
the agent browse" but "does this text name a source that is actually registered".
That is a filesystem fact, not an agent's self-report — which is why this gate does
not use a marker the agent writes for itself.

Checks the resulting text of a Write/Edit against every `source_id:` value in
`raw-kb/SOURCES.md` by substring. Deliberately format-agnostic: source_ids are
heterogeneous (dates, hyphenated titles, CAPS), so the registry is the pattern
source and the artifact is searched for it, never the reverse.

Exit 2 (blocks) when no registered source_id appears.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

SOURCE_ID = re.compile(r"^source_id:[ \t]*(\S+)[ \t]*$", re.MULTILINE)

POLICY = Path(".agents") / "policy.json"

MESSAGE = (
    "Blocked: {path} is a pipeline artifact and the text names no registered source.\n"
    "Per WORKFLOW.md (Per-Artifact Research Loop), research before writing — browse "
    "for the knowledge it needs (mandatory, automatic, standing-authorized in scope), "
    "register each acquired source in raw-kb/SOURCES.md with a full row, then write "
    "citing the registered source_id values.\n"
    "A pure-synthesis artifact still cites the source_ids carried by the upstream "
    "approved artifacts it distills. If this artifact genuinely cannot cite one, ask "
    "the owner rather than writing it ungrounded.\n"
)


def relative(path: str, root: Path) -> str | None:
    """Path relative to the vault root, forward-slashed; None if outside."""
    p = Path(path.replace("\\", "/"))
    if not p.is_absolute():
        return str(p).removeprefix("./") or None
    try:
        return p.resolve().relative_to(root).as_posix()
    except (ValueError, OSError):
        return None


def evidence_bearing_targets(root: Path) -> set[str]:
    """Artifact targets declared evidence_bearing in .agents/policy.json."""
    try:
        data = json.loads((root / POLICY).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    targets = data.get("evidence_bearing")
    if not isinstance(targets, list):
        return set()
    return {t for t in targets if isinstance(t, str)}


def is_gated_artifact(rel: str, gated: set[str]) -> bool:
    if not rel.startswith("work/") or not rel.endswith(".md"):
        return False
    return rel.removeprefix("work/") in gated


def registered_ids(root: Path) -> set[str]:
    try:
        text = (root / "raw-kb" / "SOURCES.md").read_text(encoding="utf-8")
    except OSError:
        return set()
    return {m.group(1) for m in SOURCE_ID.finditer(text)}


def written_text(tool_input: dict, target: Path) -> str:
    content = tool_input.get("content")
    if isinstance(content, str):
        return content
    parts = [tool_input.get("new_string", "")]
    try:
        parts.append(target.read_text(encoding="utf-8"))
    except OSError:
        pass
    return "\n".join(p for p in parts if isinstance(p, str))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
        tool_input = payload.get("tool_input") or {}
        path = tool_input.get("file_path", "")
        if not isinstance(path, str) or not path:
            return 0
        rel = relative(path, root)
        if not rel:
            return 0
        gated = evidence_bearing_targets(root)
        if not gated or not is_gated_artifact(rel, gated):
            return 0
        ids = registered_ids(root)
        if not ids:
            sys.stderr.write(MESSAGE.format(path=rel))
            return 2
        text = written_text(tool_input, root / rel)
        if any(sid in text for sid in ids):
            return 0
        sys.stderr.write(MESSAGE.format(path=rel))
        return 2
    except Exception:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
