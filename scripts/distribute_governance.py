#!/usr/bin/env python3
"""Batch Governance Distribution Orchestrator for Derived Vaults.

Safely synchronizes root harness governance updates across derived vaults in batch,
enforcing Tri-Zone separation, 3-way baseline comparisons, crash-resilient journaled staging,
symlink-safe Sovereign protection, and test fixture isolation.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime
import difflib
import hashlib
import json
import os
import re
import shutil
import sys
import uuid
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class TargetVault:
    project: str
    profile: str
    path: Path
    raw_date: str = ""
class SovereignViolationError(PermissionError):
    """Raised when an operation attempts to write to Sovereign Canon or outside vault root."""
    pass

class SplicingBlockedError(ValueError):
    """Raised when managed block markers are malformed, duplicate, inverted, or corrupt."""
    pass


MANAGED_BEGIN = "<!-- BEGIN HARNESS MANAGED: CORE_GOVERNANCE -->"
MANAGED_END = "<!-- END HARNESS MANAGED: CORE_GOVERNANCE -->"
CODE_FENCE_PATTERN = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})")


def splice_managed_block(target_text: str, upstream_body: str) -> tuple[str, str]:
    """Splice upstream governance rules into target document inside managed markers.

    Returns (status, spliced_text) where status is 'SPLICED' or 'UNMANAGED'.
    Raises SplicingBlockedError on malformed, duplicate, or inverted markers.
    Preserves unmanaged bytes bit-for-bit without unwanted normalization.
    """
    lines = target_text.splitlines(keepends=True)
    in_fence = False
    fence_char = ""
    fence_len = 0

    active_begins: list[int] = []
    active_ends: list[int] = []

    char_offset = 0
    line_offsets: list[int] = []
    for line in lines:
        line_offsets.append(char_offset)
        char_offset += len(line)

    for idx, line in enumerate(lines):
        m_fence = CODE_FENCE_PATTERN.match(line)
        if m_fence:
            token = m_fence.group(1)
            ch = token[0]
            length = len(token)
            if not in_fence:
                in_fence = True
                fence_char = ch
                fence_len = length
            else:
                if ch == fence_char and length >= fence_len:
                    in_fence = False
                    fence_char = ""
                    fence_len = 0
            continue

        if in_fence:
            continue

        if MANAGED_BEGIN in line:
            active_begins.append(idx)
        if MANAGED_END in line:
            active_ends.append(idx)

    if not active_begins and not active_ends:
        return "UNMANAGED", target_text

    if len(active_begins) != 1 or len(active_ends) != 1:
        raise SplicingBlockedError(
            f"Malformed managed markers: found {len(active_begins)} BEGIN and "
            f"{len(active_ends)} END markers outside code fences."
        )

    begin_line_idx = active_begins[0]
    end_line_idx = active_ends[0]

    if begin_line_idx >= end_line_idx:
        raise SplicingBlockedError(
            f"Malformed managed markers: END marker at line {end_line_idx + 1} appears "
            f"before or at BEGIN marker at line {begin_line_idx + 1}."
        )

    # Calculate byte slice:
    # Preceding: everything up to and including the line containing BEGIN
    preceding_lines = lines[:begin_line_idx + 1]
    preceding = "".join(preceding_lines)
    # If preceding does not end with newline, add one
    if preceding and not preceding.endswith("\n"):
        preceding += "\n"

    # Following: everything from the line containing END to the end of file
    following_lines = lines[end_line_idx:]
    following = "".join(following_lines)

    # Format upstream body
    body_str = upstream_body.rstrip("\n") + "\n"

    spliced = preceding + body_str + following
    return "SPLICED", spliced


SOVEREIGN_PATTERNS = (
    "work",
    "raw-kb",
    "SCOPE.md",
    ".agents/sessions",
    ".agents/Context.md",
    ".agents/Lessons.md",
    ".agents/Memory.md",
    ".agents/memory",
    ".agents/approvals",
    ".agents/telemetry",
)

ALLOWED_EXACT_FILES = {
    "CARIK-CHARTER.md",
    "MULAI-DARI-SINI.md",
    "AGENTS.md",
    "WORKFLOW.md",
    "CLAUDE.md",
    ".agents/hooks.json",
    ".agents/policy.json",
    ".codex/hooks.json",
    ".claude/settings.json",
    ".agents/.dist-journal.json",
    ".agents/harness-lineage.json",
}

ALLOWED_DIRECTORY_PREFIXES = (
    ".agents/hooks/",
    "scripts/",
    "writing-style/",
    ".agents/.dist-staging",
    ".agents/.dist-bak",
)


def resolve_destination(target_root: Path, dest_path: Path) -> Path:
    """Resolve destination canonical path safely even if file does not exist yet."""
    if dest_path.is_symlink():
        return dest_path.resolve()
    if dest_path.exists():
        return dest_path.resolve()
    # Traverse up to find closest existing parent
    curr = dest_path
    parts_to_append: list[str] = []
    while not curr.exists() and curr != curr.parent:
        parts_to_append.append(curr.name)
        curr = curr.parent
    resolved_parent = curr.resolve()
    for part in reversed(parts_to_append):
        resolved_parent = resolved_parent / part
    return resolved_parent


def assert_not_sovereign(target_root: Path, destination_path: Path) -> None:
    """Verify destination path is inside target vault and not Sovereign Canon or unregistered."""
    try:
        canonical_vault = target_root.resolve()
    except (OSError, RuntimeError) as e:
        raise SovereignViolationError(f"Cannot resolve vault root '{target_root}': {e}") from e

    try:
        canonical_dest = resolve_destination(target_root, destination_path)
    except (OSError, RuntimeError) as e:
        raise SovereignViolationError(f"Cannot resolve destination path '{destination_path}': {e}") from e

    # 1. Traversal check: must be relative to canonical vault root
    try:
        rel_path = canonical_dest.relative_to(canonical_vault).as_posix()
    except ValueError:
        raise SovereignViolationError(
            f"Security Violation: Path traversal outside vault root detected. "
            f"Destination '{canonical_dest}' is not inside vault '{canonical_vault}'"
        )

    # 2. Check Sovereign blacklist
    for sov in SOVEREIGN_PATTERNS:
        if rel_path == sov or rel_path.startswith(sov.rstrip("/") + "/"):
            raise SovereignViolationError(
                f"Security Violation: Attempted write to Sovereign Canon '{rel_path}' in vault '{canonical_vault}'"
            )

    # 3. Default-deny: must match allowed exact files or allowed directory prefixes
    is_allowed = (
        rel_path in ALLOWED_EXACT_FILES
        or any(rel_path.startswith(prefix) for prefix in ALLOWED_DIRECTORY_PREFIXES)
    )
    if not is_allowed:
        raise SovereignViolationError(
            f"Security Violation (Default-Deny): Path '{rel_path}' is not an authorized governance target."
        )

def evaluate_3way(u: str | None, t: str | None, b: str | None) -> tuple[str, str]:
    """Evaluate 3-way digest state machine across Upstream (U), Target (T), and Baseline (B).

    Returns (state_label, required_action).
    Mathematically proven mutually exclusive and exhaustive across all 64 permutations.
    """
    # 1. no-op: target already identical to upstream
    if u == t:
        return "no-op", "Keep target unmodified"
    # 2. safe_upgrade: target unmodified from baseline, upstream has update
    if u is not None and b is not None and t == b and u != t:
        return "safe_upgrade", "Stage upstream replacement"
    # 3. local_conflict (diverged): upstream and target both modified from baseline
    if u is not None and t is not None and b is not None and u != t and t != b:
        return "local_conflict", "Preserve modified target, log conflict warning, do not overwrite"
    # 4. local_conflict (delete conflict): deleted upstream, but target modified from baseline
    if u is None and t is not None and b is not None and t != b:
        return "local_conflict", "Preserve modified target, log conflict warning, do not overwrite"
    # 5. unknown_baseline: target exists, differs from upstream, but no baseline record exists
    if b is None and t is not None and u != t:
        return "unknown_baseline", "Preserve target, flag for manual review, do not overwrite"
    # 6. new: new file in upstream, never seen in target or baseline
    if u is not None and t is None and b is None:
        return "new", "Stage upstream creation"
    # 7. missing: file in upstream and baseline, but deleted/missing in target (do not recreate blindly)
    if u is not None and t is None and b is not None:
        return "missing", "Flag missing target, do not recreate silently"
    # 8. deleted: file deleted upstream and target unmodified from baseline
    if u is None and t is not None and t == b:
        return "deleted", "Stage target deletion"
    return "local_conflict", "Unclassified divergence; preserve target"


def merge_json_config(source_content: str, target_content: str, surface_name: str) -> str:
    """Merge configuration surfaces while strictly preserving child vault customizations."""
    try:
        source_dict = json.loads(source_content)
    except Exception:
        return target_content
    try:
        target_dict = json.loads(target_content)
    except Exception:
        return source_content

    if not isinstance(source_dict, dict) or not isinstance(target_dict, dict):
        return target_content

    merged = dict(source_dict)

    if surface_name in ("policy.json", ".agents/policy.json"):
        # Child overrides language and evidence_bearing
        if "prose_language" in target_dict:
            merged["prose_language"] = target_dict["prose_language"]
        if "evidence_bearing" in target_dict:
            merged["evidence_bearing"] = target_dict["evidence_bearing"]
        # Preserve custom child keys
        for k, v in target_dict.items():
            if k not in merged:
                merged[k] = v

    elif "hooks" in surface_name or "settings" in surface_name:
        for top_key, top_val in target_dict.items():
            if top_key not in merged:
                merged[top_key] = top_val
            elif isinstance(top_val, dict) and isinstance(merged.get(top_key), dict):
                sec_merged = dict(merged[top_key])
                for event_name, event_list in top_val.items():
                    if event_name not in sec_merged:
                        sec_merged[event_name] = event_list
                    elif isinstance(event_list, list) and isinstance(sec_merged.get(event_name), list):
                        existing_cmds = set()
                        for entry in sec_merged[event_name]:
                            if isinstance(entry, dict) and "hooks" in entry:
                                for h in entry["hooks"]:
                                    if isinstance(h, dict) and "command" in h:
                                        existing_cmds.add(h["command"])
                        for tgt_entry in event_list:
                            if isinstance(tgt_entry, dict) and "hooks" in tgt_entry:
                                unique_hooks = [
                                    h for h in tgt_entry["hooks"]
                                    if isinstance(h, dict) and h.get("command") not in existing_cmds
                                ]
                                if unique_hooks:
                                    sec_merged[event_name].append({
                                        **tgt_entry,
                                        "hooks": unique_hooks,
                                    })
                                    for h in unique_hooks:
                                        existing_cmds.add(h.get("command"))
                            else:
                                if tgt_entry not in sec_merged[event_name]:
                                    sec_merged[event_name].append(tgt_entry)
                merged[top_key] = sec_merged
    else:
        for k, v in target_dict.items():
            if k not in merged:
                merged[k] = v

    return json.dumps(merged, indent=2) + "\n"



REGISTRY_ROW_PATTERN = re.compile(
    r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$"
)

REQUIRED_OBSIDIAN_FILES = (
    Path(".obsidian") / "app.json",
    Path(".obsidian") / "appearance.json",
    Path(".obsidian") / "core-plugins.json",
)


def validate_target(target_path: Path, harness_root: Path) -> tuple[bool, str | None]:
    """Validate that target directory is a valid, non-recursive Obsidian vault."""
    try:
        resolved_target = target_path.resolve()
        resolved_harness = harness_root.resolve()
    except (OSError, RuntimeError) as e:
        return False, f"Failed to resolve path '{target_path}': {e}"

    if not resolved_target.is_dir():
        return False, f"Target directory does not exist: '{resolved_target}'"

    # Reject recursion: target is harness, or target is parent/ancestor of harness, or target is inside harness
    if resolved_target == resolved_harness:
        return False, f"Target rejects self-recursion: target '{resolved_target}' is the harness root"
    if resolved_harness.is_relative_to(resolved_target):
        return False, f"Target rejects ancestor recursion: target '{resolved_target}' is ancestor of harness"
    if resolved_target.is_relative_to(resolved_harness):
        return False, f"Target rejects subdirectory recursion: target '{resolved_target}' is inside harness"

    # Validate Obsidian identity files
    for req in REQUIRED_OBSIDIAN_FILES:
        obs_file = resolved_target / req
        if not obs_file.is_file():
            return False, f"Target '{resolved_target}' is missing required identity file: '{req}'"
        try:
            content = obs_file.read_text(encoding="utf-8")
            json.loads(content)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return False, f"Target '{resolved_target}' has invalid JSON in identity file '{req}': {e}"

    return True, None


def parse_registry(harness_root: Path) -> list[tuple[str, str, str, Path]]:
    """Parse Markdown registry table rows from docs/vault-registry.md."""
    reg_file = harness_root / "docs" / "vault-registry.md"
    if not reg_file.is_file():
        return []

    results: list[tuple[str, str, str, Path]] = []
    lines = reg_file.read_text(encoding="utf-8").splitlines()
    table_started = False

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        match = REGISTRY_ROW_PATTERN.match(stripped)
        if not match:
            continue
        col1, col2, col3, col4 = (c.strip() for c in match.groups())
        if col1.lower() == "date" or col2.lower() == "project":
            table_started = True
            continue
        if set(col1) == {"-"} or set(col2) == {"-"}:
            continue
        if table_started:
            date_val, project, profile, raw_path = col1, col2, col3, col4
            if raw_path:
                target_path = Path(raw_path)
                results.append((date_val, project, profile, target_path))

    return results


def discover_targets(harness_root: Path) -> tuple[list[TargetVault], list[str]]:
    """Discover, deduplicate, and validate all target vaults from docs/vault-registry.md."""
    raw_rows = parse_registry(harness_root)
    discovered: list[TargetVault] = []
    errors: list[str] = []
    seen_canonical_paths: set[Path] = set()
    project_names: dict[str, Path] = {}

    for date_val, project, profile, path in raw_rows:
        try:
            canonical_path = path.resolve()
        except Exception as e:
            errors.append(f"Cannot resolve path for project '{project}': {e}")
            continue

        if canonical_path in seen_canonical_paths:
            # Deduplicate silently or continue
            continue

        # Check duplicate project names with differing paths
        if project in project_names and project_names[project] != canonical_path:
            errors.append(
                f"Duplicate project name '{project}' resolves to distinct paths: "
                f"'{project_names[project]}' vs '{canonical_path}'"
            )
            continue

        is_valid, err_msg = validate_target(canonical_path, harness_root)
        if not is_valid:
            if err_msg:
                errors.append(err_msg)
            continue

        seen_canonical_paths.add(canonical_path)
        project_names[project] = canonical_path
        discovered.append(
            TargetVault(
                project=project,
                profile=profile,
                path=canonical_path,
                raw_date=date_val,
            )
        )

    return discovered, errors


class VaultTransactionManager:
    """Manages atomic, crash-resilient staging and rollback for one target vault."""

    def __init__(self, target_root: Path) -> None:
        self.target_root = target_root.resolve()
        self.tx_id = uuid.uuid4().hex[:12]
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
        self.staging_dir = self.target_root / ".agents" / f".dist-staging-{self.tx_id}"
        self.backup_dir = self.target_root / ".agents" / ".dist-bak" / timestamp
        self.journal_file = self.target_root / ".agents" / ".dist-journal.json"
        self.mutations: list[dict] = []

    def prepare(self, mutations: list[tuple[str, str, str]]) -> None:
        """Stage new files and create backups of existing files."""
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.mutations = []

        for rel_path, action, new_content in mutations:
            target_file = self.target_root / rel_path
            assert_not_sovereign(self.target_root, target_file)
            was_present = target_file.exists()

            if was_present:
                bak_file = self.backup_dir / rel_path
                bak_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target_file, bak_file)

            if action in ("replace", "create"):
                staged_file = self.staging_dir / rel_path
                staged_file.parent.mkdir(parents=True, exist_ok=True)
                staged_file.write_text(new_content, encoding="utf-8")

            self.mutations.append({
                "path": rel_path,
                "action": action,
                "was_present": was_present,
            })

        journal_data = {
            "transaction_id": self.tx_id,
            "status": "staged",
            "staging_dir": str(self.staging_dir.relative_to(self.target_root)),
            "backup_dir": str(self.backup_dir.relative_to(self.target_root)),
            "mutations": self.mutations,
        }
        self.journal_file.write_text(json.dumps(journal_data, indent=2), encoding="utf-8")

    def commit(self) -> None:
        """Commit staged mutations atomically into the target vault."""
        for item in self.mutations:
            rel_path = item["path"]
            action = item["action"]
            target_file = self.target_root / rel_path
            if action in ("replace", "create"):
                staged_file = self.staging_dir / rel_path
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(staged_file, target_file)
            elif action == "delete":
                if target_file.exists():
                    target_file.unlink()

        shutil.rmtree(self.staging_dir, ignore_errors=True)
        if self.journal_file.is_file():
            try:
                data = json.loads(self.journal_file.read_text(encoding="utf-8"))
                data["status"] = "committed"
                self.journal_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            except Exception:
                pass

    def rollback(self) -> None:
        """Rollback all mutations, restoring backups and removing newly created files."""
        for item in reversed(self.mutations):
            rel_path = item["path"]
            was_present = item["was_present"]
            target_file = self.target_root / rel_path
            if was_present:
                bak_file = self.backup_dir / rel_path
                if bak_file.is_file():
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(bak_file, target_file)
            else:
                if target_file.exists():
                    target_file.unlink()

        shutil.rmtree(self.staging_dir, ignore_errors=True)
        if self.journal_file.is_file():
            try:
                data = json.loads(self.journal_file.read_text(encoding="utf-8"))
                data["status"] = "rolled_back"
                self.journal_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            except Exception:
                pass


def recover_interrupted_transaction(vault_root: Path) -> bool:
    """Detect and roll back an interrupted transaction recorded in .dist-journal.json."""
    journal_file = vault_root / ".agents" / ".dist-journal.json"
    if not journal_file.is_file():
        return False
    try:
        data = json.loads(journal_file.read_text(encoding="utf-8"))
    except Exception:
        return False

    status = data.get("status")
    if status not in ("staged", "committing"):
        return False

    mutations = data.get("mutations", [])
    raw_bak = str(data.get("backup_dir") or "").strip()
    raw_stage = str(data.get("staging_dir") or "").strip()
    if not raw_stage or not raw_bak:
        return False
    try:
        staging_dir = (vault_root / raw_stage).resolve()
        backup_dir = (vault_root / raw_bak).resolve()
        agents_dir = (vault_root / ".agents").resolve()
        if not staging_dir.is_relative_to(agents_dir) or not backup_dir.is_relative_to(agents_dir):
            return False
        if not staging_dir.name.startswith(".dist-staging-"):
            return False
        assert_not_sovereign(vault_root, staging_dir)
        assert_not_sovereign(vault_root, backup_dir)
    except Exception:
        return False
    # Restore from backup
    for item in reversed(mutations):
        rel_path = item.get("path")
        was_present = item.get("was_present", True)
        if not rel_path:
            continue
        target_file = vault_root / rel_path
        try:
            assert_not_sovereign(vault_root, target_file)
        except SovereignViolationError:
            # Never touch Sovereign Canon during recovery
            continue

        if was_present and backup_dir.is_dir():
            bak_file = backup_dir / rel_path
            if bak_file.is_file():
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(bak_file, target_file)
        else:
            if target_file.exists():
                target_file.unlink()

    if staging_dir != vault_root and staging_dir.is_dir() and staging_dir.is_relative_to(agents_dir):
        shutil.rmtree(staging_dir, ignore_errors=True)

    data["status"] = "recovered"
    try:
        journal_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass
    return True


def generate_unified_diff(old_content: str, new_content: str, rel_path: str) -> str:
    """Generate terminal-rendered unified diff between old and new file content."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    diff_lines = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{rel_path}",
        tofile=f"b/{rel_path}",
    ))
    return "".join(diff_lines)


