#!/usr/bin/env python3
"""PreToolUse guard: block any tool call that WRITES to a user path outside this vault.

AGENTS.md "Mandatory Project Boundary" owns the rule and SCOPE.md "Out of scope"
carries its scope clause: writing anywhere outside this vault — another vault, another
repository, a user-global store, a global configuration — requires separate explicit
owner authorization naming that target.

Those are cognitive rules, and a cognitive rule cannot be gated. This hook converts
the boundary into a filesystem fact so it CAN be gated: a WRITE to a path under the
user-home root that is not inside the vault is denied before the tool runs.

READING IS NOT GATED. Owner ruling of 2026-08-18 repealed the clause that made a read
count as operating in a foreign directory. One hook was enforcing two prohibitions of
very different weight — the write ban, which has a corruption incident behind it, and
a read ban, which had none — and the cheap one was being charged on every ordinary
call: an owner-supplied PDF in ~/Downloads, a sibling repository, an intake copy. The
split is by TOOL, not by path.

A vault this harness GENERATED is never written to. That prohibition is absolute and
untouched by the read repeal — see `GENERATED_VAULTS_ARE_NEVER_WRITABLE`.

Three branches:

  * A read-only tool (`Read`, `Grep`, `Glob`, `NotebookRead`) returns immediately with
    no path inspection at all.
  * A shell call is allowed to name an external path only when the whole command reads:
    every segment's head verb is in `READ_ONLY_HEADS`, no redirect or `tee` appears, and
    an inbound copy (`cp`/`rsync`/`install`) writes its destination inside the vault.
  * Everything else — `Write`, `Edit`, `NotebookEdit`, `apply_patch`, and any tool name
    this file does not recognise, including a missing one — takes the path sweep and the
    denial. Unknown fails closed.

System paths (/usr, /bin, /opt, /etc, /Library, /System, /dev, /var, /tmp) are not user
data and never blocked. The session scratchpad is allowed.

Standing exception, authorized by the owner on 2026-08-13: this vault's OWN
internal-memory mirror at `<home>/.claude/projects/<vault-slug>/memory/`. Governance
requires the durable memory surfaces to be synced together, and a boundary that blocks
the mirror guarantees the mirror goes stale — the failure this exception exists to
prevent. The opening is the narrowest that works: that one directory, derived from the
vault path rather than hardcoded, and nothing else under `~/.claude`.

Escape hatch, owner-controlled and deliberately manual: set

    VAULT_ALLOW_EXTERNAL=/absolute/prefix[<os.pathsep>/another/prefix]

to authorize a NAMED external WRITE target for that runtime process. Entries are
split on `os.pathsep` (`:` on POSIX, `;` on Windows) and relative entries are ignored.
Naming the target is exactly what SCOPE.md requires, so the authorization mechanism
mirrors the rule's wording. It is read from the environment of THIS process, which is
the agent runtime's environment — an inline `VAULT_ALLOW_EXTERNAL=... cmd` inside a
gated command does not reach it, so the variable has to be exported before the runtime
starts.

Portability is POSIX-first and proven on macOS only. `USER_ROOT`, the shell-token
scan, `ALWAYS_ALLOWED`, and the memory-mirror slug assume `/`-separated paths; on
native Windows the system temp directory sits under the user root and would be denied.
Native Windows behavior is unverified until the P10 test matrix.

Never blocks on a parse failure — a broken guard must not break the session.
"""
from __future__ import annotations

import codecs
import json
import os
import re
import shlex
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent.parent

# Paths under user root that are allowed even though they sit outside the vault.
ALWAYS_ALLOWED = (
    "/private/tmp/",
    "/tmp/",
    "/var/folders/",
)

# Sensitive zones outside the vault that are ALWAYS hard-denied even under --interactive-approval.
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

# Tool names that only ever read. Compared lowercased.
READ_ONLY_TOOLS = {
    "read", "grep", "glob", "notebookread",
    "read_image", "read_file", "view_file", "view_file_outline", "view_code_item",
    "find_by_name", "grep_search", "list_dir",
    "search_web", "web_search", "websearch", "webfetch", "read_url_content",
    "update_steps", "update_plan", "todowrite",
    "taskcreate", "taskupdate", "taskget", "tasklist",
    "ask_question", "askuserquestion", "request_user_input",
    "schedule", "manage_task", "command_status", "read_terminal",
    "list_resources", "read_resource", "list_mcp_resources", "read_mcp_resource",
    "listmcpresourcestool", "readmcpresourcetool", "view_image",
    "send_message", "invoke_subagent", "define_subagent", "manage_subagents",
    "task_boundary", "notify_user",
}

