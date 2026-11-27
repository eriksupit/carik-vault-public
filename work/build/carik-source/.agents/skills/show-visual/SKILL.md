---
name: show-visual
description: >-
  Render any vault note, discussion result, analysis, search, or workflow into one offline browser-ready and A4-printable .html file with zero internet or Python dependency. Use when the owner says "buat laporan visual", "jadikan halaman yang enak dibaca", "bikin ringkasan bergambar", or "laporan untuk dicetak".
---

# show-visual

## Purpose

Mengubah catatan vault, hasil diskusi, analisis, perbandingan, atau tahapan kerja menjadi satu berkas `.html` mandiri yang nyaman dibaca di browser cukup dengan klik dua kali dan rapi saat dicetak ke kertas A4. Seluruh halaman disusun langsung sebagai teks HTML dan CSS murni tanpa internet, tanpa CDN, dan tanpa Python.

## Procedure

1. **Tetapkan sumber dan lokasi simpan di 5 laci kerja publik.** Ambil seluruh isi hanya dari berkas di dalam vault atau percakapan yang sedang berjalan. Simpan di lokasi yang diminta pemilik (misalnya di `notes/`, `work/drafts/`, atau `work/canon/`); jika pemilik tidak menyebut lokasi tertentu, simpan draf halaman di `work/drafts/YYYY-MM-DD--<slug-topik>.html` (dan pindahkan ke `work/canon/` bila pemilik menetapkannya sebagai hasil final).
2. **Pilih satu pola tata letak yang paling pas dengan isi:**

   | Pola | Cocok untuk | Struktur isi |
   | --- | --- | --- |
   | Ringkasan | status pekerjaan, progres, hasil akhir diskusi | 3 sampai 6 kartu ringkas diikuti paragraf penjelas |
   | Perbandingan | pilihan keputusan, sebelum vs sesudah, hasil riset | satu tabel jelas dengan baris rekomendasi disorot |
   | Linimasa | riwayat kegiatan, jadwal rencana, urutan proses | daftar berurutan dari atas ke bawah berisi tanggal dan status |
   | Temuan | evaluasi, analisis masalah, pemeriksaan dokumen | butir temuan per tingkat dampak beserta bukti dan tindak lanjut |

3. **Tulis satu berkas `.html` mandiri.** Letakkan seluruh aturan tampilan di dalam satu blok `<style>`, buat bagan sederhana dengan SVG bawaan atau batang CSS, dan cantumkan berkas sumber di catatan kaki. Gunakan kerangka dasar berikut:
   ```html
   <!doctype html>
   <html lang="id"><head><meta charset="utf-8">
   <meta name="viewport" content="width=device-width,initial-scale=1">
   <title>{judul}</title>
   <style>
   body{font:16px/1.5 system-ui,sans-serif;max-width:860px;margin:2rem auto;padding:0 1rem;color:#1a1a1a;background:#fff}
   .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
   .card{border:1px solid #ccc;border-radius:8px;padding:12px}
   table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:6px 8px;text-align:left}
   .src{font-size:12px;color:#555}
   @media print{@page{size:A4;margin:15mm}body{margin:0;max-width:none;color:#000}.card,table,figure,li{break-inside:avoid}}
   </style></head>
   <body><h1>{judul}</h1><p class="src">Dibuat {tanggal} · Sumber: {sumber}</p>
   <!-- isi pola -->
   </body></html>
   ```
4. **Periksa kemandirian *offline* dan kesiapan cetak A4** sebelum menyerahkan hasilnya kepada pemilik.

## Rules & Boundaries

- Dilarang menyisipkan CDN, font web, gambar luar, `<script>`, `<link>`, `@import`, ataupun alamat `http://` dan `https://` di dalam kode HTML dan CSS agar halaman selalu terbuka utuh saat komputer tidak terhubung ke internet.
- Wajib menyertakan aturan cetak `@media print` dengan `@page { size: A4; margin: 15mm; }`, teks hitam di atas latar putih, serta `break-inside: avoid` pada kartu, tabel, gambar, dan butir daftar.
- Simpan berkas hanya pada folder kerja vault (`work/drafts/`, `work/canon/`, atau `notes/`); jangan membuat folder non-standar di luar tata ruang Carik Vault.
- Seluruh teks pada halaman memakai Bahasa Indonesia yang mudah dipahami, dan dilarang menambahkan angka atau klaim yang tidak berasal dari berkas sumber atau percakapan.

## Output & Verification

1. Baca ulang berkas `.html` yang baru ditulis untuk memastikan berkas tidak kosong, memuat `@page{size:A4;margin:15mm}` (atau setara), serta bebas dari `<script`, `<link`, `@import`, `http://`, dan `https://`. (Opsional *fail-open* di CLI: jalankan `grep -nE 'https?://|@import|<script|<link' "<berkas>.html"` dan pastikan keluarannya kosong).
2. Laporkan secara deklaratif lokasi berkas `.html` (misalnya di `work/drafts/` atau `work/canon/`), pola tata letak yang digunakan, dan cara membukanya cukup dengan klik dua kali di Finder atau File Explorer tanpa koneksi internet.
