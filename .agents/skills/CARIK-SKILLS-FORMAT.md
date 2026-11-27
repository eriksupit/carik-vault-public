---
title: Carik Skills Format — Spesifikasi Baku Skill Lokal
date: 2026-11-22
updated: 2026-11-22
type: specification
status: active
tags:
  - carik-skills-format
  - local-skills
  - specification
  - carik-vault
---

# Carik Skills Format — Spesifikasi Baku Skill Lokal

Dokumen ini menetapkan satu-satunya standar format penulisan skill lokal di `.agents/skills/` untuk **Carik Vault Public** dan seluruh vault turunannya.

## 1. Identitas & Dasar Keputusan

- **Pola dasar:** Mengadopsi pola *File-First Minimal* dari **Sumber A** (`cursor/plugins/pstack/skills`, commit `7a58391`) dengan **5 Penyesuaian Wajib Carik** — tanpa menyalin field YAML proprietary dari Sumber A dan tanpa boilerplate `agents/openai.yaml` dari Sumber B (commit `abeeaf9`).
- **Lokasi kanonis:** Ditempatkan tepat di akar `.agents/skills/CARIK-SKILLS-FORMAT.md`, sejajar dengan `.agents/skills/README.md` dan `.agents/skills/manifest.json`. Berkas ini **bukan** subdirektori berisi `SKILL.md`, sehingga tidak pernah terbaca sebagai entri skill oleh `scan_store()` pada `scripts/skill_store.py:225` (`p.is_dir() and (p / "SKILL.md").is_file()`).

## 2. Enam Aturan Baku Carik Skills Format

1. **Struktur *file-first* ramping:** Tepat satu berkas `SKILL.md` per folder skill dan `0` berkas `agents/openai.yaml`. Subdirektori `scripts/` atau `references/` hanya dibuat jika benar-benar dipakai secara fungsional.
2. **Penamaan konsisten:** Nama folder skill memakai `kebab-case` maksimal 64 karakter, dan nilai `name` di frontmatter wajib sama persis dengan nama folder.
3. **Frontmatter YAML murni 2 field (Agent Skills open spec):** Hanya memuat tepat dua kunci:
   - `name`: sama persis dengan nama folder skill.
   - `description`: maksimal 400 karakter, ditulis dalam Bahasa Inggris ringkas disertai minimal 3 frasa pemicu Bahasa Indonesia yang natural untuk skill awam, penalaran, bahasa, dan media.
   - **Dilarang** menambah field lain (`format`, `carik_version`, `disable-model-invocation`, `icon`, `color`, `paths`, `title`, `date`, `tags`, dll.) agar tetap patuh spesifikasi terbuka lintas harness dan bebas bug *lookahead regex* pada `scripts/sync-skills.py:145`.
4. **Struktur tubuh 4 bagian seragam:** Diawali tepat satu heading `# <nama-skill>` diikuti tepat 4 bagian dalam Bahasa Indonesia formal-sederhana yang lugas (mengacu pada `writing-style/prose-writing-style.md`):
   - `## Purpose`
   - `## Procedure`
   - `## Rules & Boundaries`
   - `## Output & Verification`
5. **Prinsip Progressive Enhancement:** Jalur utama pada `## Procedure` wajib berjalan penuh memakai operasi baca/tulis berkas teks native bebas-Python agar dapat dipakai di harness GUI awam maupun CLI/ADE. Skrip bantu (`python3`, shell CLI, atau biner lokal) bersifat opsional *fail-open* dan tidak pernah menjadi prasyarat wajib.
   - **Pengecualian sempit untuk skill operasional khusus runtime:** `pane-management` (Herdr + `sandbox-exec` macOS) dan `deepseek-runner` (DeepSeek Harness) hanya bermakna di runtime yang menjadi objeknya, sehingga jalur utamanya boleh bergantung pada skrip runtime tersebut. Di luar runtime itu keduanya wajib aman tanpa efek: `pane-management` berhenti dan melapor pada langkah pertama, sedangkan `deepseek-runner` keluar diam-diam lewat guard `python3` dan penanda `DSH_*`. Keduanya tidak masuk paket peserta awam, dan pengecualian ini tidak berlaku bagi skill lain.
