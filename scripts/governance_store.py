#!/usr/bin/env python3
"""Validate and maintain the vault-local governance continuity store."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, time as clock_time
from pathlib import Path


LIMIT_BYTES = 64 * 1024
LIMIT_ENTRIES = 100
KEEP_ENTRIES = 30
COMPACT_ABOVE = 50
COMPACT_KEEP = 20
PRUNE_ABOVE = 200
ARCHIVE_LOCATIONS = {"handoff": "handoff/archived", "design": "docs/design/archived", "plans": "docs/plans/archived"}
FACT_FIELDS = {"title", "date", "updated", "type", "status", "tags", "fact_id", "scope", "stage", "fact_key", "effective", "source"}
ANCHOR_FIELDS = {"title", "date", "updated", "type", "status"}
ARCHIVE_ROW = re.compile(r"^- \[\[([^]|]+)\|[^]]+\]\] — (\d+) entries; SHA-256 `([0-9a-f]{64})`$")
HANDOFF_PROMPT_RE = re.compile(r"^INITIAL-PROMPT-([A-Za-z0-9][A-Za-z0-9._-]*)\.txt$")
HANDOFF_FILE_RE = re.compile(r"^HANDOFF-([A-Za-z0-9][A-Za-z0-9._-]*)\.md$")
HANDOFF_NEW_SUFFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})--(.+)$")
HANDOFF_LEGACY_SUFFIX_RE = re.compile(r"^(.+)-(\d{4}-\d{2}-\d{2})-(\d{6})$")


class StoreError(ValueError):
    def __init__(self, code: str, path: Path | str, detail: str):
        self.code, self.path, self.detail = code, str(path), detail
        super().__init__(f"{code} {self.path} {detail}")


@dataclass(frozen=True)
class Fact:
    path: Path
    title: str
    fact_id: str
    status: str
    scope: str
    stage: str
    fact_key: str
    effective: str
    supersedes: tuple[str, ...]
    superseded_by: str
    sources: tuple[str, ...]


def parse_frontmatter(path: Path) -> tuple[dict[str, object], str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise StoreError("INVALID_FRONTMATTER", path, "missing opening delimiter")
    try:
        close = lines.index("---", 1)
    except ValueError as error:
        raise StoreError("INVALID_FRONTMATTER", path, "missing closing delimiter") from error
    data: dict[str, object] = {}
    active: str | None = None
    for number, line in enumerate(lines[1:close], 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - "):
            if active not in {"tags", "source"}:
                raise StoreError("INVALID_FRONTMATTER", path, f"unsupported list at line {number}")
            assert isinstance(data[active], list)
            data[active].append(line[4:].strip().strip("\"'"))
            continue
        if line.startswith((" ", "\t")) or ":" not in line:
            raise StoreError("INVALID_FRONTMATTER", path, f"malformed line {number}")
        key, raw = line.split(":", 1)
        if key in data:
            raise StoreError("DUPLICATE_FIELD", path, key)
        active = key
        value = raw.strip().strip("\"'")
        if value.startswith("[") and value.endswith("]"):
            data[key] = tuple(v.strip().strip("\"'") for v in value[1:-1].split(",") if v.strip())
        elif not value and key in {"tags", "source"}:
            data[key] = []
        else:
            data[key] = value
    return data, "\n".join(lines[close + 1 :]).strip()


def load_facts(root: Path) -> list[Fact]:
    facts: list[Fact] = []
    for path in sorted((root / ".agents/memory").glob("*.md")):
        if path.name.startswith("."):
            continue
        data, _ = parse_frontmatter(path)
        missing = sorted(field for field in FACT_FIELDS if not data.get(field))
        if missing:
            raise StoreError("MISSING_FACT_FIELD", path, ",".join(missing))
        status = str(data["status"])
        if status not in {"active", "superseded"}:
            raise StoreError("INVALID_STATUS", path, status)
        sources = data["source"] if isinstance(data["source"], list) else [data["source"]]
        supersedes = data.get("supersedes", ())
        if isinstance(supersedes, str):
            supersedes = (supersedes,) if supersedes else ()
        facts.append(Fact(path, str(data["title"]), str(data["fact_id"]), status, str(data["scope"]), str(data["stage"]), str(data["fact_key"]), str(data["effective"]), tuple(supersedes), str(data.get("superseded_by", "")), tuple(str(v) for v in sources)))
    return facts


def validate_facts(facts: list[Fact], root: Path) -> None:
    by_id: dict[str, Fact] = {}
    slots: dict[tuple[str, str], Fact] = {}
    for fact in facts:
        if fact.fact_id in by_id:
            raise StoreError("DUPLICATE_FACT_ID", fact.path, fact.fact_id)
        by_id[fact.fact_id] = fact
        if fact.status == "active":
            slot = (fact.scope, fact.fact_key)
            if slot in slots:
                raise StoreError("ACTIVE_SLOT_CONFLICT", fact.path, f"{slot[0]}/{slot[1]}")
            slots[slot] = fact
        for source in fact.sources:
            if "://" in source or source.startswith("source_id:"):
                continue
            if (root / source).exists():
                continue
            if source.startswith(("docs/design/", "docs/plans/")):
                prefix, _, name = source.rpartition("/")
                if (root / prefix / "archived" / name).exists():
                    continue
            raise StoreError("MISSING_SOURCE", fact.path, source)
    for fact in facts:
        if fact.superseded_by:
            successor = by_id.get(fact.superseded_by)
            if successor is None:
                raise StoreError("DANGLING_SUCCESSOR", fact.path, fact.superseded_by)
            if fact.fact_id not in successor.supersedes:
                raise StoreError("NONRECIPROCAL_SUCCESSION", fact.path, fact.superseded_by)
        for previous in fact.supersedes:
            old = by_id.get(previous)
            if old is None:
                raise StoreError("DANGLING_PREDECESSOR", fact.path, previous)
            if old.superseded_by != fact.fact_id:
                raise StoreError("NONRECIPROCAL_SUCCESSION", fact.path, previous)
    for start in by_id:
        seen: set[str] = set()
        cursor = start
        while cursor and cursor in by_id:
            if cursor in seen:
                raise StoreError("SUPERSESSION_CYCLE", by_id[start].path, cursor)
            seen.add(cursor)
            cursor = by_id[cursor].superseded_by


def memory_text(root: Path, facts: list[Fact]) -> str:
    current, _ = parse_frontmatter(root / ".agents/Memory.md")
    tags = current.get("tags", ["continuity", "memory"])
    tag_lines = "\n".join(f"  - {tag}" for tag in tags)
    rows = [f"- [[memory/{f.path.stem}|{f.title}]] — {f.scope} / {f.fact_key} (`{f.fact_id}`)" for f in sorted(facts, key=lambda item: (item.scope, item.fact_key, item.fact_id)) if f.status == "active"]

    def render(updated: str) -> str:
        rendered = f"""---
