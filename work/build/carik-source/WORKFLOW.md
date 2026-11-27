---
title: Alur Kerja Spasial 5-Folder Carik Vault
date: 2026-11-23
updated: 2026-11-26
type: workflow
status: active
tags:
  - workflow
  - carik-vault
  - spasial
---

# Alur Kerja Spasial 5-Folder Carik Vault

Carik Vault menata perjalanan setiap pekerjaan secara visual melalui **5 folder berurutan** di bawah `work/`. Anda selalu tahu status sebuah dokumen cukup dengan melihat di folder mana berkas itu berada, tanpa aplikasi manajemen proyek tambahan.

## 1. Lima Folder Spasial di `work/`

| Urutan | Folder | Peran | Kapan Berkas Pindah ke Tahap Berikutnya |
|---|---|---|---|
| **1** | `work/inbox/` | Laci penampungan awal: ide mentah, potongan catatan, daftar permintaan, atau tugas yang belum dipilah. | Setelah tujuan dan batasnya cukup jelas untuk dirumuskan. |
| **2** | `work/concept/` | Ruang perancangan: kerangka gagasan, struktur dokumen, rencana kerja, atau ringkasan konsep. | Setelah pemilik menyetujui arah dan struktur konsepnya. |
| **3** | `work/drafts/` | Meja penyuntingan: naskah berjalan, draf laporan, analisis, atau dokumen yang sedang disempurnakan. | Setelah isi diverifikasi terhadap sumber dan disetujui pemilik. |
| **4** | `work/canon/` | Lemari hasil final: versi sah yang siap dibagikan, dicetak, atau dijadikan rujukan tetap. | Ketika versi baru menggantikan versi lama (versi lama dipindah ke `archive/`). |
| **5** | `work/archive/` | Rak arsip: versi terdahulu yang sudah digantikan dan berkas cadangan `.zip` (`backup-drive`). | Disimpan utuh sebagai jejak riwayat; jangan dihapus tanpa izin pemilik. |

## 2. Aturan Bahan Sumber (`raw-kb/`)

- Simpan berkas rujukan asli (PDF, transkrip, dokumen pihak ketiga) di `raw-kb/user-provided/` atau hasil riset agen di `raw-kb/agent-acquired/`. Seluruh pendaftaran dan pencatatan entri di `raw-kb/SOURCES.md` diisi secara otomatis oleh agen; pengguna awam cukup menaruh berkasnya atau menyebut sumbernya di percakapan tanpa perlu mengedit `raw-kb/SOURCES.md` sendiri.
- Untuk berkas PDF di `raw-kb/`, agen mengonversinya lebih dulu menjadi turunan Markdown lewat `pdf-read` (atau `pdf-ocr` untuk hasil pindai) sebelum isinya dikutip.

## 3. Aturan Menulis & Persetujuan

1. **Tentukan tujuan sebelum kerja besar:** untuk pekerjaan bertahap, gunakan `define-goal` agar kondisi selesai dan batas luar cakupannya jelas sejak awal.
2. **Ringkas dulu sebelum menulis berkas penting:** sebelum agen menulis ke `work/concept/`, `work/drafts/`, atau `work/canon/`, agen menyampaikan ringkasan tujuan, poin utama, dan jalur berkas sasaran.
3. **Kontrak frontmatter catatan (diisi otomatis oleh agen):** setiap catatan Markdown baru diawali 6 properti YAML dasar (`title`, `date`, `updated`, `type`, `status`, `tags`) dengan format tanggal `YYYY-MM-DD`. Seluruh properti YAML *frontmatter* ini dibuat dan diperbarui otomatis oleh agen setiap kali menulis atau merapikan berkas; pengguna awam bebas menulis catatan biasa tanpa perlu mengetik format YAML secara manual.
4. **Pelihara versi lama:** saat hasil final di `work/canon/` digantikan oleh revisi baru, pindahkan versi lama ke `work/archive/` alih-alih menghapusnya.

## 4. Kontinuitas Antarsesi

- Fakta jangka panjang dicatat ke `.agents/memory/<fakta>.md` dan dirangkum di `.agents/Memory.md` lewat skill `remember`.
- Peristiwa penting dan posisi kerja sesi dicatat tambah-saja (*append-only*) di `.agents/Context.md`, sedangkan koreksi dan pelajaran di `.agents/Lessons.md` lewat skill `session-log`.
- Saat menutup sesi kerja yang akan dilanjutkan lain waktu, buat pasangan berkas serah-terima di `handoff/` lewat skill `handoff`, lalu lanjutkan di sesi berikutnya lewat skill `bootstrap`.
