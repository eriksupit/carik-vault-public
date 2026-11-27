#!/usr/bin/env python3
"""Deterministic assembler for the public Carik Vault distribution package.

Reads work/build/carik-manifest.json, stages work/build/carik/ via a sibling
staging directory, validates JSON identity files, promotes atomically, and
writes a byte-deterministic ZIP at work/build/carik-vault-release.zip.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "work" / "build" / "carik-manifest.json"
BUILD_ROOT = (ROOT / "work" / "build").resolve()


def _assert_safe_rel(rel_str: str) -> Path:
    p = Path(rel_str)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"Unsafe relative path: {rel_str!r}")
    return p


def _assert_within_build(path: Path) -> Path:
    resolved = path.resolve()
    resolved.relative_to(BUILD_ROOT)
    return resolved


def _is_excluded(rel_path: Path, patterns: list[str]) -> bool:
    for part in rel_path.parts:
        for pat in patterns:
            if fnmatch.fnmatch(part, pat):
                return True
    return False


def _copy_regular_file(src: Path, dst: Path, validate_json: bool = False) -> None:
    if src.is_symlink():
        raise ValueError(f"Refusing symlink source: {src}")
    if not src.is_file():
        raise FileNotFoundError(f"Missing source file: {src}")
    data = src.read_bytes()
    if validate_json:
        json.loads(data.decode("utf-8"))
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    mode = src.stat().st_mode
    if mode & stat.S_IXUSR:
        dst.chmod(0o755)
    else:
        dst.chmod(0o644)


def _copy_tree_filtered(src_dir: Path, dst_dir: Path, exclude_patterns: list[str]) -> None:
    if src_dir.is_symlink():
        raise ValueError(f"Refusing symlink directory: {src_dir}")
    if not src_dir.is_dir():
        raise FileNotFoundError(f"Missing source directory: {src_dir}")
    for root_s, dirnames, filenames in os.walk(src_dir, followlinks=False):
        cur = Path(root_s)
        rel_cur = cur.relative_to(src_dir)
        kept_dirs = []
        for d in sorted(dirnames):
            full_d = cur / d
            if full_d.is_symlink():
                raise ValueError(f"Refusing symlink inside tree: {full_d}")
            if not _is_excluded(rel_cur / d, exclude_patterns):
                kept_dirs.append(d)
        dirnames[:] = kept_dirs
        for fname in sorted(filenames):
            full_f = cur / fname
            if full_f.is_symlink():
                raise ValueError(f"Refusing symlink file inside tree: {full_f}")
            rel_f = rel_cur / fname
            if _is_excluded(rel_f, exclude_patterns):
                continue
            _copy_regular_file(full_f, dst_dir / rel_f)


def _zip_entries(package_dir: Path, zip_prefix: str) -> list[tuple[str, Path, bool]]:
    entries: list[tuple[str, Path, bool]] = []
    for root_s, dirnames, filenames in os.walk(package_dir, followlinks=False):
        dirnames.sort()
        filenames.sort()
        cur = Path(root_s)
        rel_dir = cur.relative_to(package_dir)
        if rel_dir != Path("."):
            entries.append((f"{zip_prefix}/{rel_dir.as_posix()}/", cur, True))
        for fname in filenames:
            full_f = cur / fname
            entries.append((f"{zip_prefix}/{full_f.relative_to(package_dir).as_posix()}", full_f, False))
    entries.sort(key=lambda item: item[0])
    return entries


def _build_deterministic_zip(
    package_dir: Path,
    out_path: Path,
    zip_prefix: str,
    timestamp: tuple[int, int, int, int, int, int],
) -> None:
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for arcname, path, is_dir in _zip_entries(package_dir, zip_prefix):
            zi = zipfile.ZipInfo(filename=arcname, date_time=timestamp)
            zi.create_system = 3  # UNIX
            if is_dir:
                zi.compress_type = zipfile.ZIP_STORED
                zi.external_attr = (0o40755 << 16) | 0x10
                zf.writestr(zi, b"")
            else:
                zi.compress_type = zipfile.ZIP_DEFLATED
                is_exec = bool(path.stat().st_mode & stat.S_IXUSR)
                perm = 0o100755 if is_exec else 0o100644
                zi.external_attr = perm << 16
                zf.writestr(zi, path.read_bytes())


def _verify_zip(zip_file: Path, package_dir: Path, zip_prefix: str) -> None:
    expected = {arc: path for arc, path, is_dir in _zip_entries(package_dir, zip_prefix) if not is_dir}
    with zipfile.ZipFile(zip_file) as zf:
        if zf.testzip() is not None:
            raise ValueError(f"ZIP CRC check failed: {zip_file}")
        actual = {name for name in zf.namelist() if not name.endswith("/")}
        if actual != set(expected):
            raise ValueError(f"ZIP entries differ from staging tree: {sorted(actual ^ set(expected))[:5]}")
        for arc, path in expected.items():
            if zf.read(arc) != path.read_bytes():
                raise ValueError(f"ZIP entry differs from staging bytes: {arc}")


def _remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def _recover_promotion(target_dir: Path, backup_dir: Path, zip_path: Path, zip_backup: Path, journal: Path) -> None:
    """Keep the tree and ZIP an atomic pair across crashes.

    The journal exists only between the first and last promotion rename. If it is
    present, roll both outputs back to their pre-promotion state; otherwise any
    backups are leftovers of a committed promotion and are dropped.
    """
    if journal.exists():
        existed = json.loads(journal.read_text(encoding="utf-8"))
        for live, backup, had_live in (
            (target_dir, backup_dir, existed["target"]),
            (zip_path, zip_backup, existed["zip"]),
        ):
            if backup.exists():
                _remove(live)
                os.replace(backup, live)
            elif not had_live:
                _remove(live)
        journal.unlink()
    _remove(backup_dir)
    _remove(zip_backup)


def _sync_dir_in_place(src_dir: Path, dst_dir: Path) -> None:
    """Replace contents inside dst_dir without deleting or renaming dst_dir itself."""
    if dst_dir.is_symlink():
        raise ValueError(f"Refusing symlink destination: {dst_dir}")
    if not dst_dir.is_dir():
        dst_dir.mkdir(parents=True, exist_ok=True)
    for child in list(dst_dir.iterdir()):
        _remove(child)
    for root_s, dirnames, filenames in os.walk(src_dir, followlinks=False):
        cur = Path(root_s)
        rel_cur = cur.relative_to(src_dir)
        for d in sorted(dirnames):
            (dst_dir / rel_cur / d).mkdir(parents=True, exist_ok=True)
        for fname in sorted(filenames):
            _copy_regular_file(cur / fname, dst_dir / rel_cur / fname)


def _populate_staging(
    staging_dir: Path,
    manifest: dict,
    exclude_patterns: list[str],
    timestamp: tuple[int, int, int, int, int, int],
) -> None:
    # 1. Explicit empty directories
    for d_rel in manifest.get("empty_dirs", []):
        rel_p = _assert_safe_rel(d_rel)
        (staging_dir / rel_p).mkdir(parents=True, exist_ok=True)

    # 2. Whole filtered directories (e.g., writing-style/)
    for entry in manifest.get("dirs", []):
        src_d = ROOT / _assert_safe_rel(entry["src"])
        dst_d = staging_dir / _assert_safe_rel(entry["dst"])
        _copy_tree_filtered(src_d, dst_d, exclude_patterns)

    # 3. 30 public skills from factory .agents/skills/
    for skill_name in manifest.get("skills", []):
        _assert_safe_rel(skill_name)
        src_skill = ROOT / ".agents" / "skills" / skill_name
        dst_skill = staging_dir / ".agents" / "skills" / skill_name
        _copy_tree_filtered(src_skill, dst_skill, exclude_patterns)

    # 4. Explicit allowlisted files
    for entry in manifest.get("files", []):
        src_f = ROOT / _assert_safe_rel(entry["src"])
        dst_f = staging_dir / _assert_safe_rel(entry["dst"])
        _copy_regular_file(src_f, dst_f, validate_json=bool(entry.get("validate_json")))

    # 5. Skill overrides (applied after base skill copy)
    for entry in manifest.get("skill_overrides", []):
        src_f = ROOT / _assert_safe_rel(entry["src"])
        dst_f = staging_dir / _assert_safe_rel(entry["dst"])
        _copy_regular_file(src_f, dst_f)

    # 5b. Deterministic release metadata for child vault updates (.agents/carik-release.json)
    built_date = f"{timestamp[0]:04d}-{timestamp[1]:02d}-{timestamp[2]:02d}"
    release_meta = {
        "schema_version": 1,
        "upstream_repo": "https://github.com/eriksupit/carik-vault-public",
        "release_zip_url": "https://raw.githubusercontent.com/eriksupit/carik-vault-public/main/work/build/carik-vault-release.zip",
        "built_date": built_date,
        "upstream_skills": sorted(manifest.get("skills", [])),
        "upstream_owned_paths": [
            "AGENTS.md",
            "CARIK-CHARTER.md",
            "CLAUDE.md",
            "CREATIVE-LAW.md",
            "MULAI-DARI-SINI.md",
            "README.md",
            "WORKFLOW.md",
            "docs/01-CARA-KERJA-DAN-DIAGNOSIS.md",
            "docs/02-PANDUAN-HARNESS-POPULER.md",
            "docs/03-KATALOG-SKILL-VAULT.md",
            ".agents/carik-release.json",
            ".agents/commands/",
            ".agents/hooks.json",
            ".agents/hooks/",
            ".agents/skills/CARIK-SKILLS-FORMAT.md",
            ".agents/skills/README.md",
            ".agents/skills/manifest.json",
            ".claude/settings.json",
            ".codex/hooks.json",
            "scripts/",
            "writing-style/",
        ],
        "protected_user_paths": [
            "SCOPE.md",
            "ATURAN-LOKAL.md",
            "work/",
            "notes/",
            "raw-kb/",
            "handoff/",
            ".agents/Memory.md",
            ".agents/memory/",
            ".agents/Context.md",
            ".agents/Lessons.md",
            ".agents/archive/",
            ".obsidian/",
        ],
    }
    release_meta_path = staging_dir / ".agents" / "carik-release.json"
    release_meta_path.parent.mkdir(parents=True, exist_ok=True)
    release_meta_path.write_text(
        json.dumps(release_meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    release_meta_path.chmod(0o644)


def assemble(manifest_path: Path = DEFAULT_MANIFEST) -> tuple[Path, Path, str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target_rel = _assert_safe_rel(manifest["target_dir"])
    zip_rel = _assert_safe_rel(manifest["zip_output"])
    raw_target = ROOT / target_rel
    raw_zip = ROOT / zip_rel
    if raw_target.is_symlink():
        raise ValueError(f"Refusing symlink target_dir: {raw_target}")
    if raw_zip.is_symlink():
        raise ValueError(f"Refusing symlink zip_output: {raw_zip}")
    target_dir = _assert_within_build(raw_target)
    zip_path = _assert_within_build(raw_zip)
    staging_dir = _assert_within_build(target_dir.parent / f".{target_dir.name}.staging")
    backup_dir = _assert_within_build(target_dir.parent / f".{target_dir.name}.old")
    tmp_zip = _assert_within_build(zip_path.with_name(zip_path.name + ".tmp"))
    zip_backup = _assert_within_build(zip_path.with_name(zip_path.name + ".old"))
    journal = _assert_within_build(target_dir.parent / f".{target_dir.name}.promoting")
    pair = (target_dir, backup_dir, zip_path, zip_backup, journal)

    exclude_patterns: list[str] = list(manifest.get("exclude_patterns", []))
    ts_list = manifest.get("zip_timestamp", [2026, 11, 23, 0, 0, 0])
    if len(ts_list) != 6:
        raise ValueError(f"Invalid zip_timestamp: {ts_list!r}")
    timestamp = tuple(int(x) for x in ts_list)
    zip_prefix = str(manifest.get("zip_prefix", "carik-vault"))

    use_tmp_fallback = False
    try:
        _recover_promotion(*pair)
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        tmp_zip.unlink(missing_ok=True)
        staging_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # ponytail: fallback when parent work/build/ is read-only in sandbox while target_dir and zip_path are writable
        use_tmp_fallback = True

    if use_tmp_fallback:
        with tempfile.TemporaryDirectory(prefix="carik_assemble_") as tmp_root:
            tmp_root_p = Path(tmp_root)
            tmp_stage = tmp_root_p / "staging"
            tmp_stage.mkdir(parents=True, exist_ok=True)
            tmp_archive = tmp_root_p / zip_path.name
            _populate_staging(tmp_stage, manifest, exclude_patterns, timestamp)  # type: ignore[arg-type]
            _build_deterministic_zip(tmp_stage, tmp_archive, zip_prefix, timestamp)  # type: ignore[arg-type]
            _verify_zip(tmp_archive, tmp_stage, zip_prefix)
            if target_dir.is_symlink() or zip_path.is_symlink():
                raise ValueError("Refusing symlink output target during in-place fallback")
            bkp_tree = tmp_root_p / "backup_tree"
            had_tree = target_dir.is_dir()
            if had_tree:
                _sync_dir_in_place(target_dir, bkp_tree)
            had_zip = zip_path.is_file()
            bkp_zip_bytes = zip_path.read_bytes() if had_zip else None
            try:
                _sync_dir_in_place(tmp_stage, target_dir)
                zip_path.write_bytes(tmp_archive.read_bytes())
                zip_path.chmod(0o644)
            except BaseException:
                if had_tree:
                    _sync_dir_in_place(bkp_tree, target_dir)
                elif target_dir.is_dir():
                    for child in list(target_dir.iterdir()):
                        _remove(child)
                if had_zip and bkp_zip_bytes is not None:
                    zip_path.write_bytes(bkp_zip_bytes)
                    zip_path.chmod(0o644)
                elif zip_path.exists():
                    zip_path.unlink()
                raise
        return target_dir, zip_path, hashlib.sha256(zip_path.read_bytes()).hexdigest()

    try:
        _populate_staging(staging_dir, manifest, exclude_patterns, timestamp)  # type: ignore[arg-type]

        # 6. ZIP is built and verified from staging before either live output changes
        _build_deterministic_zip(staging_dir, tmp_zip, zip_prefix, timestamp)  # type: ignore[arg-type]
        _verify_zip(tmp_zip, staging_dir, zip_prefix)

        # 7. Promote both outputs as one pair; the journal is the commit marker
        journal_tmp = journal.with_name(journal.name + ".tmp")
        journal_tmp.write_text(json.dumps({"target": target_dir.exists(), "zip": zip_path.exists()}), encoding="utf-8")
        os.replace(journal_tmp, journal)
        if target_dir.exists():
            os.replace(target_dir, backup_dir)
        if zip_path.exists():
            os.replace(zip_path, zip_backup)
        os.replace(staging_dir, target_dir)
        os.replace(tmp_zip, zip_path)
        journal.unlink()
    except Exception:
        _recover_promotion(*pair)
        shutil.rmtree(staging_dir, ignore_errors=True)
        tmp_zip.unlink(missing_ok=True)
        raise

    _recover_promotion(*pair)
    return target_dir, zip_path, hashlib.sha256(zip_path.read_bytes()).hexdigest()


def main() -> int:
    manifest_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_MANIFEST
    target_dir, zip_path, digest = assemble(manifest_arg)
    print(f"ASSEMBLED {target_dir.relative_to(ROOT)}")
    print(f"ZIP {zip_path.relative_to(ROOT)} ({zip_path.stat().st_size} bytes)")
    print(f"ZIP_SHA256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