title: {current.get('title', 'Agent Memory')}
date: {current.get('date', date.today().isoformat())}
updated: {updated}
type: memory
status: active
tags:
{tag_lines}
---

# Memory

Active durable facts are indexed here. Read linked fact bodies only when relevant; superseded history remains under `memory/`.

## Active facts
"""
        return rendered + (("\n" + "\n".join(rows) + "\n") if rows else "")

    # `updated` means the last substantive content change (WORKFLOW.md), not the last time
    # this command ran. Keep the stored date whenever the rendered index is otherwise
    # identical, so verify_memory_index() compares against a fixed point instead of a value
    # that moves every midnight.
    existing = (root / ".agents/Memory.md").read_text(encoding="utf-8")
    previous = str(current.get("updated", "")).strip() or date.today().isoformat()
    unchanged = render(previous)
    return unchanged if unchanged == existing else render(date.today().isoformat())


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def verify_memory_index(root: Path, facts: list[Fact]) -> None:
    expected = memory_text(root, facts)
    if (root / ".agents/Memory.md").read_text(encoding="utf-8") != expected:
        raise StoreError("STALE_MEMORY_INDEX", ".agents/Memory.md", "run refresh-memory")


def split_anchor(text: str) -> tuple[str, list[str], str]:
    positions = [m.start() for m in re.finditer(r"(?m)^## ", text)]
    archive_start = next((p for p in positions if text[p:].startswith("## Arsip")), len(text))
    entries_at = [p for p in positions if p < archive_start]
    preamble_end = entries_at[0] if entries_at else archive_start
    entries: list[str] = []
    for index, start in enumerate(entries_at):
        end = entries_at[index + 1] if index + 1 < len(entries_at) else archive_start
        entries.append(text[start:end].rstrip() + "\n")
    return text[:preamble_end].rstrip() + "\n", entries, text[archive_start:].strip()


def check_archives(root: Path, anchor: Path) -> None:
    _, _, block = split_anchor(anchor.read_text(encoding="utf-8"))
    for line in block.splitlines():
        match = ARCHIVE_ROW.match(line)
        if not match:
            continue
        path = root / ".agents" / match.group(1)
        if not path.is_file():
            raise StoreError("BROKEN_ARCHIVE_LINK", anchor, str(path))
        if hashlib.sha256(path.read_bytes()).hexdigest() != match.group(3):
            raise StoreError("ARCHIVE_CHECKSUM_MISMATCH", path, match.group(3))


def rotate_one(root: Path, name: str, timestamp: str) -> bool:
    path = root / ".agents" / f"{name}.md"
    original = path.read_text(encoding="utf-8")
    preamble, entries, archive_block = split_anchor(original)
    if len(original.encode()) <= LIMIT_BYTES and len(entries) <= LIMIT_ENTRIES:
        return False
    if len(entries) <= KEEP_ENTRIES:
        raise StoreError("OVERSIZED_ACTIVE_WINDOW", path, f"{len(entries)} entries")
    moved, retained = entries[:-KEEP_ENTRIES], entries[-KEEP_ENTRIES:]
    kind = name.lower()
    archive = root / ".agents/archive" / kind / f"{name}.{timestamp}.md"
    if archive.exists():
        raise StoreError("ARCHIVE_COLLISION", archive, "already exists")
    archive_text = f"""---
