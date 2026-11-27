---
title: Toko Skill Lokal Carik Vault
date: 2026-11-23
updated: 2026-11-24
type: documentation
status: active
tags:
  - carik-vault
  - skills
  - portability
---

# Toko Skill Lokal Carik Vault

Direktori `.agents/skills/` menyimpan **30 skill lokal portabel** yang ikut terbawa bersama folder vault ke komputer atau aplikasi AI mana pun tanpa bergantung pada instalasi global.

## Standar Format (`CARIK-SKILLS-FORMAT.md`)

Seluruh skill di direktori ini mengikuti **[CARIK-SKILLS-FORMAT.md](CARIK-SKILLS-FORMAT.md)**: frontmatter YAML murni 2 field (`name` dan `description <= 400` karakter), judul `# <nama-skill>`, tepat 4 bagian seragam (`## Purpose`, `## Procedure`, `## Rules & Boundaries`, `## Output & Verification`) dalam Bahasa Indonesia formal-sederhana lugas, jalur utama bebas-Python, `0` berkas `agents/openai.yaml`, dan `publish_user: false` di `manifest.json`.

Untuk menambah skill baru sesuai kebutuhan Anda, gunakan skill `create-carik-skill` (cukup katakan `"buat skill baru"`).

## Daftar 30 Skill Publik & 3 Perintah Cepat

- **Kerja Harian Awam (9):** `carik-guided-goal`, `browsing`, `split-task`, `notulen`, `remember`, `show-visual`, `backup-drive`, `create-carik-skill`, `update-carik`.
- **Tuas Penalaran Inti (5):** `clarify`, `brave`, `confidence`, `recommend`, `simplify`.
- **Integritas & Eksekusi (4):** `anti-sycophancy`, `define-goal`, `goal`, `debate`.
- **Kontinuitas Sesi Bebas-Python (6):** `bootstrap`, `closing`, `handoff`, `session-log`, `orient`, `scratchpad`.
- **Bahasa Indonesia & Format Terbuka (3):** `id-prose`, `markdown`, `canvas`.
- **Media & Dokumen (3):** `pdf-read`, `pdf-ocr`, `make-pdf`.
- **Perintah cepat (`../commands/`, 3 berkas):** `bootstrap.md`, `orient.md`, `sepakat-atau-debat.md`.

Jika aplikasi AI Anda tidak memiliki pemanggil skill otomatis, buka berkas `.agents/skills/<nama-skill>/SKILL.md` secara langsung dan ikuti langkah di dalamnya.
