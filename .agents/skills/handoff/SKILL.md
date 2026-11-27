---
name: handoff
description: >-
  Write a paired session-transition package (handoff/HANDOFF-YYYY-MM-DD--<topic>.md and handoff/INITIAL-PROMPT-YYYY-MM-DD--<topic>.txt) with identical ## Goal blocks using native Python-free editing. Use when the owner says "buat handoff", "tulis serah-terima sesi", "rangkum buat sesi besok", or "buat initial prompt".
---

# handoff

## Purpose

Menyusun paket serah-terima sesi yang terdiri dari **dua berkas wajib berpasangan** — dokumen referensi `handoff/HANDOFF-<suffix>.md` dan prompt siap tempel `handoff/INITIAL-PROMPT-<suffix>.txt` — agar sesi berikutnya dapat langsung melanjutkan kerja tanpa menebak konteks. Jalur utamanya adalah penyuntingan berkas teks native bebas-Python; skrip validasi Python bersifat opsional fail-open.

## Procedure

1. **Lengkapi masukan wajib sekali jalan.** Pastikan empat hal sudah jelas (tanyakan sekali jika ada yang belum disebut, sertakan usulan bawaan): direktori tujuan (`handoff/`), satu akhiran bersama (`YYYY-MM-DD--<topik>` atau `<slug>-YYYY-MM-DD-HHMMSS`; bila `handoff/` sudah memuat paket bertanggal sama, pakai format ber-`HHMMSS` agar `bootstrap` dapat menentukan yang terbaru), cakupan sesi, serta `Session Goal` dan `Ultimate Goal` (tulis `not yet defined by user` jika `Ultimate Goal` belum ditetapkan).
2. **Periksa keamanan penimpaan.** Cek apakah salah satu dari dua berkas target sudah ada. Jika salah satu atau keduanya ada, hentikan penulisan dan tunggu konfirmasi pemilik untuk menimpa, memakai akhiran baru, atau membatalkan.
3. **Kumpulkan bukti aktual sesi.** Baca keadaan nyata dari `SCOPE.md`, `.agents/Context.md`, `.agents/Lessons.md`, dan handoff sebelumnya bila ada. Jika vault memakai Git dan perintah `git` tersedia, tambahkan `git log`, `git status`, dan `git diff --stat`; jika tidak, tulis `Git: tidak tersedia di lingkungan ini` dan susun daftar berkas berubah dari pemeriksaan berkas langsung. Jangan mengarang SHA commit, status uji, atau isi berkas dari ingatan; bila uji belum dijalankan, tulis eksplisit `belum dijalankan di sesi ini`.
4. **Susun satu blok `## Goal` identik untuk kedua berkas:**
   ```markdown
   ## Goal

   - **Session Goal:** <kondisi selesai terukur untuk sesi berikutnya>
   - **Ultimate Goal:** <tujuan besar proyek, atau "not yet defined by user">
   - **Linkage:** <satu kalimat penghubung Session Goal ke Ultimate Goal>
   ```
5. **Tulis kedua berkas berpasangan (jalur utama bebas-Python).**
   - Tulis `handoff/HANDOFF-<suffix>.md` dengan frontmatter YAML lengkap (`title`, `date`, `updated`, `type: handoff`, `status: active`, `tags`), mengacu pada `references/handoff-skeleton.md`, dan memuat blok `## Goal` secara persis.
   - Tulis `handoff/INITIAL-PROMPT-<suffix>.txt` sebagai teks biasa tanpa YAML frontmatter, mengacu pada `references/initial-prompt-skeleton.md`, memuat blok `## Goal` yang sama persis, tepat satu baris metadata `Paired handoff: handoff/HANDOFF-<suffix>.md` di luar blok `## Goal`, serta bagian penutup agar sesi penerus membuat handoff berikutnya.
   - Jika tidak menjalankan alat hitung hash/Python, **dilarang mengarang atau memalsukan checksum SHA-256**; tulis status jujur `checksum: manual / tidak dihitung`.
6. **Verifikasi opsional dengan Python (fail-open).** Jika `python3` tersedia, jalankan:
   ```bash
   python3 .agents/skills/bootstrap/scripts/resolve_handoff.py \
     --root "$PWD" \
     --initial-prompt "handoff/INITIAL-PROMPT-<suffix>.txt"
   ```
   Pastikan keluaran memuat `"goal_match": true`. Bila `scripts/governance_store.py` tersedia, dapat pula menjalankan `rotate-anchors`, `refresh-memory`, `archive-handoff`, dan `check-retention`. Jika Python tidak tersedia, verifikasi kecocokan blok `## Goal`, nama berkas, dan baris `Paired handoff:` secara manual.

## Rules & Boundaries

- Kedua berkas (`.md` dan `.txt`) sama-sama wajib; menghasilkan satu berkas saja berarti paket belum selesai.
- Dilarang menimpa berkas handoff yang sudah ada tanpa persetujuan eksplisit pemilik.
- Dilarang mengarang checksum SHA-256, hash commit, atau hasil tes.
- Baris `Paired handoff:` hanya boleh muncul satu kali di berkas `.txt` untuk menunjuk pasangan aktifnya; jalur handoff lama dalam catatan sejarah tidak boleh memakai label itu.
- Seluruh klaim keadaan di dalam handoff harus lolos verifikasi bukti primer sesuai `confidence` dan `brave`.

## Output & Verification

1. Kedua berkas `handoff/HANDOFF-<suffix>.md` dan `handoff/INITIAL-PROMPT-<suffix>.txt` ada, memiliki akhiran sama persis, frontmatter `.md` valid, dan blok `## Goal` identik di keduanya.
2. Bila `python3` dan berkas `.agents/skills/bootstrap/scripts/resolve_handoff.py` tersedia, perintah verifikasi keluar dengan kode 0 dan `"goal_match": true`; bila salah satunya tidak tersedia, laporkan `verifikasi skrip: tidak tersedia, dicek manual` beserta hasil pemeriksaan manual langkah 6.
3. Laporkan kepada pemilik: jalur kedua berkas, jumlah baris/ukuran, status kecocokan blok `## Goal`, dan status verifikasi tanpa mengulang seluruh isi dokumen.