KNOWN_WRITE_TOOLS = {
    "write", "edit", "notebookedit", "apply_patch",
    "write_to_file", "write_file",
    "replace_file_content", "multi_replace_file_content", "edit_file",
}

PATCH_HEADER_RE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File:\s*(.+)$", re.MULTILINE)
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


def extract_patch_paths(tool_input: dict) -> list[str]:
    patch_text = ""
    for key in ("patch", "input", "command", "cmd", "diff", "content"):
        val = tool_input.get(key)
        if isinstance(val, str) and val:
            patch_text = val
            break
    if not patch_text:
        return []
    paths = [_normalize_diff_path(m.group(1)) for m in PATCH_HEADER_RE.finditer(patch_text)]
    paths.extend(_normalize_diff_path(m.group(1)) for m in PATCH_MOVE_RE.finditer(patch_text))
    paths = [p for p in paths if p]
    if not paths:
        paths = [
            p
            for m in UNIFIED_DIFF_FILE_RE.finditer(patch_text)
            for p in (_normalize_diff_path(m.group(1), strip_ab=True),)
            if p
        ]
    return list(dict.fromkeys(paths))

BASH_TOOLS = {"bash", "shell", "run_command"}

# Allowlist of shell readers
READ_ONLY_HEADS = {
    "cat", "head", "tail", "less", "more", "ls", "wc", "file", "stat", "du",
    "find", "grep", "egrep", "fgrep", "rg", "diff", "cmp", "md5", "shasum",
    "basename", "dirname", "realpath", "echo", "pwd", "which", "test",
    "true", "false", ":", "[", "[[",
}
GIT_READ_SUBCOMMANDS = {"log", "status", "diff", "show", "blame", "ls-files", "rev-parse"}
COPY_HEADS = {"cp", "rsync", "install"}

SEGMENT_SPLIT = re.compile(r"\|\||&&|;|\||\n")
REDIRECT_TARGET = re.compile(r"\d*>{1,2}\s*([^\s;|&]+)")
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
GIT_VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
CONTROL_PREFIXES = {"if", "elif", "then", "else", "do", "done", "fi", "esac", "while",
                    "until", "{", "}", "!", "time"}
CONTROL_WORD_LISTS = {"for", "case", "select"}
SUBSTITUTION = re.compile(r"\$\(|`")
FIND_WRITE_ACTIONS = {"-delete", "-exec", "-execdir", "-ok", "-okdir",
                      "-fls", "-fprint", "-fprint0", "-fprintf"}

ENV_VALUE_FLAGS = {"-u", "-C", "--chdir"}
NICE_VALUE_FLAGS = {"-n"}


def unwrap_command_tokens(tokens: list[str]) -> list[str]:
    """Unwrap variable assignments, shell control keywords, and command wrappers with their flags/arguments."""
    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        if ASSIGNMENT.match(tok) or tok in CONTROL_PREFIXES:
            idx += 1
            continue
        if tok == "command":
            idx += 1
            while idx < len(tokens):
                t = tokens[idx]
                if t == "--":
                    idx += 1
                    break
                if t.startswith("-") and t != "-":
                    idx += 1
                    continue
                break
            continue
        if tok == "env":
            idx += 1
            while idx < len(tokens):
                t = tokens[idx]
                if t == "--":
                    idx += 1
                    break
                if ASSIGNMENT.match(t):
                    idx += 1
                    continue
                if t in ("-S", "--split-string"):
                    idx += 1
                    if idx < len(tokens):
                        split_str = tokens[idx]
                        idx += 1
                        try:
                            injected = shlex.split(split_str)
                            tokens = tokens[:idx] + injected + tokens[idx:]
                        except ValueError:
                            pass
                    continue
                if t.startswith("-S") and len(t) > 2:
                    split_str = t[3:] if t.startswith("-S=") else t[2:]
                    idx += 1
                    try:
                        injected = shlex.split(split_str)
                        tokens = tokens[:idx] + injected + tokens[idx:]
                    except ValueError:
                        pass
                    continue
                if t.startswith("--split-string="):
                    split_str = t.split("=", 1)[1]
                    idx += 1
                    try:
                        injected = shlex.split(split_str)
                        tokens = tokens[:idx] + injected + tokens[idx:]
                    except ValueError:
                        pass
                    continue
                if t in ENV_VALUE_FLAGS:
                    idx += 2  # skip flag and its option argument (-u FOO, -C /dir)
                    continue
                if any(t.startswith(f"{vf}=") for vf in ("--chdir",)):
                    idx += 1
                    continue
                if t.startswith("-") and t != "-":
                    idx += 1
                    continue
                break
            continue
        if tok == "nice":
            idx += 1
            while idx < len(tokens):
                t = tokens[idx]
                if t == "--":
                    idx += 1
                    break
                if t in NICE_VALUE_FLAGS:
                    idx += 2
                    continue
                if t.startswith("-") and t != "-":
                    idx += 1
                    continue
                break
            continue
        if tok in ("nohup", "exec", "builtin"):
            idx += 1
            while idx < len(tokens):
                t = tokens[idx]
                if t == "--":
                    idx += 1
                    break
                if t.startswith("-") and t != "-":
                    idx += 1
                    continue
                break
            continue
        break
    return tokens[idx:]


