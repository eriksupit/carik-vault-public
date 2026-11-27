---
name: bootstrap
description: >-
  Resume a session from the newest validated handoff pair, SCOPE.md, .agents/Memory.md, and recent Context.md and Lessons.md entries using native Python-free reads (optional resolve_handoff.py check). Use when the owner says "lanjutkan sesi", "baca handoff terbaru", "mulai dari handoff", or "/bootstrap".
---

# bootstrap

## Purpose

Memulihkan konteks kerja sesi baru secara akurat dari pasangan handoff terbaru (`handoff/INITIAL-PROMPT-*.txt` dan `handoff/HANDOFF-*.md`) beserta berkas tata kelola aktif (`SCOPE.md`, `.agents/Memory.md`, `.agents/Context.md`, `.agents/Lessons.md`). Jalur utamanya adalah pembacaan berkas native bebas-Python; skrip resolver Python dipakai sebagai verifikasi tambahan bila tersedia.

## Procedure

1. **Temukan pasangan handoff terbaru (jalur utama bebas-Python).** Daftar berkas `handoff/INITIAL-PROMPT-*.txt` di direktori `handoff/` dan pilih yang tanggalnya paling baru menurut tanggal `YYYY-MM-DD` di akhiran nama (ditambah jam `HHMMSS` bila ada), bukan urutan abjad nama berkas: `INITIAL-PROMPT-YYYY-MM-DD--topik.txt` bertanggal lebih baru tetap dipilih mengungguli `INITIAL-PROMPT-<proyek>-YYYY-MM-DD-HHMMSS.txt` bertanggal lebih lama. Bila tanggal terbaru dimiliki lebih dari satu berkas tanpa jam pembeda, berhenti dan minta pemilik menyebut berkas yang dimaksud. Bila pemilik sudah menyebut berkas spesifik, pakai berkas itu. Cari baris tunggal `Paired handoff: handoff/HANDOFF-<suffix>.md` di dalamnya; bila tidak ada pada paket lama, pasangkan dengan `handoff/HANDOFF-<suffix-sama>.md`.
2. **Validasi pasangan handoff sebelum dipakai.** Baca kedua berkas secara utuh (jangan meringkas dari judul saja) dan pastikan:
   - Akhiran nama kedua berkas sama persis dan tidak ada jalur yang keluar dari akar vault.
   - Berkas `.md` diawali frontmatter YAML sah (`title`, `date`, `updated`, `type`, `status`, dan `tags` tidak kosong dengan tanggal `YYYY-MM-DD`); berkas `.txt` tetap teks biasa.
   - Keduanya memuat tepat satu blok literal `## Goal` dengan isi `Session Goal`, `Ultimate Goal`, dan `Linkage` yang identik.
   - Jika ada validasi gagal, hentikan proses dan laporkan berkas atau aturan yang gagal; jangan diam-diam mundur ke handoff lama.
3. **Verifikasi opsional dengan Python (fail-open).** Bila `python3` tersedia, jalankan:
   ```bash
   python3 .agents/skills/bootstrap/scripts/resolve_handoff.py --root "$PWD"
   python3 scripts/governance_store.py check
   ```
   Jika skrip berjalan dan melaporkan kegagalan paket atau store, hentikan dan laporkan galatnya. Jika `python3` tidak tersedia, lanjutkan dengan validasi manual langkah 2.
4. **Baca tata kelola dan jangkar sesi aktif.** Baca `SCOPE.md` dan `.agents/Memory.md` (buka berkas fakta di `.agents/memory/` hanya yang relevan dengan tugas). Baca indeks heading (`## `) dan entri terbaru dari `.agents/Context.md` dan `.agents/Lessons.md` (bukan seluruh berkas bila sudah panjang).
5. **Rekonsiliasi perbedaan keadaan.** Bandingkan klaim di handoff terhadap `.agents/Context.md` dan jalankan hanya pemeriksaan baca-saja yang diminta paket handoff. Jika ada selisih, jangkar sesi (`.agents/Context.md`) dan bukti berkas aktual mengungguli snapshot handoff untuk fakta yang sudah terjadi, sedangkan handoff memandu langkah lanjut yang direncanakan.
6. **Baca berkas bacaan awal** yang tercantum di initial prompt secara berurutan, lalu mulai tugas pertama yang sudah diotorisasi pemilik.

## Rules & Boundaries

- Paket handoff adalah konteks dan batasan, **bukan izin otorisasi baru** untuk mutasi, penghapusan, commit, push, atau tindakan berisiko yang belum disetujui pemilik di sesi ini.
- Instruksi pemilik dan aturan proyek saat ini selalu mengungguli isi handoff lama bila lebih ketat.
- Dilarang melompat ke handoff yang lebih lama saat handoff terbaru rusak atau tidak cocok.
- Jangan menjalankan rotasi/arsip anchor saat bootstrap; arsip adalah tugas penutupan sesi.

## Output & Verification

1. Kedua nama berkas handoff terverifikasi berpasangan sah dan blok `## Goal` keduanya cocok.
2. Keadaan live (`SCOPE.md`, `.agents/Memory.md`, entri terbaru `.agents/Context.md` & `.agents/Lessons.md`, serta pemeriksaan baca-saja) telah direkonsiliasi terhadap klaim handoff.
3. Laporkan kepada pemilik dalam Bahasa Indonesia sederhana: pasangan handoff yang dipakai, ringkasan `Goal` terverifikasi, perbedaan keadaan aktual bila ada, dan tugas pertama yang mulai dijalankan.
