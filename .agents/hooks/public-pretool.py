#!/usr/bin/env python3
"""Public Class C PreToolUse entrypoint for Carik Vault.

Runs three deterministic filesystem/security guards in order:
  1. vault-boundary-guard.py  (2-layer external boundary: hard-deny sensitive
     system/credential zones; interactive permission for ordinary work folders)
  2. git-scope-guard.py       (auto-dormant when ROOT_PAKET/.git is absent)
  3. interview_credential_redactor.py (fail-closed scan on persisted bytes)

Normalizes stdin JSON payloads from Claude Code, Antigravity, and Codex.
Never leaks secret values, payloads, hashes, or tracebacks on credential block.
"""
from __future__ import annotations

import codecs
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT_PAKET = Path(__file__).resolve().parents[2]
HOOKS_DIR = Path(__file__).resolve().parent

SENSITIVE_HOME_DIRS = (
    ".ssh",
    ".aws",
    ".gnupg",
    ".kube",
    ".config",
    ".gemini",
    ".codex",
    ".claude",
    "Library/LaunchAgents",
)

SAFE_HOME_SUBDIRS = (
    ".gemini/antigravity-cli/brain",
    ".gemini/antigravity/brain",
)

SENSITIVE_HOME_FILES = (
    ".netrc",
    ".zshrc",
    ".bashrc",
    ".bash_profile",
    ".zprofile",
    ".profile",
    ".npmrc",
    ".pypirc",
    ".gitconfig",
)

HARD_DENY_STDERR_MARKERS = (
    "allow-external",
    ".agents/sessions",
    "inline script",
    "dynamic variable or substitution",
    "unrecognized tool",
    "called without valid target path",
)

ANTIGRAVITY_TOOL_MAP = {
    "run_command": "Bash",
    "view_file": "Read",
    "read_file": "Read",
    "read_image": "Read",
    "view_file_outline": "Read",
    "view_code_item": "Read",
    "find_by_name": "Glob",
    "grep_search": "Grep",
    "list_dir": "Glob",
    # Non-mutating Antigravity, Codex, Claude Code, and MCP tools mapped to Read
    "search_web": "Read",
    "web_search": "Read",
    "WebSearch": "Read",
    "WebFetch": "Read",
    "read_url_content": "Read",
    "update_steps": "Read",
    "update_plan": "Read",
    "TodoWrite": "Read",
    "TaskCreate": "Read",
    "TaskUpdate": "Read",
    "TaskGet": "Read",
    "TaskList": "Read",
    "ask_question": "Read",
    "AskUserQuestion": "Read",
    "request_user_input": "Read",
    "manage_task": "Read",
    "command_status": "Read",
    "read_terminal": "Read",
    "schedule": "Read",
    "list_resources": "Read",
    "read_resource": "Read",
    "list_mcp_resources": "Read",
    "read_mcp_resource": "Read",
    "ListMcpResourcesTool": "Read",
    "ReadMcpResourceTool": "Read",
    "view_image": "Read",
    "send_message": "Read",
    "invoke_subagent": "Read",
    "define_subagent": "Read",
    "manage_subagents": "Read",
    "task_boundary": "Read",
    "notify_user": "Read",
    # Mutating tools
    "write_to_file": "Write",
    "write_file": "Write",
    "replace_file_content": "Edit",
    "multi_replace_file_content": "Edit",
    "edit_file": "Edit",
}

WRITE_TOOLS = {"Write", "Edit", "NotebookEdit", "apply_patch"}

PATCH_HEADER_RE = re.compile(r"^\*\*\* (Add|Update|Delete) File:\s*(.+)$", re.MULTILINE)
PATCH_MOVE_RE = re.compile(r"^\*\*\* Move to:\s*(.+)$", re.MULTILINE)
UNIFIED_DIFF_FILE_RE = re.compile(r"^(?:\+\+\+|---)[ \t]+(.+)$", re.MULTILINE)


def _normalize_diff_path(raw_path: str, *, strip_ab: bool = False) -> str:
    s = raw_path.strip()
    if not s:
        return ""
    if s[0] in ('"', "'"):
        q = s[0]
        end = 1
        escaped = False
        while end < len(s):
            ch = s[end]
            if escaped:
                escaped = False
            elif ch == "\\" and q == '"':
                escaped = True
            elif ch == q:
                break
            end += 1
        inner = s[1:end]
        if q == '"' and "\\" in inner:
            try:
                inner = codecs.escape_decode(inner.encode("utf-8"))[0].decode("utf-8", errors="replace")
            except Exception:
                pass
        s = inner.strip().strip("'\"")
    else:
        s = s.split("\t", 1)[0].strip().strip("'\"")
    if s == "/dev/null":
        return ""
    if strip_ab and s.startswith(("a/", "b/")):
        s = s[2:].lstrip()
        if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
            s = s[1:-1].strip()
    return s


