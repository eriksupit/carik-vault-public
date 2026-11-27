#!/usr/bin/env python3
"""PreToolUse guard: block broad `git add` so staging stays explicit-path only.

Reads the Claude Code hook JSON from stdin. If the Bash command stages the whole
tree (`git add -A`, `--all`, `-u`, `--update`, a combined short flag containing A/u,
or a whole-tree or wildcard pathspec such as `.`, `:/`, or `*`, before or after `--`),
force-pushes, or stages session files together with task files, exit 2 to block and
explain on stderr. Explicit-path staging (`git add -- path`, `git add path/file`) passes.

The git head is matched by basename, so `/usr/bin/git` and `git.exe` are covered.
Tokenizing uses POSIX `shlex`; native Windows quoting is unverified until P10.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys

SEGMENT_SPLIT = re.compile(r"&&|\|\||;|\||\n")
GLOBAL_VALUE_FLAGS = ("-C", "-c", "--git-dir", "--work-tree")
WHOLE_TREE_PATHSPECS = {".", "./", ":", ":/"}


def git_args(command: str, subcommand: str):
    """Yield the arguments of every `git <subcommand>` simple command in `command`."""
    for segment in SEGMENT_SPLIT.split(command):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            tokens = segment.split()
        head = next((i for i, t in enumerate(tokens) if os.path.basename(t) in ("git", "git.exe")), None)
        if head is None:
            continue
        rest = tokens[head + 1 :]
        i = 0
        while i < len(rest) and rest[i].startswith("-"):
            i += 2 if rest[i] in GLOBAL_VALUE_FLAGS else 1
        if i < len(rest) and rest[i] == subcommand:
            yield rest[i + 1 :]


def split_pathspecs(args: list[str]) -> tuple[list[str], list[str]]:
    """Separate option flags from pathspecs; everything after `--` is a pathspec."""
    flags: list[str] = []
    paths: list[str] = []
    after_dash_dash = False
    for a in args:
        if a == "--" and not after_dash_dash:
            after_dash_dash = True
        elif not after_dash_dash and a.startswith("-"):
            flags.append(a)
        else:
            paths.append(a)
    return flags, paths


def forced_push_check(command: str) -> str | None:
    for args in git_args(command, "push"):
        for a in args:
            if a in ("-f", "--force") or a.startswith("--force-with-lease") or a.startswith("+"):
                return a
            if re.fullmatch(r"-[A-Za-z]+", a) and "f" in a[1:]:
                return a
    return None


def session_path_mixed_check(command: str) -> bool:
    for args in git_args(command, "add"):
        _, paths = split_pathspecs(args)
        session = [p.startswith(".agents/sessions") or ".agents/sessions/" in p for p in paths]
        if any(session) and not all(session):
            return True
    return False


def broad_git_add(command: str) -> str | None:
    for args in git_args(command, "add"):
        flags, paths = split_pathspecs(args)
        for a in flags:
            if a in ("-A", "--all", "-u", "--update"):
                return a
            if re.fullmatch(r"-[A-Za-z]+", a) and ("A" in a[1:] or "u" in a[1:]):
                return a
        for p in paths:
            if p in WHOLE_TREE_PATHSPECS or "*" in p:
                return p
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # never block on a parse failure
    command = (payload.get("tool_input") or {}).get("command", "")
    if not isinstance(command, str) or not command:
        return 0

    fp_flag = forced_push_check(command)
    if fp_flag:
        sys.stderr.write(
            f"Blocked: forced push is strictly prohibited (`{fp_flag}` violates team coordination and history immutability rules).\n"
        )
        return 2

    if session_path_mixed_check(command):
        sys.stderr.write(
            "Blocked: session continuity files cannot be staged together with project task files in the same commit.\n"
        )
        return 2

    flag = broad_git_add(command)
    if flag:
        sys.stderr.write(
            f"Blocked: broad staging `{flag}` violates the isolated-commit rule.\n"
            "Stage explicit task paths only: `git add -- <path>...` "
            "(see WORKFLOW.md, Isolated Git Commit and GitHub Push).\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
