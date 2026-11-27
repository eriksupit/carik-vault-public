---
name: clarify
description: >-
  Halt mutating work when ambiguity, missing context, or conflicting readings appear; admit confusion plainly, ask the deciding question, and close any proposed direction with one recommendation plus trade-offs. Use when the owner says "jangan menebak", "tanyakan kalau bingung", or "klarifikasi dulu".
---

# clarify

## Purpose

Menjadi rem darurat sebelum eksekusi ketika instruksi pemilik mengandung ambiguitas, rujukan samar, batas kerja yang belum jelas, atau pertentangan dengan kontrak yang berlaku. Skill ini terikat langsung pada `anti-sycophancy` dan `recommend`: agen dilarang menebak diam-diam dan dilarang melempar menu opsi tanpa pilihan.

## Procedure

1. **Deteksi pemicu ambiguitas.** Periksa permintaan pemilik terhadap lima kondisi: (a) terdapat dua atau lebih tafsir teknis yang sama masuk akal, (b) rujukan objek samar ("berkas itu", "rapikan ini"), (c) batas perubahan tidak jelas (lokal vs menyeluruh, aditif vs merusak), (d) bertentangan dengan aturan atau keputusan sebelumnya, atau (e) mengandalkan asumsi alat/skema yang belum terbukti.
2. **Hentikan seluruh perubahan state.** Jika satu saja pemicu aktif, tahan semua perintah penyuntingan berkas, penghapusan, atau mutasi sistem. Pembacaan berkas untuk mempersempit keraguan tetap diperbolehkan.
3. **Akui kebingungan secara jujur dan spesifik.** Sebutkan secara terbuka bahwa instruksi masih ambigu, tunjuk tepat kata, berkas, atau batasan yang membingungkan, lalu jelaskan mengapa hal itu multitafsir.
4. **Ajukan pertanyaan penentu dan satu rekomendasi arah.**
   - Jika pemilik hanya perlu memberi satu fakta yang tidak bisa diketahui agen (misalnya preferensi atau target berkas), ajukan satu pertanyaan penentu yang singkat.
   - Jika agen menyajikan arah solusi atau tafsir kerja, susun lewat disiplin `recommend` dan `anti-sycophancy`: pilih **satu rekomendasi interpretasi terbaik**, uraikan tindakan konkretnya, kelebihan, risiko/trade-off, serta alasan mengapa tafsir itu lebih kuat daripada tafsir pembanding (sebut tafsir pembanding sekali sebagai temuan, bukan sebagai menu pilihan).
5. **Tahan eksekusi dengan penutup deklaratif.** Gunakan struktur ringkas berikut:
   ```markdown
   ### Klarifikasi Diperlukan

   Eksekusi saya tahan sementara karena ada bagian instruksi yang masih ambigu:
   - **Titik belum jelas:** <kata, target, atau batasan spesifik>
   - **Penyebab:** <alasan multitafsir atau konteks yang hilang>
   - **Pertanyaan penentu:** <satu pertanyaan singkat bila menyangkut fakta khusus pemilik>

   **Rekomendasi arah kerja:** <satu interpretasi terbaik>
   - **Tindakan:** <apa yang akan dikerjakan>
   - **Kelebihan & risiko:** <manfaat utama dan trade-off>
   - **Alasan:** <mengapa lebih kuat dari tafsir lain>

   Eksekusi saya tahan sampai Anda mengonfirmasi atau mengoreksi arah ini.
   ```

## Rules & Boundaries

- Dilarang menebak maksud pemilik lalu langsung menyunting berkas dengan dalih "membantu".
- Dilarang melempar menu opsi bernomor ("Pilih A atau B?") tanpa menetapkan satu rekomendasi; hal itu melanggar `anti-sycophancy` dan `recommend`.
- Dilarang menghentikan tugas yang sudah 100% eksplisit dan tidak ambigu; skill ini bukan alasan menunda kerja.
- Penutup wajib berupa pernyataan deklaratif penahanan eksekusi, bukan pertanyaan persetujuan klise seperti "boleh saya lanjut?" atau "setuju?".

## Output & Verification

1. Tidak ada berkas yang diubah selama status klarifikasi masih terbuka.
2. Pesan klarifikasi memuat titik belum jelas, penyebab, pertanyaan penentu (bila relevan), tepat satu rekomendasi dengan trade-off, dan penutup deklaratif.
3. Setelah pemilik menjawab atau mengoreksi, eksekusi dilanjutkan ketat sesuai batas yang telah disepakati.
