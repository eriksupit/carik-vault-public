---
name: goal
description: >-
  Drive a task across repeated passes until the verbatim Completion condition from define-goal holds, classifying each gap as self-closable or owner-only before iterating or escalating. Use when the owner says "/goal", "kerjakan sampai beres", "jangan berhenti sampai", or "ulang sampai tuntas".
---

# goal

## Purpose

Menjalankan mesin iterasi kerja sampai `Completion condition` yang ditetapkan secara verbatim oleh `define-goal` benar-benar terpenuhi. Skill ini hanya mengatur mekanika perulangan: ambang bukti >95% dipegang `confidence`, keteguhan kerja dipegang `brave`, dan bentuk penyampaian akhir dipegang `anti-sycophancy`.

## Procedure

1. **Kunci `Completion condition` secara verbatim.** Ambil syarat selesai langsung dari `define-goal` (atau kunci ulang menjadi pernyataan benar/salah yang dapat diperiksa sebelum putaran pertama jika dipanggil langsung). Jangan melonggarkan syarat di tengah jalan.
2. **Kerjakan satu putaran nyata.** Hasilkan artefak, suntingan, pengukuran, atau temuan bukti yang dapat diperiksa. Perlakukan hasil putaran sebagai **kandidat**, bukan keluaran final.
3. **Evaluasi kandidat bagian demi bagian.** Bandingkan kandidat secara ketat terhadap setiap unsur pada `Completion condition`.
   - Seluruh syarat terpenuhi → lanjut ke langkah 6.
   - Masih ada bagian belum terpenuhi → sebutkan bagian spesifik yang kurang, lalu lanjut ke langkah 4.
4. **Klasifikasikan setiap celah yang tersisa:**
   - **Kelas 1 — Bisa ditutup sendiri sekarang:** cukup dengan membaca berkas, menjalankan perintah, atau memperbaiki artefak. Kerjakan tindakan paling berdampak, perbarui kandidat, lalu kembali ke langkah 3.
   - **Kelas 2 — Menunggu keadaan eksternal:** fakta penentu belum tersedia dan menunggu proses luar selesai. Jangan mengulang penalaran kosong; tunggu dengan batas waktu/percobaan yang jelas, atau catat status tertunda di `.agents/Context.md` lalu tutup putaran secara deklaratif.
   - **Kelas 3 — Khusus pemilik:** membutuhkan preferensi, izin, atau data yang hanya dimiliki pemilik. Lanjut ke langkah 7.
5. **Ulangi sampai tuntas.** Jalankan putaran berikutnya terhadap celah Kelas 1. Setiap putaran wajib menambah bukti baru yang dapat diperiksa; bila sebuah putaran tidak menghasilkan bukti baru, klasifikasi ulang celahnya ke Kelas 2 atau Kelas 3.
6. **Akhiri saat syarat terpenuhi penuh.** Sampaikan hasil akhir melalui disiplin `anti-sycophancy`: satu laporan lugas yang menyebut syarat mana yang terpenuhi dan bukti verifikasinya, ditutup secara deklaratif.
7. **Eskalasi terukur (hanya untuk celah Kelas 3).** Jika sisa celah murni milik pemilik, tampilkan empat hal: (a) kandidat terbaik saat ini, (b) celah spesifik yang menghambat, (c) masukan atau izin terkecil yang dibutuhkan, dan (d) satu rekomendasi sementara yang siap dijalankan begitu celah tertutup.

## Rules & Boundaries

- Dilarang mengarang atau memperlemah `Completion condition` yang diberikan `define-goal`.
- Dilarang berhenti di tengah jalan dengan alasan "sudah cukup baik", "memakan waktu lama", atau menyembunyikan celah di balik kata ragu.
- Pemenuhan sebagian bukanlah selesai; satu unsur gagal berarti putaran wajib dilanjutkan.
- Dilarang menghentikan kerja untuk bertanya ke pemilik bila celah masih termasuk Kelas 1 yang bisa ditutup dengan membaca berkas atau menjalankan pemeriksaan.

## Output & Verification

1. Setiap unsur dalam `Completion condition` memiliki bukti verifikasi langsung bahwa nilainya terpenuhi (atau tercatat sebagai eskalasi Kelas 3 yang terukur).
2. Setiap putaran kerja tercatat menambah bukti baru, tanpa putaran kosong atau tambalan sementara.
3. Laporan penutup bersifat deklaratif dan menyebut bukti pemenuhan kondisi selesai secara langsung.
