---
name: branch-scope
description: >-
  Keep the active Git branch isolated to its authorized task by checking branch state, HEAD, recent commits, and SCOPE.md before acting. Use when the owner says "cek scope cabang", "apa tugas di branch ini", "cek SCOPE.md", or "jaga batas branch".
---

# branch-scope

## Purpose

Menjaga cabang Git (atau worktree) kerja tetap terisolasi pada lingkup tugas yang diotorisasi pemilik dan mencegah kebocoran perubahan yang tidak berkaitan. Batas kerja selalu ditentukan oleh `SCOPE.md` milik pemilik, bukan ditebak dari nama cabang semata.

## Procedure

1. **Periksa identitas repositori, cabang aktif, dan commit terbaru:**
   ```bash
   ROOT=$(git rev-parse --show-toplevel)
   BRANCH=$(git rev-parse --abbrev-ref HEAD)
   HEAD_COMMIT=$(git rev-parse --short HEAD)
   ```
2. **Baca `SCOPE.md` di akar repositori.**
   - Jika `SCOPE.md` ada, baca seluruh isinya sebagai kontrak batas kerja cabang ini.
   - Jika `SCOPE.md` tidak ada pada cabang fitur/kerja (selain `main`), perlakukan sebagai celah informasi dan tanyakan lingkup resminya kepada pemilik lewat `clarify` sebelum melakukan perubahan substantif; jangan menebak dari nama cabang.
3. **Tinjau riwayat commit dan berkas yang berubah pada cabang ini:**
   ```bash
   git log main..HEAD --oneline
   git status --short
   ```
   Pastikan seluruh berkas yang dimodifikasi dan pekerjaan yang akan dijalankan berada di dalam lingkup `SCOPE.md`.
4. **Sampaikan ringkasan lingkup cabang.** Nyatakan nama cabang, `HEAD`, isi pokok `SCOPE.md`, daftar commit sejak `main`, dan apakah ada perubahan di luar lingkup yang perlu dipisahkan.

## Rules & Boundaries

- Dilarang menyimpulkan atau mempersempit/memperluas lingkup kerja hanya dari nama cabang; `SCOPE.md` adalah sumber otoritatif.
- Dilarang mencampur perubahan di luar `SCOPE.md` ke dalam cabang atau commit yang sama; jika pemilik meminta tugas di luar `SCOPE.md`, angkat konflik lingkupnya lebih dulu lewat `anti-sycophancy`.
- Jangan menganggap ketiadaan `SCOPE.md` pada cabang fitur sebagai kebebasan mengubah berkas apa saja.
- Gunakan bersama `orient` pada sesi pertama (`orient` menjelaskan cara kerja vault, `branch-scope` memastikan batas tugas cabang saat ini).

## Output & Verification

1. Nama cabang aktif, commit `HEAD`, isi `SCOPE.md` (atau pernyataan eksplisit bahwa `SCOPE.md` tidak ada), serta daftar commit `main..HEAD` telah dibaca langsung dari repositori.
2. Seluruh perubahan di `git status` terverifikasi berada dalam batas tugas cabang tanpa kebocoran berkas tak terkait.
3. Laporkan ringkasan batas cabang beserta sitasi sumber `SCOPE.md` dalam Bahasa Indonesia sederhana.
