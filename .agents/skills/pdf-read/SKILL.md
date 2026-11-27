---
name: pdf-read
description: >-
  Convert a registered raw-kb/ PDF into a provenance-bearing Markdown derivative before reading or citing it, verifying page coverage with optional fail-open scripts and never installing software without approval. Use when the owner says "baca PDF ini", "ubah PDF ke markdown", "ekstrak PDF", or "proses PDF di raw-kb".
---

# pdf-read

## Purpose

Menjadi langkah pertama setiap kali ada berkas PDF di bawah `raw-kb/` sebelum isi PDF dibaca sebagai bukti, dikutip, atau dirujuk di catatan mana pun. Skill ini memastikan PDF terdaftar di `raw-kb/SOURCES.md`, dikonversi menjadi turunan Markdown berprovenansi (`.md`), diverifikasi cakupan halamannya, dan selanjutnya seluruh kerja hanya merujuk turunan `.md` tersebut.

## Procedure

1. **Pastikan prasyarat pendaftaran.** Pastikan direktori kerja adalah akar vault dan PDF sudah terdaftar di `raw-kb/SOURCES.md`. Jangan membaca, mengutip, atau merujuk berkas `.pdf` mentah sebelum turunan `.md` selesai dan terverifikasi.
2. **Periksa kesiapan alat ekstraksi (opsional fail-open).** Jika `python3` tersedia, jalankan:
   ```bash
   python3 .agents/skills/pdf-read/scripts/pdf_ingest.py doctor --vault "$PWD"
   ```
   - Bila hasil `tool_unavailable` atau `tool_version_mismatch` (atau `python3` tidak tersedia), **berhenti dan laporkan `install_proposal` atau ketiadaan alat kepada pemilik**. Dilarang memasang paket atau memperbarui biner tanpa izin eksplisit pemilik.
3. **Konversi PDF ke Markdown.** Setelah pemeriksaan alat lulus, jalankan dengan jalur eksplisit (jangan menimpa berkas turunan yang sudah ada):
   ```bash
   python3 .agents/skills/pdf-read/scripts/pdf_ingest.py ingest \
     --vault "$PWD" \
     --source raw-kb/<provenance>/<sumber>.pdf \
     --output raw-kb/<provenance>/<sumber>.md \
     --source-id <source-id-terdaftar>
   ```
   - Jika statusnya `ocr_required` atau `partial_extraction` (PDF hasil pindai/gambar atau halaman teks kosong), jangan perlakukan sebagai bukti dan alihkan ke skill `pdf-ocr`.
   - Hanya status `converted` yang sah untuk dilanjutkan.
4. **Catat turunan di `raw-kb/SOURCES.md`.** Perbarui entri sumber yang ada pada daftar `derived_files` memakai nilai JSON keluaran adapter (`path`, `sha256`, `kind: faithful-format-conversion`, `tool`, `tool_version`, `source_sha256`, `page_count`, `extraction_options`). Baca ulang entri dan turunan `.md` untuk memastikan penanda `<!-- Page N -->` mencakup seluruh halaman `1..page_count`.
5. **Hapus PDF sumber hanya bila tiga syarat terpenuhi penuh.** Setelah (a) seluruh halaman terverifikasi ada di `.md`, (b) `derived_files` tercatat lengkap dengan `source_sha256`, dan (c) berkas `.pdf` sudah terlacak di Git sehingga dapat dipulihkan lewat `git show`, hapus PDF dengan `git rm "raw-kb/<provenance>/<sumber>.pdf"` (bukan `rm` biasa) sambil mempertahankan entri `SOURCES.md` tetap utuh.

## Rules & Boundaries

- Dilarang mengutip atau menjadikan berkas `.pdf` mentah di `raw-kb/` sebagai dasar klaim sebelum turunan `.md` terverifikasi dan terdaftar.
- Dilarang memasang perangkat lunak (`pdf2md`, `poppler`, Cargo, dll.) tanpa persetujuan eksplisit pemilik.
- Dilarang menghapus PDF yang belum terlacak Git, belum terverifikasi halamannya, atau berstatus `ocr_required` / `partial_extraction`.
- Dilarang menyimpan cache paket, biner, atau kata sandi PDF di dalam vault.

## Output & Verification

1. Berkas turunan `raw-kb/<provenance>/<sumber>.md` ada, seluruh penanda `<!-- Page N -->` cocok dengan `page_count`, dan tercatat pada `derived_files` di `raw-kb/SOURCES.md`.
2. Bila PDF dihapus, penghapusan dilakukan via `git rm` hanya setelah ketiga syarat terpenuhi.
3. Laporkan kepada pemilik jalur turunan `.md`, jumlah halaman terverifikasi, alat ekstraksi yang dipakai, dan status tindak lanjut (atau `install_proposal` / pengalihan ke `pdf-ocr` bila terhenti).
