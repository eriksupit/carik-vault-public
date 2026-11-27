---
title: Portable Skill Store
date: 2026-07-24
updated: 2026-11-24
type: documentation
status: active
tags:
  - file-over-app-harness
  - skills
  - portability
  - continuity
---

# Portable Skill Store

This directory is the **single, agent-neutral source** for the skills a vault needs to function. It travels with the vault (git / copy), so the vault keeps working across computers instead of depending on a per-machine global install. Sibling `../commands/` holds portable slash-commands the same way.

## Why this exists

Skills normally live in per-machine global config (`~/.claude/skills`, `~/.codex/skills`, `~/.agents/skills`). Move the vault to another computer and those skills are absent, so vault function breaks. Bundling them here makes the vault self-carrying.

The harness store is canonical for every harness-owned skill. User-global stores receive generated mirrors through an explicit publication command. An immutable-implementation digest covers instructions, scripts, references, assets, and other resources, so matching `SKILL.md` files cannot conceal divergent executable content. Exact manifest-declared live-data paths use a separate digest and remain preserved during update.

## Discovery is per-agent

- **Claude** does not read `.agents/skills/` directly. Project skills therefore remain
  canonical only in `.agents/skills/`; Claude consumes published user-global copies
  under `~/.claude/skills/`.
- **Codex** reads an explicit registry in `~/.codex/config.toml` (`[[skills.config]]`
  blocks with absolute `path`s). It does **not** folder-scan.

`scripts/sync-skills.py` handles publication and runtime registration. `--wire-project`
removes obsolete managed `.claude/skills` and `.claude/commands` adapters.

## Usage

```bash
python3 scripts/sync-skills.py --wire-project
python3 scripts/sync-skills.py --wire-project --apply
python3 scripts/sync-skills.py --check
python3 scripts/sync-skills.py --check --canonical-root /absolute/canonical-harness
python3 scripts/sync-skills.py --publish-user
python3 scripts/sync-skills.py --publish-user --skill bootstrap --skill handoff
python3 scripts/sync-skills.py --publish-user --apply
python3 scripts/sync-skills.py --publish-user --apply --apply-codex
python3 scripts/sync-skills.py --update-vault /absolute/vault/path
python3 scripts/sync-skills.py --update-vault /absolute/vault/path --preserve-target-metadata --skill bootstrap --skill handoff
python3 scripts/sync-skills.py --update-vault /absolute/vault/path --apply
```

- `--check` is read-only and fails on invalid metadata, retired active skills, or divergent same-name directories.
- A generated vault may add `--canonical-root /absolute/canonical-harness` to compare its immutable skill implementations with the owning harness as well as user-global mirrors. A root-local check without this flag cannot prove that the canonical harness matches.
- `--wire-project` removes former managed `.claude/skills` and `.claude/commands`
  symlinks or per-entry link directories, leaving both canonical trees exclusively
  under `.agents/`. It previews unless `--apply` is passed and refuses paths
  containing content it did not create.
- Publication and vault updates are previews unless `--apply` explicitly authorizes file writes.
- Repeat `--skill NAME` to constrain an operation to approved skills. Cross-harness updates use `--preserve-target-metadata` so the target keeps its own `README.md` and `manifest.json`; generated-vault updates retain the default metadata replacement. A generated vault keeps the same `.agents`-only project skill layout.
- `indonesian-logic-growth` and `konversi-bahasa-logis` exist in a film-domain variant inside `file-over-app-film`. Never run `--update-vault` against that harness with a full sweep; always pass explicit `--skill` selections. `publish_user: false` protects the user-global stores, but `--update-vault` selects on `generated`, so the universal variant would overwrite the domain one in place.
- Codex configuration remains separately gated by `--apply-codex`; the script preserves unrelated entries and backs up the previous config.

## Standar Format Skill Carik (`CARIK-SKILLS-FORMAT.md`)

Seluruh skill lokal di direktori ini wajib mematuhi **[CARIK-SKILLS-FORMAT.md](CARIK-SKILLS-FORMAT.md)** sebagai satu-satunya standar format penulisan skill khas Carik: frontmatter YAML murni 2 field (`name` dan `description <= 400` karakter), judul `# <nama-skill>`, tepat 4 bagian seragam (`## Purpose`, `## Procedure`, `## Rules & Boundaries`, `## Output & Verification`) dalam Bahasa Indonesia formal-sederhana lugas, prosedur utama native bebas-Python (*Progressive Enhancement*), `0` berkas `agents/openai.yaml`, dan `0` ketergantungan global.

## Bundled set (37 skill induk aktif pasca-L0–L5, F4, Gelombang 1, & Pengukuhan *Intelligence-First*)

Daftar ringkas 37 skill induk aktif di `.agents/skills/`:

- **Kerja Harian Awam (9):** `carik-guided-goal`, `browsing`, `split-task`, `notulen`, `remember`, `show-visual`, `backup-drive`, `create-carik-skill`, `update-carik`.
- **Tuas Penalaran Inti (5):** `clarify`, `brave`, `confidence`, `recommend`, `simplify`.
- **Integritas & Eksekusi (4):** `anti-sycophancy`, `define-goal`, `goal`, `debate`.
- **Kontinuitas Sesi Bebas-Python (6):** `bootstrap`, `closing`, `handoff`, `session-log`, `orient`, `scratchpad`.
- **Bahasa Indonesia & Format Terbuka (4):** `id-prose` (rekonstruksi prosa Indonesia), `anti-translationese` (audit kalimat), `markdown`, `canvas`. Aturan gaya permanen tinggal di `writing-style/prose-writing-style.md` dan satu-satunya gerbang bahasa adalah `fact_diff.py`.
- **Media & Dokumen (3):** `pdf-read`, `pdf-ocr`, `make-pdf`.
- **Rekayasa Perangkat Lunak (`app-build`, 3):** `architect`, `grill-with-docs`, `to-prd`.
- **Khusus Operasional Pabrik (3):** `pane-management`, `deepseek-runner`, `branch-scope`.
- **Command aktif (`../commands/`, 4 berkas):** `bootstrap.md`, `buat-vault.md`, `orient.md`, `sepakat-atau-debat.md`.

Domain — declared per profile in `profiles/<name>/profile.json` `bundled_skills`; both shipped profiles currently declare `[]`.

`bundled_skills` must be **dependency-closed**: if a bundled skill invokes another skill, that skill must also be bundled (universal or domain). The initializer does not resolve dependencies automatically.

Canonical source of every harness-owned skill: this `.agents/skills/` directory. Ownership and distribution live in `manifest.json` (with `publish_user: false` for local skills). `~/.agents/skills/` is canonical only for names classified as `global_only`; `~/.claude/skills/` receives generated mirrors, and Codex points to the owning source. A profile or project variant that changes behavior must use `<profile>-<skill>` or `<project>-<skill>` rather than reuse a universal name.

## Live documents (data, not logic) — two different scopes

Growth skills accumulate a living record. These are **data**, and they travel differently from skill logic:

- **Per-vault records** — e.g. `Indonesian-Logic-Language.md` (from `indonesian-logic-growth`) and `Lessons.md`. The skill creates and appends them under **each vault's own `.agents/`** (not here). They are vault content, so they travel with the vault automatically; nothing to bundle.
- **Cross-project ledger** — `craft-ledger.md` moved with `id-screenwriter-growth` to `file-over-app-film` on 2026-08-09 and is canonical there. The principle stands wherever a ledger lives: one shared append-only record, declared as live data, never forked per vault.
