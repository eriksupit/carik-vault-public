#!/usr/bin/env python3
"""Deterministic Stage-Reset & Reopen Invalidation Engine.

Reverts active project state to an upstream pipeline stage, sweeping invalidated
downstream authored files into SHA-256-verified run-scoped archives, distilling a
Reset Post-Mortem Dossier, and restoring baseline coordination manifests to
locked state. Stage order and coordination manifests are profile-driven.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def load_active_profile(vault_root: Path) -> dict[str, Any]:
    """Load the active profile JSON dictionary for this vault.

    A generated vault carries its profile at the vault root; the harness itself
    carries the shipped profiles under `profiles/<name>/profile.json`. Both are
    read here so the engine works in either place without a second code path.
    """
    candidates = [
        vault_root / "profile.json",
        *sorted((vault_root / "profiles").glob("*/profile.json")),
    ]
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if isinstance(data, dict) and "pipeline" in data:
            return data
    raise SystemExit(
        "stage-reset: no profile.json with a pipeline array found; cannot order stages"
    )


def pipeline_stages(vault_root: Path) -> list[str]:
    """Ordered stage names for this vault, from the active profile.

    A generated vault carries its profile at the vault root; the harness itself
    carries the shipped profiles under `profiles/<name>/profile.json`. Both are
    read here so the engine works in either place without a second code path.
    """
    profile = load_active_profile(vault_root)
    stages = profile.get("pipeline")
    if isinstance(stages, list) and all(isinstance(s, str) for s in stages) and stages:
        return stages
    raise SystemExit(
        "stage-reset: no profile.json with a pipeline array found; cannot order stages"
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StageResetError(Exception):
    pass


class InvalidStageError(StageResetError):
    pass


def format_post_mortem_draft(
    run_id: str,
    from_stage: str,
    to_stage: str,
    cause: str,
    revoked: list[str],
    salvaged: list[str],
    swept_count: int,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d")
    revoked_bullets = (
        "\n".join(f"- {r}" for r in revoked)
        if revoked
        else "- (Tidak ada pembatalan khusus)"
    )
    salvaged_bullets = (
        "\n".join(f"- {s}" for s in salvaged)
        if salvaged
        else "- (Tidak ada aset diselamatkan)"
    )

    return f"""---
title: "Reset Post-Mortem — {run_id}"
date: {now}
updated: {now}
type: post-mortem
run_id: {run_id}
from_stage: {from_stage}
to_stage: {to_stage}
status: archived
tags:
  - post-mortem
  - stage-reset
  - archive
---

# Reset Post-Mortem — {run_id} ({from_stage} $\\rightarrow$ {to_stage})

## 1. Executive Summary & Root Cause
- **Target Pemunduran:** `{to_stage}`
- **Panggung Asal:** `{from_stage}`
- **Akar Masalah Struktural:** {cause}

## 2. Revoked Decisions (Keputusan yang Dicabut)
{revoked_bullets}

## 3. Salvaged Assets (Aset yang Diselamatkan)
{salvaged_bullets}

