#!/usr/bin/env python3
"""Tests for prose-language-gate.py."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "prose-language-gate.py"
SESSION = "test-session-0001"


def make_root(skills_logged: list[str]) -> Path:
    root = Path(tempfile.mkdtemp(prefix="prose-gate-test-"))
    for directory in ("work/scenes", "raw-kb/agent-acquired", "writing-style", "handoff", ".agents/skills/goal", "docs"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    log = root / ".agents" / "telemetry" / "skill-usage.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    (root / ".agents" / "policy.json").write_text(
        json.dumps({"prose_language": "id"}), encoding="utf-8")
    log.write_text(
        "".join(
            json.dumps({"at": "2026-08-12T00:00:00+00:00", "session_id": SESSION, "skill": s}) + "\n"
            for s in skills_logged
        ),
        encoding="utf-8",
    )
    return root


def run(root: Path, file_path: str, session: str = SESSION) -> int:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(root)
    payload = {"tool_name": "Write", "session_id": session, "tool_input": {"file_path": file_path}}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    ).returncode


def main() -> int:
    clean = make_root([])                          # skill never invoked
    ran = make_root(["anti-translationese"])       # skill invoked this session
    other = make_root(["recommendation"])          # a different skill invoked

    cases: list[tuple[str, int, int]] = [
        ("advises on a work prose draft without blocking", run(clean, f"{clean}/work/concept/draft.md"), 0),
        ("allows a raw-kb note without language gate", run(clean, f"{clean}/raw-kb/user-provided/source.md"), 0),
        ("allows raw-kb/SOURCES.md structured table", run(clean, f"{clean}/raw-kb/SOURCES.md"), 0),
        ("allows raw-kb/agent-acquired derivative", run(clean, f"{clean}/raw-kb/agent-acquired/doc.md"), 0),
        ("advises on a writing-style document without blocking", run(clean, f"{clean}/writing-style/panduan.md"), 0),
        ("advises when only a DIFFERENT skill ran", run(other, f"{other}/work/concept/draft.md"), 0),
        ("advises a different session_id sharing the log", run(ran, f"{ran}/work/concept/draft.md", "other-session"), 0),
        ("allows prose once the skill ran", run(ran, f"{ran}/work/concept/draft.md"), 0),
        ("allows AGENTS.md", run(clean, f"{clean}/AGENTS.md"), 0),
        ("allows a SKILL.md", run(clean, f"{clean}/.agents/skills/goal/SKILL.md"), 0),
        ("allows a handoff document", run(clean, f"{clean}/handoff/HANDOFF-x.md"), 0),
        ("allows a python file under work/", run(clean, f"{clean}/work/script.py"), 0),
        ("allows a doc outside the prose roots", run(clean, f"{clean}/docs/design/note.md"), 0),
        ("allows a path outside the vault entirely", run(clean, "/etc/hosts"), 0),
        ("never blocks with no file_path", run(clean, ""), 0),
    ]
    undeclared = make_root([])
    (undeclared / ".agents" / "policy.json").unlink()
    english = make_root([])
    (english / ".agents" / "policy.json").write_text(json.dumps({"prose_language": "en"}), encoding="utf-8")
    cases += [
        ("allows prose when no language is declared", run(undeclared, f"{undeclared}/work/scenes/S.md"), 0),
        ("allows prose in an English-declared vault", run(english, f"{english}/work/scenes/S.md"), 0),
    ]

    failures = 0
    for label, got, expected in cases:
        ok = got == expected
        failures += not ok
        print(f"{'ok' if ok else 'FAIL'}: {label} (exit {got}, expected {expected})")
    print(f"\n{len(cases) - failures}/{len(cases)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
