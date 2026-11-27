#!/usr/bin/env python3
"""Local Forge Vault Generator — Inisialisasi Vault Turunan Mandiri.

Mengkristalisasi vault Carik baru yang bersih dan mandiri berbasis Doktrin
Dwi-Tunggal CARIK-CHARTER.md (File-Over-App dan Reasoning-Over-Mechanic),
mendukung profil yang dideklarasikan di `profiles/<nama>/profile.json`
(default `app-build` untuk rekayasa perangkat lunak deterministik).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from distribute_governance import extract_managed_block, splice_managed_block  # noqa: E402

COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")

REQUIRED_OBSIDIAN_FILES = (
    "app.json",
    "appearance.json",
    "core-plugins.json",
)


def validate_target(
    target_path: Path,
    vault_root: Path,
    allow_existing: bool = False,
) -> tuple[bool, str | None]:
    """Validate that target directory is valid and non-recursive."""
    try:
        resolved_target = target_path.resolve()
        resolved_vault = vault_root.resolve()
    except (OSError, RuntimeError) as e:
        return False, f"Failed to resolve path '{target_path}': {e}"

    if resolved_target == resolved_vault:
        return False, f"Target rejects self-recursion: target cannot be vault root '{resolved_target}'"

    if resolved_vault.is_relative_to(resolved_target):
        return False, f"Target rejects ancestor recursion: target '{resolved_target}' is ancestor of vault"

    if resolved_target.is_relative_to(resolved_vault):
        return False, f"Target rejects subdirectory recursion: target '{resolved_target}' is inside vault"

    if resolved_target.is_dir() and not allow_existing:
        # Directory exists: ensure it is empty
        items = list(resolved_target.iterdir())
        if items:
            return False, f"Target directory is not empty: contains {len(items)} item(s)"

    return True, None


def render_template(content: str, project_name: str, today: str) -> str:
    """Render template placeholders {{PROJECT_NAME}} and {{DATE}}."""
    return content.replace("{{PROJECT_NAME}}", project_name).replace("{{DATE}}", today)


def zip_directory(source_dir: Path, zip_path: Path) -> None:
    """Package a directory recursively into a zip archive."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                p = Path(root) / file
                arcname = p.relative_to(source_dir)
                zf.write(p, arcname)


