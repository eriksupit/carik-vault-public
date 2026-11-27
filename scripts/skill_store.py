#!/usr/bin/env python3
"""Validate, compare, and publish Agent Skill directories without dependencies."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_DESCRIPTION_LENGTH = 1024
IDENTITY_FILES = ("app.json", "appearance.json", "core-plugins.json")


class SkillValidationError(ValueError):
    pass


@dataclass(frozen=True)
class SkillMetadata:
    name: str
    description: str


@dataclass(frozen=True)
class Diagnostic:
    level: str
    code: str
    path: Path
    message: str


@dataclass(frozen=True)
class SkillRecord:
    name: str
    directory: Path
    metadata: SkillMetadata
    digest: str
    live_digest: str
    owner: str


def _decode_quoted(value: str, path: Path) -> str:
    try:
        if value.startswith('"'):
            parsed = json.loads(value)
        else:
            if not value.endswith("'"):
                raise ValueError("unterminated single-quoted scalar")
            parsed = value[1:-1].replace("''", "'")
    except (ValueError, json.JSONDecodeError) as error:
        raise SkillValidationError(f"{path}: malformed quoted scalar: {error}") from error
    if not isinstance(parsed, str):
        raise SkillValidationError(f"{path}: routing field must be a string")
    return parsed


def _scalar(lines: list[str], index: int, raw: str, path: Path, field: str) -> tuple[str, int]:
    value = raw.strip()
    if value in {">", ">-", ">+", "|", "|-", "|+"}:
        chunks: list[str] = []
        cursor = index + 1
        while cursor < len(lines) and (lines[cursor].startswith((" ", "\t")) or not lines[cursor].strip()):
            line = lines[cursor]
            chunks.append(line[2:] if line.startswith("  ") else line.lstrip("\t"))
            cursor += 1
        if not chunks:
            raise SkillValidationError(f"{path}: {field} block scalar is empty")
        if value.startswith(">"):
            parsed = " ".join(part.strip() for part in chunks if part.strip())
        else:
            parsed = "\n".join(chunks)
        return parsed.rstrip("\n") if value.endswith("-") else parsed, cursor
    if not value:
        raise SkillValidationError(f"{path}: {field} is empty")
    if value.startswith(("'", '"')):
        return _decode_quoted(value, path), index + 1
    if ": " in value:
        raise SkillValidationError(f"{path}: plain {field} contains an unquoted ': ' sequence")
    if " #" in value:
        raise SkillValidationError(f"{path}: plain {field} contains an unquoted comment")
    return value, index + 1


def parse_skill_metadata(path: Path) -> SkillMetadata:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise SkillValidationError(f"{path}: missing opening frontmatter delimiter")
    try:
        close = lines.index("---", 1)
    except ValueError as error:
        raise SkillValidationError(f"{path}: missing closing frontmatter delimiter") from error
    frontmatter = lines[1:close]
    fields: dict[str, str] = {}
    index = 0
    while index < len(frontmatter):
        line = frontmatter[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if line.startswith((" ", "\t")):
            index += 1
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):(?:\s*(.*))?$", line)
        if not match:
            raise SkillValidationError(f"{path}: malformed frontmatter line {index + 2}: {line}")
        key, raw = match.group(1), match.group(2) or ""
        if key in {"name", "description"}:
            if key in fields:
                raise SkillValidationError(f"{path}: duplicate {key} field")
            fields[key], index = _scalar(frontmatter, index, raw, path, key)
        else:
            index += 1
    name = fields.get("name", "").strip()
    description = fields.get("description", "").strip()
    if not name:
        raise SkillValidationError(f"{path}: name is required")
    if not NAME_PATTERN.fullmatch(name):
        raise SkillValidationError(f"{path}: name must use lowercase letters, numbers, and single hyphens")
    if len(name) > 64:
        raise SkillValidationError(f"{path}: name exceeds 64 characters")
    if name != path.parent.name:
        raise SkillValidationError(f'{path}: name "{name}" does not match parent directory "{path.parent.name}"')
    if not description:
        raise SkillValidationError(f"{path}: description is required")
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise SkillValidationError(f"{path}: description exceeds 1024 characters ({len(description)})")
    return SkillMetadata(name=name, description=description)


def is_runtime_artifact(directory: Path, path: Path) -> bool:
    relative = path.relative_to(directory)
    return (
        "__pycache__" in relative.parts
        or path.suffix == ".pyc"
        or path.name == ".DS_Store"
    )


def implementation_digest(directory: Path, live_data: tuple[str, ...] = ()) -> str:
    excluded = set(live_data)
    for relative in excluded:
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts or any(char in relative for char in "*?[]"):
            raise SkillValidationError(f"invalid live_data path: {relative}")
    digest = hashlib.sha256()
    for path in sorted(
        p for p in directory.rglob("*") if p.is_file() and not is_runtime_artifact(directory, p)
    ):
        relative_text = path.relative_to(directory).as_posix()
        if relative_text in excluded:
            continue
        relative = relative_text.encode("utf-8")
        data = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def directory_digest(directory: Path) -> str:
    return implementation_digest(directory)


def live_data_digest(directory: Path, live_data: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for relative_text in sorted(live_data):
        path = directory / relative_text
        relative = relative_text.encode("utf-8")
        data = path.read_bytes() if path.is_file() else b"<missing>"
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def store_role(root: Path) -> str:
    init_skill = root / ".agents" / "skills" / "file-over-app-init" / "SKILL.md"
    return "harness" if init_skill.is_file() else "generated"


def require_harness_role(root: Path) -> None:
    if store_role(root) != "harness":
        raise SkillValidationError("publication must run from the canonical harness, not a generated snapshot")


def load_manifest(path: Path) -> dict[str, object]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SkillValidationError(f"{path}: invalid manifest: {error}") from error
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("harness_owned"), dict):
        raise SkillValidationError(f"{path}: unsupported manifest structure")
    return manifest


def _declared_owner(name: str, source_owner: str, manifest: dict[str, object]) -> str:
    harness = manifest.get("harness_owned", {})
    global_only = set(manifest.get("global_only", []))
    retired = set(manifest.get("retired", []))
    if name in retired:
        return "retired"
    if name in harness:
        return "harness" if source_owner == "harness" else "harness-mirror"
    if name in global_only:
        if source_owner == "harness":
            raise SkillValidationError(f"global-only skill {name} must not exist in harness store")
        return "global-only"
    if source_owner == "harness":
        raise SkillValidationError(f"undeclared harness skill: {name}")
    return "global-unmanaged"


def scan_store(store: Path, owner: str, manifest: dict[str, object]) -> list[SkillRecord]:
    records: list[SkillRecord] = []
    try:
        if not store.is_dir():
            return records
        entries = sorted(p for p in store.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())
    except (PermissionError, OSError):
        return records
    retired = set(manifest.get("retired", []))
    for directory in entries:
        if directory.name in retired:
            metadata = SkillMetadata(directory.name, "retired active directory")
            records.append(SkillRecord(
                directory.name,
                directory,
                metadata,
                directory_digest(directory),
                live_data_digest(directory, ()),
                "retired",
            ))
            continue
        metadata = parse_skill_metadata(directory / "SKILL.md")
        declared = _declared_owner(metadata.name, owner, manifest)
        rule = manifest.get("harness_owned", {}).get(metadata.name, {})
        live_data = tuple(rule.get("live_data", [])) if isinstance(rule, dict) else ()
        records.append(SkillRecord(
            metadata.name,
            directory,
            metadata,
            implementation_digest(directory, live_data),
            live_data_digest(directory, live_data),
            declared,
        ))
    return records


def _publishes(name: str, manifest: dict[str, object]) -> bool:
    """Does THIS vault publish `name` into the user-global stores?"""
    rule = manifest.get("harness_owned", {}).get(name, {})
    return isinstance(rule, dict) and rule.get("publish_user") is True


def classify_merged(project: list[SkillRecord], user: list[SkillRecord], manifest: dict[str, object]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    retired = set(manifest.get("retired", []))
    combined: dict[str, list[SkillRecord]] = {}
    for record in project + user:
        combined.setdefault(record.name, []).append(record)
        if record.name in retired:
            diagnostics.append(Diagnostic("error", "retired-active-skill", record.directory, f"retired skill is active: {record.name}"))
    for name, records in sorted(combined.items()):
        if name in retired:
            continue
        if len(records) < 2:
            continue
        first = records[0]
        for other in records[1:]:
            if first.digest == other.digest:
                diagnostics.append(Diagnostic("info", "identical-mirror", other.directory, f"{name} has identical immutable implementation"))
                if first.live_digest != other.live_digest:
                    diagnostics.append(Diagnostic("info", "live-data-divergence", other.directory, f"{name} has different declared live data"))
            elif _publishes(name, manifest):
                diagnostics.append(Diagnostic("error", "divergent-collision", other.directory, f"{name} differs from {first.directory}"))
            else:
                diagnostics.append(Diagnostic(
                    "info", "unpublished-divergence", other.directory,
                    f"{name} differs from {first.directory} (not published to user stores by this vault; ignoring)",
                ))
    return diagnostics


def validate_vault_target(root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for name in IDENTITY_FILES:
        path = root / ".obsidian" / name
        if not path.is_file():
            diagnostics.append(Diagnostic("error", "missing-vault-identity", path, "required Obsidian identity file is missing"))
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            diagnostics.append(Diagnostic("error", "invalid-vault-identity", path, str(error)))
            continue
        if not isinstance(value, dict):
            diagnostics.append(Diagnostic("error", "invalid-vault-identity", path, "identity JSON must contain an object"))
    return diagnostics


def _relative_files(directory: Path) -> dict[str, bytes]:
    return {
        p.relative_to(directory).as_posix(): p.read_bytes()
        for p in directory.rglob("*")
        if p.is_file() and not is_runtime_artifact(directory, p)
    }


def _resolve_publication_destination(destination: Path, source: Path, apply: bool) -> Path | None:
    """Publication must never dereference a symlink into a physical copy.

    A link already resolving to the source needs no publication; a link to another
    directory is written through, leaving the link itself intact; a dangling link is
    removed before a real directory takes its place. Returns None when there is
    nothing to publish.

    A destination that does not exist yet is a physical directory by design, because
    this function serves the store where skill content actually lives. A runtime
    discovery tree that holds links instead of content is NOT that store: publish to
    it with `ensure_runtime_link`, never with `publish_directory`.
    """
    if not destination.is_symlink():
        return destination
    resolved = destination.resolve()
    if not resolved.exists():
        if apply:
            destination.unlink()
        return destination
    if resolved == source.resolve():
        return None
    if not resolved.is_dir():
        raise SkillValidationError(
            f"publication destination {destination} links to a non-directory: {resolved}"
        )
    return resolved


def publish_directory(source: Path, destination: Path, live_data: tuple[str, ...], apply: bool) -> list[str]:
    resolved_destination = _resolve_publication_destination(destination, source, apply)
    if resolved_destination is None:
        return []
    destination = resolved_destination
    source_files = _relative_files(source)
    destination_files = _relative_files(destination) if destination.is_dir() else {}
    preserved_names = {name for name in live_data if name in destination_files}
    changes = sorted(
        name
        for name in source_files.keys() | destination_files.keys()
        if name not in preserved_names and source_files.get(name) != destination_files.get(name)
    )
    if not apply or not changes:
        return changes
    preserved = {name: destination_files[name] for name in live_data if name in destination_files}
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup_root = destination.parent.parent / ".skill-sync-backups"
    with tempfile.TemporaryDirectory(prefix=f".{destination.name}-publish-") as temporary:
        staged = Path(temporary) / destination.name
        shutil.copytree(
            source,
            staged,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )
        for name, data in preserved.items():
            path = staged / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        parse_skill_metadata(staged / "SKILL.md")
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = backup_root / destination.name
        if backup.exists():
            shutil.rmtree(backup)
        if destination.exists():
            backup_root.mkdir(parents=True, exist_ok=True)
            destination.rename(backup)
        try:
            shutil.copytree(staged, destination)
        except Exception:
            if destination.exists():
                shutil.rmtree(destination)
            if backup.exists():
                backup.rename(destination)
            raise
    return changes


def ensure_runtime_link(link: Path, target: Path, apply: bool) -> list[str]:
    """A runtime discovery tree holds links, never copies.

    `~/.claude/skills/<name>` exists so a runtime can find a skill whose content
    lives exactly once, under `~/.agents/skills/<name>`. Publishing a copy there is
    what reintroduces the physical duplication the store is built to avoid, so this
    ensures a relative link instead. A physical directory already standing in the
    link's place is converted only when it is byte-identical to the target, and is
    never deleted when it is not.
    """
    relative = os.path.relpath(target.resolve(), link.parent.resolve())
    if link.is_symlink():
        resolved = link.resolve()
        if resolved.exists() and resolved == target.resolve():
            return []
    elif link.exists():
        if not link.is_dir():
            raise SkillValidationError(f"runtime link path {link} is occupied by a file")
        if directory_digest(link) != directory_digest(target):
            raise SkillValidationError(
                f"runtime link path {link} holds a physical directory that differs from {target}"
            )
    change = [f"{link.name} -> {relative}"]
    if not apply:
        return change
    if link.is_symlink() or link.is_file():
        link.unlink()
    elif link.is_dir():
        shutil.rmtree(link)
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(relative, target_is_directory=True)
    return change