def memory_mirror_prefix() -> str:
    """This vault's own internal-memory mirror directory, derived from the vault path."""
    slug = str(VAULT).replace("/", "-")
    return str(Path.home() / ".claude" / "projects" / slug / "memory") + "/"


USER_ROOT = str(Path.home().parent)
PATH_TOKEN = re.compile(re.escape(USER_ROOT) + r"/[^\s'\"`,;:()\[\]{}<>|&]+")
TILDE_TOKEN = re.compile(r"~[^\s'\"`,;:()\[\]{}<>|&]*")


def GENERATED_VAULTS_ARE_NEVER_WRITABLE() -> None:
    """THE HARNESS NEVER CHANGES A VAULT IT GENERATED. NOT ONE FILE."""


MUTATING_HEADS = {
    "cp", "mv", "tee", "touch", "sed", "install", "rm", "truncate", "mkdir",
}
INTERPRETERS = {"python", "python3", "perl", "ruby", "node", "bash", "sh", "zsh"}
INTERPRETER_EVAL_FLAGS = {"-c", "-e"}
INLINE_EXTERNAL_WRITE_MARKERS = (
    "Path.home()", "os.path.expanduser", "os.environ['HOME']", 'os.environ["HOME"]',
    "os.environ.get('HOME')", 'os.environ.get("HOME")', "$ENV{HOME}",
)
INLINE_MUTATION_PATTERNS = re.compile(
    r"(?:"
    r"open\s*\([^)]*['\"][wa\+x]"     # open() in write/append/create mode
    r"|\.write\s*\("                  # .write()
    r"|\.writelines\s*\("             # .writelines()
    r"|write_text\s*\("               # Path.write_text()
    r"|write_bytes\s*\("              # Path.write_bytes()
    r"|os\.(?:remove|unlink|rmdir|mkdir|makedirs|rename|replace)\s*\("
    r"|shutil\.(?:rmtree|copy|move)\s*\("
    r"|fs\.(?:write|append|unlink|rm|mkdir|rename)"
    r"|File\.(?:write|open)\s*\("
    r"|FileUtils\."
    r"|open\s*\([^)]*>\s*"            # Perl open with >
    r")"
)


def is_allow_external_target(path_str: str) -> bool:
    try:
        p = Path(path_str.strip().strip("'\""))
        if not p.is_absolute():
            p = (VAULT / p).resolve()
        else:
            p = p.resolve()
        return p == (VAULT / ".agents" / "allow-external").resolve()
    except Exception:
        return False


def is_foreign_sessions_target(path_str: str) -> bool:
    try:
        p = Path(path_str.strip().strip("'\""))
        if not p.is_absolute():
            p = (VAULT / p).resolve()
        else:
            p = p.resolve()
        p_str = str(p)
        vault_sessions = str((VAULT / ".agents" / "sessions").resolve())
        if "/.agents/sessions" in p_str and not p_str.startswith(vault_sessions):
            return True
        return False
    except Exception:
        return False


