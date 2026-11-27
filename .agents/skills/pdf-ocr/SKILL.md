---
name: pdf-ocr
description: >-
  Convert a registered scanned or image-based raw-kb/ PDF rejected by pdf-read into a provenance-bearing Markdown derivative using optional Tesseract and Poppler tools only with owner authorization. Use when the owner says "OCR PDF ini", "baca PDF hasil scan", "ekstrak teks gambar PDF", or "konversi PDF scan".
---

# pdf-ocr

## Purpose

Mengonversi berkas PDF hasil pindai atau berbasis gambar di bawah `raw-kb/` yang sebelumnya ditolak oleh `pdf-read` dengan status `ocr_required` atau `partial_extraction` menjadi turunan Markdown berprovenansi. Proses memakai alat mesin lokal (`pdftotext`, `pdftoppm`, dan `tesseract`) secara opsional fail-open tanpa menjadikan alat tersebut ketergantungan wajib vault.

## Procedure

1. **Verifikasi prasyarat.** Pastikan `pdf-read` sudah dijalankan lebih dulu dan menolak berkas dengan `ocr_required` atau `partial_extraction`, serta PDF sumber sudah terdaftar di `raw-kb/SOURCES.md`.
2. **Periksa ketersediaan alat OCR (opsional fail-open).** Jika `python3` tersedia, jalankan:
   ```bash
   python3 .agents/skills/pdf-ocr/scripts/pdf_ocr.py doctor --vault "$PWD"
   ```
   - Jika hasil `tool_unavailable` (atau `python3`/Tesseract/Poppler belum terpasang), **berhenti dan sampaikan `install_proposal` kepada pemilik untuk meminta izin eksplisit**. Dilarang memasang paket apa pun tanpa persetujuan pemilik.
3. **Jalankan konversi OCR.** Setelah pemeriksaan alat lulus, jalankan dengan jalur eksplisit tanpa menimpa turunan yang sudah ada:
   ```bash
   python3 .agents/skills/pdf-ocr/scripts/pdf_ocr.py ingest \
     --vault "$PWD" \
     --source raw-kb/<provenance>/<sumber>.pdf \
     --output raw-kb/<provenance>/<sumber>.md \
     --source-id <source-id-terdaftar>
   ```
   Adapter mengekstrak teks dengan `pdftotext -layout` dan merender halaman bergambar (<100 karakter non-spasi) pada 150 DPI via `pdftoppm` lalu membaca teksnya lewat `tesseract`. Hanya status `converted` yang sah untuk dicatat.
4. **Daftarkan turunan OCR ke `raw-kb/SOURCES.md`.** Tambahkan entri pada `derived_files` dari keluaran JSON adapter (`path`, `sha256`, `kind: ocr-derivative`, `tool: pdftotext+pdftoppm+tesseract`, `source_sha256`, `page_count`, `ocr_pages`). Baca ulang entri sumber dan berkas `.md` hasil konversi.
5. **Uji regresi bila mengubah adapter.** Jika ada perubahan pada skrip adapter, jalankan `python3 .agents/skills/pdf-ocr/scripts/test_pdf_ocr.py`.

## Rules & Boundaries

- Skill ini **tidak pernah** menghapus, memindahkan, atau menimpa berkas PDF sumber; keberhasilan OCR tidak memberi izin penghapusan PDF.
- Hasil OCR memiliki tingkat keyakinan lebih rendah daripada ekstraksi teks asli (ditandai `pdf_type: scanned` di frontmatter); jangan perlakukan sebagai salinan identik byte tanpa verifikasi halaman.
- Dilarang memasang Tesseract, Poppler, atau perangkat lunak lain tanpa persetujuan eksplisit pemilik.
- Dilarang memasukkan biner, cache paket, atau kata sandi PDF ke dalam vault.

## Output & Verification

1. Berkas turunan `raw-kb/<provenance>/<sumber>.md` terbentuk lengkap (status `converted`), memuat penanda `pdf_type: scanned`, dan terdaftar pada `derived_files` di `raw-kb/SOURCES.md`.
2. Berkas PDF sumber tetap utuh di lokasi semula.
3. Laporkan kepada pemilik jalur turunan `.md`, jumlah halaman total, daftar halaman yang diproses OCR (`ocr_pages`), serta status pemeriksaan (atau `install_proposal` bila alat belum tersedia).
