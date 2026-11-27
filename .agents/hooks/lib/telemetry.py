#!/usr/bin/env python3
"""Single owner of the skill-usage telemetry record schema.

`skill-usage-recorder.py` and every runtime adapter import this instead of
re-implementing the record shape: three copies of one schema is three places
for it to diverge, and the gates that consume this log would then mean
different things per runtime.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

TELEMETRY_RELATIVE = Path(".agents") / "telemetry" / "skill-usage.jsonl"


def record_skill_usage(root: Path, session_id: str, skill: str) -> None:
    """Append one canonical skill-usage record. Never raises past the caller."""
    log = root / TELEMETRY_RELATIVE
    log.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session_id": str(session_id)[:64],
        "skill": skill,
    }
    with log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
