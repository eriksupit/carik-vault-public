#!/usr/bin/env python3
"""Translate Codex hook envelopes and dispatch the canonical shared hooks."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS = Path(__file__).resolve().parent
PATCH_PATH = re.compile(r"^\*\*\* (Add|Update|Delete) File: (.+)$", re.MULTILINE)
MOVE_PATH = re.compile(r"^\*\*\* Move to: (.+)$", re.MULTILINE)


def redacted(value):
    if isinstance(value, dict):
        return {key: redacted(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redacted(item) for item in value]
    if isinstance(value, str):
        value = re.sub(r"/(?:Users|home)/[^\s\"']+", "<USER_PATH>", value)
        return value if len(value) <= 500 else value[:500] + "<TRUNCATED>"
    return value


def record_probe(payload: dict, mode: str, target: str = "") -> None:
    destination = os.environ.get("VAULT_HOOK_PROBE_DIR")
    if not destination:
        return
    try:
        root = Path(destination).resolve()
        if not (str(root).startswith("/private/tmp/") or str(root).startswith("/tmp/")):
            return
        root.mkdir(parents=True, exist_ok=True)
        event = re.sub(r"[^A-Za-z0-9_-]", "_", str(payload.get("hook_event_name", "unknown")))
        body = {"adapter_mode": mode, "target": target, "payload": redacted(payload)}
        (root / f"{event}-{uuid.uuid4().hex}.json").write_text(
            json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def load_payload() -> dict:
    try:
        value = json.load(sys.stdin)
        return value if isinstance(value, dict) else {}
    except (json.JSONDecodeError, ValueError):
        return {}


def project_env() -> dict[str, str]:
    env = os.environ.copy()
    if "AGENT_PROJECT_DIR" not in env:
        env["AGENT_PROJECT_DIR"] = str(ROOT)
    if "CLAUDE_PROJECT_DIR" not in env:
        env["CLAUDE_PROJECT_DIR"] = str(ROOT)
    return env


def git_root_matches() -> bool:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            # Not a git repository: a generated vault before `git init`. Enforcement
            # must still run — activation never depends on git being present.
            return True
        return Path(result.stdout.strip()).resolve() == ROOT
    except (OSError, subprocess.SubprocessError):
        return True


def run_hook(script: str, payload: dict, args: list[str] | None = None) -> subprocess.CompletedProcess[str] | None:
    target = (HOOKS / script).resolve()
    if target.parent != HOOKS or not target.is_file():
        return None
    try:
        cmd = [sys.executable, str(target)]
        if args:
            cmd.extend(args)
        return subprocess.run(
            cmd,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=ROOT,
            env=project_env(),
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def emit(result: subprocess.CompletedProcess[str] | None, event: str) -> int:
    if result is None:
        return 0
    if result.stdout:
        output = result.stdout
        if event == "Stop":
            try:
                parsed = json.loads(output)
                if parsed.get("decision") == "block":
                    output = json.dumps(
                        {"decision": "block", "reason": parsed.get("reason", "Hook requested continuation.")}
                    )
            except (json.JSONDecodeError, AttributeError, ValueError):
                pass
        sys.stdout.write(output)
    elif event == "Stop" and result.returncode == 0:
        sys.stdout.write("{}")
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.returncode


def patch_targets(payload: dict) -> list[tuple[str, str, str, str]]:
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    if not isinstance(command, str):
        return []
    matches = list(PATCH_PATH.finditer(command))
    targets: list[tuple[str, str, str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else command.find("*** End Patch", match.end())
        section = command[match.start() : end if end >= 0 else len(command)]
        action, path = match.group(1), match.group(2).strip()
        move = MOVE_PATH.search(section)
        result_path = move.group(1).strip() if move else path
        targets.append((result_path, action, section, path))
    return list(dict.fromkeys(targets))


def patch_paths(payload: dict) -> list[str]:
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    if not isinstance(command, str):
        return []
    paths = [match.group(2).strip() for match in PATCH_PATH.finditer(command)]
    paths.extend(path.strip() for path in MOVE_PATH.findall(command))
    return list(dict.fromkeys(paths))


def projected_text(path: str, action: str, section: str, source_path: str = "") -> str:
    if action == "Delete":
        return ""
    target = Path(source_path or path)
    if not target.is_absolute():
        target = ROOT / target
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    for line in section.splitlines():
        if line.startswith("-") and not line.startswith("---"):
            try:
                lines.remove(line[1:])
            except ValueError:
                pass
        elif line.startswith("+") and not line.startswith("+++"):
            lines.append(line[1:])
    return "\n".join(lines)


def file_payload(
    payload: dict, path: str, action: str, section: str, source_path: str = ""
) -> dict:
    result = dict(payload)
    result["tool_input"] = {
        "file_path": path,
        "content": projected_text(path, action, section, source_path),
    }
    return result


def direct(payload: dict, script: str, extra_args: list[str] | None = None) -> int:
    return emit(run_hook(script, payload, extra_args), str(payload.get("hook_event_name") or ""))


def tool_payloads(payload: dict) -> list[tuple[str, dict]]:
    """Return (action, per-file payload) pairs for apply_patch, Write, and Edit."""
    tool_input = payload.get("tool_input")
    tool_name = payload.get("tool_name")
    if tool_name in ("Write", "Edit") and isinstance(tool_input, dict):
        path = tool_input.get("file_path") or tool_input.get("path")
        if not isinstance(path, str) or not path:
            return []
        return [(tool_name, {**payload, "tool_input": {**tool_input, "file_path": path}})]
    return [
        (action, file_payload(payload, path, action, section, source_path))
        for path, action, section, source_path in patch_targets(payload)
    ]


def patch_pre(payload: dict) -> int:
    for action, f_payload in tool_payloads(payload):
        if action == "Delete":
            continue
        for script in (
            "goal-contract-gate.py",
            "discussion-intake-gate.py",
            "artifact-research-gate.py",
            "prose-language-gate.py",
            "incident-gate.py",
        ):
            result = run_hook(script, f_payload)
            if result is not None and result.returncode != 0:
                return emit(result, "PreToolUse")
    return 0


def patch_post(payload: dict) -> int:
    for action, f_payload in tool_payloads(payload):
        if action not in ("Write", "Edit"):
            f_payload["tool_name"] = "Edit"
        for script in ("frontmatter-reminder.py", "artifact-preview-gate.py"):
            result = run_hook(script, f_payload)
            if result is not None and result.stderr:
                sys.stderr.write(result.stderr)
    return 0


def main() -> int:
    payload = load_payload()
    if not payload or not git_root_matches():
        return 0
    if len(sys.argv) < 2:
        return 0
    mode = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) >= 3 else ""
    extra_args = sys.argv[3:] if len(sys.argv) > 3 else None
    record_probe(payload, mode, target)
    if mode == "direct" and len(sys.argv) >= 3:
        return direct(payload, target, extra_args)
    if mode == "patch-pre":
        return patch_pre(payload)
    if mode == "patch-post":
        return patch_post(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
