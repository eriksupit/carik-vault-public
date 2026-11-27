---
name: session-log
description: >-
  Manage append-only .agents/Context.md (events and position) and .agents/Lessons.md (corrections and insights) via native Python-free READ, APPEND, INIT, and ARCHIVE to .agents/archive/. Use when the owner says "tarik anchor", "refresh konteks", "catat ke log sesi", or "arsipkan anchor".
---

# session-log

## Purpose

Mengelola dua berkas jangkar sesi yang bersifat tambah-saja (*append-only*) untuk mencegah lupa konteks dan pengulangan kesalahan: `.agents/Context.md` (kronologi peristiwa dan posisi kerja saat ini) dan `.agents/Lessons.md` (koreksi serta pelajaran berulang). Jalur utamanya adalah operasi baca dan sunting berkas teks native bebas-Python; skrip Python bersifat opsional fail-open.

## Procedure

1. **READ — Segarkan konteks tanpa menghabiskan jendela konteks.**
   - Baca daftar heading (`## `) dan sekitar 20 baris terakhir `.agents/Context.md` untuk menangkap garis waktu dan `Current position` terbaru.
   - Baca daftar heading (`## `) pada `.agents/Lessons.md` untuk melihat pelajaran yang aktif.
   - Buka isi entri lama atau berkas di bawah `## Arsip` hanya bila relevan dengan tugas saat ini. Pembacaan penuh hanya dilakukan jika pemilik melaporkan agen melenceng/halusinasi dan indeks heading belum cukup menjelaskan penyebabnya.
2. **APPEND — Catat unit kerja bermakna.** Tambahkan entri baru di bagian paling bawah (jangan menulis ulang entri lama):
   - Ke `.agents/Context.md` (setelah milestone, keputusan penting, umpan balik besar, atau hambatan teratasi):
     ```markdown
     ## [YYYY-MM-DD HH:MM] <judul mandiri yang menyebut peristiwa utama>
     - What happened: <satu baris>
     - Result: <satu baris>
     - Current position: <satu baris>
     ```
   - Ke `.agents/Lessons.md` (setelah koreksi pemilik, kesalahan yang terdeteksi sendiri, atau temuan penting):
     ```markdown
     ## [YYYY-MM-DD HH:MM] <judul mandiri yang menyebut inti pelajaran>
     - Lesson: <satu baris instruksi yang harus diikuti>
     - Why: <satu baris bukti atau pemicu>
     ```
3. **INIT — Buat berkas jangkar baru bila belum ada.** Jika `.agents/Context.md` atau `.agents/Lessons.md` belum ada, buat dengan judul header, aturan append-only, dan contoh format entri. Jika sudah ada isinya, jangan menimpa diam-diam; rekomendasikan `ARCHIVE` dulu sebelum `INIT`.
4. **ARCHIVE — Rotasi parsial non-destruktif ke `.agents/archive/`.** Jalankan hanya atas permintaan pemilik atau saat penutupan sesi ketika berkas melewati batas (misalnya >64 KiB atau >100 entri):
   - **Jalur utama bebas-Python:** pindahkan entri-entri lama ke `.agents/archive/<Context|Lessons>-YYYY-MM-DD-HHMM.md` sambil menyisakan sekitar 30 entri terbaru di berkas induk, lalu catat tautan arsip, jumlah entri, dan rentang tanggalnya pada bagian `## Arsip` di bagian atas berkas induk (tanpa mengarang checksum SHA-256).
   - **Jalur opsional Python (fail-open):** bila `python3` dan `scripts/governance_store.py` tersedia, jalankan `python3 scripts/governance_store.py rotate-anchors && python3 scripts/governance_store.py check`.
5. **PURGE — Kosongkan ke templat (destruktif, khusus perintah eksplisit).** Tahan eksekusi sampai pemilik memberi konfirmasi eksplisit tanpa ambigu (misalnya mengetik `ya hapus` atau flag `--confirm`); kata "ya" atau "ok" saja tidak cukup.

## Rules & Boundaries

- Berkas bersifat **append-only** selama sesi aktif: dilarang menyunting atau menghapus entri lama di luar prosedur `ARCHIVE` atau `PURGE` terkonfirmasi.
- Pisahkan isi secara tegas: `Context.md` hanya untuk peristiwa dan posisi kerja; `Lessons.md` hanya untuk koreksi dan pelajaran.
- Tulis judul heading secara mandiri (sebutkan peristiwa atau aturannya, bukan label samar seperti `Catatan sesi`), dan jaga tiap entri ringkas (maksimal 4 baris).
- Jangan melakukan `APPEND` pada setiap pemanggilan tool kecil agar sinyal tetap bersih.
- Jangan pernah memalsukan checksum saat mengarsipkan secara manual tanpa alat hash.

## Output & Verification

1. Untuk `APPEND`: baca ekor `.agents/Context.md` atau `.agents/Lessons.md` untuk memastikan entri baru tercatat di bawah tanpa merusak entri lama.
2. Untuk `ARCHIVE`: pastikan berkas arsip baru ada di `.agents/archive/`, berkas induk masih menyimpan entri terbaru, dan tautan `## Arsip` sesuai.
3. Laporkan ringkas operasi yang dijalankan (`READ`, `APPEND`, `INIT`, `ARCHIVE`, atau `PURGE`) dan lokasi berkas yang diperbarui.