def write_lineage_ledger(
    target_root: Path,
    harness_source: str,
    harness_commit: str,
    surfaces: list[dict],
    conflicts_count: int,
    protected_count: int,
) -> Path:
    """Record cryptographic distribution ledger in target vault's .agents/harness-lineage.json."""
    ledger_path = target_root / ".agents" / "harness-lineage.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    status = "synchronized" if conflicts_count == 0 else "partial_conflict"
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    data = {
        "schema_version": 2,
        "harness_source": str(harness_source),
        "harness_commit": str(harness_commit),
        "distribution_timestamp": timestamp,
        "status": status,
        "surfaces": surfaces,
        "conflicts_count": conflicts_count,
        "sovereign_protected_count": protected_count,
    }
    ledger_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return ledger_path


REQUIRED_PREFLIGHT_HOOK_LIBS = (
    Path(".agents") / "hooks" / "lib" / "registry.py",
    Path(".agents") / "hooks" / "lib" / "parity.py",
)


def preflight_check(target_root: Path) -> tuple[bool, str | None]:
    """Verify physical hook existence before verify_activation can be safely invoked."""
    for rel_lib in REQUIRED_PREFLIGHT_HOOK_LIBS:
        lib_path = target_root / rel_lib
        if not lib_path.is_file():
            return False, f"Missing hook registry library at {rel_lib}; verify_activation cannot verify activation safely."
    return True, None


