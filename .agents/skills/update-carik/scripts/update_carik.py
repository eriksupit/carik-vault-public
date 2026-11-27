#!/usr/bin/env python3
"""Optional fail-open updater for child Carik vaults.

Uses Python standard library only (zero external dependencies):
- Reads official Carik release package (ZIP, extracted release folder, or GitHub URL).
- Defaults to --dry-run (preview only, zero writes).
- With --apply, updates only upstream-owned files declared in .agents/carik-release.json,
  merges .agents/skills/manifest.json to preserve user custom skills, backs up overwritten
  files to a unique work/archive/update-backup-YYYY-MM-DD-HHMMSS[-N]/ (with added.txt), and never
  overwrites protected user paths.
- Rejects the whole update on symlinks or on writes to existing paths the target does not
  own; rolls back if a write fails.
- Seeds SEED_IF_MISSING files from the release only when the target lacks them.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import stat
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

DEFAULT_RELEASE_ZIP_URL = (
    "https://raw.githubusercontent.com/eriksupit/carik-vault-public/main/work/build/carik-vault-release.zip"
)

DEFAULT_PROTECTED_USER_PATHS = (
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
)

# Protected continuity files a migrated child vault may lack; copied only if absent.
SEED_IF_MISSING = ("SCOPE.md", ".agents/Memory.md", ".agents/Context.md", ".agents/Lessons.md")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _matches_prefix(rel_posix: str, rules: list[str] | tuple[str, ...]) -> bool:
    for rule in rules:
        if rule.endswith("/"):
            if rel_posix.startswith(rule) or rel_posix == rule.rstrip("/"):
                return True
        elif rel_posix == rule:
            return True
    return False


def _is_upstream_allowed(
    rel_posix: str,
    upstream_owned_paths: list[str],
    upstream_skills: set[str],
    protected_user_paths: list[str],
) -> bool:
    if _matches_prefix(rel_posix, protected_user_paths):
        return False
    if _matches_prefix(rel_posix, DEFAULT_PROTECTED_USER_PATHS):
        return False
    if _matches_prefix(rel_posix, upstream_owned_paths):
        return True
    if rel_posix.startswith(".agents/skills/"):
        parts = rel_posix.split("/")
        if len(parts) >= 4 and parts[2] in upstream_skills:
            return True
    return False


def _safe_extract_zip(zip_path: Path, dest_dir: Path) -> Path:
    dest_resolved = dest_dir.resolve()
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            member_path = Path(info.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"Jalur tidak aman di dalam arsip ZIP: {info.filename!r}")
            target = (dest_dir / member_path).resolve()
            target.relative_to(dest_resolved)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info, "r") as src_f, open(target, "wb") as dst_f:
                    shutil.copyfileobj(src_f, dst_f)
                mode = (info.external_attr >> 16) & 0o777
                if mode & stat.S_IXUSR:
                    target.chmod(0o755)
                else:
                    target.chmod(0o644)

    direct_meta = dest_dir / ".agents" / "carik-release.json"
    if direct_meta.is_file():
        return dest_dir
    for child in sorted(dest_dir.iterdir()):
        if child.is_dir() and (child / ".agents" / "carik-release.json").is_file():
            return child
    raise FileNotFoundError("Metadata rilis .agents/carik-release.json tidak ditemukan di dalam paket sumber.")


def _resolve_release_root(source_path: Path, tmp_dir: Path) -> Path:
    if source_path.is_file() and source_path.suffix.lower() == ".zip":
        return _safe_extract_zip(source_path, tmp_dir / "extracted")
    if source_path.is_dir():
        if (source_path / ".agents" / "carik-release.json").is_file():
            return source_path
        raise FileNotFoundError(
            f"Folder sumber tidak memuat .agents/carik-release.json: {source_path}"
        )
    raise FileNotFoundError(f"Sumber paket rilis tidak ditemukan: {source_path}")


def _download_github_zip(url: str, tmp_dir: Path) -> Path:
    parsed = urllib.parse.urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"URL rilis tidak valid: {url!r}")
    zip_out = tmp_dir / "carik-vault-release.zip"
    req = urllib.request.Request(  # noqa: S310 - scheme limited to http(s) above
        url.strip(),
        headers={"User-Agent": "CarikVault-Updater/1.0 (+https://github.com/eriksupit/carik-vault-public)"},
    )
    with urllib.request.urlopen(req, timeout=20.0) as resp:  # noqa: S310 - scheme limited to http(s) above
        zip_out.write_bytes(resp.read())
    return zip_out


def _merge_skill_manifest(src_bytes: bytes, dst_path: Path, upstream_skills: set[str]) -> bytes:
    src_data = json.loads(src_bytes.decode("utf-8"))
    if not dst_path.is_file():
        return src_bytes
    try:
        dst_data = json.loads(dst_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return src_bytes

    merged_ho: dict[str, Any] = dict(src_data.get("harness_owned", {}))
    for skill_name, entry in dst_data.get("harness_owned", {}).items():
        if skill_name not in upstream_skills and skill_name not in merged_ho:
            merged_ho[skill_name] = entry

    merged = dict(src_data)
    merged["harness_owned"] = dict(sorted(merged_ho.items()))
    return (json.dumps(merged, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _has_symlink(target_root: Path, rel_posix: str) -> bool:
    cur = target_root
    for part in rel_posix.split("/"):
        cur = cur / part
        if cur.is_symlink():
            return True
    return False


def _ownership_drift(target_root: Path, rels: list[str], release_meta: dict[str, Any]) -> list[str]:
    """Existing target paths that the target's own metadata does not mark upstream-owned:
    planned writes, plus new ownership claims in the release metadata (even without files)."""
    meta_path = target_root / ".agents" / "carik-release.json"
    if not meta_path.is_file():
        return []
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Metadata target {meta_path} tidak terbaca: {exc}") from exc
    owned = list(meta.get("upstream_owned_paths", []))
    skills = set(meta.get("upstream_skills", []))
    writes = [
        rel
        for rel in rels
        if rel not in SEED_IF_MISSING
        and rel != ".agents/carik-release.json"
        and os.path.lexists(target_root / rel)
        and not _is_upstream_allowed(rel, owned, skills, [])
    ]
    claimed_paths = [
        rule
        for rule in release_meta.get("upstream_owned_paths", [])
        if not _is_upstream_allowed(rule.rstrip("/"), owned, skills, [])
        and rule != ".agents/carik-release.json"
        and os.path.lexists(target_root / rule.rstrip("/"))
    ]
    claimed_skills = [
        f".agents/skills/{name}/"
        for name in release_meta.get("upstream_skills", [])
        if name not in skills and os.path.lexists(target_root / ".agents" / "skills" / name)
    ]
    return writes + [p for p in claimed_paths + claimed_skills if p not in writes]


def _apply_writes(
    target_root: Path, planned_writes: list[tuple[str, bytes, bool]], added: list[str], updated: list[str]
) -> tuple[str, str, str | None]:
    """Back up, then write. Returns (backup_dir, status, reason); restores the target on failure."""
    archive = target_root / "work" / "archive"
    rels = [p for p, _, _ in planned_writes] + ["work/archive/x"]
    new_dirs = {
        d for rel in rels for d in (target_root / rel).parents
        if target_root in d.parents and not d.exists()
    }
    backup_root: Path | None = None
    written: list[str] = []
    try:
        archive.mkdir(parents=True, exist_ok=True)
        name = "update-backup-" + dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")
        candidate, n = archive / name, 1
        while True:
            try:
                candidate.mkdir(exist_ok=False)
                break
            except FileExistsError:
                n += 1
                candidate = archive / f"{name}-{n}"
        backup_root = candidate
        (backup_root / "added.txt").write_text("".join(p + "\n" for p in added), encoding="utf-8")
        for rel in updated:
            bkp = backup_root / rel
            bkp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target_root / rel, bkp)

        for rel, payload, is_exec in planned_writes:
            if _has_symlink(target_root, rel):
                raise OSError(f"Symlink muncul setelah pemeriksaan: {rel}")
            dst = target_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            mode = 0o755 if is_exec else 0o644
            # O_NOFOLLOW is POSIX-only; on Windows the per-write symlink check above remains the guard.
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(dst, flags, mode)
            written.append(rel)
            with os.fdopen(fd, "wb") as fh:
                fh.write(payload)
            dst.chmod(mode)
    except Exception as exc:  # noqa: BLE001 - any failure here must roll back
        try:
            for rel in reversed(written):
                if _has_symlink(target_root, rel):
                    raise OSError(f"Symlink di jalur pemulihan: {rel}")
                if rel in updated:
                    shutil.copy2(backup_root / rel, target_root / rel)  # type: ignore[operator]
                else:
                    (target_root / rel).unlink(missing_ok=True)
            if backup_root is not None:
                shutil.rmtree(backup_root)
            for d in sorted(new_dirs, key=lambda p: len(p.parts), reverse=True):
                if d.exists() and not any(d.iterdir()):
                    d.rmdir()
        except Exception as rb_exc:  # noqa: BLE001 - report, keep the backup for manual recovery
            bkp_rel = backup_root.relative_to(target_root).as_posix() if backup_root else "(tidak ada)"
            return bkp_rel, "rollback_failed", (
                f"Penulisan gagal ({exc}) dan pemulihan otomatis gagal ({rb_exc}). "
                f"Pulihkan manual: salin balik berkas dari {bkp_rel}/ dan hapus berkas yang tercantum di {bkp_rel}/added.txt."
            )
        return "", "rolled_back", f"Penulisan gagal dan target dipulihkan: {exc}"
    return backup_root.relative_to(target_root).as_posix(), "applied", None


def _detect_user_custom_skills(target_root: Path, upstream_skills: set[str]) -> list[str]:
    skills_dir = target_root / ".agents" / "skills"
    if not skills_dir.is_dir():
        return []
    custom: list[str] = []
    for child in sorted(skills_dir.iterdir()):
        if child.is_dir() and (child / "SKILL.md").is_file() and child.name not in upstream_skills:
            custom.append(child.name)
    return custom


def run_update(
    target_root: Path,
    source_path: Path | None,
    from_github: bool,
    github_url: str | None,
    apply: bool,
) -> dict[str, Any]:
    target_root = target_root.resolve()
    if not target_root.is_dir():
        raise FileNotFoundError(f"Folder vault target tidak ditemukan: {target_root}")

    if not github_url:
        local_meta = target_root / ".agents" / "carik-release.json"
        if local_meta.is_file():
            try:
                github_url = json.loads(local_meta.read_text(encoding="utf-8")).get(
                    "release_zip_url", DEFAULT_RELEASE_ZIP_URL
                )
            except (OSError, ValueError):
                github_url = DEFAULT_RELEASE_ZIP_URL
        else:
            github_url = DEFAULT_RELEASE_ZIP_URL

    with tempfile.TemporaryDirectory(prefix="carik-update-") as tmp:
        tmp_dir = Path(tmp)
        if from_github:
            downloaded = _download_github_zip(str(github_url), tmp_dir)
            release_root = _resolve_release_root(downloaded, tmp_dir)
            source_label = str(github_url)
        else:
            if source_path is None:
                raise ValueError("Sertakan --source <zip-atau-folder> atau --from-github.")
            release_root = _resolve_release_root(source_path.resolve(), tmp_dir)
            source_label = str(source_path.resolve())

        release_meta = json.loads((release_root / ".agents" / "carik-release.json").read_text(encoding="utf-8"))
        upstream_skills = set(release_meta.get("upstream_skills", []))
        upstream_owned_paths = list(release_meta.get("upstream_owned_paths", []))
        protected_user_paths = list(release_meta.get("protected_user_paths", DEFAULT_PROTECTED_USER_PATHS))

        added: list[str] = []
        updated: list[str] = []
        unchanged: list[str] = []
        skipped_protected: list[str] = []

        planned_writes: list[tuple[str, bytes, bool]] = []
        symlinked: list[str] = [p for p in ("work", "work/archive") if _has_symlink(target_root, p)]

        for root_s, dirnames, filenames in os.walk(release_root, followlinks=False):
            dirnames.sort()
            filenames.sort()
            cur = Path(root_s)
            for fname in filenames:
                src_file = cur / fname
                if src_file.is_symlink():
                    continue
                rel_posix = src_file.relative_to(release_root).as_posix()
                if _has_symlink(target_root, rel_posix):
                    symlinked.append(rel_posix)
                    continue
                if rel_posix in SEED_IF_MISSING:
                    if os.path.lexists(target_root / rel_posix):
                        skipped_protected.append(rel_posix)
                    else:
                        added.append(rel_posix)
                        planned_writes.append((rel_posix, src_file.read_bytes(), False))
                    continue
                if not _is_upstream_allowed(
                    rel_posix, upstream_owned_paths, upstream_skills, protected_user_paths
                ):
                    skipped_protected.append(rel_posix)
                    continue

                dst_file = target_root / rel_posix
                src_bytes = src_file.read_bytes()
                if rel_posix == ".agents/skills/manifest.json":
                    src_bytes = _merge_skill_manifest(src_bytes, dst_file, upstream_skills)
                is_exec = bool(src_file.stat().st_mode & stat.S_IXUSR)

                if not dst_file.exists():
                    added.append(rel_posix)
                    planned_writes.append((rel_posix, src_bytes, is_exec))
                elif _sha256_bytes(dst_file.read_bytes()) != _sha256_bytes(src_bytes):
                    updated.append(rel_posix)
                    planned_writes.append((rel_posix, src_bytes, is_exec))
                else:
                    unchanged.append(rel_posix)

        base = {"source": source_label, "target": str(target_root)}
        if symlinked:
            return {**base, "status": "rejected", "reason": "Jalur target melewati symlink: " + ", ".join(symlinked)}

        drift = _ownership_drift(target_root, [p for p, _, _ in planned_writes], release_meta)
        if drift:
            return {**base, "status": "rejected", "reason": "Paket mengklaim jalur lokal yang sudah ada: " + ", ".join(drift)}

        custom_skills = _detect_user_custom_skills(target_root, upstream_skills)
        backup_dir_rel: str | None = None

        if apply and planned_writes:
            backup_dir_rel, status, reason = _apply_writes(target_root, planned_writes, added, updated)
            if reason:
                return {**base, "status": status, "reason": reason, "backup_dir": backup_dir_rel or None}

        return {
            "status": "applied" if apply else "dry-run",
            "source": source_label,
            "release_built_date": release_meta.get("built_date"),
            "target": str(target_root),
            "backup_dir": backup_dir_rel,
            "counts": {
                "added": len(added),
                "updated": len(updated),
                "unchanged": len(unchanged),
                "skipped_protected": len(skipped_protected),
            },
            "added": added,
            "updated": updated,
            "preserved_user_skills": custom_skills,
            "skipped_protected": skipped_protected,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail-open updater for child Carik vaults.")
    parser.add_argument("--target", default=".", help="Path to child Carik vault root (default: .)")
    parser.add_argument("--source", default=None, help="Path to carik-vault-release.zip or extracted release folder.")
    parser.add_argument("--from-github", action="store_true", help="Download official release ZIP from GitHub.")
    parser.add_argument("--url", default=None, help="Override GitHub release ZIP URL.")
    parser.add_argument("--apply", action="store_true", help="Apply update after previewing (default is dry-run).")
    args = parser.parse_args(argv)

    try:
        result = run_update(
            target_root=Path(args.target),
            source_path=Path(args.source) if args.source else None,
            from_github=bool(args.from_github),
            github_url=args.url,
            apply=bool(args.apply),
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["status"] in ("dry-run", "applied") else 1
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(
            json.dumps(
                {
                    "status": "unavailable",
                    "reason": str(exc),
                    "fallback": "Gunakan jalur utama bebas-Python: unduh carik-vault-release.zip lalu salin hanya berkas upstream-owned setelah pratinjau dan cadangan.",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
