#!/usr/bin/env python3
"""Deterministic Incident Control Registry and Dual-Protocol Gate.

Modes:
  PreToolUse: Exit code 2 on prohibited actions, diagnostic on stderr.
  Stop:       Class B advisory only: a matched stop token prints a warning on stderr
              and exits 0 without a block decision (substring matching on prose must
              not judge meaning, CREATIVE-LAW Invariant 4).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
INCIDENTS_DIR = ROOT / ".agents" / "incidents"
INCIDENT_PATTERN = re.compile(r"^INC-\d{4}-[\w-]+\.md$")


def parse_simple_yaml(text: str) -> Dict[str, Any]:
    """Parse minimal YAML frontmatter without external dependencies."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("Missing initial '---' frontmatter delimiter")

    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx == -1:
        raise ValueError("Missing closing '---' frontmatter delimiter")

    data: Dict[str, Any] = {}
    current_parent: Optional[str] = None

    for raw_line in lines[1:end_idx]:
        line = raw_line.rstrip()
        if not line or line.strip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        if ":" not in stripped:
            continue

        key, val = stripped.split(":", 1)
        key = key.strip()
        val = val.strip().strip("'\"")

        if indent == 0:
            if not val:
                current_parent = key
                data[key] = {}
            else:
                current_parent = None
                data[key] = val
        elif indent > 0 and current_parent:
            data[current_parent][key] = val
        else:
            raise ValueError(f"Unexpected indentation in line: {raw_line}")

    return data


def load_incidents(is_stop_mode: bool) -> List[Dict[str, Any]]:
    """Load and validate all active incidents strictly matching INC-NNNN-*.md."""
    if not INCIDENTS_DIR.exists():
        return []

    incidents: List[Dict[str, Any]] = []
    for file in sorted(INCIDENTS_DIR.iterdir()):
        if not file.is_file():
            continue
        if not INCIDENT_PATTERN.match(file.name):
            continue

        content = file.read_text(encoding="utf-8")
        try:
            meta = parse_simple_yaml(content)
        except Exception as e:
            err_msg = f"Corrupted incident registry in {file.name}: {e}"
            sys.stderr.write(f"[incident-gate] ERROR: {err_msg}\n")
            if is_stop_mode:
                out = {"decision": "block", "reason": err_msg}
                print(json.dumps(out))
                sys.exit(0)
            else:
                sys.exit(2)

        meta["_file"] = file.name
        incidents.append(meta)

    return incidents


def handle_stop(payload: Dict[str, Any], incidents: List[Dict[str, Any]]) -> None:
    msg = payload.get("last_assistant_message", "")
    for inc in incidents:
        if inc.get("status") != "active" or inc.get("trigger_class") != "stop_token":
            continue
        token = inc.get("activation_predicate", {}).get("token")
        if token and token in msg:
            sys.stderr.write(
                f"[incident-gate] advisory [{inc.get('id', 'INC-UNKNOWN')}]: stop token '{token}' appears in the final message; review it before ending the turn.\n"
            )
    sys.exit(0)


def handle_pre_tool(payload: Dict[str, Any], incidents: List[Dict[str, Any]]) -> None:
    tool_name = payload.get("tool_name") or payload.get("toolAction") or ""
    tool_input = payload.get("tool_input") or {}

    command = (
        tool_input.get("command")
        or tool_input.get("CommandLine")
        or tool_input.get("cmd")
        or ""
    )
    file_path = (
        tool_input.get("file_path")
        or tool_input.get("TargetFile")
        or tool_input.get("path")
        or ""
    )

    for inc in incidents:
        if inc.get("status") != "active":
            continue

        trigger_class = inc.get("trigger_class", "")
        pred = inc.get("activation_predicate", {})
        token = pred.get("token")
        glob_pat = pred.get("glob")
        inc_id = inc.get("id", "INC-UNKNOWN")

        if trigger_class == "bash_command" and command:
            if token and token in command:
                sys.stderr.write(
                    f"[incident-gate] Blocked by incident gate [{inc_id}]: prohibited command token matched '{token}'.\n"
                )
                sys.exit(2)

        if trigger_class == "file_path" and file_path:
            import fnmatch
            if glob_pat and fnmatch.fnmatch(file_path, glob_pat):
                sys.stderr.write(
                    f"[incident-gate] Blocked by incident gate [{inc_id}]: prohibited file path glob matched '{glob_pat}'.\n"
                )
                sys.exit(2)
            elif token and token in file_path:
                sys.stderr.write(
                    f"[incident-gate] Blocked by incident gate [{inc_id}]: prohibited file token matched '{token}'.\n"
                )
                sys.exit(2)

    sys.exit(0)


def main() -> None:
    is_stop_mode = len(sys.argv) > 1 and sys.argv[1].lower() == "stop"

    raw_input = sys.stdin.read()
    payload: Dict[str, Any] = {}
    if raw_input.strip():
        try:
            payload = json.loads(raw_input)
        except Exception as e:
            sys.stderr.write(f"[incident-gate] Invalid JSON input: {e}\n")
            sys.exit(2 if not is_stop_mode else 0)

    if not is_stop_mode and "last_assistant_message" in payload and "tool_name" not in payload:
        is_stop_mode = True

    incidents = load_incidents(is_stop_mode)

    if is_stop_mode:
        handle_stop(payload, incidents)
    else:
        handle_pre_tool(payload, incidents)


if __name__ == "__main__":
    main()
