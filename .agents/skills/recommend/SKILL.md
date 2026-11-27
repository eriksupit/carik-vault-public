---
name: recommend
description: >-
  Compose debate, confidence (>98% on primary evidence), and brave to deliver one definitive best recommendation with upside, risk, and fit, banning unguided menus and interrogative closers. Use when the owner says "pilihkan yang terbaik", "menurutmu yang mana?", or "satu rekomendasi saja".
---

# recommend

## Purpose

Menyatukan tiga skill inti — `debate`, `confidence`, dan `brave` — ke dalam satu jalur keputusan tunggal untuk menghasilkan **satu rekomendasi terbaik** yang teruji. Skill ini dipakai setiap kali pemilik meminta pilihan terbaik, arah strategis, langkah berikutnya, atau putusan akhir dari perbandingan beberapa alternatif.

## Procedure

1. **Rumuskan keputusan dan batas keras.** Nyatakan persoalan keputusan dalam satu kalimat beserta batasan yang tidak bisa dilanggar, mengikuti langkah awal `debate`.
2. **Uji alternatif lewat `debate`.** Bandingkan alternatif melalui beberapa sudut pandang disiplin yang relevan beserta sanggahan silangnya. Jangan berhenti pada intuisi pertama dan jangan melewatkan tahap sanggahan.
3. **Verifikasi kandidat terpilih di ambang >98% lewat `confidence`.** Perlakukan hasil sintesis `debate` sebagai kandidat rekomendasi, lalu jalankan loop `confidence` dengan ambang dinaikkan menjadi **>98%** di atas bukti primer. Selama celah masih bisa ditutup agen, terus lakukan verifikasi bukti primer hingga melampaui 98%.
4. **Sajikan satu rekomendasi final lewat `brave` dan `anti-sycophancy`.**
   - Nyatakan secara tegas **satu rekomendasi terbaik** beserta alasannya.
   - Jika membandingkan dua atau lebih opsi dalam uraian, setiap opsi wajib memuat: (a) kelebihan, (b) risiko/kelemahan, dan (c) kapan opsi itu tepat dipakai, lalu tegaskan mengapa satu opsi terpilih paling sesuai untuk konteks pemilik.
   - Ikuti pedoman gaya Bahasa Indonesia yang aktif (`writing-style/prose-writing-style.md`).
   - Tutup dengan pernyataan deklaratif tentang keputusan dan langkah selanjutnya.
5. **Tangani kasus >98% yang mustahil dicapai mandiri.** Bila sisa celah murni merupakan fakta khusus pemilik (anggaran, selera, atau otorisasi), jalankan eskalasi Iterasi Transparan dari `confidence`: sebutkan celah spesifiknya dan tetap berikan satu rekomendasi sementara, bukan menu kosong.

## Rules & Boundaries

- Dilarang menyajikan menu opsi tanpa pilihan ("Pilih A atau B?", "Terserah Anda"). Jika dua opsi benar-benar setara secara teknis, nyatakan kesetaraan itu lalu tetap pilih satu sebagai rekomendasi utama.
- Dilarang menutup rekomendasi dengan pertanyaan validasi interogatif ("Setuju?", "Boleh saya lanjut?", "Approve atau koreksi?"). Jika tindakan berisiko tinggi menunggu izin pemilik, nyatakan penahanan secara deklaratif ("Eksekusi saya tahan sampai Anda menyatakan setuju.").
- Dilarang memakai kata menghindar seperti "tergantung kebutuhan" tanpa menentukan pilihan untuk konteks yang sedang dibahas.
- Skill ini adalah lapisan pengorkestra tipis; mekanisme panel tetap mengikuti `debate`, verifikasi bukti mengikuti `confidence`, dan keteguhan penyampaian mengikuti `brave`.

## Output & Verification

1. Jawaban memuat tepat satu rekomendasi utama yang ditopang bukti primer (>98% atau eskalasi celah khusus pemilik yang dinamai eksplisit).
2. Bila ada perbandingan opsi, setiap opsi mencantumkan kelebihan, risiko, dan kondisi cocoknya sebelum ditutup pada satu pilihan terbaik.
3. Tidak ada menu tanpa pilihan, tidak ada kata ragu, dan penutup berbentuk kalimat deklaratif.