def _extract_patch_text(args: dict) -> str:
    for key in ("patch", "input", "command", "cmd", "diff", "content"):
        val = args.get(key)
        if isinstance(val, str) and val:
            return val
    return ""


def _parse_patch_targets(patch_text: str) -> tuple[list[tuple[str, str, str, str]], list[str]]:
    if not patch_text:
        return [], []
    matches = list(PATCH_HEADER_RE.finditer(patch_text))
    targets: list[tuple[str, str, str, str]] = []
    paths: list[str] = []
    if matches:
        for index, match in enumerate(matches):
            end = (
                matches[index + 1].start()
                if index + 1 < len(matches)
                else patch_text.find("*** End Patch", match.end())
            )
            section = patch_text[match.start() : end if end >= 0 else len(patch_text)]
            action = match.group(1)
            src_path = _normalize_diff_path(match.group(2))
            move = PATCH_MOVE_RE.search(section)
            dst_path = _normalize_diff_path(move.group(1)) if move else src_path
            targets.append((dst_path, action, section, src_path))
            for cand in (src_path, dst_path):
                if cand and cand not in paths:
                    paths.append(cand)
        return targets, paths

    for match in UNIFIED_DIFF_FILE_RE.finditer(patch_text):
        cand = _normalize_diff_path(match.group(1), strip_ab=True)
        if cand and cand not in paths:
            paths.append(cand)
    return [], paths


def _load_redactor():
    spec = importlib.util.spec_from_file_location(
        "interview_credential_redactor",
        HOOKS_DIR / "interview_credential_redactor.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("scanner-failure")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _emit_antigravity(is_agy: bool, decision: str, reason: str | None = None) -> None:
    if not is_agy:
        return
    out: dict[str, str] = {"decision": decision}
    if reason is not None:
        out["reason"] = reason
    sys.stdout.write(json.dumps(out) + "\n")


def _is_claude_code(is_agy: bool, raw_payload: dict) -> bool:
    if is_agy:
        return False
    if os.environ.get("CODEX_SANDBOX") or os.environ.get("CODEX_THREAD_ID") or raw_payload.get("harness") == "codex":
        return False
    if os.environ.get("CLAUDE_PROJECT_DIR") or raw_payload.get("hook_event_name") == "PreToolUse":
        return True
    return False


def _extract_offending_paths(vbg_stderr: str, canon_input: dict, persist: dict) -> list[str]:
    paths: list[str] = []
    for line in vbg_stderr.splitlines():
        if line.startswith("  ") and line.strip():
            cand = line.strip()
            if cand not in paths:
                paths.append(cand)
    for key in ("file_path", "path", "target_file", "TargetFile", "destination", "notebook_path"):
        val = canon_input.get(key)
        if isinstance(val, str) and val.strip() and _resolve_inside_root(val.strip()) is None:
            if val.strip() not in paths:
                paths.append(val.strip())
    fp = persist.get("file_path")
    if isinstance(fp, str) and fp.strip() and _resolve_inside_root(fp.strip()) is None:
        if fp.strip() not in paths:
            paths.append(fp.strip())
    patch_paths = persist.get("patch_paths")
    if isinstance(patch_paths, list):
        for pp in patch_paths:
            if isinstance(pp, str) and pp.strip() and _resolve_inside_root(pp.strip()) is None:
                if pp.strip() not in paths:
                    paths.append(pp.strip())
    return paths


def _is_sensitive_external_path(path_str: str) -> bool:
    raw = path_str.strip().strip("'\"")
    if not raw:
        return False
    expanded = Path(raw).expanduser()
    lexical = Path(os.path.abspath(expanded if expanded.is_absolute() else ROOT_PAKET / expanded))
    try:
        resolved = lexical.resolve()
    except Exception:
        resolved = lexical

    home_lexical = Path(os.path.abspath(Path.home()))
    home_resolved = Path.home().resolve()

    for p in (lexical, resolved):
        name = p.name
        if name == ".env" or name.startswith(".env."):
            return True
        if ".agents/allow-external" in p.as_posix():
            return True
        for home in (home_lexical, home_resolved):
            try:
                rel = p.relative_to(home)
            except ValueError:
                continue
            parts = rel.parts
            if not parts:
                return True
            rel_posix = rel.as_posix()
            if any(rel_posix == sub or rel_posix.startswith(sub + "/") for sub in SAFE_HOME_SUBDIRS):
                continue
            if any(rel_posix == d or rel_posix.startswith(d + "/") for d in SENSITIVE_HOME_DIRS):
                return True
            if len(parts) == 1 and parts[0] in SENSITIVE_HOME_FILES:
                return True
    return False


def _is_hard_deny_boundary(vbg_stderr: str, offending: list[str]) -> bool:
    lowered = vbg_stderr.lower()
    if any(marker in lowered for marker in HARD_DENY_STDERR_MARKERS):
        return True
    if not offending:
        return True
    return any(_is_sensitive_external_path(p) for p in offending)


def _emit_claude_ask(offending: list[str]) -> None:
    target_label = ", ".join(offending[:3])
    reason = (
        f"Agen ingin menulis ke folder di luar Carik Vault ({target_label}). "
        "Klik Allow jika Anda mengizinkan tindakan ini."
    )
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }
    sys.stdout.write(json.dumps(out) + "\n")


