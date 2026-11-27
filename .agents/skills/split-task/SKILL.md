---
name: split-task
description: >-
  Split a compound request into small ordered tasks the owner can check off, saving to work/TODO.txt only when asked. Use when the owner says "pecah jadi langkah", "urai tugas ini", "apa saja yang harus dikerjakan", or "bikin daftar tugas".
---

# split-task

## Purpose

Memecah permintaan pemilik yang memuat beberapa tugas sekaligus menjadi daftar langkah kecil yang berurutan dan bisa dicentang satu per satu. Skill ini membantu pemilik melihat urutan kerja, ketergantungan antartugas, dan hambatan informasi sebelum pekerjaan dimulai, tanpa memerlukan Python atau alat eksternal.

## Procedure

1. **Ekstrak seluruh permintaan.** Baca pesan pemilik satu kali secara utuh, lalu catat setiap permintaan terpisah, termasuk yang terselip di tengah kalimat. Jangan menghilangkan permintaan yang ada dan jangan menambah tugas baru di luar permintaan pemilik.
2. **Rumuskan setiap langkah dengan hasil nyata.** Mulai tiap baris dengan kata kerja dan sebutkan hasil yang terlihat (contoh: `Tulis ringkasan rapat ke catatan`, bukan `Tangani rapat`).
3. **Urutkan berdasarkan ketergantungan.** Letakkan tugas yang hasilnya dibutuhkan tugas lain di urutan lebih awal, lalu ikuti prioritas yang disebutkan pemilik.
4. **Tandai hambatan informasi.** Jika suatu tugas belum bisa dikerjakan karena data kurang, beri catatan singkat dalam bahasa biasa: `(menunggu: <informasi yang belum ada>)`.
5. **Tampilkan daftar bernomor.** Sajikan daftar dalam Bahasa Indonesia sederhana tanpa istilah teknis, nama alat, atau jalur berkas internal kecuali pemilik menyebutkannya lebih dulu:
   ```markdown
   1. <kata kerja> <hasil nyata>
   2. <kata kerja> <hasil nyata> (menunggu: <informasi yang belum ada>)
   ```
   Tutup dengan satu kalimat deklaratif yang menyebut langkah pertama yang akan dikerjakan.
6. **Perbarui status saat dikerjakan.** Begitu satu langkah selesai, tandai `[x]` di percakapan. Bila daftar disimpan ke `work/TODO.txt`, ubah `[ ]` pada baris milik daftar ini menjadi `[X]`.
7. **Simpan ke `work/TODO.txt` hanya bila diminta.** Tambahkan blok baru di bagian paling akhir `work/TODO.txt` (jangan menyisipkan di atas atau di tengah entri lama) dengan format berikut:
   ```text
   [ ] Tugas pengguna — YYYY-MM-DD — <topik singkat>:
       [ ] <langkah 1>
       [ ] <langkah 2>
   ```

## Rules & Boundaries

- Lewati skill ini jika permintaan pemilik hanya berupa satu tindakan tunggal yang sudah jelas.
- Dilarang menulis atau mengubah `work/TODO.txt` sebelum pemilik meminta menyimpannya (misalnya "simpan" atau "catat ke TODO").
- Dilarang menyunting, mengurutkan ulang, atau mengubah tanda centang baris milik blok tugas lain di `work/TODO.txt`.
- Semua operasi dilakukan dengan penyuntingan teks biasa; tidak butuh Python atau aplikasi pihak ketiga.

## Output & Verification

1. Setiap permintaan dalam pesan pemilik muncul tepat satu kali pada daftar bernomor, berurutan sesuai ketergantungan, dan berawal kata kerja.
2. Jika disimpan ke `work/TODO.txt`, baca ulang berkas tersebut untuk memastikan seluruh entri lama tidak berubah dan blok baru berada di baris paling bawah.
3. Laporkan daftar tugas kepada pemilik dalam Bahasa Indonesia sederhana dan nyatakan langkah pertama yang mulai dikerjakan.