def load_profile(
    vault_root: Path,
    profile_name: str,
) -> tuple[dict[str, Any] | None, Path | None, str | None]:
    """Load profile configuration from profiles/<profile_name>/profile.json."""
    profile_dir = vault_root / "profiles" / profile_name
    profile_json = profile_dir / "profile.json"
    if profile_json.is_file():
        try:
            data = json.loads(profile_json.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            return None, None, f"Invalid profile.json for '{profile_name}': {e}"
        if data.get("name") != profile_name:
            return None, None, f"Profile name mismatch: expected '{profile_name}', got '{data.get('name')}'"
        pipeline = data.get("pipeline")
        if not isinstance(pipeline, list) or not pipeline or not all(isinstance(s, str) and s for s in pipeline):
            return None, None, f"Profile '{profile_name}' must declare a non-empty 'pipeline' list"
        entry_stage = data.get("entry_stage")
        if entry_stage not in pipeline:
            return None, None, f"Profile '{profile_name}' entry_stage '{entry_stage}' is not in pipeline"
        return data, profile_dir, None

    return None, None, f"Unknown profile '{profile_name}': missing {profile_json}"


def _resolve_template_file(
    rel_path: str,
    profile_dir: Path | None,
    clean_templates_dir: Path,
) -> Path | None:
    """Locate a template file in profile_dir/templates, profile_dir, or templates/clean."""
    candidates: list[Path] = []
    if profile_dir is not None:
        candidates.append(profile_dir / "templates" / rel_path)
        candidates.append(profile_dir / rel_path)
    candidates.append(clean_templates_dir / rel_path)
    for c in candidates:
        if c.is_file():
            return c
    return None


def spawn_vault(
    target_dir: Path,
    project_name: str,
    vault_source: Path | None = None,
    today: str | None = None,
    archive_zip_path: Path | None = None,
    allow_existing: bool = False,
    profile: str = "app-build",
) -> tuple[bool, str]:
    """Generate a clean, self-contained derived vault for the selected profile."""
    vault_root = (vault_source or Path(__file__).resolve().parent.parent).resolve()
    target_dir = target_dir.resolve()
    today_str = today or date.today().isoformat()

    # 1. Validation
    is_valid, err = validate_target(target_dir, vault_root, allow_existing=allow_existing)
    if not is_valid:
        return False, err or "Invalid target"

    templates_dir = vault_root / "templates" / "clean"
    profile_data, profile_dir, prof_err = load_profile(vault_root, profile)
    if prof_err or profile_data is None:
        return False, prof_err or f"Failed to load profile '{profile}'"

    target_dir.mkdir(parents=True, exist_ok=True)

    # 2. Constitutional & Governance Root Documents
    charter_src = _resolve_template_file("CARIK-CHARTER.md", profile_dir, templates_dir)
    if charter_src is None and (vault_root / "CARIK-CHARTER.md").is_file():
        charter_src = vault_root / "CARIK-CHARTER.md"
    if charter_src is not None:
        shutil.copy2(charter_src, target_dir / "CARIK-CHARTER.md")

    root_templates = (
        ("AGENTS.md", "AGENTS.md"),
        ("README.md", "README.md"),
        ("SCOPE.md", "SCOPE.md"),
        ("WORKFLOW.md", "WORKFLOW.md"),
        ("MULAI-DARI-SINI.md", "MULAI-DARI-SINI.md"),
        ("CREATIVE-LAW.md", "CREATIVE-LAW.md"),
    )
    for src_rel, dst_rel in root_templates:
        if src_rel == "WORKFLOW.md" and profile_dir is not None and (profile_dir / "WORKFLOW.md").is_file():
            src_path: Path | None = profile_dir / "WORKFLOW.md"
        else:
            src_path = _resolve_template_file(src_rel, profile_dir, templates_dir)
        if src_path is not None and src_path.is_file():
            raw = src_path.read_text(encoding="utf-8")
            rendered = render_template(raw, project_name, today_str)
            # The harness-managed core governance block lives once, in this vault's
            # live document; the clean template carries only the empty markers.
            live_doc = vault_root / dst_rel
            core_block = extract_managed_block(live_doc.read_text(encoding="utf-8")) if live_doc.is_file() else None
            if core_block is not None:
                _, rendered = splice_managed_block(rendered, core_block)
            (target_dir / dst_rel).write_text(rendered, encoding="utf-8")

    # 3. .obsidian identity files
    obsidian_dest = target_dir / ".obsidian"
    obsidian_dest.mkdir(exist_ok=True)
    obsidian_src = vault_root / ".obsidian"
    for obs_name in REQUIRED_OBSIDIAN_FILES:
        src_obs = obsidian_src / obs_name
        if src_obs.is_file():
            shutil.copy2(src_obs, obsidian_dest / obs_name)

    # .gitignore (profile-specific override or root fallback)
    gitignore_src = _resolve_template_file(".gitignore", profile_dir, templates_dir)
    if gitignore_src is None or not gitignore_src.is_file():
        gitignore_src = vault_root / ".gitignore"
    if gitignore_src.is_file():
        shutil.copy2(gitignore_src, target_dir / ".gitignore")

    # 4. work/ structure driven by profile pipeline
    work_dir = target_dir / "work"
    work_dir.mkdir(exist_ok=True)
    pipeline_stages: list[str] = profile_data["pipeline"]
    for sub in pipeline_stages:
        sub_dir = work_dir / sub
        sub_dir.mkdir(parents=True, exist_ok=True)
        gitkeep = sub_dir / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    # 4b. raw-kb/ non-destructive initialization
    raw_kb_dir = target_dir / "raw-kb"
    raw_kb_dir.mkdir(exist_ok=True)
    for rsub in ("user-provided", "agent-acquired"):
        rsub_dir = raw_kb_dir / rsub
        rsub_dir.mkdir(exist_ok=True)
        rgitkeep = rsub_dir / ".gitkeep"
        if not rgitkeep.exists():
            rgitkeep.touch()
    sources_tmpl = vault_root / "raw-kb" / "SOURCES-TEMPLATE.md"
    sources_dst = raw_kb_dir / "SOURCES.md"
    if sources_tmpl.is_file() and not sources_dst.exists():
        shutil.copy2(sources_tmpl, sources_dst)

    # 4c. handoff/ initialization
    handoff_dest = target_dir / "handoff"
    handoff_dest.mkdir(exist_ok=True)
    handoff_readme_src = vault_root / "handoff" / "README.md"
    handoff_readme_dst = handoff_dest / "README.md"
    if handoff_readme_src.is_file() and not handoff_readme_dst.exists():
        shutil.copy2(handoff_readme_src, handoff_readme_dst)
    handoff_arch_dir = handoff_dest / "archived"
    handoff_arch_dir.mkdir(exist_ok=True)
    handoff_arch_readme = handoff_arch_dir / "README.md"
    if not handoff_arch_readme.exists():
        handoff_arch_readme.write_text(
            f"""---
title: Archived Handoff Pairs
date: {today_str}
updated: {today_str}
type: documentation
status: active
tags:
  - carik-vault
  - handoff
  - archive
  - continuity
---

# Archived Handoff Pairs

Superseded `HANDOFF-*.md` / `INITIAL-PROMPT-*.txt` pairs, moved here by `python3 scripts/governance_store.py archive-handoff`.

## Arsip
""",
            encoding="utf-8",
        )

    # 4d. docs/design + docs/plans: governance_store.py archive-docs requires both
    for dsub in ("design", "plans"):
        (target_dir / "docs" / dsub).mkdir(parents=True, exist_ok=True)
    design_readme_src = vault_root / "docs" / "design" / "README.md"
    design_readme_dst = target_dir / "docs" / "design" / "README.md"
    if design_readme_src.is_file() and not design_readme_dst.exists():
        shutil.copy2(design_readme_src, design_readme_dst)
    plans_keep = target_dir / "docs" / "plans" / ".gitkeep"
    if not plans_keep.exists():
        plans_keep.touch()

    # work/WORKFLOW.md (mirror of root WORKFLOW.md)
    wf_text = (target_dir / "WORKFLOW.md").read_text(encoding="utf-8")
    (work_dir / "WORKFLOW.md").write_text(wf_text, encoding="utf-8")

    # work/TODO.txt
    todo_tmpl = _resolve_template_file("work/TODO.txt", profile_dir, templates_dir)
    if todo_tmpl is not None and todo_tmpl.is_file():
        raw_todo = todo_tmpl.read_text(encoding="utf-8")
        (work_dir / "TODO.txt").write_text(render_template(raw_todo, project_name, today_str), encoding="utf-8")

    # 4e. Profile entry_artifacts
    for art in profile_data.get("entry_artifacts", []):
        tmpl_rel = art.get("template", "")
        target_rel = art.get("target", "")
        initial_status = art.get("initial_status")
        if not tmpl_rel or not target_rel:
            continue
        art_src = _resolve_template_file(tmpl_rel, profile_dir, templates_dir)
        if art_src is None or not art_src.is_file():
            return False, f"Missing entry_artifact template '{tmpl_rel}' for profile '{profile}'"
        rendered_art = render_template(art_src.read_text(encoding="utf-8"), project_name, today_str)
        if initial_status:
            status_match = re.search(r"^status:\s*['\"]?([^'\"\n]+)['\"]?\s*$", rendered_art, re.MULTILINE)
            actual_status = status_match.group(1).strip() if status_match else None
            if actual_status != initial_status:
                return (
                    False,
                    f"Entry artifact '{target_rel}' status mismatch: expected '{initial_status}', got '{actual_status}'",
                )
        art_dst = work_dir / target_rel
        art_dst.parent.mkdir(parents=True, exist_ok=True)
        art_dst.write_text(rendered_art, encoding="utf-8")

    # 4f. Optional resource_files
    for res in profile_data.get("resource_files", []):
        res_src_rel = res.get("source", "")
        res_dst_rel = res.get("target", "")
        if not res_src_rel or not res_dst_rel or profile_dir is None:
            continue
        res_src = profile_dir / res_src_rel
        if res_src.is_file():
            res_dst = target_dir / res_dst_rel
            res_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(res_src, res_dst)

    # 5. writing-style/ & scripts/
    ws_dest = target_dir / "writing-style"
    ws_dest.mkdir(exist_ok=True)
    ws_src = vault_root / "writing-style"
    if ws_src.is_dir():
        for f in ws_src.iterdir():
            if f.is_file() and f.suffix in (".md", ".txt"):
                shutil.copy2(f, ws_dest / f.name)

    scripts_dest = target_dir / "scripts"
    scripts_dest.mkdir(exist_ok=True)
    for sname in (
        "prose_style_audit.py",
        "spawn_vault.py",
        "test_spawn_vault.py",
        "governance_store.py",
        "test_governance_store.py",
        "distribute_governance.py",
        "sync-skills.py",
        "skill_store.py",
        "verify_activation.py",
    ):
        src_s = vault_root / "scripts" / sname
        if src_s.is_file():
            shutil.copy2(src_s, scripts_dest / sname)

    for rel in (
        ".agents/Indonesian-Logic-Language.md",
        ".agents/incidents/.gitkeep",
        "raw-kb/SOURCES-TEMPLATE.md",
    ):
        src_r = vault_root / rel
        if src_r.is_file():
            (target_dir / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_r, target_dir / rel)

    # Copy clean templates and profiles so child vault can also spawn vaults
    if templates_dir.is_dir():
        shutil.copytree(templates_dir, target_dir / "templates" / "clean", dirs_exist_ok=True, ignore=COPY_IGNORE)
    profiles_src = vault_root / "profiles"
    if profiles_src.is_dir():
        shutil.copytree(profiles_src, target_dir / "profiles", dirs_exist_ok=True, ignore=COPY_IGNORE)

    # 6. .agents/ structure
    agents_dir = target_dir / ".agents"
    agents_dir.mkdir(exist_ok=True)

    for subdir in ("skills", "commands", "hooks"):
        src_sub = vault_root / ".agents" / subdir
        if src_sub.is_dir():
            shutil.copytree(src_sub, agents_dir / subdir, dirs_exist_ok=True, ignore=COPY_IGNORE)

    # Configurations (with profile-specific .agents/policy.json override if present)
    for conf in (".agents/policy.json", ".agents/skills.json", ".agents/hooks.json", ".codex/hooks.json"):
        src_c: Path | None = None
        if conf == ".agents/policy.json":
            src_c = _resolve_template_file(".agents/policy.json", profile_dir, templates_dir)
        if src_c is None or not src_c.is_file():
            src_c = vault_root / conf
        if src_c.is_file():
            dst_c = target_dir / conf
            dst_c.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_c, dst_c)

    claude_settings = vault_root / ".claude" / "settings.json"
    if claude_settings.is_file():
        dst_cs = target_dir / ".claude" / "settings.json"
        dst_cs.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(claude_settings, dst_cs)
    for obsolete_claude_dir in ("commands", "skills"):
        obs_path = target_dir / ".claude" / obsolete_claude_dir
        if obs_path.is_dir():
            shutil.rmtree(obs_path)

    # 7. Clean Continuity Stores
    context_content = f"""---
title: Context Ledger — {project_name}
date: {today_str}
updated: {today_str}
type: context-ledger
status: active
tags:
  - context
  - session
---

# Context Ledger — {project_name}

## Sesi Inisialisasi ({today_str})
- Vault Carik (profil `{profile}`) berhasil diinisialisasi untuk proyek '{project_name}'.
- Tata kelola: CARIK-CHARTER.md & Doktrin Dwi-Tunggal aktif.
"""
    (agents_dir / "Context.md").write_text(context_content, encoding="utf-8")

    lessons_content = f"""---
title: Lessons Ledger — {project_name}
date: {today_str}
updated: {today_str}
type: lessons-ledger
status: active
tags:
  - lessons
  - proses
---

# Lessons Ledger — {project_name}

Catatan gaya bahasa, preferensi kerja, dan koreksi proses pengguna disimpan di sini.
"""
    (agents_dir / "Lessons.md").write_text(lessons_content, encoding="utf-8")

    memory_content = f"""---
title: Memory Index — {project_name}
date: {today_str}
updated: {today_str}
type: memory-index
status: active
tags:
  - memory
  - fakta
---

# Memory Index — {project_name}

Indeks fakta kunci dan informasi penting terkait proyek '{project_name}'.
"""
    (agents_dir / "Memory.md").write_text(memory_content, encoding="utf-8")
    memory_dir = agents_dir / "memory"
    memory_dir.mkdir(exist_ok=True)
    existing_facts = list(memory_dir.glob("*.md"))
    if existing_facts:
        archive_mem = agents_dir / "archive" / f"memory-pre-spawn-{today_str}"
        archive_mem.mkdir(parents=True, exist_ok=True)
        for f in existing_facts:
            shutil.move(str(f), str(archive_mem / f.name))
    memory_keep = memory_dir / ".gitkeep"
    if not memory_keep.exists():
        memory_keep.touch()
    # Build the index in the store's own format so the continuity gate passes at birth.
    subprocess.run(
        [sys.executable, "scripts/governance_store.py", "refresh-memory"],
        cwd=target_dir,
        check=True,
        capture_output=True,
        text=True,
    )

    # 8. Archive zip packaging (if requested)
    if archive_zip_path:
        zip_path = Path(archive_zip_path).resolve()
        zip_directory(target_dir, zip_path)

    return True, f"Vault '{project_name}' (profile={profile}) successfully spawned at {target_dir}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local Forge Vault Generator — Inisialisasi Vault Turunan Mandiri."
    )
    parser.add_argument("--target", required=True, type=Path, help="Path direktori vault target")
    parser.add_argument("--project-name", default=None, help="Nama proyek (default: nama folder target)")
    parser.add_argument(
        "--profile",
        default="app-build",
        help="Profil vault dari profiles/<nama>/profile.json (default: 'app-build', rekayasa perangkat lunak)",
    )
    parser.add_argument("--source", default=None, type=Path, help="Akar direktori vault pembuat")
    parser.add_argument("--archive-zip", default=None, type=Path, help="Simpan salinan berkas zip ke path ini")
    parser.add_argument(
        "--allow-existing",
        action="store_true",
        help="Izinkan inisialisasi pada direktori yang sudah memiliki berkas (seperti raw-kb/)",
    )
    parser.add_argument(
        "--allow-external",
        action="store_true",
        help="Izin eksplisit pemilik untuk menulis target/zip di folder pengguna di luar vault (setara VAULT_ALLOW_EXTERNAL)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_dir = args.target.resolve()
    project_name = args.project_name or target_dir.name
    vault_source = args.source or Path(__file__).resolve().parent.parent
    source_root = vault_source.resolve()
    allowed_roots = [Path(p).resolve() for p in os.environ.get("VAULT_ALLOW_EXTERNAL", "").split(":") if p.strip()]

    def unauthorized_external(path: Path) -> bool:
        return (
            not path.is_relative_to(source_root)
            and not args.allow_external
            and not any(path.is_relative_to(root) for root in allowed_roots)
        )

    zip_path = args.archive_zip.resolve() if args.archive_zip else None
    if zip_path is not None and unauthorized_external(zip_path):
        print(f"[!] Ditolak: zip '{zip_path}' berada di luar vault tanpa izin (VAULT_ALLOW_EXTERNAL atau --allow-external).", file=sys.stderr)
        return 1

    if unauthorized_external(target_dir):
        if zip_path is None:
            print(
                f"[!] Ditolak: target '{target_dir}' berada di luar vault tanpa izin eksplisit.\n"
                "    Izinkan lewat VAULT_ALLOW_EXTERNAL=<path> atau --allow-external, atau tambahkan\n"
                f"    --archive-zip work/archive/{target_dir.name}.zip untuk ekspor ZIP tanpa menulis ke target.",
                file=sys.stderr,
            )
            return 1
        # validate_target rejects in-vault targets, so the vault is staged in a private OS temp
        # dir that is deleted after zipping; only the (authorized) ZIP path is written.
        print(f"[*] Target '{target_dir}' di luar vault: vault dirakit di staging sementara, hanya ZIP yang ditulis.")
        with tempfile.TemporaryDirectory(prefix="carik-spawn-") as staging:
            success, msg = spawn_vault(
                target_dir=Path(staging) / target_dir.name,
                project_name=project_name,
                vault_source=vault_source,
                archive_zip_path=zip_path,
                profile=args.profile,
            )
        if success:
            msg = f"Vault '{project_name}' dirakit di staging sementara yang sudah dibersihkan; target '{target_dir}' tidak ditulis"
    else:
        print(f"[*] Memulai inisialisasi vault '{project_name}' (profil: {args.profile}) di: {target_dir}...")
        success, msg = spawn_vault(
            target_dir=target_dir,
            project_name=project_name,
            vault_source=vault_source,
            archive_zip_path=zip_path,
            allow_existing=args.allow_existing,
            profile=args.profile,
        )

    if not success:
        print(f"[!] Gagal: {msg}", file=sys.stderr)
        return 1
    print(f"[✓] {msg}")
    if zip_path is not None:
        print(f"[✓] Berkas arsip zip siap di: {zip_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
