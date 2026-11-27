---
title: Carik Vault - Gambaran Paket & Kompatibilitas Lintas Harness
date: 2026-11-23
updated: 2026-11-26
type: documentation
status: active
tags:
  - carik-vault
  - readme
  - progressive-enhancement
---

# Carik Vault

**Carik Vault** adalah templat ruang kerja pengetahuan berbasis berkas teks terbuka (*File-Over-App*) dengan prinsip **Progressive Enhancement**. Sebanyak 28 skill teks dan ingatan berjalan penuh lewat berkas Markdown di aplikasi GUI tanpa Python maupun terminal. Dua skill olah PDF lokal (`pdf-read` dan `pdf-ocr`) serta pengaman fisik batas folder vault membutuhkan `python3` dan alat lokal pada lingkungan yang mendukungnya.

Untuk panduan cepat penggunaan harian, buka [MULAI-DARI-SINI.md](MULAI-DARI-SINI.md). Untuk aturan kerja agen lintas aplikasi, lihat [AGENTS.md](AGENTS.md).

## Isi Utama Paket (2 Zona Folder)

Struktur paket dibagi menjadi dua zona yang seragam di seluruh dokumentasi (`MULAI-DARI-SINI.md`, `AGENTS.md`, dan `CREATIVE-LAW.md`).

- **Zona Kerja Harian:** `MULAI-DARI-SINI.md`, `work/` (terdiri dari 5 folder berurutan: `inbox/`, `concept/`, `drafts/`, `canon/`, dan `archive/`), `notes/`, `raw-kb/`, serta `handoff/`.
- **Zona Pendukung:**
  - Referensi dan pedoman: `docs/` ([Cara Kerja dan Diagnosis](docs/01-CARA-KERJA-DAN-DIAGNOSIS.md), [Panduan Harness Populer](docs/02-PANDUAN-HARNESS-POPULER.md), [Katalog 30 Skill](docs/03-KATALOG-SKILL-VAULT.md)) dan `writing-style/prose-writing-style.md`.
  - Berkas aturan akar: `AGENTS.md`, `WORKFLOW.md`, `SCOPE.md`, `README.md`, `CARIK-CHARTER.md`, `CREATIVE-LAW.md`, `CLAUDE.md`, serta `ATURAN-LOKAL.md` (berkas opsional milik user untuk aturan pribadi).
  - Folder teknis di belakang layar: `.agents/skills/` (30 skill lokal), `.agents/commands/` (3 perintah cepat: `bootstrap.md`, `orient.md`, `sepakat-atau-debat.md`), `.agents/hooks/` (pengaman fisik batas folder dan kredensial yang hanya aktif di lingkungan pendukung; bila Python tidak terpasang, peluncur keluar aman tanpa menghambat kerja), `.obsidian/`, `.claude/`, `.codex/`, dan `scripts/`.

## Status Kompatibilitas 12 Harness

Seluruh 12 target aplikasi membaca `AGENTS.md` sebagai satu sumber aturan kerja bersama. Perilaku akses folder, antarmuka, dan dukungan hook ditentukan oleh masing-masing aplikasi vendor (diverifikasi per 2026-11-26), sedangkan aturan kerja dan 30 skill berasal dari berkas Carik Vault. Status dukungan dan pengujian saat ini tercatat secara jujur pada tabel berikut.

| Aplikasi / Harness | Cara Kerja & Pengaman | Status Pengujian |
|---|---|---|
| **ChatGPT Desktop (macOS dan Windows)** | Akses folder lokal hanya tersedia di aplikasi ChatGPT Desktop (versi web di browser tidak dapat membuka folder lokal, per 2026-11-26); berjalan lewat lapisan teks Markdown | Belum diuji perangkat secara terpisah (verifikasi lewat Tes Koneksi 10 Detik) |
| **Claude Cowork (Desktop)** | Berjalan lewat lapisan teks Markdown; hook `.claude/settings.json` tidak terbukti aktif di Cowork (berbeda dari Claude Code CLI) | Teruji baca, baca skill, dan lintas harness di macOS; uji tulis berkas baru belum diuji terpisah |
| **Antigravity App** | Berjalan lewat lapisan teks Markdown dan mendukung pengaman otomatis `.agents/hooks.json` saat `python3` tersedia | Teruji di macOS; Linux dan WSL belum diuji perangkat penuh; Windows native berjalan lewat lapisan teks |
| **Antigravity CLI (`agy`)** | Mendukung lapisan teks dan pengaman fisik otomatis saat `python3` tersedia | Teruji di macOS; Linux dan WSL belum diuji perangkat penuh; Windows native berjalan lewat lapisan teks |
| **Claude Code** | Mendukung lapisan teks dan pengaman fisik otomatis saat `python3` tersedia | Teruji di macOS; Linux dan WSL belum diuji perangkat penuh; Windows native berjalan lewat lapisan teks |
| **Codex** | Mendukung lapisan teks dan pengaman fisik otomatis saat `python3` tersedia | Teruji di macOS; Linux dan WSL belum diuji perangkat penuh; Windows native berjalan lewat lapisan teks |
| **OhMyPi/Pi (`omp`)** | Berjalan lewat lapisan teks Markdown tanpa adapter hook bawaan | Berjalan lewat lapisan teks |
| **Cursor** | Memakai `AGENTS.md` sebagai sumber aturan bersama | Belum diuji perangkat secara penuh |
| **Windsurf** | Memakai `AGENTS.md` sebagai sumber aturan bersama | Belum diuji perangkat secara penuh |
| **Kiro** | Memakai `AGENTS.md` sebagai sumber aturan bersama | Belum diuji perangkat secara penuh |
| **Zed** | Memakai `AGENTS.md` sebagai sumber aturan bersama | Belum diuji perangkat secara penuh |
| **DeepSeek Harness** | Memakai `AGENTS.md` sebagai sumber aturan bersama | Belum diuji perangkat secara penuh |

## Catatan Skill Lokal dan Pembaruan Paket

### Isolasi 30 Skill Lokal

Seluruh 30 skill lokal di `.agents/skills/` disetel `"publish_user": false` pada `.agents/skills/manifest.json`. Pengaturan ini memastikan paket Carik Vault **tidak menimpa** koleksi skill global yang sudah ada di komputer Anda (seperti `~/.claude/skills/` atau `~/.agents/skills/`).

Pengguna CLI (`Claude Code`, `Codex`, atau `Antigravity CLI`) dapat memeriksa potensi benturan nama dengan koleksi global lewat perintah opsional berikut dari akar vault:

```bash
python3 -B scripts/sync-skills.py --check
```

Pengguna aplikasi GUI dapat melewati langkah pemeriksaan CLI ini.

### Cara Memperbarui Carik Vault

Pembaruan sistem dilakukan lewat skill `update-carik` dengan dua jalur:

- **Pengguna CLI yang terhubung internet:** ambil rilis terbaru langsung dari repositori GitHub publik `eriksupit/carik-vault-public` tanpa perlu login.
- **Pengguna aplikasi GUI atau offline:** unduh lalu ekstrak berkas `carik-vault-release.zip` ke dalam subfolder di `work/inbox/` (misalnya `work/inbox/carik-vault/`), lalu minta agen memperbarui Carik dari subfolder tersebut.

Skill `update-carik` selalu menampilkan pratinjau perubahan sebelum menulis dan mencadangkan berkas sistem lama ke `work/archive/`. Catatan kerja, bahan di `raw-kb/`, `SCOPE.md`, `ATURAN-LOKAL.md`, ingatan sesi, dan skill buatan Anda sendiri tetap utuh dan tidak ditimpa.
