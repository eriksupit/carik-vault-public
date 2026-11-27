---
name: define-goal
description: >-
  Define and post a checkable ## Goal Contract in chat before any non-trivial work, using five literal English labels compatible with goal-contract-gate.py; defines only, never executes. Use when the owner says "tentukan goal", "apa goal-nya", "tulis goal dulu", or "/define-goal".
---

# define-goal

## Purpose

Mengubah permintaan non-trivial menjadi satu blok **Goal Contract** yang singkat, terlihat di percakapan, dan dapat diuji benar-salahnya sebelum tindakan perubahan pertama dijalankan. Skill ini hanya mendefinisikan dan memublikasikan kontrak tujuan; eksekusi pekerjaan dilakukan oleh `goal` atau alur kerja penerimanya.

## Procedure

1. **Periksa apakah kontrak diperlukan.** Lewati untuk tugas tunggal yang sepele dan hasil akhirnya sudah jelas (membaca satu berkas, pencarian fakta singkat, suntingan satu baris yang sudah eksplisit). Jalankan jika tugas bertahap, mengubah artefak, mengandung kata kualitas samar ("bagus", "rapi", "lengkap"), multitafsir, atau akan diserahkan ke `goal` maupun subagen.
2. **Rumuskan ulang tujuan tanpa memperluas atau menyempitkan.** Tulis apa yang benar-benar diminta pemilik dalam satu kalimat.
3. **Ubah kata kualitas menjadi kondisi selesai yang teramati.** Ganti penilaian subjektif dengan fakta yang dapat diperiksa (misalnya berkas ada, perintah uji keluar dengan kode 0, setiap klaim merujuk bukti). Uji ketajamannya: dua orang tidak boleh berbeda pendapat soal apakah kondisi sudah terpenuhi.
4. **Tetapkan evaluator dan batas luar cakupan.** Pilih pemeriksa yang dapat dijalankan langsung oleh agen (perintah, inspeksi berkas, diff) dan sebutkan minimal satu hal yang sengaja tidak dikerjakan agar tidak terjadi pelebaran cakupan. Cocokkan terhadap `SCOPE.md` bila ada.
5. **Tutup celah informasi sebelum memublikasikan.** Jika ada detail yang bisa dijawab oleh berkas proyek, baca berkasnya dulu. Untuk `Ultimate goal` yang belum disebutkan pemilik, isi `not yet defined by user` alih-alih mengarang.
6. **Publikasikan blok `## Goal Contract` secara persis di percakapan** sebelum tindakan mutasi pertama:
   ```markdown
   ## Goal Contract

   - **Objective:** <tujuan dalam satu kalimat>
   - **Completion condition:** <pernyataan benar/salah yang dapat diperiksa langsung>
   - **Evaluator:** <perintah, pemeriksaan berkas, atau pengamatan penentu>
   - **Out of scope:** <hal yang sengaja tidak dicakup>
   - **Ultimate goal:** <tujuan lebih besar, atau "not yet defined by user">
   ```
7. **Serahkan ke pelaksana.** Kirim baris `Completion condition` secara verbatim ke `goal` atau subagen penerima. Contoh kontrak untuk berbagai jenis tugas tersedia di `references/examples.md`.
8. **Ubah secara terbuka bila tujuan bergeser.** Jika pemilik mengubah arah di tengah jalan, publikasikan blok `## Goal Contract` yang diperbarui beserta alasan perubahannya.

## Rules & Boundaries

- Header wajib persis `## Goal Contract` — **dilarang** memakai header `## Goal` karena header tersebut milik `handoff` dan diparsing oleh `bootstrap`.
- Kelima label wajib tetap dalam Bahasa Inggris literal (`Objective`, `Completion condition`, `Evaluator`, `Out of scope`, `Ultimate goal`) agar 100% kompatibel dengan `.agents/hooks/goal-contract-gate.py`; isi nilainya ditulis dalam bahasa percakapan.
- Jaga panjang blok tetap ringkas (maksimal sekitar 10 baris) dan jangan mengubahnya menjadi daftar rencana kerja.
- Skill ini **hanya mendefinisikan**, tidak mengeksekusi pekerjaan.
- `Completion condition` tidak boleh dilonggarkan saat diteruskan ke `goal`.

## Output & Verification

1. Blok `## Goal Contract` tampil jelas di percakapan sebelum perintah tulis/sunting pertama dijalankan.
2. Kelima label literal Inggris lengkap, tidak memakai `## Goal`, dan `Completion condition` terukur secara objektif.
3. Tidak ada pekerjaan mutasi yang dilakukan sebelum kontrak dipublikasikan dan batas cakupan selaras dengan `SCOPE.md`.
