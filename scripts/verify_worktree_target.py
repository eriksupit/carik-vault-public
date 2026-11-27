#!/usr/bin/env python3
"""Worktree Target Binding Guard.

Enforces absolute worktree root binding, path containment, and git toplevel
congruence before any mutation command executes. Enforces WORKFLOW.md's
repository-boundary rule: repo_root must equal project_root before a commit,
remote configuration, or push.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


class WorktreeBindingError(RuntimeError):
    """Raised when an operation violates worktree target binding."""


def resolve_git_toplevel(path: Path | str) -> Path | None:
    """Resolve the git toplevel directory for a given path."""
    target = Path(path).resolve()
    if not target.exists():
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return Path(proc.stdout.strip()).resolve()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def verify_worktree_binding(
    expected_worktree: Path | str,
    target_path: Path | str | None = None,
    cwd: Path | str | None = None,
    require_git_congruence: bool = True,
) -> bool:
    """Verify that execution context and mutation target strictly reside within the expected worktree.

    Invariants enforced:
    1. expected_worktree exists and is a valid directory.
    2. If require_git_congruence is True:
       git rev-parse --show-toplevel inside expected_worktree must resolve identically
       to expected_worktree.resolve().
    3. If cwd is provided:
       cwd.resolve() must reside within or equal expected_worktree.resolve().
    4. If target_path is provided:
       target_path.resolve() must reside within or equal expected_worktree.resolve().
       Path traversal and symlink escapes outside the boundary raise WorktreeBindingError.
    """
    expected_root = Path(expected_worktree).resolve()
    if not expected_root.is_dir():
        raise WorktreeBindingError(
            f"Expected worktree directory does not exist or is not a directory: {expected_root}"
        )

    if require_git_congruence:
        git_toplevel = resolve_git_toplevel(expected_root)
        if git_toplevel is None:
            raise WorktreeBindingError(
                f"Expected worktree is not a valid git repository or worktree: {expected_root}"
            )
        if git_toplevel != expected_root:
            raise WorktreeBindingError(
                f"Git toplevel mismatch: git rev-parse returned {git_toplevel}, expected {expected_root}"
            )

    if cwd is not None:
        resolved_cwd = Path(cwd).resolve()
        try:
            resolved_cwd.relative_to(expected_root)
        except ValueError:
            raise WorktreeBindingError(
                f"Current working directory {resolved_cwd} escapes expected worktree {expected_root}"
            )

    if target_path is not None:
        resolved_target = Path(target_path).resolve()
        try:
            resolved_target.relative_to(expected_root)
        except ValueError:
            raise WorktreeBindingError(
                f"Target path {resolved_target} escapes expected worktree {expected_root}"
            )

    return True


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for worktree target binding verification and execution wrapper."""
    parser = argparse.ArgumentParser(
        description="Verify worktree target binding before mutation.",
        prog="verify_worktree_target.py",
    )
    parser.add_argument(
        "--worktree",
        required=True,
        type=Path,
        help="Path to expected worktree root.",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Optional mutation target file or directory to verify.",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=None,
        help="Optional working directory to verify against worktree root.",
    )
    parser.add_argument(
        "--no-git-check",
        action="store_true",
        help="Disable git rev-parse toplevel congruence check.",
    )
    parser.add_argument(
        "--run",
        nargs=argparse.REMAINDER,
        help="Command and arguments to execute if worktree binding verification passes.",
    )

    args = parser.parse_args(argv)

    try:
        verify_worktree_binding(
            expected_worktree=args.worktree,
            target_path=args.path,
            cwd=args.cwd,
            require_git_congruence=not args.no_git_check,
        )
    except WorktreeBindingError as err:
        sys.stderr.write(f"ERROR: Worktree binding violation: {err}\n")
        return 2

    if args.run:
        # Strip leading '--' if passed by remainder
        cmd = args.run
        if cmd and cmd[0] == "--":
            cmd = cmd[1:]
        if not cmd:
            sys.stderr.write("ERROR: Empty command passed to --run\n")
            return 2

        expected_root = args.worktree.resolve()
        res = subprocess.run(cmd, cwd=expected_root)
        return res.returncode

    sys.stdout.write(f"OK: worktree binding verified for {args.worktree.resolve()}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