6. **Kemandirian & keterbukaan:** Nol ketergantungan pada direktori global (`~/.agents/`, `~/.claude/`, dll.), nilai `publish_user: false` pada `.agents/skills/manifest.json` untuk skill lokal, serta nol ketergantungan pada aplikasi desktop Obsidian sebagai runtime eksekusi.

## 3. Template Baku Siap Salin

```markdown
---
name: <nama-skill-kebab-case>
description: >-
  <Ringkasan Bahasa Inggris 1 kalimat tentang fungsi dan kapan dipakai. Use when the owner says "<pemicu-id-1>", "<pemicu-id-2>", or "<pemicu-id-3>".>
---

# <nama-skill-kebab-case>

## Purpose

Jelaskan tujuan operasional skill, masalah yang diselesaikan, dan kapan agen wajib menjalankannya.

## Procedure

1. Langkah utama berbasis baca/tulis berkas teks native (bebas-Python, berjalan penuh di GUI awam maupun CLI/ADE).
2. Langkah lanjutan yang konkret, terurut, dan dapat diverifikasi.
3. (Opsional *fail-open*) Jalur skrip bantu apabila lingkungan mendukung `python3` atau CLI terkait; jika tidak tersedia, lewati bersih tanpa gagal keras dan selesaikan lewat jalur teks native.

## Rules & Boundaries

- Batasan tegas, hal yang dilarang, serta keterkaitan wajib dengan skill atau pagar keselamatan lain (misalnya `vault-boundary-guard.py`, `anti-sycophancy`, `recommend`).
- Larangan memasang perangkat lunak otomatis atau bergantung pada direktori global maupun aplikasi Obsidian sebagai runtime.

## Output & Verification

1. Bentuk keluaran akhir yang diserahkan kepada pemilik atau ditulis ke berkas sasaran.
2. Bukti verifikasi deterministik yang wajib diperiksa sebelum menyatakan selesai (baca balik berkas, cek struktur, atau hasil skrip opsional bila aktif).
```

## 4. Daftar Cek Verifikasi Deterministik

Setiap skill baru atau yang diperbarui wajib lolos seluruh pemeriksaan berikut sebelum dinyatakan selesai:

- [ ] Hanya ada satu berkas `SKILL.md` di `.agents/skills/<nama-skill>/` dan `0` berkas `agents/openai.yaml`.
- [ ] Frontmatter YAML hanya memiliki tepat 2 kunci: `name` dan `description`.
- [ ] Nilai `name` sama persis dengan nama folder (`kebab-case`, panjang `<= 64`).
- [ ] Panjang `description` tidak melebihi `400` karakter dan memuat minimal 3 frasa pemicu Bahasa Indonesia yang natural (untuk skill awam/penalaran/bahasa/media).
- [ ] Judul tingkat pertama adalah `# <nama-skill>` dan memiliki tepat 4 heading tingkat kedua secara berurutan: `## Purpose`, `## Procedure`, `## Rules & Boundaries`, `## Output & Verification`.
- [ ] Prosedur utama bebas-Python; seluruh skrip bantu (bila ada) bersifat opsional *fail-open*.
- [ ] Tidak ada rujukan ke skill yang sudah dihapus atau ke jalur direktori global.
- [ ] Perintah `python3 scripts/sync-skills.py --check` selesai dengan `errors=0`.

## 5. Sumber Tunggal untuk Calon Skill `create-carik-skill`

Calon skill `create-carik-skill` (Tahap F4) wajib merujuk langsung ke berkas `.agents/skills/CARIK-SKILLS-FORMAT.md` ini sebagai **satu-satunya sumber kebenaran format** tanpa menduplikasi ulang aturan atau template di dalamnya. Pembuatan `create-carik-skill` sendiri tetap tunduk pada gerbang wawancara wajib bersama pemilik sebelum `SKILL.md`-nya ditulis.
