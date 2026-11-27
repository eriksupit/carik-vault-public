---
name: show-visual
description: >-
  Render any artifact, discussion result, analysis, search, or process into one offline browser-ready and A4-printable .html file with zero internet or Python dependency. Use when the owner says "buat laporan visual", "jadikan halaman yang enak dibaca", "bikin ringkasan bergambar", or "laporan untuk dicetak".
---

# show-visual

## Purpose

Menampilkan artefak vault, hasil akhir diskusi, analisa, hasil pencarian, atau proses kerja apa pun menjadi satu berkas `.html` mandiri yang enak dibaca di browser cukup dengan klik dua kali dan rapi dicetak di kertas A4. Seluruh halaman dibuat langsung sebagai teks HTML/CSS tanpa internet, tanpa CDN, dan tanpa Python.

## Procedure

1. **Tetapkan sumber dan tujuan lokasi.** Ambil isi hanya dari berkas vault atau percakapan berjalan. Simpan di jalur yang diminta pemilik; jika tidak disebut, gunakan `work/review/YYYY-MM-DD--<slug-topik>.html`.
2. **Pilih satu pola tata letak yang sesuai:**

   | Pola | Cocok untuk | Struktur isi |
   | --- | --- | --- |
   | Ringkasan | status, progres, hasil akhir diskusi | 3–6 kartu metrik diikuti paragraf pendek |
   | Perbandingan | opsi, sebelum vs sesudah, hasil pencarian | satu tabel dengan baris rekomendasi disorot |
   | Linimasa | riwayat, rencana, tahapan proses | daftar vertikal berurutan dengan tanggal dan status |
   | Temuan | audit, analisa, tinjauan masalah | temuan dikelompokkan per tingkat dampak beserta bukti dan langkah lanjut |

3. **Tulis satu berkas `.html` mandiri.** Semua gaya ditulis inline dalam satu blok `<style>`, grafik memakai inline SVG atau batang CSS, dan setiap angka mencantumkan sumber berkasnya di catatan kaki. Gunakan kerangka dasar berikut:
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
4. **Periksa kebersihan offline dan tata cetak** sebelum melapor kepada pemilik.

## Rules & Boundaries

- Dilarang memuat CDN, font web, gambar eksternal, `<script>`, `<link>`, `@import`, atau tautan `http://` / `https://` di markup maupun CSS.
- Wajib menyertakan aturan `@media print` dengan `@page { size: A4; margin: 15mm; }`, teks hitam di latar putih, dan `break-inside: avoid` pada kartu, tabel, gambar, serta daftar.
- Seluruh teks yang tampak ke pembaca menggunakan Bahasa Indonesia sederhana; jalur berkas diletakkan di catatan kaki, bukan di judul bagian.
- Dilarang menambah angka, klaim, atau fakta yang tidak berasal dari berkas vault atau percakapan.

## Output & Verification

1. Pastikan halaman 100% offline dengan memeriksa bahwa perintah berikut tidak menghasilkan keluaran:
   ```bash
   grep -nE 'https?://|@import|<script|<link' "<berkas>.html"
   ```
2. Pastikan berkas ada, tidak kosong, dan memuat `@page{size:A4;margin:15mm}` (atau setara).
3. Laporkan kepada pemilik dalam Bahasa Indonesia sederhana lokasi berkas `.html`, ringkasan pola yang dipakai, dan bahwa berkas dapat dibuka langsung lewat klik dua kali tanpa internet serta siap dicetak A4.
