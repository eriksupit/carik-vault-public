---
name: simplify
description: >-
  Choose the smallest complete change and prefer removing unnecessary abstractions, layers, or complexity without skipping scope or verification. Use when the owner says "jangan bikin ribet", "yang simpel aja", "sederhanakan strukturnya", or "buat lebih ringkas".
---

# simplify

## Purpose

Menahan dorongan rekayasa berlebihan dengan memilih perubahan terkecil yang menyelesaikan masalah secara utuh. Skill ini mengutamakan penghapusan kompleksitas, struktur yang datar, dan keterbacaan bagi manusia yang merawat berkas atau kode di kemudian hari, tanpa mengurangi cakupan tugas maupun verifikasi.

## Procedure

1. **Cari yang bisa dihapus sebelum menambah.** Saat merancang atau merapikan solusi, periksa dulu bagian mubazir, kode mati, lapisan perantara, atau aturan duplikat yang dapat dipangkas.
2. **Jaga struktur tetap datar.** Hindari abstraksi berlapis-lapis. Jika menjawab satu pertanyaan sederhana mengharuskan penelusuran melintasi lebih dari tiga berkas atau lapisan, ratakan strukturnya.
3. **Satukan keputusan di satu sumber kebenaran.** Jangan mengulang logika atau pilihan yang sama di banyak tempat; simpan di satu titik dan kirim hasilnya sebagai nilai sederhana.
4. **Kecilkan diff secara sadar.** Pilih perubahan paling ringkas yang langsung menutup akar masalah. Sedikit baris yang jelas selalu mengalahkan kerangka panjang yang terasa "elegan" tetapi melelahkan dirawat.
5. **Pertanyakan penerusan sinyal berlapis.** Jika sebuah rencana memaksa pelemparan parameter baru menembus banyak tipe, skema, atau lapisan pipa, berhenti sejenak dan cari jalur yang lebih langsung.
6. **Bersihkan sisa perubahan.** Hapus kode atau konfigurasi mati yang timbul akibat perubahan saat ini, lalu jalankan seluruh pemeriksaan dan uji yang relevan.

## Rules & Boundaries

- Sederhana berarti efisien, bukan ceroboh: dilarang melewatkan cakupan yang diminta pemilik, pengujian, atau verifikasi akhir.
- Hapus kode mati yang langsung dihasilkan oleh perubahan saat ini; minta persetujuan pemilik sebelum menghapus kode atau berkas lama di luar lingkup perubahan.
- Dilarang menambah ketergantungan baru, skrip pembantu, atau abstraksi generik untuk masalah yang hanya muncul satu kali.
- Pegangan utama: jika manusia akan merasa lelah membaca dan merawat hasilnya, rancangannya terlalu rumit dan harus disederhanakan.

## Output & Verification

1. Bandingkan diff akhir terhadap tujuan tugas: setiap baris tambahan memiliki alasan fungsional langsung dan tidak ada lapisan perantara tak perlu.
2. Seluruh cakupan permintaan terpenuhi dan verifikasi atau uji yang relevan lulus tanpa pengecualian.
3. Laporkan perubahan secara ringkas kepada pemilik beserta bagian kompleksitas yang berhasil dipangkas dan bukti verifikasinya.