def _normalize_payload(raw: dict) -> tuple[bool, str, dict, dict]:
    """Return (is_antigravity, canonical_tool, canonical_tool_input, persist_meta)."""
    if isinstance(raw.get("toolCall"), dict):
        tc = raw["toolCall"]
        raw_name = str(tc.get("name") or "")
        raw_args = tc.get("args")
        args = raw_args if isinstance(raw_args, dict) else ({"patch": raw_args} if isinstance(raw_args, str) else {})
        canon_tool = ANTIGRAVITY_TOOL_MAP.get(raw_name, raw_name)
        canon_input: dict[str, str] = {}
        persist: dict[str, object] = {}

        if canon_tool == "Bash":
            canon_input["command"] = str(args.get("CommandLine") or args.get("command") or "")
        elif canon_tool == "apply_patch":
            patch_text = _extract_patch_text(args)
            if patch_text:
                canon_input["patch"] = patch_text
            fpath = str(args.get("TargetFile") or args.get("Path") or args.get("file_path") or "")
            if fpath:
                canon_input["file_path"] = fpath
            patch_targets, patch_paths = _parse_patch_targets(patch_text)
            persist["file_path"] = fpath
            persist["patch"] = patch_text
            persist["patch_targets"] = patch_targets
            persist["patch_paths"] = patch_paths
        elif canon_tool in ("Write", "Edit"):
            fpath = str(
                args.get("TargetFile")
                or args.get("Path")
                or args.get("file_path")
                or ""
            )
            if fpath:
                canon_input["file_path"] = fpath
            content = args.get("CodeContent")
            if content is None:
                content = args.get("Content")
            if isinstance(content, str):
                canon_input["content"] = content
                persist["content"] = content
            old_str = args.get("TargetContent")
            if old_str is None:
                old_str = args.get("Target")
            if isinstance(old_str, str):
                persist["old_string"] = old_str
            new_str = args.get("ReplacementContent")
            if new_str is None:
                new_str = args.get("Replacement")
            if isinstance(new_str, str):
                canon_input["new_string"] = new_str
                persist["new_string"] = new_str
            chunks = args.get("ReplacementChunks")
            if isinstance(chunks, list):
                persist["chunks"] = chunks
            if args.get("Append") is True:
                persist["append"] = True
            persist["file_path"] = fpath
        elif canon_tool in ("Read", "Grep", "Glob"):
            fpath = str(args.get("AbsolutePath") or args.get("Path") or args.get("file_path") or "")
            if fpath:
                canon_input["file_path"] = fpath
        return True, canon_tool, canon_input, persist

    # Claude Code / Codex envelope
    raw_name = str(raw.get("tool_name") or raw.get("tool") or "")
    tinput = raw.get("tool_input")
    if isinstance(tinput, str):
        tinput = {"patch": tinput}
    elif not isinstance(tinput, dict):
        alt = raw.get("input")
        tinput = alt if isinstance(alt, dict) else ({"patch": alt} if isinstance(alt, str) else {})
    canon_tool = ANTIGRAVITY_TOOL_MAP.get(raw_name, raw_name)
    canon_input = dict(tinput)
    if "cmd" in canon_input and "command" not in canon_input:
        canon_input["command"] = canon_input["cmd"]
    fpath = str(
        canon_input.get("file_path")
        or canon_input.get("path")
        or canon_input.get("target_file")
        or canon_input.get("TargetFile")
        or canon_input.get("notebook_path")
        or ""
    )
    patch_text = _extract_patch_text(canon_input) if canon_tool == "apply_patch" else (
        canon_input.get("patch") if isinstance(canon_input.get("patch"), str) else canon_input.get("input")
    )
    if canon_tool == "apply_patch" and isinstance(patch_text, str) and patch_text and "patch" not in canon_input:
        canon_input["patch"] = patch_text
    patch_targets, patch_paths = _parse_patch_targets(patch_text) if isinstance(patch_text, str) else ([], [])
    persist = {
        "file_path": fpath,
        "content": canon_input.get("content") if isinstance(canon_input.get("content"), str) else canon_input.get("new_source"),
        "old_string": canon_input.get("old_string") if isinstance(canon_input.get("old_string"), str) else canon_input.get("target"),
        "new_string": canon_input.get("new_string") if isinstance(canon_input.get("new_string"), str) else canon_input.get("replacement"),
        "patch": patch_text,
        "patch_targets": patch_targets,
        "patch_paths": patch_paths,
        "append": bool(canon_input.get("append")),
    }
    return False, canon_tool, canon_input, persist