title: {name} Archive {timestamp}
date: {date.today().isoformat()}
updated: {date.today().isoformat()}
type: {kind}-archive
status: active
tags:
  - continuity
  - archive
---

# {name} Archive

Archive from `.agents/{name}.md`; the parent retains the newest entries.

{chr(10).join(moved).rstrip()}
"""
    digest = hashlib.sha256(archive_text.encode()).hexdigest()
    relative = archive.relative_to(root / ".agents")
    row = f"- [[{relative}|{name} {timestamp}]] — {len(moved)} entries; SHA-256 `{digest}`"
    rows = [line for line in archive_block.splitlines() if line.startswith("- [[")]
    new_block = "## Arsip\n\n" + "\n".join(rows + [row])
    parent_text = preamble + "\n" + "\n".join(retained).rstrip() + "\n\n" + new_block + "\n"
    if len(parent_text.encode()) > LIMIT_BYTES:
        raise StoreError("OVERSIZED_ACTIVE_WINDOW", path, "newest 30 entries exceed 64 KiB")
    archive.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(archive, archive_text)
    try:
        if hashlib.sha256(archive.read_bytes()).hexdigest() != digest:
            raise StoreError("ARCHIVE_CHECKSUM_MISMATCH", archive, digest)
        atomic_write(path, parent_text)
    except BaseException:
        archive.unlink(missing_ok=True)
        raise
    return True


def resolve_active_handoff(root: Path) -> tuple[Path, Path]:
    resolver = root / ".agents/skills/bootstrap/scripts/resolve_handoff.py"
    if not resolver.is_file():
        raise StoreError("MISSING_RESOLVER", resolver, "bootstrap resolver not found")
    result = subprocess.run([sys.executable, str(resolver), "--root", str(root)], capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        raise StoreError("HANDOFF_RESOLVE_FAILED", root / "handoff", (result.stderr or result.stdout).strip())
    data = json.loads(result.stdout)
    return Path(data["initial_prompt"]), Path(data["handoff"])


def _move_to_archive(root: Path, src: Path, dest: Path) -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(src.relative_to(root))],
        cwd=root, capture_output=True, text=True,
    ).returncode == 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    if tracked:
        subprocess.run(["git", "mv", str(src.relative_to(root)), str(dest.relative_to(root))], cwd=root, check=True)
    else:
        src.rename(dest)


def rotate_index_rows(index_path: Path, timestamp: str, index_title: str, index_kind: str) -> bool:
    text = index_path.read_text(encoding="utf-8")
    preamble, _, archive_block = split_anchor(text)
    rows = [line for line in archive_block.splitlines() if line.startswith("- ")]
    if len(index_path.read_bytes()) <= LIMIT_BYTES and len(rows) <= LIMIT_ENTRIES:
        return False
    if len(rows) <= KEEP_ENTRIES:
        raise StoreError("OVERSIZED_ACTIVE_WINDOW", index_path, f"{len(rows)} entries")
    moved, retained = rows[:-KEEP_ENTRIES], rows[-KEEP_ENTRIES:]
    sub_index = index_path.parent / f"index-{timestamp}.md"
    if sub_index.exists():
        raise StoreError("ARCHIVE_COLLISION", sub_index, "already exists")
    sub_text = f"""---
