#!/usr/bin/env python3
"""Resolve the newest validated handoff pair for a project root."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, time as clock_time
from pathlib import Path


PROMPT_RE = re.compile(r"^INITIAL-PROMPT-([A-Za-z0-9][A-Za-z0-9._-]*)\.txt$")
HANDOFF_RE = re.compile(r"^HANDOFF-([A-Za-z0-9][A-Za-z0-9._-]*)\.md$")
PAIRED_HANDOFF_RE = re.compile(
    r"^Paired handoff:[ \t]+(handoff/HANDOFF-[A-Za-z0-9][A-Za-z0-9._-]*\.md)[ \t]*$",
    re.MULTILINE,
)
PAIRED_HANDOFF_LABEL_RE = re.compile(r"^Paired handoff:", re.MULTILINE)
GOAL_RE = re.compile(r"^## Goal\s*$([\s\S]*?)(?=^##\s|\Z)", re.MULTILINE)
GOAL_LABELS = ("Session Goal", "Ultimate Goal", "Linkage")
FRONTMATTER_REQUIRED = ("title", "date", "updated", "type", "status", "tags")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PLAIN_NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$")
TAG_SCALAR_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
FRONTMATTER_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
BOOTSTRAP_RE = re.compile(r"^## Bootstrap Reading.*$([\s\S]*?)(?=^##\s|\Z)", re.MULTILINE)
BACKTICK_RE = re.compile(r"`([^`]+)`")
NEW_SUFFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})--(.+)$")
LEGACY_SUFFIX_RE = re.compile(r"^(.+)-(\d{4}-\d{2}-\d{2})-(\d{6})$")


class ResolutionError(Exception):
    pass


def suffix_stamp(suffix: str) -> tuple[str, str | None]:
    """Return (YYYY-MM-DD, HHMMSS or None) for `YYYY-MM-DD--slug` or `<prefix>-YYYY-MM-DD-HHMMSS`."""
    if match := NEW_SUFFIX_RE.fullmatch(suffix):
        day, clock = match.group(1), None
    elif match := LEGACY_SUFFIX_RE.fullmatch(suffix):
        day, clock = match.group(2), match.group(3)
    else:
        raise ResolutionError(
            f"handoff suffix matches neither YYYY-MM-DD--slug nor <prefix>-YYYY-MM-DD-HHMMSS: {suffix}; pass --initial-prompt explicitly"
        )
    try:
        date.fromisoformat(day)
        if clock is not None:
            clock_time(int(clock[:2]), int(clock[2:4]), int(clock[4:]))
    except ValueError as exc:
        raise ResolutionError(f"handoff suffix has an invalid date or time: {suffix}; pass --initial-prompt explicitly") from exc
    return day, clock


def newest_initial_prompt(candidates: list[Path]) -> Path:
    """Pick the chronologically newest prompt; refuse when the newest date cannot be ordered."""
    stamped = [(suffix_stamp(PROMPT_RE.fullmatch(path.name).group(1)), path) for path in candidates]
    stamped.sort(key=lambda item: (item[0][0], item[0][1] or "", item[1].name))
    (top_day, top_clock), top = stamped[-1]
    rivals = [path.name for (day, clock), path in stamped[:-1] if day == top_day and (top_clock is None or clock in (None, top_clock))]
    if rivals:
        names = ", ".join(sorted(rivals + [top.name]))
        raise ResolutionError(f"cannot order handoffs dated {top_day} without HHMMSS: {names}; pass --initial-prompt explicitly")
    return top


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ResolutionError(f"cannot read {path}: {exc}") from exc


def ensure_within_root(root: Path, candidate: Path) -> Path:
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ResolutionError(f"path escapes project root: {candidate}") from exc
    return resolved


def goal_block(text: str, label: str) -> str:
    matches = list(GOAL_RE.finditer(text))
    if not matches:
        raise ResolutionError(f"missing ## Goal block in {label}")
    if len(matches) != 1:
        raise ResolutionError(f"expected exactly one ## Goal block in {label}")
    block = matches[0].group(1).strip().replace("\r\n", "\n")
    if not block:
        raise ResolutionError(f"empty ## Goal block in {label}")
    for field in GOAL_LABELS:
        pattern = re.compile(rf"^- \*\*{re.escape(field)}:\*\*[ \t]+(.+)$", re.MULTILINE)
        values = pattern.findall(block)
        if len(values) != 1 or not values[0].strip():
            raise ResolutionError(f"missing or duplicate {field} in {label}")
    return block


def yaml_text_scalar(raw_value: str) -> str | None:
    value = raw_value.strip()
    if not value or value.startswith("#"):
        return None
    quoted = value[0] in {"\"", "'"}
    if quoted:
        quote = value[0]
        if len(value) < 2 or value[-1] != quote:
            return None
        value = value[1:-1].strip()
        # Accept a deliberately strict YAML quoted-scalar subset: no escapes or nested quote marks.
        if "\\" in value or quote in value:
            return None
    else:
        value = value.split(" #", 1)[0].strip()
        if re.search(r":[ \t]", value):
            return None
    if not value or value.lower() in {"null", "~"}:
        return None
    if not quoted:
        if value[0] in "-?:,[]{}&*!|>%@`" or "\t" in value:
            return None
        if value.lower() in {"true", "false", "yes", "no", "on", "off"}:
            return None
        if PLAIN_NUMBER_RE.fullmatch(value):
            return None
    return value


def valid_tag_scalar(raw_value: str) -> bool:
    value = yaml_text_scalar(raw_value)
    return value is not None and bool(TAG_SCALAR_RE.fullmatch(value))


def valid_inline_tags(raw_value: str) -> bool:
    value = raw_value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return False
    body = value[1:-1].strip()
    if not body:
        return False
    items = [item.strip() for item in body.split(",")]
    return all(valid_tag_scalar(item) for item in items)


def validate_handoff_frontmatter(text: str, label: str) -> None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ResolutionError(f"missing YAML frontmatter in {label}")
    try:
        end = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration as exc:
        raise ResolutionError(f"unclosed YAML frontmatter in {label}") from exc

    values: dict[str, str] = {}
    tag_items: list[str] = []
    invalid_tag_item = False
    active_key: str | None = None
    for raw_line in lines[1:end]:
        if raw_line.startswith((" ", "\t")):
            item = raw_line.strip()
            if not item or item.startswith("#"):
                continue
            if active_key == "tags":
                inline_parent = values.get("tags", "").split(" #", 1)[0].strip()
                if inline_parent or not item.startswith("-") or not valid_tag_scalar(item[1:]):
                    invalid_tag_item = True
                else:
                    tag_items.append(yaml_text_scalar(item[1:]) or "")
                continue
            raise ResolutionError(f"invalid YAML frontmatter in {label}")
        active_key = None
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if ":" not in raw_line:
            raise ResolutionError(f"invalid YAML frontmatter in {label}")
        key, value = raw_line.split(":", 1)
        key = key.strip()
        if not FRONTMATTER_KEY_RE.fullmatch(key):
            raise ResolutionError(f"invalid YAML frontmatter in {label}")
        if key in values:
            raise ResolutionError(f"duplicate frontmatter property {key} in {label}")
        values[key] = value.strip()
        active_key = key

    missing = [key for key in FRONTMATTER_REQUIRED if key not in values]
    if missing:
        raise ResolutionError(f"missing frontmatter properties in {label}: {', '.join(missing)}")
    for key, raw_value in values.items():
        if key not in FRONTMATTER_REQUIRED and raw_value and yaml_text_scalar(raw_value) is None:
            raise ResolutionError(f"invalid YAML frontmatter in {label}")
    for key in ("title", "type", "status"):
        if yaml_text_scalar(values[key]) is None:
            raise ResolutionError(f"empty frontmatter property {key} in {label}")
    for key in ("date", "updated"):
        value = yaml_text_scalar(values[key])
        if value is None or not ISO_DATE_RE.fullmatch(value):
            raise ResolutionError(f"invalid {key} in {label}: {values[key]}")
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ResolutionError(f"invalid {key} in {label}: {values[key]}") from exc
    inline_list = valid_inline_tags(values["tags"])
    if invalid_tag_item or (not tag_items and not inline_list):
        raise ResolutionError(f"tags must be a non-empty YAML list in {label}")


def bootstrap_paths(initial_text: str, root: Path) -> list[str]:
    section = BOOTSTRAP_RE.search(initial_text)
    if not section:
        return []
    paths: list[str] = []
    for line in section.group(1).splitlines():
        if "lazy-on-demand" in line.lower() or "optional:" in line.lower():
            continue
        for token in BACKTICK_RE.findall(line):
            candidate = Path(token)
            if candidate.is_absolute() or ".." in candidate.parts:
                raise ResolutionError(f"unsafe bootstrap path: {token}")
            resolved = ensure_within_root(root, root / candidate)
            if token.endswith("/"):
                if not resolved.is_dir():
                    raise ResolutionError(f"missing mandatory bootstrap directory: {token}")
                continue  # safe existing directory shorthand is not returned as a file
            if "/" in token or candidate.suffix:
                resolved = ensure_within_root(root, root / candidate)
                if not resolved.is_file():
                    raise ResolutionError(f"missing mandatory bootstrap file: {token}")
                paths.append(token)
    return list(dict.fromkeys(paths))


def select_initial(root: Path, handoff_dir: Path, initial_prompt: Path | None) -> Path:
    if initial_prompt is None:
        candidates: list[Path] = []
        for path in handoff_dir.iterdir():
            if not path.is_file() or not PROMPT_RE.fullmatch(path.name):
                continue
            ensure_within_root(root, path)
            if path.is_symlink():
                raise ResolutionError(f"initial prompt must not be a symlink: {path}")
            candidates.append(path)
        if not candidates:
            raise ResolutionError("no handoff/INITIAL-PROMPT-*.txt package found")
        return newest_initial_prompt(candidates)

    if initial_prompt.is_absolute() or ".." in initial_prompt.parts:
        raise ResolutionError(f"unsafe initial prompt path: {initial_prompt}")
    initial = root / initial_prompt
    ensure_within_root(root, initial)
    if initial.is_symlink():
        raise ResolutionError(f"initial prompt must not be a symlink: {initial}")
    if initial.parent != handoff_dir or not initial.is_file() or not PROMPT_RE.fullmatch(initial.name):
        raise ResolutionError(f"missing or malformed initial prompt: {initial}")
    return initial


def resolve(root: Path, initial_prompt: Path | None = None) -> dict[str, object]:
    root = root.resolve()
    handoff_dir = root / "handoff"
    if not handoff_dir.is_dir():
        raise ResolutionError(f"missing handoff directory: {handoff_dir}")
    initial = select_initial(root, handoff_dir, initial_prompt)
    suffix = PROMPT_RE.fullmatch(initial.name).group(1)
    initial_text = read_text(initial)
    explicit = PAIRED_HANDOFF_RE.findall(initial_text)
    labels = PAIRED_HANDOFF_LABEL_RE.findall(initial_text)
    if len(labels) != len(explicit):
        raise ResolutionError("malformed paired handoff field")
    if len(explicit) > 1:
        raise ResolutionError("initial prompt declares more than one paired handoff")
    handoff = root / explicit[0] if explicit else handoff_dir / f"HANDOFF-{suffix}.md"
    ensure_within_root(root, handoff)
    if handoff.is_symlink():
        raise ResolutionError(f"paired handoff must not be a symlink: {handoff}")
    match = HANDOFF_RE.fullmatch(handoff.name)
    if handoff.parent != handoff_dir or not handoff.is_file() or not match:
        raise ResolutionError(f"missing or malformed paired handoff: {handoff}")
    if match.group(1) != suffix:
        raise ResolutionError("paired handoff suffix does not match initial prompt")
    handoff_text = read_text(handoff)
    validate_handoff_frontmatter(handoff_text, str(handoff.relative_to(root)))
    if goal_block(initial_text, str(initial.relative_to(root))) != goal_block(handoff_text, str(handoff.relative_to(root))):
        raise ResolutionError("paired ## Goal blocks do not match exactly")
    return {
        "root": str(root),
        "initial_prompt": str(initial),
        "handoff": str(handoff),
        "timestamp_suffix": suffix,
        "goal_match": True,
        "bootstrap_files": bootstrap_paths(initial_text, root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="project root containing handoff/")
    parser.add_argument(
        "--initial-prompt",
        type=Path,
        help="root-relative handoff/INITIAL-PROMPT-<suffix>.txt to validate; default: latest",
    )
    args = parser.parse_args()
    try:
        result = resolve(Path(args.root), args.initial_prompt)
    except ResolutionError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