def _run_guard(script_name: str, canonical_payload: dict) -> subprocess.CompletedProcess[str]:
    script_path = (HOOKS_DIR / script_name).resolve()
    env = os.environ.copy()
    env.setdefault("CLAUDE_PROJECT_DIR", str(ROOT_PAKET))
    env.setdefault("AGENT_PROJECT_DIR", str(ROOT_PAKET))
    return subprocess.run(
        [sys.executable, "-B", str(script_path)],
        input=json.dumps(canonical_payload),
        text=True,
        capture_output=True,
        cwd=ROOT_PAKET,
        env=env,
        timeout=30,
        check=False,
    )


def _resolve_inside_root(file_path: str) -> Path | None:
    if not file_path:
        return None
    expanded = Path(file_path).expanduser()
    p = expanded if expanded.is_absolute() else ROOT_PAKET / expanded
    try:
        resolved = p.resolve()
        root_resolved = ROOT_PAKET.resolve()
        resolved.relative_to(root_resolved)
        return resolved
    except Exception:
        return None


def _project_patch_bytes(persist: dict) -> bytes:
    pieces: list[str] = []
    patch_targets = persist.get("patch_targets")
    if isinstance(patch_targets, list) and patch_targets:
        for dst_path, action, section, src_path in patch_targets:
            if action == "Delete":
                continue
            existing_lines: list[str] = []
            src_resolved = _resolve_inside_root(str(src_path or dst_path or ""))
            if src_resolved is not None and src_resolved.is_file():
                existing_lines = src_resolved.read_bytes().decode("utf-8", errors="strict").splitlines()
            proj_lines = list(existing_lines)
            stripped_section: list[str] = []
            for line in str(section).splitlines():
                if line.startswith(("*** ", "@@")):
                    continue
                if line.startswith("-") and not line.startswith("---"):
                    try:
                        proj_lines.remove(line[1:])
                    except ValueError:
                        pass
                elif line.startswith("+") and not line.startswith("+++"):
                    proj_lines.append(line[1:])
                    stripped_section.append(line[1:])
                elif line.startswith(" "):
                    stripped_section.append(line[1:])
                elif not line.startswith(("+++", "---")):
                    stripped_section.append(line)
            if stripped_section:
                pieces.append("\n".join(stripped_section))
            if proj_lines:
                pieces.append("\n".join(proj_lines))
        return "\n".join(pieces).encode("utf-8", errors="strict")

    raw_text = str(persist.get("patch") or persist.get("content") or persist.get("new_string") or "")
    if not raw_text:
        return b""
    unprefixed = [
        line[1:] if (line.startswith("+") and not line.startswith("+++")) else line
        for line in raw_text.splitlines()
        if not (line.startswith("-") and not line.startswith("---"))
    ]
    return (raw_text + "\n" + "\n".join(unprefixed)).encode("utf-8", errors="strict")