def generate_migration_patch(target_content: str, upstream_block: str, rel_path: str) -> str:
    """Generate a unified diff patch to migrate a legacy unmanaged document without mutating target."""
    lines = target_content.splitlines(keepends=True)
    insert_idx = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                insert_idx = i + 1
                break
    managed_section = (
        f"\n{MANAGED_BEGIN}\n"
        f"{upstream_block.rstrip(chr(10))}\n"
        f"{MANAGED_END}\n\n"
    )
    new_lines = lines[:insert_idx] + [managed_section] + lines[insert_idx:]
    new_content = "".join(new_lines)
    return generate_unified_diff(target_content, new_content, rel_path)


class DistributionArgParser(argparse.ArgumentParser):
    def parse_args(self, args=None, namespace=None):
        parsed = super().parse_args(args=args, namespace=namespace)
        if getattr(parsed, "apply", False) or getattr(parsed, "generate_migration_patch", False):
            parsed.preview = False
        elif not getattr(parsed, "preview", False):
            parsed.preview = True
        return parsed


def build_arg_parser() -> argparse.ArgumentParser:
    parser = DistributionArgParser(
        description="Synchronize root harness governance across derived vaults in batch."
    )
    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument("--all", action="store_true", help="Distribute to all vaults in docs/vault-registry.md")
    target_group.add_argument("--project", type=str, help="Distribute only to named project")
    target_group.add_argument("--target", type=str, help="Distribute only to specified target path")

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--preview", action="store_true", help="Preview changes without disk mutation (default)")
    mode_group.add_argument("--apply", action="store_true", help="Apply governance updates atomically")
    mode_group.add_argument("--generate-migration-patch", action="store_true", help="Generate migration patch for unmanaged legacy targets")
    return parser


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_of_str(text: str) -> str:
    return sha256_of_bytes(text.encode("utf-8"))