title: {index_title} Index {timestamp}
date: {date.today().isoformat()}
updated: {date.today().isoformat()}
type: {index_kind}-index
status: active
tags:
  - archive
---

# {index_title} Index {timestamp}

Archive from `{index_path.relative_to(index_path.parents[1])}`; the parent retains the newest {KEEP_ENTRIES} rows.

{chr(10).join(moved).rstrip()}
"""
    digest = hashlib.sha256(sub_text.encode()).hexdigest()
    relative = sub_index.relative_to(index_path.parent)
    pointer_row = f"- [[{relative}|{index_title} Index {timestamp}]] — {len(moved)} entries; SHA-256 `{digest}`"
    new_block = "## Arsip\n\n" + "\n".join([pointer_row] + retained)
    parent_text = preamble.rstrip() + "\n\n" + new_block + "\n"
    if len(parent_text.encode()) > LIMIT_BYTES:
        raise StoreError("OVERSIZED_ACTIVE_WINDOW", index_path, f"newest {KEEP_ENTRIES} rows exceed 64 KiB")
    atomic_write(sub_index, sub_text)
    try:
        if hashlib.sha256(sub_index.read_bytes()).hexdigest() != digest:
            raise StoreError("ARCHIVE_CHECKSUM_MISMATCH", sub_index, digest)
        atomic_write(index_path, parent_text)
    except BaseException:
        sub_index.unlink(missing_ok=True)
        raise
    return True


def append_index_rows(index_path: Path, new_rows: list[str], timestamp: str, index_title: str, index_kind: str) -> None:
    if not index_path.is_file():
        raise StoreError("MISSING_ARCHIVE_INDEX", index_path, f"{index_path} must exist before archiving")
    text = index_path.read_text(encoding="utf-8")
    preamble, _, archive_block = split_anchor(text)
    existing_rows = [line for line in archive_block.splitlines() if line.startswith("- ")]
    new_block = "## Arsip\n\n" + "\n".join(existing_rows + new_rows)
    parent_text = preamble.rstrip() + "\n\n" + new_block + "\n"
    atomic_write(index_path, parent_text)
    rotate_index_rows(index_path, timestamp, index_title, index_kind)


def rotate_handoff_index(root: Path, timestamp: str) -> bool:
    return rotate_index_rows(root / "handoff/archived/README.md", timestamp, "Handoff Archive", "handoff-archive")


def append_handoff_index_rows(root: Path, rows: list[tuple[str, str, str]], timestamp: str) -> None:
    today = date.today().isoformat()
    new_rows = [f"- `{suffix}` — archived {today} — HANDOFF SHA-256 `{handoff_digest}`; INITIAL-PROMPT SHA-256 `{prompt_digest}`" for suffix, handoff_digest, prompt_digest in rows]
    append_index_rows(root / "handoff/archived/README.md", new_rows, timestamp, "Handoff Archive", "handoff-archive")


def command_archive_handoff(root: Path, timestamp: str) -> None:
    handoff_dir = root / "handoff"
    archived_dir = handoff_dir / "archived"
    if not handoff_dir.is_dir():
        raise StoreError("MISSING_HANDOFF_DIR", handoff_dir, "not found")
    active_initial, _active_handoff = resolve_active_handoff(root)
    active_match = HANDOFF_PROMPT_RE.fullmatch(active_initial.name)
    if not active_match:
        raise StoreError("HANDOFF_RESOLVE_FAILED", active_initial, "resolved initial prompt has an unexpected name")
    active_suffix = active_match.group(1)

    prompts: dict[str, Path] = {}
    handoffs: dict[str, Path] = {}
    for path in handoff_dir.iterdir():
        if not path.is_file():
            continue
        match = HANDOFF_PROMPT_RE.fullmatch(path.name)
        if match:
            prompts[match.group(1)] = path
            continue
        match = HANDOFF_FILE_RE.fullmatch(path.name)
        if match:
            handoffs[match.group(1)] = path

    to_archive = sorted(suffix for suffix in prompts if suffix != active_suffix)
    if not to_archive:
        return

    archived_dir.mkdir(parents=True, exist_ok=True)
    rows: list[tuple[str, str, str]] = []
    for suffix in to_archive:
        initial = prompts[suffix]
        handoff = handoffs.get(suffix)
        if handoff is None:
            raise StoreError("UNPAIRED_HANDOFF", initial, f"missing HANDOFF-{suffix}.md")
        for src in (handoff, initial):
            dest = archived_dir / src.name
            if dest.exists():
                raise StoreError("ARCHIVE_COLLISION", dest, "already exists")
        handoff_digest = hashlib.sha256(handoff.read_bytes()).hexdigest()
        prompt_digest = hashlib.sha256(initial.read_bytes()).hexdigest()
        _move_to_archive(root, handoff, archived_dir / handoff.name)
        _move_to_archive(root, initial, archived_dir / initial.name)
        rows.append((suffix, handoff_digest, prompt_digest))

    append_handoff_index_rows(root, rows, timestamp)

    remaining = [
        p for p in handoff_dir.iterdir()
        if p.is_file() and (HANDOFF_PROMPT_RE.fullmatch(p.name) or HANDOFF_FILE_RE.fullmatch(p.name))
    ]
    if len(remaining) != 2:
        raise StoreError("HANDOFF_INVARIANT_VIOLATION", handoff_dir, f"{len(remaining)} files remain at top level")


# Escape hatch for consumers that must hold a completed plan out of archiving.
DOC_ARCHIVE_EXCLUDED_STEMS: set[str] = set()


APPROVED_DESIGN_RE = re.compile(r"^\*\*Approved design:\*\*\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def resolve_paired_design(root: Path, plan_path: Path) -> Path | None:
    """Locate the design document a plan pairs with.

    Prefers the plan's explicit `**Approved design:**` pointer, which is the
    authoritative link and the only one that works when design and plan carry
    different slugs (this harness pairs e.g. `…-skill-store-remediation-…` with
    `…-skill-store-canonical-sync-and-validation`, which no stem rule derives).
    Accepts either a markdown link (`[title](../design/x.md)`) or a bare or
    backticked path (`docs/design/x.md`); the former resolves against the plan's
    own directory, the latter against the repository root. Falls back to stem
    derivation for plans written before the pointer became conventional.
    """
    match = APPROVED_DESIGN_RE.search(plan_path.read_text(encoding="utf-8"))
    if match:
        target = match.group(1).strip()
        link = MARKDOWN_LINK_RE.search(target)
        if link:
            declared = (plan_path.parent / link.group(1)).resolve()
        else:
            declared = root / target.strip("`")
        if declared.is_file():
            return declared
    stem = plan_path.stem
    if stem.endswith("-implementation"):
        stem = stem[: -len("-implementation")]
    candidate = root / "docs/design" / f"{stem}.md"
    return candidate if candidate.is_file() else None


def rewrite_pair_links(text: str) -> str:
    text = text.replace("](../design/", "](../../design/archived/")
    text = text.replace("](../plans/", "](../../plans/archived/")
    return text


def command_archive_docs(root: Path, timestamp: str) -> None:
    plans_dir = root / "docs/plans"
    design_dir = root / "docs/design"
    if not plans_dir.is_dir() or not design_dir.is_dir():
        raise StoreError("MISSING_DOCS_DIR", root / "docs", "docs/design or docs/plans not found")

    eligible: list[tuple[Path, Path]] = []
    for plan_path in sorted(plans_dir.iterdir()):
        if not plan_path.is_file() or plan_path.suffix != ".md":
            continue
        data, _ = parse_frontmatter(plan_path)
        if str(data.get("status", "")) != "completed":
            continue
        if plan_path.stem in DOC_ARCHIVE_EXCLUDED_STEMS:
            continue
        design_path = resolve_paired_design(root, plan_path)
        if design_path is None:
            raise StoreError("UNRESOLVED_DESIGN_PAIR", plan_path, "no matching design file for a completed plan")
        design_data, _ = parse_frontmatter(design_path)
        if str(design_data.get("status", "")) != "approved":
            continue
        eligible.append((plan_path, design_path))

    if not eligible:
        return

    design_archive = design_dir / "archived"
    plans_archive = plans_dir / "archived"
    design_archive.mkdir(parents=True, exist_ok=True)
    plans_archive.mkdir(parents=True, exist_ok=True)

    rows: list[tuple[str, str, str]] = []
    for plan_path, design_path in eligible:
        plan_dest = plans_archive / plan_path.name
        design_dest = design_archive / design_path.name
        for dest in (plan_dest, design_dest):
            if dest.exists():
                raise StoreError("ARCHIVE_COLLISION", dest, "already exists")
        atomic_write(plan_path, rewrite_pair_links(plan_path.read_text(encoding="utf-8")))
        atomic_write(design_path, rewrite_pair_links(design_path.read_text(encoding="utf-8")))
        plan_digest = hashlib.sha256(plan_path.read_bytes()).hexdigest()
        design_digest = hashlib.sha256(design_path.read_bytes()).hexdigest()
        _move_to_archive(root, plan_path, plan_dest)
        _move_to_archive(root, design_path, design_dest)
        rows.append((plan_path.stem, design_digest, plan_digest))

    today = date.today().isoformat()
    design_rows = [f"- `{stem}` — archived {today} — DESIGN SHA-256 `{design_digest}`" for stem, design_digest, _plan_digest in rows]
    plan_rows = [f"- `{stem}` — archived {today} — PLAN SHA-256 `{plan_digest}`" for stem, _design_digest, plan_digest in rows]
    _ensure_index_scaffold(design_archive / "README.md", "Archived Design Documents")
    _ensure_index_scaffold(plans_archive / "README.md", "Archived Implementation Plans")
    append_index_rows(design_archive / "README.md", design_rows, timestamp, "Design Archive", "design-archive")
    append_index_rows(plans_archive / "README.md", plan_rows, timestamp, "Plans Archive", "plans-archive")


def _ensure_index_scaffold(index_path: Path, title: str) -> None:
    if index_path.is_file():
        return
    atomic_write(index_path, f"""---
