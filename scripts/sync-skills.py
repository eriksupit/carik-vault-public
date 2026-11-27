#!/usr/bin/env python3
"""Validate and publish this vault's canonical portable skill store."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from skill_store import (
    Diagnostic,
    SkillValidationError,
    classify_merged,
    ensure_runtime_link,
    load_manifest,
    publish_directory,
    scan_store,
    validate_vault_target,
    require_harness_role,
)

BEGIN = "# >>> file-over-app-harness vault skills (managed by sync-skills.py — do not edit) >>>"
END = "# <<< file-over-app-harness vault skills <<<"


def vault_root() -> Path:
    return Path(__file__).resolve().parent.parent


def manifest_path(root: Path) -> Path:
    return root / ".agents" / "skills" / "manifest.json"


def build_codex_block(skill_paths: list[Path], disabled: set[str] = frozenset()) -> str:
    lines = [BEGIN]
    seen: set[Path] = set()
    for path in sorted(skill_paths):
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        state = "false" if resolved.parent.name in disabled else "true"
        lines.extend(("[[skills.config]]", f'path = "{resolved}"', f"enabled = {state}", ""))
    lines.append(END)
    return "\n".join(lines)


SKILL_STANZA_NAME = re.compile(r"""^path\s*=\s*["'].*/\.agents/skills/([^/]+)/SKILL\.md["']\s*$""")


def strip_managed_block(text: str) -> str:
    if BEGIN not in text:
        return text.rstrip("\n")
    head, _, rest = text.partition(BEGIN)
    _, separator, tail = rest.partition(END)
    if not separator:
        raise ValueError("Codex config contains an unterminated managed skill block")
    return (head.rstrip("\n") + "\n" + tail.lstrip("\n")).rstrip("\n")


def drop_unmanaged_stanzas(text: str, owned: set[str]) -> str:
    """Remove loose `[[skills.config]]` stanzas for skills the managed block owns.

    A config written before the managed block existed registers skills as bare
    stanzas. Appending the block without removing those leaves two registrations
    under one name, and the runtime resolves the skill to whichever it reads
    first — so the duplicate is worse than the stale pointer it was meant to
    replace. A stanza for a name this vault does not own is left alone: it
    belongs to another vault and is not ours to unregister.
    """
    lines = text.split("\n")
    kept: list[str] = []
    index = 0
    while index < len(lines):
        if lines[index].strip() != "[[skills.config]]":
            kept.append(lines[index])
            index += 1
            continue
        end = index + 1
        while end < len(lines) and not lines[end].lstrip().startswith("["):
            end += 1
        stanza = lines[index:end]
        names = [
            match.group(1)
            for match in (SKILL_STANZA_NAME.match(line.strip()) for line in stanza)
            if match
        ]
        if not any(name in owned for name in names):
            kept.extend(stanza)
        index = end
    return "\n".join(kept).rstrip("\n")


def disabled_skills(text: str) -> set[str]:
    """Skill names the incoming config has switched off for this runtime.

    A name counts as disabled only when EVERY stanza declaring it says
    `enabled = false`; one enabled registration means the owner wants it on.
    Carrying this forward matters because the managed block rewrites the
    stanzas, and re-enabling a skill the owner turned off is a behaviour change
    that hides inside a diff full of relocated entries.
    """
    states: dict[str, list[bool]] = {}
    current: str | None = None
    for raw in text.split("\n"):
        line = raw.strip()
        match = SKILL_STANZA_NAME.match(line)
        if match:
            current = match.group(1)
        elif line.startswith("enabled") and current is not None:
            states.setdefault(current, []).append(line.split("=", 1)[1].strip() == "true")
            current = None
    return {name for name, flags in states.items() if flags and not any(flags)}


def apply_codex_block(text: str, skill_paths: list[Path]) -> str:
    owned = {path.parent.name for path in skill_paths}
    disabled = disabled_skills(text) & owned
    base = drop_unmanaged_stanzas(strip_managed_block(text), owned)
    return base + "\n\n" + build_codex_block(skill_paths, disabled) + "\n"


def print_diagnostics(diagnostics) -> int:
    errors = 0
    for item in diagnostics:
        print(f"{item.level.upper()} {item.code}: {item.path}: {item.message}")
        errors += item.level == "error"
    return errors


DESCRIPTION_BUDGET = 400


def description_budget_errors(root: Path) -> int:
    """A skill whose frontmatter description exceeds a harness catalog's metadata budget is
    dropped from that catalog silently — the SKILL.md stays on disk, but the skill never
    fires. Observed threshold on one harness was ~505 chars; 400 keeps a margin. Full trigger
    text belongs in the body under `## Trigger reference`, not in the description."""
    errors = 0
    for path in sorted((root / ".agents" / "skills").glob("*/SKILL.md")):
        frontmatter = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
        if not frontmatter:
            continue
        field = re.search(
            r"^description:\s*(.*?)(?=\n[A-Za-z_][A-Za-z0-9_]*:|\Z)", frontmatter.group(1), re.S | re.M
        )
        if not field:
            continue
        value = re.sub(r"\s+", " ", re.sub(r"^\s*[>|][-+]?\s*", "", field.group(1))).strip()
        if len(value) > DESCRIPTION_BUDGET:
            print(
                f"ERROR description-budget: {path}: description is {len(value)} chars, "
                f"budget is {DESCRIPTION_BUDGET} — move the surplus to `## Trigger reference`"
            )
            errors += 1
    return errors


def check(
    root: Path,
    user_store: Path,
    claude_store: Path,
    canonical_root: Path | None = None,
) -> int:
    manifest = load_manifest(manifest_path(root))
    canonical = canonical_root
    try:
        project = scan_store(root / ".agents" / "skills", "harness", manifest)
        user = scan_store(user_store, "global", manifest)
        claude = scan_store(claude_store, "global", manifest)
        canonical_records = []
        canonical_diagnostics = []
        comparison_manifest = manifest
        if canonical is not None:
            require_harness_role(canonical)
            canonical_manifest = load_manifest(manifest_path(canonical))
            canonical_records = scan_store(canonical / ".agents" / "skills", "harness", canonical_manifest)
            comparison_manifest = {
                **manifest,
                "harness_owned": {
                    **manifest["harness_owned"],
                    **canonical_manifest["harness_owned"],
                },
                "retired": sorted(set(manifest.get("retired", [])) | set(canonical_manifest.get("retired", []))),
            }
            project_by_name = {record.name: record for record in project}
            canonical_by_name = {record.name: record for record in canonical_records}
            expected_names = {
                name
                for name, rule in canonical_manifest["harness_owned"].items()
                if rule.get("generated") == "universal"
                or (rule.get("generated") == "profile" and name in project_by_name)
            }
            for name, rule in sorted(canonical_manifest["harness_owned"].items()):
                if rule.get("generated") == "never" and name in project_by_name:
                    canonical_diagnostics.append(Diagnostic(
                        "error",
                        "harness-only-skill",
                        project_by_name[name].directory,
                        f"generated vault contains harness-only canonical skill: {name}",
                    ))
            for name in sorted(expected_names):
                canonical_record = canonical_by_name.get(name)
                project_record = project_by_name.get(name)
                if canonical_record is None:
                    raise SkillValidationError(f"canonical manifest declares missing skill: {name}")
                if project_record is None:
                    canonical_diagnostics.append(Diagnostic(
                        "error",
                        "missing-canonical-skill",
                        root / ".agents" / "skills" / name,
                        f"generated vault is missing canonical skill: {name}",
                    ))
                elif project_record.digest != canonical_record.digest:
                    canonical_diagnostics.append(Diagnostic(
                        "error",
                        "canonical-divergence",
                        project_record.directory,
                        f"{name} differs from canonical owner {canonical_record.directory}",
                    ))
    except SkillValidationError as error:
        print(f"ERROR invalid-skill: {error}")
        return 1
    diagnostics = canonical_diagnostics + classify_merged(project, [*user, *claude], comparison_manifest)
    errors = print_diagnostics(diagnostics)
    errors += description_budget_errors(root)
    canonical_suffix = f" canonical={canonical}" if canonical is not None else ""
    print(
        f"CHECK project={len(project)} canonical={len(canonical_records)} "
        f"user={len(user)} claude={len(claude)} errors={errors}{canonical_suffix}"
    )
    return 1 if errors else 0


def publish_user(
    root: Path,
    user_store: Path,
    claude_store: Path,
    apply: bool,
    selected_names: frozenset[str] | None = None,
) -> int:
    require_harness_role(root)
    manifest = load_manifest(manifest_path(root))
    project_store = root / ".agents" / "skills"
    scan_store(project_store, "harness", manifest)
    eligible = {
        name for name, rule in manifest["harness_owned"].items() if rule.get("publish_user") is True
    } | set(manifest.get("global_only", []))
    unknown = (selected_names or frozenset()) - eligible
    if unknown:
        raise SkillValidationError(f"skills not eligible for user publication: {', '.join(sorted(unknown))}")
    copies: list[tuple[Path, Path, tuple[str, ...]]] = []
    links: list[tuple[Path, Path]] = []
    for name, rule in sorted(manifest["harness_owned"].items()):
        if rule.get("publish_user") is True and (selected_names is None or name in selected_names):
            copies.append((project_store / name, user_store / name, tuple(rule.get("live_data", []))))
            links.append((claude_store / name, user_store / name))
    for name in manifest.get("global_only", []):
        if selected_names is not None and name not in selected_names:
            continue
        if (user_store / name).is_dir():
            links.append((claude_store / name, user_store / name))
    mode = "APPLY" if apply else "PREVIEW"
    print(f"{mode} publish-user operations={len(copies) + len(links)}")
    for source, destination, live_data in copies:
        changes = publish_directory(source, destination, live_data, apply=apply)
        if changes:
            print(f"  {source} -> {destination}: {len(changes)} changed file(s)")
            for relative in changes:
                print(f"    - {relative}")
    for link, target in links:
        for change in ensure_runtime_link(link, target, apply=apply):
            print(f"  link {link.parent}: {change}")
    return 0


def update_vault(
    root: Path,
    target: Path,
    apply: bool,
    preserve_target_metadata: bool = False,
    selected_names: frozenset[str] | None = None,
) -> int:
    require_harness_role(root)
    identity_errors = validate_vault_target(target)
    if identity_errors:
        return 1 if print_diagnostics(identity_errors) else 0
    manifest = load_manifest(manifest_path(root))
    target_store = target / ".agents" / "skills"
    existing = {p.name for p in target_store.iterdir() if p.is_dir()} if target_store.is_dir() else set()
    selected: list[tuple[str, dict]] = []
    for name, rule in sorted(manifest["harness_owned"].items()):
        distribution = rule.get("generated")
        if distribution == "universal" or (distribution == "profile" and name in existing):
            if selected_names is None or name in selected_names:
                selected.append((name, rule))
    eligible = {name for name, _ in selected}
    unknown = (selected_names or frozenset()) - eligible
    if unknown:
        raise SkillValidationError(f"skills not eligible for target update: {', '.join(sorted(unknown))}")
    mode = "APPLY" if apply else "PREVIEW"
    metadata_mode = "preserve-target" if preserve_target_metadata else "replace-from-source"
    print(f"{mode} update-vault target={target} skills={len(selected)} metadata={metadata_mode}")
    for name, rule in selected:
        source = root / ".agents" / "skills" / name
        destination = target_store / name
        changes = publish_directory(source, destination, tuple(rule.get("live_data", [])), apply=apply)
        if changes:
            print(f"  {name}: {len(changes)} changed file(s)")
    if apply and not preserve_target_metadata:
        for store_file in ("README.md", "manifest.json"):
            (target_store / store_file).write_bytes((root / ".agents" / "skills" / store_file).read_bytes())
    return 0


def codex_paths(root: Path, user_store: Path) -> list[Path]:
    manifest = load_manifest(manifest_path(root))
    paths = [user_store / name / "SKILL.md" for name, rule in manifest["harness_owned"].items() if rule.get("publish_user")]
    paths.extend(user_store / name / "SKILL.md" for name in manifest.get("global_only", []) if (user_store / name / "SKILL.md").is_file())
    return paths


def write_codex(config: Path, paths: list[Path], apply: bool) -> int:
    missing = [path for path in paths if not path.is_file()]
    if missing:
        print("ERROR Codex skill paths do not exist:")
        for path in missing:
            print(f"  - {path}")
        return 1
    if not config.is_file():
        print(f"ERROR codex config not found: {config}")
        return 1
    current = config.read_text(encoding="utf-8")
    result = apply_codex_block(current, paths)
    print(("APPLY" if apply else "PREVIEW") + f" codex paths={len(paths)} config={config}")
    if apply:
        config.with_suffix(config.suffix + ".sync-skills.bak").write_text(current, encoding="utf-8")
        config.write_text(result, encoding="utf-8")
    return 0


def wire_project(root: Path, apply: bool) -> int:
    """Remove obsolete project-local Claude skill and command adapters.

    Canonical skills and commands live only under `.agents/`. Managed directory
    symlinks and the older per-entry link directories are removable. Any foreign
    content is reported and left untouched.
    """
    removals: list[tuple[Path, int]] = []
    conflicts: list[tuple[Path, str]] = []

    for name in ("skills", "commands"):
        source = root / ".agents" / name
        adapter = root / ".claude" / name
        if adapter.is_symlink():
            if source.is_dir() and adapter.resolve() == source.resolve():
                removals.append((adapter, 1))
            else:
                conflicts.append((adapter, f"links to {adapter.resolve()} instead of {source}"))
        elif adapter.is_dir():
            entries = [path for path in adapter.iterdir() if not path.name.startswith(".")]
            stray = [
                path.name
                for path in entries
                if not (path.is_symlink() and path.resolve() == (source / path.name).resolve())
            ]
            if stray:
                conflicts.append(
                    (adapter, "holds entries this script did not create: " + ", ".join(sorted(stray)[:5]))
                )
            else:
                removals.append((adapter, len(entries)))
        elif adapter.exists():
            conflicts.append((adapter, "occupied by a file"))

    mode = "APPLY" if apply else "PREVIEW"
    print(f"{mode} wire-project remove={len(removals)} conflicts={len(conflicts)}")
    for path, count in removals:
        print(f"  remove {path} ({count} managed link(s))")
        if apply:
            if path.is_symlink():
                path.unlink()
            else:
                for entry in path.iterdir():
                    entry.unlink()
                path.rmdir()
    for path, why in conflicts:
        print(f"ERROR wiring-conflict: {path}: {why}")
    return 1 if conflicts else 0


def self_test() -> int:
    paths = [Path("/tmp/a/SKILL.md"), Path("/tmp/b/SKILL.md")]
    sample = '[[skills.config]]\npath = "/keep/SKILL.md"\nenabled = false\n'
    once = apply_codex_block(sample, paths)
    assert apply_codex_block(once, paths) == once
    assert strip_managed_block(once).strip() == sample.strip()
    print("SELF-TEST PASSED")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true")
    action.add_argument("--publish-user", action="store_true")
    action.add_argument("--update-vault", type=Path)
    action.add_argument("--self-test", action="store_true")
    action.add_argument(
        "--wire-project",
        action="store_true",
        help="remove obsolete project-local .claude/skills and .claude/commands adapters",
    )
    parser.add_argument(
        "--skill",
        action="append",
        default=[],
        metavar="NAME",
        help="limit publication or target update to this skill; repeat for multiple skills",
    )
    parser.add_argument(
        "--preserve-target-metadata",
        action="store_true",
        help="with --update-vault, update skill directories without replacing target README.md or manifest.json",
    )
    parser.add_argument("--apply", action="store_true", help="authorize file publication")
    parser.add_argument("--apply-codex", action="store_true", help="authorize Codex config mutation")
    parser.add_argument("--codex-config", type=Path, default=Path.home() / ".codex" / "config.toml")
    parser.add_argument(
        "--canonical-root",
        type=Path,
        help="with --check in a generated vault, compare against the canonical harness store",
    )
    parser.add_argument("--dry-run", action="store_true", help="compatibility alias for the default preview mode")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = vault_root()
    user_store = Path.home() / ".agents" / "skills"
    claude_store = Path.home() / ".claude" / "skills"
    selected_names = frozenset(args.skill) if args.skill else None
    if selected_names is not None and not (args.publish_user or args.update_vault):
        print("ERROR --skill requires --publish-user or --update-vault")
        return 2
    if args.preserve_target_metadata and not args.update_vault:
        print("ERROR --preserve-target-metadata requires --update-vault")
        return 2
    if args.self_test:
        return self_test()
    if args.wire_project:
        return wire_project(root, apply=args.apply)
    if args.check:
        canonical_root = args.canonical_root.resolve() if args.canonical_root else None
        return check(root, user_store, claude_store, canonical_root=canonical_root)
    if args.publish_user:
        if args.apply_codex and not args.apply:
            print("ERROR --apply-codex requires --apply so published paths exist before registration")
            return 2
        result = publish_user(
            root,
            user_store,
            claude_store,
            apply=args.apply,
            selected_names=selected_names,
        )
        if result or not args.apply_codex:
            return result
        return write_codex(args.codex_config, codex_paths(root, user_store), apply=True)
    if args.update_vault:
        return update_vault(
            root,
            args.update_vault.resolve(),
            apply=args.apply,
            preserve_target_metadata=args.preserve_target_metadata,
            selected_names=selected_names,
        )
    if args.apply or args.apply_codex:
        print("ERROR --apply and --apply-codex require --publish-user, --update-vault, or --wire-project")
        return 2
    canonical_root = args.canonical_root.resolve() if args.canonical_root else None
    return check(root, user_store, claude_store, canonical_root=canonical_root)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (SkillValidationError, ValueError) as error:
        print(f"ERROR {error}")
        sys.exit(1)
