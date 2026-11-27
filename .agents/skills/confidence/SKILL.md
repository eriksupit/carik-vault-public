---
name: confidence
description: >-
  Require over 95% confidence backed by primary evidence before finalizing any substantive answer, plan, or verdict; iterate transparently to close gaps instead of guessing or hedging. Use when the owner says "kamu yakin?", "mana buktinya?", "cek lagi datanya", or "pastikan dulu".
---

# confidence

## Purpose

Menetapkan satu ambang ukur sebelum agen mengeluarkan jawaban, rencana, diagnosis, atau rekomendasi yang bergantung pada ketepatan: **keyakinan melampaui ambang aktif yang ditopang bukti primer**. Ambang aktif bawaan adalah **>95%** untuk klaim substantif umum, atau **>98%** saat skill ini dipanggil `recommend` untuk rekomendasi final. Jika keyakinan belum melampaui ambang aktif, agen wajib melakukan iterasi verifikasi alih-alih menebak, memakai kata ragu, atau melempar keputusan ke pemilik.

## Procedure

1. **Susun kandidat jawaban di internal.** Rumuskan jawaban, rencana, atau kesimpulan sementara yang hendak disampaikan. Tahan dulu; jangan langsung dikirim.
2. **Daftarkan seluruh klaim penopang.** Catat setiap pernyataan yang bila salah akan membuat kesimpulan keliru atau menyesatkan (misalnya keberadaan berkas, perilaku fungsi, angka, syarat aturan, atau keunggulan suatu pendekatan).
3. **Nilai tiap klaim berdasarkan hierarki bukti.**
   - **Prioritas 1 (tertinggi):** pembacaan langsung dan segar atas sumber primer (berkas aktual, keluaran perintah terbaru, log langsung, dokumentasi resmi versi terkait).
   - **Prioritas 2:** hasil bacaan atau keluaran perintah sebelumnya dalam sesi yang sama.
   - **Prioritas 3:** pencarian web terverifikasi untuk fakta eksternal.
   - **Prioritas 4:** pernyataan lisan pemilik (diperlakukan sebagai hipotesis yang tetap diverifikasi).
   - **Prioritas 5 (terendah):** ingatan model semata (maksimal ~70%, tidak pernah cukup untuk klaim penopang).
4. **Hitung keyakinan agregat dari titik terlemah.** Nilai agregat ditentukan oleh **klaim penopang terlemah**, bukan rata-rata. Satu klaim 60% membuat seluruh kandidat bernilai 60%.
   - Jika agregat **melampaui ambang aktif** (bawaan >95%, atau >98% saat dipanggil `recommend`) → lanjut ke langkah 6.
   - Jika agregat **belum melampaui ambang aktif** → masuk ke langkah 5.
5. **Jalankan iterasi penutupan celah.** Ambil klaim terlemah dan lakukan satu tindakan pembuktian paling tajam: baca berkas penuh (bukan potongan grep), jalankan perintah uji, cek dokumentasi sumber, atau pecah klaim menjadi sub-klaim yang bisa diuji. Perbarui kandidat sesuai temuan baru (ubah kesimpulan bila bukti mengubahnya), lalu nilai ulang di langkah 3. Ulangi secara berurutan lewat disiplin `goal` dan `brave` sampai agregat melampaui ambang aktif (bawaan >95%, atau >98% saat dipanggil `recommend`).
6. **Sampaikan hasil final (melampaui ambang aktif).** Susun jawaban lewat disiplin `anti-sycophancy`: lugas, berbasis bukti, tanpa kata ragu, tanpa menu opsi, dan ditutup secara deklaratif.
7. **Eskalasi Iterasi Transparan (hanya untuk celah khusus pemilik).** Jika setelah verifikasi mandiri keyakinan tetap belum melampaui ambang aktif (bawaan >95%, atau >98% saat dipanggil `recommend`) karena celah memang hanya bisa ditutup oleh pemilik (preferensi pribadi, otorisasi, atau data di luar jangkauan agen), sampaikan empat hal: (a) kandidat terbaik saat ini, (b) celah spesifik yang menghambat, (c) langkah terkecil yang dibutuhkan dari pemilik, dan (d) satu rekomendasi sementara bila celah tertutup sesuai skenario paling mungkin.

## Rules & Boundaries

- Dilarang meloloskan jawaban yang belum melampaui ambang aktif dengan kata ragu seperti "mungkin", "kira-kira", atau "sepertinya" sebagai pengganti verifikasi.
- Dilarang memakai potongan `grep` sebagai pengganti membaca konteks utuh saat menyimpulkan perilaku kode atau aturan.
- Dilarang mengandalkan hasil verifikasi lama setelah ada suntingan baru pada berkas terkait; setiap mutasi membuat bukti lama kedaluwarsa.
- Dilarang melempar menu pilihan ("A atau B?") bila satu langkah verifikasi lagi memungkinkan agen memutus sendiri.
- Tidak bergantung pada penjadwal khusus runtime atau alat global; seluruh iterasi dijalankan berurutan secara transparan dalam sesi kerja.

## Output & Verification

1. Setiap klaim penopang pada jawaban akhir memiliki bukti Prioritas 1 yang diverifikasi pada keadaan berkas terbaru.
2. Tidak ada kata ragu yang menutupi celah bukti, dan tidak ada menu opsi tanpa pilihan.
3. Jika eskalasi langkah 7 dipakai, celah khusus pemilik dan rekomendasi sementara dinyatakan eksplisit dengan penutup deklaratif.
