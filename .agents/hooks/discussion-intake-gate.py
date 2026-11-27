#!/usr/bin/env python3
"""PreToolUse gate: enforce discussion intake discipline across pipeline stages.

Class C physical safety brake: exits with code 2 to block premature agent drafting
in downstream stages before entry artifacts are established and marked active.
Supports dynamic profile resolution from profile.json and owner bypass.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

WRITE_TOOLS = {
    "write", "edit", "write_to_file", "replace_file_content",
    "multi_replace_file_content", "notebookedit", "apply_patch"
}

ACTIVE_STATUS_PATTERN = re.compile(
    r"^status:\s*(active|recorded|approved|completed|done)\b",
    re.MULTILINE | re.IGNORECASE,
)

INTAKE_EXEMPT_PATTERN = re.compile(
    r"^intake_exempt:\s*true\b",
    re.MULTILINE | re.IGNORECASE,
)


def resolve_profile(root: Path) -> dict:
    candidates = [
        root / "work" / "profile.json",
        root / "profile.json",
        root / "profiles" / "carik" / "profile.json",
    ]
    for cand in candidates:
        if cand.is_file():
            try:
                return json.loads(cand.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
    return {
        "pipeline": ["inbox", "concept", "drafts", "canon", "archive"],
        "entry_stage": "concept",
        "entry_artifacts": ["concept.md"],
    }


def is_intake_exempt(content: str, target_file: Path) -> bool:
    if content and INTAKE_EXEMPT_PATTERN.search(content):
        return True
    if target_file.is_file():
        try:
            disk_text = target_file.read_text(encoding="utf-8")
            if INTAKE_EXEMPT_PATTERN.search(disk_text):
                return True
        except OSError:
            pass
    return False


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_name = str(payload.get("tool_name") or "").lower()
    if tool_name and tool_name not in WRITE_TOOLS:
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = str(
        tool_input.get("file_path")
        or tool_input.get("path")
        or tool_input.get("TargetFile")
        or ""
    )
    if not file_path:
        return 0

    # Owner bypass via environment variable
    if os.environ.get("VAULT_BYPASS_INTAKE") == "1":
        return 0

    # Normalize relative to vault root
    p = Path(file_path.replace("\\", "/"))
    if p.is_absolute():
        try:
            rel_path = p.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            return 0  # Outside vault, handled by vault-boundary-guard
    else:
        rel_path = str(p).removeprefix("./")

    # Only gate files under work/
    if not rel_path.startswith("work/"):
        return 0

    parts = rel_path.split("/")
    # Exempt root work files like work/WORKFLOW.md or work/profile.json
    if len(parts) < 3:
        return 0

    target_stage = parts[1]
    target_file = (ROOT / rel_path).resolve()
    content = str(tool_input.get("content") or "")

    # Check for frontmatter exemption
    if is_intake_exempt(content, target_file):
        return 0

    profile = resolve_profile(ROOT)
    pipeline = profile.get("pipeline") or []
    entry_stage = profile.get("entry_stage") or "concept"
    entry_artifacts = profile.get("entry_artifacts") or []

    # If stage is not declared in pipeline, pass
    if target_stage not in pipeline or entry_stage not in pipeline:
        return 0

    target_idx = pipeline.index(target_stage)
    entry_idx = pipeline.index(entry_stage)

    # If target stage is downstream of entry stage
    if target_idx > entry_idx:
        # Check if entry artifacts exist and are active
        missing_or_inactive: list[str] = []
        for art_item in entry_artifacts:
            if isinstance(art_item, dict):
                artifact_name = str(art_item.get("target") or art_item.get("name") or "")
            else:
                artifact_name = str(art_item)

            if not artifact_name:
                continue

            cand1 = ROOT / "work" / artifact_name
            cand2 = ROOT / "work" / entry_stage / artifact_name
            cand3 = ROOT / artifact_name
            found_path = cand1 if cand1.is_file() else (cand2 if cand2.is_file() else (cand3 if cand3.is_file() else None))

            if not found_path:
                missing_or_inactive.append(f"missing: {artifact_name}")
                continue

            try:
                art_text = found_path.read_text(encoding="utf-8")
                if not ACTIVE_STATUS_PATTERN.search(art_text):
                    missing_or_inactive.append(f"inactive status: {artifact_name}")
            except OSError:
                missing_or_inactive.append(f"unreadable: {artifact_name}")

        if missing_or_inactive:
            err = (
                f"Blocked by discussion intake discipline: cannot draft in downstream stage '{target_stage}' "
                f"until entry stage '{entry_stage}' artifacts are established and marked active.\n"
                f"Unsatisfied entry requirements: {', '.join(missing_or_inactive)}.\n"
                f"Per Carik Charter line 156, conduct the intake interview with the project owner first, "
                f"or set intake_exempt: true in frontmatter, or export VAULT_BYPASS_INTAKE=1.\n"
            )
            sys.stderr.write(err)
            return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