def _project_post_image_bytes(canon_tool: str, persist: dict) -> bytes | None:
    if canon_tool not in WRITE_TOOLS:
        return None

    if canon_tool == "apply_patch":
        return _project_patch_bytes(persist)

    target = _resolve_inside_root(str(persist.get("file_path") or ""))
    existing_bytes: bytes | None = None
    if target is not None and target.is_file():
        existing_bytes = target.read_bytes()

    if canon_tool == "Write":
        content = persist.get("content")
        if not isinstance(content, str):
            return b""
        new_bytes = content.encode("utf-8", errors="strict")
        if persist.get("append") and existing_bytes is not None:
            return existing_bytes + new_bytes
        return new_bytes

    if canon_tool == "Edit":
        chunks = persist.get("chunks")
        old_s = persist.get("old_string")
        new_s = persist.get("new_string")
        if existing_bytes is not None:
            existing_text = existing_bytes.decode("utf-8", errors="strict")
            projected = existing_text
            if isinstance(chunks, list) and chunks:
                for ch in chunks:
                    if not isinstance(ch, dict):
                        continue
                    t_c = ch.get("TargetContent")
                    r_c = ch.get("ReplacementContent")
                    if isinstance(r_c, str):
                        if isinstance(t_c, str) and t_c and t_c in projected:
                            projected = projected.replace(t_c, r_c, 1)
                        else:
                            projected = projected + "\n" + r_c
            elif isinstance(new_s, str):
                if isinstance(old_s, str) and old_s and old_s in projected:
                    projected = projected.replace(old_s, new_s)
                else:
                    projected = projected + "\n" + new_s
            return projected.encode("utf-8", errors="strict")
        if isinstance(chunks, list) and chunks:
            joined = "\n".join(
                str(ch.get("ReplacementContent") or "")
                for ch in chunks
                if isinstance(ch, dict)
            )
            return joined.encode("utf-8", errors="strict")
        if isinstance(new_s, str):
            return new_s.encode("utf-8", errors="strict")
        if isinstance(persist.get("content"), str):
            return str(persist["content"]).encode("utf-8", errors="strict")
        return b""

    if canon_tool == "NotebookEdit":
        text = persist.get("patch") or persist.get("content") or persist.get("new_string") or ""
        return str(text).encode("utf-8", errors="strict")

    return None


def main() -> int:
    raw_bytes = sys.stdin.buffer.read()
    try:
        raw_text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        sys.stderr.write("scanner-failure\n")
        return 2

    if not raw_text.strip():
        return 0

    try:
        raw_payload = json.loads(raw_text)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(raw_payload, dict):
        return 0

    is_agy, canon_tool, canon_input, persist = _normalize_payload(raw_payload)
    canonical_payload = {"tool_name": canon_tool, "tool_input": canon_input}
    claude_ask_targets: list[str] | None = None

    # (a) vault-boundary-guard.py (2-layer external boundary)
    vbg = _run_guard("vault-boundary-guard.py", canonical_payload)
    if vbg.returncode != 0:
        offending = _extract_offending_paths(vbg.stderr, canon_input, persist)
        if _is_hard_deny_boundary(vbg.stderr, offending):
            reason = vbg.stderr.strip() or "vault-boundary-blocked"
            if vbg.stderr:
                sys.stderr.write(vbg.stderr)
            _emit_antigravity(is_agy, "deny", reason)
            return 2
        if _is_claude_code(is_agy, raw_payload):
            claude_ask_targets = offending

    # (b) git-scope-guard.py — auto-dormant when ROOT_PAKET/.git is absent
    if (ROOT_PAKET / ".git").exists() and canon_tool == "Bash" and canon_input.get("command"):
        gsg = _run_guard("git-scope-guard.py", canonical_payload)
        if gsg.returncode != 0:
            reason = gsg.stderr.strip() or "git-scope-blocked"
            if gsg.stderr:
                sys.stderr.write(gsg.stderr)
            _emit_antigravity(is_agy, "deny", reason)
            return 2

    # (c) interview_credential_redactor.py — fail-closed scan on persisted post-image
    if canon_tool in WRITE_TOOLS:
        try:
            redactor = _load_redactor()
            post_bytes = _project_post_image_bytes(canon_tool, persist)
            if post_bytes is not None:
                redactor.assert_destination_safe(post_bytes)
        except Exception as exc:
            family = getattr(exc, "family", "scanner-failure")
            sys.stderr.write(f"{family}\n")
            _emit_antigravity(is_agy, "deny", family)
            return 2

    if claude_ask_targets is not None:
        _emit_claude_ask(claude_ask_targets)
        return 0

    _emit_antigravity(is_agy, "allow")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