## 4. Swept Artifacts Manifest Summary
- Jumlah berkas yang disapu ke karantina: {swept_count} berkas.
- Status Integritas: Tercatat pada `MANIFEST.json` dan `CHECKSUMS.sha256`.
"""


class StageResetEngine:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.profile = load_active_profile(self.root)
        self.stages = pipeline_stages(self.root)
        self.coordination_manifests: list[str] = (
            self.profile.get("coordination_manifests") or []
        )
        self.baseline_templates: dict[str, str] = (
            self.profile.get("baseline_templates") or {}
        )
        self.generated_patterns: set[str] = set(
            self.profile.get("generated_files_to_delete") or []
        )

    def resolve_downstream_stages(self, target_stage: str) -> list[str]:
        target = target_stage.strip().rstrip("/")
        if target.startswith("work/"):
            target = target[len("work/") :]

        if target not in self.stages:
            raise InvalidStageError(
                f"Target stage '{target_stage}' is not in pipeline stages: {self.stages}"
            )

        idx = self.stages.index(target)
        raw_downstream = self.stages[idx + 1 :]

        downstream = []
        for s in raw_downstream:
            base = s.split("/")[0] if "/" in s else s
            if base not in downstream:
                downstream.append(base)
        return downstream

    def discover_invalidation_scope(self, target_stage: str) -> dict[str, Any]:
        downstream_stages = self.resolve_downstream_stages(target_stage)
        authored_to_sweep: list[Path] = []
        manifests_to_reset: list[Path] = []
        generated_to_delete: list[Path] = []

        manifest_set = {self.root / m for m in self.coordination_manifests}

        for stage in downstream_stages:
            stage_dir = self.root / "work" / stage
            if not stage_dir.is_dir():
                continue

            for file_path in stage_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.name.startswith("."):
                    continue

                if file_path in manifest_set:
                    manifests_to_reset.append(file_path)
                elif file_path.name in self.generated_patterns:
                    generated_to_delete.append(file_path)
                else:
                    authored_to_sweep.append(file_path)

        return {
            "target_stage": target_stage,
            "downstream_stages": downstream_stages,
            "authored_to_sweep": sorted(authored_to_sweep),
            "manifests_to_reset": sorted(manifests_to_reset),
            "generated_to_delete": sorted(generated_to_delete),
        }

    def check(self, target_stage: str) -> dict[str, Any]:
        scope = self.discover_invalidation_scope(target_stage)
        return {
            "ok": True,
            "target_stage": target_stage,
            "affected_stages": scope["downstream_stages"],
            "files_to_sweep_count": len(scope["authored_to_sweep"]),
            "manifests_to_reset_count": len(scope["manifests_to_reset"]),
            "generated_to_delete_count": len(scope["generated_to_delete"]),
        }

    def plan(
        self,
        target_stage: str,
        cause: str,
        revoked: list[str] | None = None,
        salvaged: list[str] | None = None,
    ) -> dict[str, Any]:
        scope = self.discover_invalidation_scope(target_stage)

        # Tentukan from_stage (panggung hilir paling jauh yang memuat berkas)
        from_stage = (
            scope["downstream_stages"][-1] if scope["downstream_stages"] else "unknown"
        )
        for s in reversed(scope["downstream_stages"]):
            if (self.root / "work" / s).is_dir() and any(
                (self.root / "work" / s).rglob("*.*")
            ):
                from_stage = s
                break

        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        run_id = f"run-{timestamp}"
        post_mortem_md = format_post_mortem_draft(
            run_id=run_id,
            from_stage=from_stage,
            to_stage=target_stage,
            cause=cause,
            revoked=revoked or [],
            salvaged=salvaged or [],
            swept_count=len(scope["authored_to_sweep"]),
        )

        to_hash = f"{target_stage}:{from_stage}:{len(scope['authored_to_sweep'])}:{timestamp}:{cause}"
        plan_token = hashlib.sha256(to_hash.encode()).hexdigest()[:16]

        plan_data = {
            "ok": True,
            "plan_token": plan_token,
            "run_id": run_id,
            "timestamp": timestamp,
            "target_stage": target_stage,
            "downstream_stages": scope["downstream_stages"],
            "from_stage": from_stage,
            "cause": cause,
            "revoked": revoked or [],
            "salvaged": salvaged or [],
            "post_mortem_markdown": post_mortem_md,
            "authored_to_sweep": [
                p.relative_to(self.root).as_posix() for p in scope["authored_to_sweep"]
            ],
            "manifests_to_reset": [
                p.relative_to(self.root).as_posix() for p in scope["manifests_to_reset"]
            ],
            "generated_to_delete": [
                p.relative_to(self.root).as_posix()
                for p in scope["generated_to_delete"]
            ],
        }

        agents_dir = self.root / ".agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "stage-reset-token.json").write_text(
            json.dumps(plan_data, indent=2), encoding="utf-8"
        )

        return plan_data

    def apply(
        self, plan_token: str, custom_post_mortem: str | None = None
    ) -> dict[str, Any]:
        token_file = self.root / ".agents" / "stage-reset-token.json"
        if not token_file.is_file():
            raise StageResetError(
                "No active stage-reset plan found. Run 'stage_reset.py plan' first."
            )

        try:
            plan_data = json.loads(token_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StageResetError(
                f"Active stage-reset plan at {token_file} is unreadable or malformed: {exc}"
            ) from exc
        if plan_data.get("plan_token") != plan_token:
            raise StageResetError(
                f"Provided plan_token '{plan_token}' does not match active token."
            )

        run_id = plan_data["run_id"]
        from_stage = plan_data["from_stage"]
        to_stage = plan_data["target_stage"].replace("/", "-")
        archive_dirname = f"{run_id}-{from_stage}-to-{to_stage}"
        archive_run_dir = self.root / "archive" / "runs" / archive_dirname
        archive_run_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = archive_run_dir / "MANIFEST.json"
        if manifest_path.is_file():
            # Resume an interrupted apply: the manifest written before the first
            # move still records the original checksums.
            manifest_entries = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            manifest_entries = []
            for rel_path_str in plan_data["authored_to_sweep"]:
                src = self.root / rel_path_str
                if not src.is_file():
                    continue
                file_bytes = src.read_bytes()
                manifest_entries.append(
                    {
                        "path": rel_path_str,
                        "size_bytes": len(file_bytes),
                        "sha256": hashlib.sha256(file_bytes).hexdigest(),
                    }
                )
            (archive_run_dir / "CHECKSUMS.sha256").write_text(
                "".join(f"{e['sha256']}  {e['path']}\n" for e in manifest_entries),
                encoding="utf-8",
            )
            tmp_manifest = manifest_path.with_suffix(".json.tmp")
            tmp_manifest.write_text(
                json.dumps(manifest_entries, indent=2) + "\n", encoding="utf-8"
            )
            tmp_manifest.replace(manifest_path)

        # 1. Pindahkan authored files; tiap tujuan diverifikasi SHA-256 terhadap manifest
        for entry in manifest_entries:
            rel_path_str = entry["path"]
            src = self.root / rel_path_str
            dst = archive_run_dir / rel_path_str
            if src.is_file():
                if _sha256(src) != entry["sha256"]:
                    raise StageResetError(
                        f"{rel_path_str} changed since the manifest was written; refusing to archive or delete the newer revision"
                    )
                if dst.is_file() and _sha256(dst) == entry["sha256"]:
                    src.unlink()  # earlier run copied but did not remove the source
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.move(str(src), str(dst))
                    except OSError as exc:
                        raise StageResetError(
                            f"Failed to quarantine {rel_path_str}: {exc}"
                        ) from exc
            elif not dst.is_file():
                raise StageResetError(
                    f"{rel_path_str} is missing from both the work tree and the archive"
                )
            if _sha256(dst) != entry["sha256"]:
                raise StageResetError(
                    f"Archived {rel_path_str} does not match its manifest SHA-256"
                )

        # 2. Hapus file-file perakitan generated yang tidak relevan
        for rel_path_str in plan_data["generated_to_delete"]:
            gen_file = self.root / rel_path_str
            if gen_file.is_file():
                gen_file.unlink()

        # 3. Tulis RESET-POST-MORTEM.md
        post_mortem_content = (
            custom_post_mortem
            if custom_post_mortem
            else plan_data["post_mortem_markdown"]
        )
        (archive_run_dir / "RESET-POST-MORTEM.md").write_text(
            post_mortem_content, encoding="utf-8"
        )

        # 4. Restorasi coordination manifests ke template baseline berstatus 'locked'
        manifests_note = None
        if not self.coordination_manifests:
            manifests_note = "no coordination manifests declared by this profile"
        else:
            for rel_manifest_str in plan_data["manifests_to_reset"]:
                manifest_file = self.root / rel_manifest_str
                if rel_manifest_str in self.baseline_templates:
                    manifest_file.parent.mkdir(parents=True, exist_ok=True)
                    manifest_file.write_text(
                        self.baseline_templates[rel_manifest_str], encoding="utf-8"
                    )
                else:
                    if manifest_file.suffix == ".json":
                        manifest_file.write_text(
                            '{"status": "locked"}\n', encoding="utf-8"
                        )
                    else:
                        manifest_file.write_text(
                            "---\nstatus: locked\n---\n", encoding="utf-8"
                        )

        # 5. Bersihkan subdirektori kosong di folder work/ yang terdampak
        for stage in plan_data["downstream_stages"]:
            stage_dir = self.root / "work" / stage
            if stage_dir.is_dir():
                for sub in sorted(stage_dir.rglob("*"), reverse=True):
                    if sub.is_dir() and not any(sub.iterdir()):
                        with contextlib.suppress(OSError):
                            sub.rmdir()

        # 6. Hapus token sementara
        token_file.unlink(missing_ok=True)

        res = {
            "ok": True,
            "run_id": run_id,
            "archive_run_dir": archive_run_dir.relative_to(self.root).as_posix(),
            "swept_files_count": len(manifest_entries),
            "manifests_reset_count": len(plan_data["manifests_to_reset"]),
        }
        if manifests_note:
            res["manifests_note"] = manifests_note
        return res


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic Stage-Reset & Reopen Invalidation Engine"
    )
    parser.add_argument(
        "--vault",
        default=".",
        help="Path to vault root (default: current directory)",
    )
    parser.add_argument(
        "--list-stages",
        action="store_true",
        help="List ordered pipeline stages for this vault and exit",
    )
    subparsers = parser.add_subparsers(dest="command")

    # check
    check_p = subparsers.add_parser(
        "check", help="Check invalidation scope for a target stage"
    )
    check_p.add_argument(
        "--target",
        required=True,
        help="Target upstream stage (e.g. research or implementation-plan)",
    )

    # plan
    plan_p = subparsers.add_parser(
        "plan", help="Generate stage-reset execution plan and token"
    )
    plan_p.add_argument("--target", required=True, help="Target upstream stage")
    plan_p.add_argument(
        "--cause", required=True, help="Root cause explanation for reset"
    )
    plan_p.add_argument(
        "--revoked", nargs="*", default=[], help="Revoked decisions bullets"
    )
    plan_p.add_argument(
        "--salvaged", nargs="*", default=[], help="Salvaged assets bullets"
    )

    # apply
    apply_p = subparsers.add_parser("apply", help="Execute atomic stage-reset sweep")
    apply_p.add_argument("--token", required=True, help="Plan authorization token")
    apply_p.add_argument(
        "--post-mortem", help="Path to approved custom post-mortem markdown file"
    )

    args = parser.parse_args(argv)
    vault_root = Path(args.vault).resolve()

    if args.list_stages:
        try:
            stages = pipeline_stages(vault_root)
            for stage in stages:
                print(stage)
            return 0
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1

    if not args.command:
        parser.print_help(sys.stderr)
        return 1

    try:
        engine = StageResetEngine(vault_root)
        if args.command == "check":
            res = engine.check(args.target)
            print(json.dumps(res, indent=2))
        elif args.command == "plan":
            res = engine.plan(args.target, args.cause, args.revoked, args.salvaged)
            print(json.dumps(res, indent=2))
        elif args.command == "apply":
            custom_pm = (
                Path(args.post_mortem).read_text(encoding="utf-8")
                if args.post_mortem
                else None
            )
            res = engine.apply(args.token, custom_pm)
            print(json.dumps(res, indent=2))
        return 0
    except StageResetError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