title: {title}
date: {date.today().isoformat()}
updated: {date.today().isoformat()}
type: documentation
status: active
tags:
  - archive
---

# {title}

## Arsip

""")


GOAL_BLOCK_RE = re.compile(r"^## Goal\s*$([\s\S]*?)(?=^##\s|\Z)", re.MULTILINE)


def _archive_dir(root: Path, location: str) -> Path:
    if location not in ARCHIVE_LOCATIONS:
        raise StoreError("INVALID_LOCATION", location, "must be one of: " + ", ".join(sorted(ARCHIVE_LOCATIONS)))
    return root / ARCHIVE_LOCATIONS[location]


def _handoff_stamp(suffix: str) -> tuple[str, str]:
    """(YYYY-MM-DD, HHMMSS or "") for `YYYY-MM-DD--slug` or `<prefix>-YYYY-MM-DD-HHMMSS`."""
    if match := HANDOFF_NEW_SUFFIX_RE.fullmatch(suffix):
        day, clock = match.group(1), ""
    elif match := HANDOFF_LEGACY_SUFFIX_RE.fullmatch(suffix):
        day, clock = match.group(2), match.group(3)
    else:
        raise StoreError("UNDATED_HANDOFF", suffix, "suffix matches neither YYYY-MM-DD--slug nor <prefix>-YYYY-MM-DD-HHMMSS")
    try:
        date.fromisoformat(day)
        if clock:
            clock_time(int(clock[:2]), int(clock[2:4]), int(clock[4:]))
    except ValueError as exc:
        raise StoreError("UNDATED_HANDOFF", suffix, "invalid date or HHMMSS") from exc
    return day, clock


def _raw_entries(root: Path, location: str) -> list[str]:
    """Oldest-first stable identifiers for raw archived items. One identifier per pair for handoff (ordered by suffix date and HHMMSS), per document otherwise."""
    directory = _archive_dir(root, location)
    if not directory.is_dir():
        return []
    if location == "handoff":
        suffixes: set[str] = set()
        for path in directory.iterdir():
            if not path.is_file():
                continue
            match = HANDOFF_PROMPT_RE.fullmatch(path.name) or HANDOFF_FILE_RE.fullmatch(path.name)
            if match:
                suffixes.add(match.group(1))
        return sorted(suffixes, key=lambda suffix: (*_handoff_stamp(suffix), suffix))
    identifiers = []
    for path in directory.iterdir():
        if not path.is_file() or path.suffix != ".md":
            continue
        if path.name in {"README.md", "COMPACTION-LOG.md"} or path.name.startswith("index-"):
            continue
        identifiers.append(path.stem)
    return sorted(identifiers)


def _compaction_eligible(raw: list[str], location: str) -> list[str]:
    """Oldest entries beyond COMPACT_KEEP; refuse when the cut splits handoffs whose order is undecidable."""
    if len(raw) <= COMPACT_ABOVE:
        return []
    cut = len(raw) - COMPACT_KEEP
    if location == "handoff":
        split_day = _handoff_stamp(raw[cut - 1])[0]
        if _handoff_stamp(raw[cut])[0] == split_day:
            clocks = [clock for day, clock in map(_handoff_stamp, raw) if day == split_day]
            if "" in clocks or len(set(clocks)) != len(clocks):
                raise StoreError("AMBIGUOUS_HANDOFF_ORDER", split_day, "retention cut splits a date whose handoffs lack distinct HHMMSS; rename with HHMMSS before compacting")
    return raw[:cut]


def _log_path(root: Path, location: str) -> Path:
    return _archive_dir(root, location) / "COMPACTION-LOG.md"


def _logged_entries(root: Path, location: str) -> list[str]:
    log = _log_path(root, location)
    if not log.is_file():
        return []
    rows = []
    for line in log.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^- `([^`]+)`", line)
        if match:
            rows.append(match.group(1))
    return rows


def check_retention(root: Path) -> list[dict]:
    findings: list[dict] = []
    for location in sorted(ARCHIVE_LOCATIONS):
        raw = _raw_entries(root, location)
        logged = _logged_entries(root, location)
        eligible = _compaction_eligible(raw, location)
        if eligible:
            findings.append({"location": location, "action": "compact", "eligible_count": len(eligible), "oldest_identifiers": eligible[:5]})
        total = len(raw) + len(logged)
        if total > PRUNE_ABOVE and logged:
            prune_eligible = logged[: total - PRUNE_ABOVE]
            if prune_eligible:
                findings.append({"location": location, "action": "prune", "eligible_count": len(prune_eligible), "oldest_identifiers": prune_eligible[:5]})
    return findings


def command_check_retention(root: Path) -> None:
    findings = check_retention(root)
    if not findings:
        print("OK check-retention")
        return
    for finding in findings:
        ids = ", ".join(finding["oldest_identifiers"])
        print(f"RETENTION {finding['location']} {finding['action']} eligible={finding['eligible_count']} oldest=[{ids}]")


def _entry_paths(root: Path, location: str, identifier: str) -> list[Path]:
    directory = _archive_dir(root, location)
    if location == "handoff":
        return [directory / f"HANDOFF-{identifier}.md", directory / f"INITIAL-PROMPT-{identifier}.txt"]
    return [directory / f"{identifier}.md"]


def _summary_for(root: Path, location: str, identifier: str) -> str:
    if location == "handoff":
        handoff_path = _archive_dir(root, location) / f"HANDOFF-{identifier}.md"
        if handoff_path.is_file():
            match = GOAL_BLOCK_RE.search(handoff_path.read_text(encoding="utf-8"))
            if match:
                first_line = next((line.strip() for line in match.group(1).splitlines() if line.strip()), "")
                if first_line:
                    return first_line[:120]
        return identifier
    doc_path = _archive_dir(root, location) / f"{identifier}.md"
    if doc_path.is_file():
        data, _ = parse_frontmatter(doc_path)
        return f"{data.get('title', identifier)} ({data.get('date', '')})"
    return identifier


def _new_compaction_log(location: str, today: str) -> str:
    return f"""---
