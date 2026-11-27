---
name: define-goal
description: >-
  Define and post a checkable ## Goal Contract in chat before any non-trivial work, using five literal English labels so scope and done criteria stay clear; defines only, never executes. Use when the owner says "tentukan goal", "apa goal-nya", "tulis goal dulu", or "/define-goal".
---

# define-goal

## Purpose

Mengubah permintaan bertahap atau multitafsir menjadi satu blok **Goal Contract** yang ringkas, tampil jelas di percakapan, dan dapat diuji benar-salahnya sebelum pekerjaan dimulai. Skill ini hanya mendefinisikan dan memublikasikan kontrak tujuan; pelaksanaan pekerjaannya diserahkan ke `goal` atau alur kerja berikutnya.

## Procedure

1. **Periksa apakah kontrak diperlukan.** Lewati untuk tugas tunggal yang sepele dan hasil akhirnya sudah jelas (membaca satu berkas, menjawab satu fakta, suntingan satu baris yang eksplisit). Jalankan bila tugas bertahap, membuat/mengubah dokumen penting, memuat kata kualitas samar ("bagus", "rapi", "lengkap"), multitafsir, atau akan dijalankan lewat `goal`.
2. **Rumuskan ulang tujuan tanpa memperluas atau menyempitkan.** Tulis apa yang benar-benar diminta pemilik dalam satu kalimat.
3. **Ubah kata kualitas menjadi kondisi selesai yang teramati.** Ganti penilaian subjektif dengan fakta yang dapat diperiksa langsung (misalnya berkas selesai ditulis, seluruh bagian lengkap, setiap angka merujuk sumber di `raw-kb/SOURCES.md`). Uji ketajamannya: dua orang tidak boleh berbeda pendapat soal apakah kondisi sudah terpenuhi.
4. **Tetapkan evaluator dan batas luar cakupan.** Pilih cara pemeriksaan yang objektif (membaca ulang berkas, cek daftar syarat, atau hasil verifikasi) dan sebutkan minimal satu hal yang sengaja tidak dikerjakan agar lingkup tidak melebar. Cocokkan terhadap `SCOPE.md` bila ada.
5. **Tutup celah informasi sebelum memublikasikan.** Jika ada detail yang sudah terjawab di berkas vault, baca berkasnya dulu. Untuk `Ultimate goal` yang belum disebutkan pemilik, isi `not yet defined by user` alih-alih mengarang.
6. **Publikasikan blok `## Goal Contract` secara persis di percakapan** sebelum tindakan penyuntingan pertama:
   ```markdown
   ## Goal Contract

   - **Objective:** <tujuan dalam satu kalimat>
   - **Completion condition:** <pernyataan benar/salah yang dapat diperiksa langsung>
   - **Evaluator:** <pemeriksaan berkas, daftar cek, atau pengamatan penentu>
   - **Out of scope:** <hal yang sengaja tidak dicakup>
   - **Ultimate goal:** <tujuan lebih besar, atau "not yet defined by user">
   ```
7. **Serahkan ke pelaksana.** Teruskan baris `Completion condition` secara verbatim ke `goal` atau langkah kerja berikutnya. Contoh kontrak untuk berbagai jenis tugas tersedia di `references/examples.md`.
8. **Ubah secara terbuka bila tujuan bergeser.** Jika pemilik mengubah arah di tengah pekerjaan, publikasikan blok `## Goal Contract` yang diperbarui beserta alasan perubahannya.

## Rules & Boundaries

- Header wajib persis `## Goal Contract` — **dilarang** memakai header `## Goal` karena header tersebut milik `handoff` dan dibaca oleh `bootstrap`.
- Kelima label wajib tetap dalam Bahasa Inggris literal (`Objective`, `Completion condition`, `Evaluator`, `Out of scope`, `Ultimate goal`) agar seragam lintas harness; isi nilainya ditulis dalam bahasa percakapan.
- Jaga panjang blok tetap ringkas (maksimal sekitar 10 baris) dan jangan mengubahnya menjadi daftar to-do panjang.
- Skill ini **hanya mendefinisikan**, tidak mengeksekusi pekerjaan, dan 100% bebas-Python.
- `Completion condition` tidak boleh dilonggarkan saat diteruskan ke `goal`.

## Output & Verification

1. Blok `## Goal Contract` tampil jelas di percakapan sebelum berkas apa pun dibuat atau disunting.
2. Kelima label literal Inggris lengkap, tidak memakai `## Goal`, dan `Completion condition` dapat diuji benar/salah secara objektif.
3. Lingkup pada kontrak selaras dengan `SCOPE.md` dan tidak ada pekerjaan mutasi yang dijalankan di dalam skill ini.