def sha256_of_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        return sha256_of_bytes(path.read_bytes())
    except Exception:
        return None


def extract_managed_block(text: str) -> str | None:
    """Extract content inside managed markers from upstream reference file."""
    lines = text.splitlines(keepends=True)
    begin_idx = -1
    end_idx = -1
    for idx, line in enumerate(lines):
        if MANAGED_BEGIN in line:
            begin_idx = idx
        elif MANAGED_END in line:
            end_idx = idx
    if begin_idx != -1 and end_idx != -1 and begin_idx < end_idx:
        return "".join(lines[begin_idx + 1:end_idx])
    return None


def get_harness_commit(harness_root: Path) -> str:
    """Retrieve current harness git commit hash or 'unversioned'."""
    git_head = harness_root / ".git" / "HEAD"
    if git_head.is_file():
        try:
            ref = git_head.read_text(encoding="utf-8").strip()
            if ref.startswith("ref: "):
                ref_file = harness_root / ".git" / ref[5:]
                if ref_file.is_file():
                    return ref_file.read_text(encoding="utf-8").strip()[:12]
            return ref[:12]
        except Exception:
            pass
    return "unversioned"


def count_sovereign_files(target_root: Path) -> int:
    """Count existing files under Zone 3 Sovereign Canon."""
    count = 0
    for pattern in SOVEREIGN_PATTERNS:
        p = target_root / pattern
        if p.is_file():
            count += 1
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.is_file():
                    count += 1
    return count