def allowed_prefixes() -> list[str]:
    prefixes = [str(VAULT), memory_mirror_prefix()]
    allow_file = VAULT / ".agents" / "allow-external"
    if allow_file.exists():
        try:
            for line in allow_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("~"):
                    prefixes.append(str(Path(line).expanduser()))
                elif Path(line).is_absolute():
                    prefixes.append(line)
                else:
                    prefixes.append(str((VAULT / line).resolve()))
        except Exception as err:
            sys.stderr.write(f"[vault-boundary-guard] WARN: failed reading {allow_file}: {err}\n")
    extra = os.environ.get("VAULT_ALLOW_EXTERNAL", "")
    prefixes.extend(p for p in (part.strip() for part in extra.split(os.pathsep)) if Path(p).is_absolute())
    return prefixes


def is_external(token: str, prefixes: list[str], cwd: Path | None = None) -> bool:
    if cwd is None:
        cwd = VAULT
    candidate = token.strip().strip("'\"")
    if len(candidate) > 2 and (candidate.endswith(",") or candidate.endswith(";")):
        candidate = candidate.rstrip(",;")
    if candidate.startswith("~"):
        candidate = str(Path(candidate).expanduser())
    elif not Path(candidate).is_absolute():
        try:
            candidate = str((cwd / candidate).resolve())
        except Exception as err:
            sys.stderr.write(f"[vault-boundary-guard] WARN: failed resolving candidate path '{candidate}': {err}\n")
            return False
    else:
        try:
            candidate = str(Path(candidate).resolve())
        except Exception:
            pass
    if not candidate.startswith(USER_ROOT + os.sep):
        return False
    if any(candidate.startswith(p) for p in ALWAYS_ALLOWED):
        return False
    return not any(
        candidate == p or candidate.startswith(p.rstrip(os.sep) + os.sep) for p in prefixes
    )


def git_subcommand(tokens: list[str]) -> str:
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in GIT_VALUE_FLAGS:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token
    return ""


def bash_reads_only(command: str) -> bool:
    if SUBSTITUTION.search(command):
        return False
    prefixes = allowed_prefixes()
    for target in REDIRECT_TARGET.findall(command):
        if target.startswith("&"):
            continue  # file descriptor dupe
        if is_external(target, prefixes):
            return False
    for segment in SEGMENT_SPLIT.split(command):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            return False
        tokens = unwrap_command_tokens(tokens)
        if not tokens:
            continue
        if tokens[0] in CONTROL_WORD_LISTS:
            continue
        head = os.path.basename(tokens[0])
        if head == "git":
            if git_subcommand(tokens) not in GIT_READ_SUBCOMMANDS:
                return False
        elif head == "find":
            if any(token in FIND_WRITE_ACTIONS for token in tokens[1:]):
                return False
        elif head in COPY_HEADS:
            if len(tokens) < 2 or is_external(tokens[-1], prefixes):
                return False
        elif head not in READ_ONLY_HEADS:
            return False
    return True


