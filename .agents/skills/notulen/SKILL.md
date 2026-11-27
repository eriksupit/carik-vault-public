---
name: notulen
description: >-
  Turn a meeting or discussion into structured minutes that separate final decisions from pending proposals, saved to notes/meeting-minutes/YYYY-MM-DD--topic.md. Use when the owner says "catat rapat", "buat notulen", "rangkum diskusi tadi", or "simpan hasil meeting".
---

# notulen

## Purpose

Mengubah catatan rapat, transkrip, atau hasil diskusi menjadi dokumen notulen terstruktur yang memisahkan tegas antara keputusan final, usulan yang belum diputus, dan tindak lanjut. Seluruh proses memakai penulisan Markdown biasa tanpa bergantung pada Python atau perangkat lunak tambahan.

## Procedure

1. **Kumpulkan sumber.** Gunakan hanya isi percakapan, transkrip yang ditempel, atau catatan dari pemilik. Jika sumber kosong atau terlalu singkat sehingga topik dan poin bahasan belum tampak, jangan menulis berkas; tanyakan secara langsung apa topik dan poin rapatnya.
2. **Catat konteks dan argumen.** Susun bagian **Masalah & konteks** (latar belakang pertemuan) dan **Argumen kunci** (posisi utama beserta nama penyampainya). Jangan menilai pihak mana yang menang kecuali sumber menyatakan demikian.
3. **Pisahkan hasil ke tiga kategori tegas.** Masukkan setiap poin hasil rapat ke tepat satu kelompok:
   - **Keputusan:** disetujui secara eksplisit oleh pihak berwenang; cantumkan nama penyetuju atau kutipan ringkas persetujuannya.
   - **Usulan pending:** sudah dibahas tetapi belum disetujui atau baru disetujui bersyarat. Poin yang samar wajib masuk ke sini, bukan ke Keputusan.
   - **Tindak lanjut:** tugas konkret beserta penanggung jawab dan tenggatnya. Isi `belum ditentukan` bila sumber tidak menyebut nama atau tanggal.
4. **Tulis berkas notulen.** Simpan ke `notes/meeting-minutes/YYYY-MM-DD--<slug-topik>.md` (buat folder bila belum ada). Jika nama berkas sudah terpakai, tambahkan akhiran angka (`-2`, `-3`) alih-alih menimpa berkas lama. Gunakan templat berikut:
   ```markdown
   ---
   title: Notulen — <topik>
   date: YYYY-MM-DD
   updated: YYYY-MM-DD
   type: meeting-minutes
   status: active
   tags:
     - notulen
   ---

   # Notulen — <topik>

   - Tanggal: YYYY-MM-DD
   - Peserta: <nama peserta, atau "tidak disebut">
   - Sumber: <percakapan / transkrip / catatan pemilik>

   ## Masalah & konteks
   - <latar belakang pertemuan>

   ## Argumen kunci
   - <posisi utama> — disampaikan oleh <nama>

   ## Keputusan
   - <keputusan final> — disetujui oleh <nama>

   ## Usulan pending
   - <usulan> — alasan belum diputus: <alasan>

   ## Tindak lanjut
   - [ ] <tugas> — penanggung jawab: <nama>, tenggat: <tanggal>
   ```
   Biarkan bagian yang kosong tetap ada dengan isi `- Tidak ada.` daripada menghapus judul bagiannya.
5. **Baca ulang berkas** sebelum melaporkan hasilnya kepada pemilik.

## Rules & Boundaries

- Dilarang mengarang nama peserta, angka, keputusan, atau tenggat yang tidak ada di sumber.
- Poin yang masih mengandung keraguan tidak boleh dimasukkan ke bagian **Keputusan**.
- Dilarang menimpa berkas notulen yang sudah ada di `notes/meeting-minutes/`.
- Dilarang memasukkan jargon mesin (persentase keyakinan, nama model, nama tool) ke dalam notulen maupun laporan obrolan.

## Output & Verification

1. Berkas `notes/meeting-minutes/YYYY-MM-DD--<slug-topik>.md` ada, memiliki frontmatter lengkap, dan memuat kelima bagian tubuh (`Masalah & konteks`, `Argumen kunci`, `Keputusan`, `Usulan pending`, `Tindak lanjut`).
2. Setiap klaim di dalam notulen cocok dengan sumber tanpa tambahan di luar sumber.
3. Laporkan kepada pemilik dalam Bahasa Indonesia sederhana: lokasi berkas serta jumlah keputusan, usulan pending, dan tindak lanjut yang tercatat.