def collect_upstream_surfaces(harness_root: Path) -> dict[str, str]:
    """Collect all Zone 1 and Zone 2 candidate files from harness root."""
    surfaces: dict[str, str] = {}
    for exact in ALLOWED_EXACT_FILES:
        if exact.startswith(".agents/.dist-"):
            continue
        p = harness_root / exact
        if p.is_file():
            try:
                surfaces[exact] = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                pass

    for prefix in ("scripts/", "writing-style/", ".agents/hooks/"):
        dir_path = harness_root / prefix
        if dir_path.is_dir():
            for f in dir_path.rglob("*"):
                if f.is_file() and not f.name.endswith(".pyc") and "__pycache__" not in f.parts:
                    rel = f.relative_to(harness_root).as_posix()
                    try:
                        surfaces[rel] = f.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        pass
    return surfaces


def distribute_to_target(
    harness_root: Path,
    target: TargetVault,
    apply: bool = False,
    generate_migration: bool = False,
) -> dict:
    """Evaluate and distribute governance updates to one target vault."""
    pre_ok, pre_err = preflight_check(target.path)
    if not pre_ok:
        return {
            "project": target.project,
            "path": target.path,
            "status": "PREFLIGHT_FAILED",
            "error": pre_err,
            "mutations_count": 0,
            "conflicts_count": 1,
            "diffs": [],
        }

    # Check for interrupted transaction; only recover on apply=True to preserve zero-mutation preview
    journal_file = target.path / ".agents" / ".dist-journal.json"
    if journal_file.is_file():
        try:
            j_data = json.loads(journal_file.read_text(encoding="utf-8"))
            if j_data.get("status") in ("staged", "committing"):
                if apply:
                    recover_interrupted_transaction(target.path)
                else:
                    return {
                        "project": target.project,
                        "path": target.path,
                        "status": "INTERRUPTED_TRANSACTION_PENDING",
                        "error": "Interrupted transaction detected in .dist-journal.json; run with --apply to recover.",
                        "mutations_count": 0,
                        "conflicts_count": 1,
                        "diffs": [],
                    }
        except Exception:
            pass

    # Read existing lineage ledger baseline if present
    lineage_file = target.path / ".agents" / "harness-lineage.json"
    baseline_map: dict[str, str] = {}
    if lineage_file.is_file():
        try:
            lin_data = json.loads(lineage_file.read_text(encoding="utf-8"))
            for surf in lin_data.get("surfaces", []):
                if isinstance(surf, dict) and "path" in surf:
                    baseline_map[surf["path"]] = surf.get("source_sha256")
        except Exception:
            pass

    upstream_surfaces = collect_upstream_surfaces(harness_root)
    mutations: list[tuple[str, str, str]] = []
    surfaces_record: list[dict] = []
    conflicts_count = 0
    unified_diffs: list[str] = []

    for rel_path, upstream_content in sorted(upstream_surfaces.items()):
        target_file = target.path / rel_path
        u_digest = sha256_of_str(upstream_content)
        t_digest = sha256_of_file(target_file)
        b_digest = baseline_map.get(rel_path)

        # Zone 2: Hybrid documents
        if rel_path in ("AGENTS.md", "WORKFLOW.md", "CLAUDE.md"):
            upstream_block = extract_managed_block(upstream_content)
            if upstream_block is not None and target_file.is_file():
                tgt_text = target_file.read_text(encoding="utf-8")
                try:
                    status, spliced = splice_managed_block(tgt_text, upstream_block)
                    if status == "SPLICED":
                        if spliced != tgt_text:
                            diff = generate_unified_diff(tgt_text, spliced, rel_path)
                            if diff:
                                unified_diffs.append(diff)
                            mutations.append((rel_path, "replace", spliced))
                            surfaces_record.append({
                                "path": rel_path,
                                "zone": "hybrid_governance",
                                "action": "spliced",
                                "source_sha256": u_digest,
                                "target_sha256": sha256_of_str(spliced),
                            })
                        else:
                            surfaces_record.append({
                                "path": rel_path,
                                "zone": "hybrid_governance",
                                "action": "no-op",
                                "source_sha256": u_digest,
                                "target_sha256": t_digest,
                            })
                    elif status == "UNMANAGED":
                        if generate_migration:
                            patch = generate_migration_patch(tgt_text, upstream_block, rel_path)
                            unified_diffs.append(patch)
                        conflicts_count += 1
                        surfaces_record.append({
                            "path": rel_path,
                            "zone": "hybrid_governance",
                            "action": "unmanaged_legacy",
                            "source_sha256": u_digest,
                            "target_sha256": t_digest,
                        })
                except SplicingBlockedError as e:
                    conflicts_count += 1
                    surfaces_record.append({
                        "path": rel_path,
                        "zone": "hybrid_governance",
                        "action": "splicing_blocked",
                        "error": str(e),
                    })

        # Zone 1: JSON Configurations
        elif rel_path.endswith(".json") and ("policy" in rel_path or "hooks" in rel_path or "settings" in rel_path):
            if target_file.is_file():
                tgt_text = target_file.read_text(encoding="utf-8")
                merged_text = merge_json_config(upstream_content, tgt_text, rel_path)
                try:
                    is_semantic_diff = (json.loads(merged_text) != json.loads(tgt_text))
                except Exception:
                    is_semantic_diff = (merged_text != tgt_text)

                if is_semantic_diff:
                    diff = generate_unified_diff(tgt_text, merged_text, rel_path)
                    if diff:
                        unified_diffs.append(diff)
                    mutations.append((rel_path, "replace", merged_text))
                    surfaces_record.append({
                        "path": rel_path,
                        "zone": "universal_core",
                        "action": "config_merged",
                        "source_sha256": u_digest,
                        "target_sha256": sha256_of_str(merged_text),
                    })
                else:
                    surfaces_record.append({
                        "path": rel_path,
                        "zone": "universal_core",
                        "action": "no-op",
                        "source_sha256": u_digest,
                        "target_sha256": t_digest,
                    })
            else:
                diff = generate_unified_diff("", upstream_content, rel_path)
                if diff:
                    unified_diffs.append(diff)
                mutations.append((rel_path, "create", upstream_content))
                surfaces_record.append({
                    "path": rel_path,
                    "zone": "universal_core",
                    "action": "created",
                    "source_sha256": u_digest,
                    "target_sha256": u_digest,
                })

        # Zone 1: Infrastructure surfaces (3-way evaluation)
        else:
            state, _ = evaluate_3way(u_digest, t_digest, b_digest)
            if state == "safe_upgrade":
                tgt_text = target_file.read_text(encoding="utf-8") if target_file.is_file() else ""
                diff = generate_unified_diff(tgt_text, upstream_content, rel_path)
                if diff:
                    unified_diffs.append(diff)
                mutations.append((rel_path, "replace", upstream_content))
                surfaces_record.append({
                    "path": rel_path,
                    "zone": "universal_core",
                    "action": "updated",
                    "source_sha256": u_digest,
                    "target_sha256": u_digest,
                })
            elif state == "new":
                diff = generate_unified_diff("", upstream_content, rel_path)
                if diff:
                    unified_diffs.append(diff)
                mutations.append((rel_path, "create", upstream_content))
                surfaces_record.append({
                    "path": rel_path,
                    "zone": "universal_core",
                    "action": "created",
                    "source_sha256": u_digest,
                    "target_sha256": u_digest,
                })
            elif state == "deleted":
                diff = generate_unified_diff(target_file.read_text(encoding="utf-8"), "", rel_path)
                if diff:
                    unified_diffs.append(diff)
                mutations.append((rel_path, "delete", ""))
                surfaces_record.append({
                    "path": rel_path,
                    "zone": "universal_core",
                    "action": "deleted",
                    "source_sha256": None,
                    "target_sha256": None,
                })
            elif state in ("local_conflict", "unknown_baseline"):
                conflicts_count += 1
                surfaces_record.append({
                    "path": rel_path,
                    "zone": "universal_core",
                    "action": state,
                    "source_sha256": u_digest,
                    "target_sha256": t_digest,
                })
            elif state == "no-op":
                surfaces_record.append({
                    "path": rel_path,
                    "zone": "universal_core",
                    "action": "no-op",
                    "source_sha256": u_digest,
                    "target_sha256": t_digest,
                })

    sov_count = count_sovereign_files(target.path)

    if apply and mutations:
        tx = VaultTransactionManager(target.path)
        try:
            tx.prepare(mutations)
            tx.commit()
            write_lineage_ledger(
                target.path,
                str(harness_root),
                get_harness_commit(harness_root),
                surfaces_record,
                conflicts_count,
                sov_count,
            )
        except (Exception, KeyboardInterrupt) as e:
            tx.rollback()
            return {
                "project": target.project,
                "path": target.path,
                "status": "TRANSACTION_FAILED",
                "error": str(e),
                "mutations_count": 0,
                "conflicts_count": conflicts_count + 1,
                "diffs": [],
            }

    final_status = "SYNCHRONIZED" if conflicts_count == 0 else "PARTIAL_CONFLICT"
    if not apply and mutations:
        final_status = "PENDING_MUTATIONS"

    return {
        "project": target.project,
        "path": target.path,
        "status": final_status,
        "mutations_count": len(mutations),
        "conflicts_count": conflicts_count,
        "diffs": unified_diffs,
        "surfaces": surfaces_record,
    }