def offending_paths(payload: dict) -> list[str]:
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return []
    
    prefixes = allowed_prefixes()
    offenders: list[str] = []

    for key in ("file_path", "path", "target_file", "TargetFile", "destination", "notebook_path", "target"):
        val = tool_input.get(key)
        if isinstance(val, str) and val.strip():
            candidate = val.strip().rstrip(".,'\"")
            if is_external(candidate, prefixes) and candidate not in offenders:
                offenders.append(candidate)

    if str(payload.get("tool_name") or "").lower() == "apply_patch":
        for p_cand in extract_patch_paths(tool_input):
            candidate = p_cand.strip().rstrip(".,'\"")
            if is_external(candidate, prefixes):
                try:
                    resolved_c = str((VAULT / candidate).resolve()) if not Path(candidate).expanduser().is_absolute() else candidate
                except Exception:
                    resolved_c = candidate
                if resolved_c not in offenders:
                    offenders.append(resolved_c)

    haystack: list[str] = []
    for key in ("command", "file_path", "path", "notebook_path", "pattern", "TargetFile", "target_file"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            haystack.append(value)
    if not haystack:
        return offenders

    expanded_haystack: list[str] = []
    for text in haystack:
        expanded_haystack.append(text)
        expanded = (
            text.replace("${HOME}", str(Path.home()))
            .replace("$HOME", str(Path.home()))
            .replace("~", str(Path.home()))
            .replace("${PWD}", str(VAULT))
            .replace("$PWD", str(VAULT))
            .replace("$(pwd)", str(VAULT))
            .replace("`pwd`", str(VAULT))
        )
        if expanded != text:
            expanded_haystack.append(expanded)

    for text in expanded_haystack:
        for match in PATH_TOKEN.findall(text):
            candidate = match.rstrip(".,'\"")
            if is_external(candidate, prefixes) and candidate not in offenders:
                offenders.append(candidate)
        for match in TILDE_TOKEN.findall(text):
            candidate = match.rstrip(".,'\"")
            if is_external(candidate, prefixes) and candidate not in offenders:
                offenders.append(candidate)
        # Traversal checks for non-command targets (command strings are CWD-evaluated in main)
        if "command" not in tool_input or text != tool_input.get("command"):
            for match in re.findall(r"(?:[^\s'\"`,;:()\[\]{}<>|&]*/)*\.\.(?:/[^\s'\"`,;:()\[\]{}<>|&]*)*", text):
                candidate = match.rstrip(".,'\"")
                if is_external(candidate, prefixes):
                    try:
                        resolved = str((VAULT / candidate).resolve())
                    except Exception:
                        resolved = candidate
                    if resolved not in offenders:
                        offenders.append(resolved)
    return offenders


def _is_sensitive_external_path(path_str: str) -> bool:
    raw = path_str.strip().strip("'\"")
    if not raw:
        return False
    expanded = Path(raw).expanduser()
    lexical = Path(os.path.abspath(expanded if expanded.is_absolute() else VAULT / expanded))
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


def _parse_cli_mode() -> tuple[bool, str]:
    interactive = "--interactive-approval" in sys.argv[1:]
    runtime = ""
    for arg in sys.argv[1:]:
        if arg.startswith("--runtime="):
            runtime = arg.split("=", 1)[1].strip().lower()
    return interactive, runtime


def _handle_external_write(
    targets: list[str],
    payload: dict,
    interactive: bool,
    runtime: str,
    deny_message: str,
) -> int:
    """Apply hard-deny or interactive-approval policy for external write targets."""
    if not interactive or not targets or any(_is_sensitive_external_path(t) for t in targets):
        sys.stderr.write(deny_message)
        return 2

    is_claude = (
        runtime == "claude-code"
        or (
            not runtime
            and not os.environ.get("CODEX_SANDBOX")
            and not os.environ.get("CODEX_THREAD_ID")
            and not any(os.environ.get(m) for m in ("DSH_SESSION_ID", "DSH_HOME", "DSH_SESSION_JSONL"))
            and (bool(os.environ.get("CLAUDE_PROJECT_DIR")) or payload.get("hook_event_name") == "PreToolUse")
        )
    )
    if is_claude:
        target_label = ", ".join(targets[:3])
        out = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": (
                    f"Agen ingin menulis ke folder di luar vault ({target_label}). "
                    "Klik Allow jika Anda mengizinkan tindakan ini."
                ),
            }
        }
        sys.stdout.write(json.dumps(out) + "\n")
        return 0
    return 0


