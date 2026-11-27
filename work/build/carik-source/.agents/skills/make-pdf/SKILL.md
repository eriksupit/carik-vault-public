---
name: make-pdf
description: >-
  Turn a vault note, report, or result into a print-ready A4 PDF by building a self-contained HTML page via show-visual, getting owner approval, and guiding Save as PDF or optional headless export. Use when the owner says "jadikan PDF", "buat PDF", "simpan sebagai PDF", or "cetak ke PDF".
---

# make-pdf

## Purpose

Mengubah catatan, notulen, laporan, atau hasil kerja di dalam Carik Vault menjadi satu berkas PDF ukuran A4 yang rapi untuk dibagikan atau dicetak. Jalur utamanya bebas Python dan bebas terminal: agen menyiapkan halaman HTML siap cetak melalui `show-visual`, meminta persetujuan pemilik, lalu memandu penyimpanan ke PDF lewat browser (atau mengekspornya otomatis bila lingkungan mendukung browser *headless*).

## Procedure

1. **Tetapkan sumber isi.** Pilih berkas di vault atau bagian percakapan yang akan dijadikan PDF. Jika pemilik belum menyebut berkas tertentu, gunakan dokumen terakhir yang sedang dikerjakan dan nyatakan pilihan itu secara jelas. Seluruh isi wajib berasal dari berkas vault atau percakapan tanpa tambahan fakta karangan.
2. **Susun halaman HTML siap cetak lewat `show-visual`.** Ikuti `.agents/skills/show-visual/SKILL.md` untuk menghasilkan satu berkas `.html` mandiri tanpa internet dengan aturan `@page { size: A4; margin: 15mm; }`. Simpan di lokasi yang diminta pemilik (di `work/drafts/`, `work/canon/`, atau `notes/`); bila tidak ditentukan, tulis draf halaman di `work/drafts/YYYY-MM-DD--<slug-topik>.html`.
3. **Tahan ekspor PDF sampai pemilik menyetujui tampilan HTML.** Beri tahu lokasi berkas `.html` agar pemilik dapat membukanya lewat klik dua kali, dan nyatakan secara deklaratif bahwa pembuatan PDF menunggu persetujuan isi dari pemilik.
4. **Ekspor menjadi PDF di folder kerja vault** (misalnya `work/canon/YYYY-MM-DD--<slug-topik>.pdf` untuk versi final, atau berdampingan di `work/drafts/` / `notes/` sesuai permintaan pemilik):
   - **Jalur Utama (Bebas Terminal, untuk Semua Pengguna):** pandu pemilik dalam tiga langkah singkat: (1) klik dua kali berkas `.html` hingga terbuka di browser; (2) tekan `Cmd+P` di Mac atau `Ctrl+P` di Windows; (3) ubah tujuan cetak menjadi **Save as PDF** / **Simpan sebagai PDF** dengan ukuran kertas **A4**, lalu simpan ke `work/canon/` (atau folder yang sama dengan berkas HTML).
   - **Jalur Opsional Otomatis (CLI bila browser *headless* tersedia, *fail-open*):** cari aplikasi Chrome atau Edge lokal tanpa menginstal apa pun:
     ```bash
     for b in google-chrome chromium chromium-browser microsoft-edge \
       "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
       "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"; do
       command -v "$b" >/dev/null 2>&1 && { echo "$b"; break; }
     done
     ```
     Bila ditemukan, cetak langsung ke jalur sasaran di dalam vault:
     ```bash
     "<browser>" --headless --disable-gpu --no-pdf-header-footer \
       --print-to-pdf="<jalur-keluaran>.pdf" "file://$PWD/<berkas>.html"
     ```
     Jika browser tidak ditemukan atau perintah gagal, beralih bersih ke panduan Jalur Utama tanpa gagal keras.
5. **Verifikasi keberadaan berkas PDF** sebelum menyatakan PDF selesai dibuat.

## Rules & Boundaries

- Dilarang mengklaim berkas PDF sudah jadi tanpa bukti nyata keberadaan berkas. Pada Jalur Utama manual, sampaikan bahwa panduan cetak siap dijalankan dan berkas PDF baru berstatus tersimpan setelah pemilik menyimpannya.
- Seluruh berkas `.html` dan `.pdf` disimpan di dalam laci kerja publik vault (`work/drafts/`, `work/canon/`, atau `notes/`). Jangan memakai folder di luar tata ruang Carik Vault, dan patuhi izin eksplisit pada `AGENTS.md` bila pemilik meminta menyalin hasil akhirnya ke luar vault.
- Dilarang memasang perangkat lunak atau pustaka PDF tambahan tanpa izin eksplisit pemilik.
- Dilarang mengekspor isi yang belum disetujui pemilik, dan gabungkan beberapa catatan sumber menjadi satu halaman HTML lebih dulu bila pemilik meminta satu dokumen PDF gabungan.

## Output & Verification

1. Berkas `.html` telah memenuhi syarat *offline* dan tata cetak A4 dari `show-visual`.
2. Pada jalur otomatis CLI, pastikan berkas `<jalur-keluaran>.pdf` berukuran lebih dari 0 byte dan diawali tanda `%PDF-` (`ls -l "<jalur-keluaran>.pdf" && head -c 5 "<jalur-keluaran>.pdf"`). Pada jalur manual GUI, periksa keberadaan berkas `.pdf` di folder sasaran setelah pemilik menyimpannya.
3. Laporkan secara deklaratif lokasi berkas `.html` dan `.pdf` serta cara yang digunakan; bila berkas `.pdf` belum disimpan pada jalur manual, sebutkan langkah simpan yang tinggal dilakukan pemilik.