def run_distribution(
    harness_root: Path,
    project_filter: str | None = None,
    target_filter: Path | None = None,
    all_targets: bool = False,
    apply: bool = False,
    generate_migration: bool = False,
) -> tuple[int, list[dict]]:
    """Top-level distribution loop across discovered targets."""
    targets, errors = discover_targets(harness_root)
    if errors:
        for err in errors:
            sys.stderr.write(f"Discovery Warning: {err}\n")

    selected_targets: list[TargetVault] = []
    if target_filter:
        canonical_tf = target_filter.resolve()
        selected_targets = [t for t in targets if t.path == canonical_tf]
        if not selected_targets:
            # Validate on demand if single target was provided
            is_valid, err_msg = validate_target(canonical_tf, harness_root)
            if is_valid:
                selected_targets = [TargetVault(project=canonical_tf.name, profile="unknown", path=canonical_tf)]
            else:
                sys.stderr.write(f"Target Error: {err_msg}\n")
                return 1, []
    elif project_filter:
        selected_targets = [t for t in targets if t.project == project_filter]
        if not selected_targets:
            sys.stderr.write(f"Error: Project '{project_filter}' not found in docs/vault-registry.md\n")
            return 1, []
    elif all_targets:
        selected_targets = targets
    else:
        selected_targets = targets

    results: list[dict] = []
    has_failures = False

    for t in selected_targets:
        res = distribute_to_target(harness_root, t, apply=apply, generate_migration=generate_migration)
        results.append(res)
        if res.get("status") in ("PREFLIGHT_FAILED", "TRANSACTION_FAILED"):
            has_failures = True

    return (1 if has_failures else 0), results


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    harness_root = Path.cwd().resolve()
    target_path = Path(args.target).resolve() if args.target else None

    exit_code, results = run_distribution(
        harness_root=harness_root,
        project_filter=args.project,
        target_filter=target_path,
        all_targets=args.all,
        apply=args.apply,
        generate_migration=args.generate_migration_patch,
    )

    mode_label = "APPLY" if args.apply else "PREVIEW"
    print(f"\n=== BATCH GOVERNANCE DISTRIBUTION ({mode_label}) ===")
    print(f"Processed {len(results)} target vault(s)")
    for r in results:
        print(f"\n[{r.get('project')}] ({r.get('path')})")
        print(f"  Status: {r.get('status')}")
        print(f"  Mutations: {r.get('mutations_count')} | Conflicts: {r.get('conflicts_count')}")
        if r.get("surfaces"):
            for s in r.get("surfaces", []):
                act = s.get("action", "")
                if act in ("unmanaged_legacy", "splicing_blocked", "local_conflict", "unknown_baseline"):
                    print(f"  [{act.upper()}] {s.get('path')}")
        if r.get("diffs"):
            print("  --- Diffs ---")
            for d in r.get("diffs"):
                print(d)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