def main() -> int:
    interactive, runtime = _parse_cli_mode()
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as err:
        sys.stderr.write(f"[vault-boundary-guard] WARN: malformed JSON payload ({err}); passing through\n")
        return 0  # never block on a parse failure
    if not isinstance(payload, dict):
        sys.stderr.write("[vault-boundary-guard] WARN: payload is not a JSON object; passing through\n")
        return 0

    tool_raw = payload.get("tool_name")
    raw_input = payload.get("tool_input")
    if not tool_raw and not isinstance(raw_input, dict):
        return 0

    tool = str(tool_raw or "").lower()
    if tool in READ_ONLY_TOOLS:
        return 0

    tool_input = raw_input if isinstance(raw_input, dict) else {}

    # Anti-privilege escalation on tool write/edit/apply_patch
    escalation_candidates = [
        val.strip()
        for key in ("file_path", "path", "target_file", "TargetFile", "destination", "notebook_path", "target")
        for val in (tool_input.get(key),)
        if isinstance(val, str) and val.strip()
    ]
    if tool == "apply_patch":
        escalation_candidates.extend(extract_patch_paths(tool_input))
    for val in escalation_candidates:
        if is_allow_external_target(val):
            sys.stderr.write(
                "Blocked: agent modification to .agents/allow-external is strictly prohibited.\n"
                "This file controls security boundaries and may only be edited directly by the human owner.\n"
            )
            return 2
        if is_foreign_sessions_target(val):
            sys.stderr.write("Blocked: writing to foreign .agents/sessions/ is strictly prohibited.\n")
            return 2

    if tool in BASH_TOOLS:
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        if isinstance(command, str) and command:
            # Check for inline interpreter external write markers
            for marker in INLINE_EXTERNAL_WRITE_MARKERS:
                if marker in command:
                    sys.stderr.write(
                        "Blocked: inline script attempts to resolve or write to user home outside vault.\n"
                        f"  {marker}\n"
                    )
                    return 2

            # Check mutating command tokens with stateful CWD tracking
            current_dir = VAULT
            prefixes = allowed_prefixes()
            deferred_external: list[str] = []
            for segment in SEGMENT_SPLIT.split(command):
                # Evaluate shell redirections within this segment against current_dir
                for target in REDIRECT_TARGET.findall(segment):
                    if target.startswith("&"):
                        continue
                    clean_target = target.strip("'\"")
                    target_exp = (
                        clean_target.replace("${HOME}", str(Path.home()))
                        .replace("$HOME", str(Path.home()))
                        .replace("~", str(Path.home()))
                        .replace("${PWD}", str(current_dir))
                        .replace("$PWD", str(current_dir))
                        .replace("$(pwd)", str(current_dir))
                        .replace("`pwd`", str(current_dir))
                    )
                    # If unresolved variable or dynamic substitution remains, fail closed
                    if "$" in target_exp or "`" in target_exp:
                        sys.stderr.write(
                            "Blocked: shell redirection contains dynamic variable or substitution which fails closed.\n"
                            f"  {target}\n"
                        )
                        return 2
                    if is_allow_external_target(target_exp):
                        sys.stderr.write(
                            "Blocked: agent modification to .agents/allow-external is strictly prohibited.\n"
                        )
                        return 2
                    if is_foreign_sessions_target(target_exp):
                        sys.stderr.write("Blocked: writing to foreign .agents/sessions/ is strictly prohibited.\n")
                        return 2
                    if is_external(target_exp, prefixes, cwd=current_dir):
                        if not interactive or _is_sensitive_external_path(target_exp):
                            sys.stderr.write(
                                "Blocked: shell redirection WRITES to a user path outside the vault.\n"
                                f"  {target_exp}\n"
                            )
                            return 2
                        if target_exp not in deferred_external:
                            deferred_external.append(target_exp)

                try:
                    tokens = shlex.split(segment)
                except ValueError:
                    continue
                tokens = unwrap_command_tokens(tokens)
                if not tokens:
                    continue
                head = os.path.basename(tokens[0])
                if head in ("cd", "pushd"):
                    args = [t for t in tokens[1:] if not t.startswith("-") and t != "--"]
                    dest = args[0] if args else "~"
                    dest_exp = (
                        dest.replace("${HOME}", str(Path.home()))
                        .replace("$HOME", str(Path.home()))
                        .replace("~", str(Path.home()))
                        .replace("${PWD}", str(current_dir))
                        .replace("$PWD", str(current_dir))
                        .replace("$(pwd)", str(current_dir))
                        .replace("`pwd`", str(current_dir))
                    )
                    if Path(dest_exp).is_absolute():
                        resolved_dest = Path(dest_exp).resolve()
                    else:
                        resolved_dest = (current_dir / dest_exp).resolve()
                    if is_external(str(resolved_dest), prefixes, cwd=current_dir):
                        if not interactive or _is_sensitive_external_path(str(resolved_dest)):
                            sys.stderr.write(
                                "Blocked: this tool call changes directory outside the vault.\n"
                                f"  {dest_exp}\n"
                            )
                            return 2
                        if str(resolved_dest) not in deferred_external:
                            deferred_external.append(str(resolved_dest))
                    current_dir = resolved_dest
                elif head in COPY_HEADS:
                    # For cp, install, rsync: source files may reside outside vault (reads allowed);
                    # only the destination target (last positional argument) writes to disk.
                    dest_candidates = [t for t in tokens[1:] if t != "--" and not t.startswith("-")]
                    if dest_candidates:
                        dest_tok = dest_candidates[-1]
                        expanded_tok = (
                            dest_tok.replace("${HOME}", str(Path.home()))
                            .replace("$HOME", str(Path.home()))
                            .replace("~", str(Path.home()))
                            .replace("${PWD}", str(current_dir))
                            .replace("$PWD", str(current_dir))
                            .replace("$(pwd)", str(current_dir))
                            .replace("`pwd`", str(current_dir))
                        )
                        if is_allow_external_target(expanded_tok):
                            sys.stderr.write(
                                "Blocked: agent modification to .agents/allow-external is strictly prohibited.\n"
                            )
                            return 2
                        if is_foreign_sessions_target(expanded_tok):
                            sys.stderr.write("Blocked: writing to foreign .agents/sessions/ is strictly prohibited.\n")
                            return 2
                        if is_external(expanded_tok, prefixes, cwd=current_dir):
                            if not interactive or _is_sensitive_external_path(expanded_tok):
                                sys.stderr.write(
                                    "Blocked: this tool call WRITES to a user path outside the vault.\n"
                                    f"  {expanded_tok}\n"
                                )
                                return 2
                            if expanded_tok not in deferred_external:
                                deferred_external.append(expanded_tok)
                elif head in MUTATING_HEADS:
                    for tok in tokens[1:]:
                        if tok == "--" or tok.startswith("-"):
                            continue
                        expanded_tok = (
                            tok.replace("${HOME}", str(Path.home()))
                            .replace("$HOME", str(Path.home()))
                            .replace("~", str(Path.home()))
                            .replace("${PWD}", str(current_dir))
                            .replace("$PWD", str(current_dir))
                            .replace("$(pwd)", str(current_dir))
                            .replace("`pwd`", str(current_dir))
                        )
                        if is_allow_external_target(expanded_tok):
                            sys.stderr.write(
                                "Blocked: agent modification to .agents/allow-external is strictly prohibited.\n"
                            )
                            return 2
                        if is_foreign_sessions_target(expanded_tok):
                            sys.stderr.write("Blocked: writing to foreign .agents/sessions/ is strictly prohibited.\n")
                            return 2
                        if is_external(expanded_tok, prefixes, cwd=current_dir):
                            if not interactive or _is_sensitive_external_path(expanded_tok):
                                sys.stderr.write(
                                    "Blocked: this tool call WRITES to a user path outside the vault.\n"
                                    f"  {expanded_tok}\n"
                                )
                                return 2
                            if expanded_tok not in deferred_external:
                                deferred_external.append(expanded_tok)
                elif head in INTERPRETERS and any(f in tokens for f in INTERPRETER_EVAL_FLAGS):
                    code_str = " ".join(tokens)
                    if any(marker in code_str for marker in INLINE_EXTERNAL_WRITE_MARKERS):
                        sys.stderr.write(
                            "Blocked: inline script attempts to resolve or write to user home outside vault.\n"
                        )
                        return 2
                    if INLINE_MUTATION_PATTERNS.search(code_str):
                        sys.stderr.write(
                            "Blocked: inline script file-writing and mutating calls are blocked by vault boundary guard.\n"
                        )
                        return 2

            if not deferred_external and bash_reads_only(command):
                return 0

            # Check absolute or tilde offender paths in command
            offenders = offending_paths(payload)
            for item in deferred_external:
                if item not in offenders:
                    offenders.append(item)
            if offenders:
                listed = "\n".join(f"  {p}" for p in offenders[:5])
                return _handle_external_write(
                    offenders,
                    payload,
                    interactive,
                    runtime,
                    "Blocked: this tool call WRITES to a user path outside the vault.\n"
                    f"{listed}\n",
                )
            return 0

    if tool in KNOWN_WRITE_TOOLS:
        target_path = None
        for key in ("file_path", "path", "target_file", "TargetFile", "destination", "notebook_path", "target"):
            val = tool_input.get(key)
            if isinstance(val, str) and val.strip():
                target_path = val.strip()
                break
        if not target_path and tool == "apply_patch":
            extracted = extract_patch_paths(tool_input)
            if extracted:
                target_path = extracted[0]
        if not target_path:
            sys.stderr.write(
                f"Blocked: write tool '{payload.get('tool_name')}' called without valid target path.\n"
            )
            return 2
        offenders = offending_paths(payload)
        if offenders:
            listed = "\n".join(f"  {p}" for p in offenders[:5])
            return _handle_external_write(
                offenders,
                payload,
                interactive,
                runtime,
                "Blocked: this tool call WRITES to a user path outside the vault.\n"
                f"{listed}\n",
            )
        return 0

    # Fail closed for any unrecognized tool
    sys.stderr.write(
        f"Blocked: unrecognized tool '{payload.get('tool_name')}' fails closed by default.\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
