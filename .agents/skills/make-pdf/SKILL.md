---
name: make-pdf
description: >-
  Turn a vault note, report, or result into a print-ready PDF: build an A4 HTML page via show-visual, get owner approval, then export with a headless browser or guide Save as PDF. Use when the owner says "jadikan PDF", "buat PDF", "simpan sebagai PDF", "ekspor ke PDF", or "cetak ke PDF". Never claims a PDF exists without file evidence.
---

# make-pdf

## Purpose

Mengubah isi vault (catatan, laporan, hasil kerja) menjadi satu berkas PDF yang rapi dicetak di kertas A4. Jalur utamanya tidak butuh Python: halaman disusun sebagai HTML lewat `show-visual`, lalu dicetak ke PDF oleh browser. Skill ini dipakai saat pemilik ingin hasil yang bisa dikirim, dicetak, atau diarsipkan sebagai dokumen tetap.

## Procedure

1. **Pilih sumber.** Tetapkan berkas atau bagian percakapan yang akan dijadikan PDF. Bila pemilik tidak menyebutnya, ambil artefak terakhir yang sedang dibahas dan sebutkan pilihan itu dalam satu kalimat. Isi PDF hanya boleh berasal dari berkas vault atau percakapan.
2. **Susun artefak.** Tentukan judul, urutan bagian, dan sumber setiap angka. Jangan menambah fakta baru.
3. **Buat HTML ramah cetak lewat `show-visual`.** Ikuti aturan `.agents/skills/show-visual/SKILL.md`: satu berkas `.html` mandiri, tanpa internet, dengan `@page { size: A4; margin: 15mm; }`. Simpan di jalur yang diminta pemilik; bila tidak ada, pakai `work/review/YYYY-MM-DD--<topik>.html`.
4. **Minta persetujuan.** Sebutkan lokasi berkas HTML dan minta pemilik membukanya (klik dua kali). Ekspor PDF ditahan sampai pemilik menyatakan isinya sudah benar.
5. **Ekspor PDF.** Nama keluaran sama dengan HTML, berakhiran `.pdf`.
   - **Jalur otomatis (bila browser headless tersedia).** Cari browser:
     ```bash
     for b in google-chrome chromium chromium-browser microsoft-edge \
       "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
       "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"; do
       command -v "$b" >/dev/null 2>&1 && { echo "$b"; break; }
     done
     ```
     Lalu cetak:
     ```bash
     "<browser>" --headless --disable-gpu --no-pdf-header-footer \
       --print-to-pdf="<keluaran>.pdf" "file://$PWD/<berkas>.html"
     ```
   - **Jalur manual (pengguna awam atau browser tidak ditemukan).** Pandu pemilik dalam tiga langkah: buka berkas HTML dengan klik dua kali; tekan `Ctrl+P` (Windows/Linux) atau `Cmd+P` (Mac); pilih tujuan **Simpan sebagai PDF** / **Save as PDF**, ukuran kertas A4, lalu simpan ke folder yang sama dengan HTML.
6. **Periksa hasil** (lihat bagian terakhir) sebelum melapor.

## Rules & Boundaries

- Dilarang menyatakan PDF sudah tersimpan tanpa bukti berkas. Pada jalur manual, PDF baru dianggap ada setelah pemilik menyimpannya dan pemeriksaan berkas berhasil.
- PDF dan HTML ditulis di dalam vault. Menulis ke luar vault diblokir oleh `.agents/hooks/vault-boundary-guard.py`; pemilik sendiri yang memindahkan berkas ke luar.
- Tidak memasang perangkat lunak. Bila tidak ada browser yang bisa dipakai secara headless, gunakan jalur manual.
- Isi yang belum disetujui pemilik tidak diekspor.
- Satu permintaan menghasilkan satu PDF. Bila sumbernya banyak, gabungkan dulu menjadi satu HTML.

## Output & Verification

1. HTML lolos pemeriksaan `show-visual`: `grep -nE 'https?://|@import|<script|<link' <berkas>.html` tidak mengeluarkan apa pun.
2. PDF ada dan sah:
   ```bash
   ls -l "<keluaran>.pdf" && head -c 5 "<keluaran>.pdf"
   ```
   Ukurannya lebih dari 0 byte dan lima bait pertamanya `%PDF-`.
3. Laporkan kepada pemilik dalam bahasa Indonesia sederhana: lokasi PDF, jumlah halaman bila diketahui, dan jalur ekspor yang dipakai. Bila pemeriksaan gagal, katakan PDF belum jadi dan sebutkan langkah berikutnya.