title: {location.title()} Archive Compaction Log
date: {today}
updated: {today}
type: documentation
status: active
tags:
  - archive
  - compaction-log
---

# {location.title()} Archive Compaction Log

Permanent, append-only record of raw archived entries removed by `compact-archive`. Never rotated, never pruned. Each row's SHA-256 is the checksum of the entry's raw content at the moment it was compacted, so identity survives even after the raw file is gone.

"""


def command_compact_archive(root: Path, location: str) -> None:
    eligible = _compaction_eligible(_raw_entries(root, location), location)
    if not eligible:
        return
    today = date.today().isoformat()
    digests: dict[str, str] = {}
    new_rows = []
    for identifier in eligible:
        paths = _entry_paths(root, location, identifier)
        for path in paths:
            if not path.is_file():
                raise StoreError("MISSING_ARCHIVE_ENTRY", path, "expected raw archived file not found")
        digest = hashlib.sha256(b"".join(path.read_bytes() for path in paths)).hexdigest()
        digests[identifier] = digest
        new_rows.append(f"- `{identifier}` — SHA-256 `{digest}` — compacted {today} — {_summary_for(root, location, identifier)}")

    log_path = _log_path(root, location)
    existing_text = log_path.read_text(encoding="utf-8") if log_path.is_file() else _new_compaction_log(location, today)
    new_text = existing_text.rstrip("\n") + "\n" + "\n".join(new_rows) + "\n"
    atomic_write(log_path, new_text)

    written = log_path.read_text(encoding="utf-8")
    for identifier, digest in digests.items():
        if f"`{identifier}`" not in written or digest not in written:
            raise StoreError("COMPACTION_LOG_VERIFY_FAILED", log_path, identifier)

    for identifier in eligible:
        for path in _entry_paths(root, location, identifier):
            if path.is_file():
                path.unlink()


def command_prune_archive(root: Path, location: str) -> None:
    raw = _raw_entries(root, location)
    logged = _logged_entries(root, location)
    total = len(raw) + len(logged)
    if total <= PRUNE_ABOVE or not logged:
        return
    eligible = logged[: total - PRUNE_ABOVE]
    if not eligible:
        return
    log_path = _log_path(root, location)
    eligible_set = set(eligible)
    remaining = len(eligible)
    kept_lines = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^- `([^`]+)`", line)
        if match and match.group(1) in eligible_set and remaining > 0:
            remaining -= 1
            continue
        kept_lines.append(line)
    atomic_write(log_path, "\n".join(kept_lines) + "\n")


def command_check(root: Path) -> None:
    facts = load_facts(root)
    validate_facts(facts, root)
    verify_memory_index(root, facts)
    for name in ("Context", "Lessons"):
        path = root / ".agents" / f"{name}.md"
        data, _ = parse_frontmatter(path)
        missing = sorted(field for field in ANCHOR_FIELDS if not data.get(field))
        if missing:
            raise StoreError("MISSING_ANCHOR_FIELD", path, ",".join(missing))
        _, entries, _ = split_anchor(path.read_text(encoding="utf-8"))
        if len(path.read_bytes()) > LIMIT_BYTES and len(entries) <= KEEP_ENTRIES:
            raise StoreError("OVERSIZED_ACTIVE_WINDOW", path, f"{len(entries)} entries")
        check_archives(root, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "refresh-memory", "rotate-anchors", "archive-handoff", "archive-docs", "check-retention", "compact-archive", "prune-archive"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--timestamp", default=datetime.now().strftime("%Y%m%dT%H%M%S"))
    parser.add_argument("--location", choices=tuple(sorted(ARCHIVE_LOCATIONS)))
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command in ("compact-archive", "prune-archive") and not args.location:
        print(f"ERROR --location is required for {args.command}")
        return 2
    if args.command == "check" and not (root / ".agents/Memory.md").is_file() and not (root / ".agents/memory").is_dir():
        print("SKIP check (no .agents/Memory.md or .agents/memory/; public clone without governance store)")
        return 0
    try:
        facts = load_facts(root)
        validate_facts(facts, root)
        if args.command == "refresh-memory":
            atomic_write(root / ".agents/Memory.md", memory_text(root, facts))
        elif args.command == "rotate-anchors":
            rotate_one(root, "Context", args.timestamp)
            rotate_one(root, "Lessons", args.timestamp)
        elif args.command == "archive-handoff":
            command_archive_handoff(root, args.timestamp)
        elif args.command == "archive-docs":
            command_archive_docs(root, args.timestamp)
        elif args.command == "check-retention":
            command_check_retention(root)
            return 0
        elif args.command == "compact-archive":
            command_compact_archive(root, args.location)
        elif args.command == "prune-archive":
            command_prune_archive(root, args.location)
        else:
            command_check(root)
    except (OSError, StoreError) as error:
        if isinstance(error, StoreError):
            print(error)
        else:
            print(f"IO_ERROR {getattr(error, 'filename', root)} {error}")
        return 1
    print(f"OK {args.command}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
