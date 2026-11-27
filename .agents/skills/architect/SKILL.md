---
name: architect
description: >-
  Design code architecture before implementation via five phases: Ground, Sketch types and module boundaries, Owner Approval gate, Implement, and Scrap on repeated friction. Use when the owner says "rancang arsitektur", "architect ini", "sketsa kontrak kode", or "desain modul dulu".
---

# architect

## Purpose

Memandu *agent* utama atau *supervisor* merancang kontrak arsitektur kode—cara pemanggil memakai modul, tipe data, *function signatures*, dan batas modul—sebelum menulis implementasi penuh, serta menetapkan syarat objektif kapan sketsa harus dibuang dan dirancang ulang (*Scrap*) alih-alih ditambal gejala. Seluruh proses berjalan bebas-Python dan lintas *harness* tanpa ketergantungan pada model atau plugin eksternal.

## Procedure

1. **Fase A — *Ground* (Pahami sistem nyata dan preseden).**
   - Untuk kode yang sudah ada: baca langsung subsistem yang tersentuh, alur data, dan alasan rancangan lamanya; menyebut nama berkas tanpa menelusuri perilaku nyata bukan *grounding*.
   - Untuk *build* baru (*greenfield*) atau arsitektur non-trivial: jalankan riset preseden arsitektur nyata (repositori *open-source* teruji di GitHub, dokumentasi resmi, RFC/*post-mortem*) lewat `browsing` untuk mempelajari pola, *anti-pattern*, *trade-off*, dan lisensi, lalu catat sumbernya ke `raw-kb/SOURCES.md`.
2. **Fase B — *Sketch* (Tulis kontrak sebelum isi).**
   - Susun sketsa mulai dari cara pemanggil menggunakan modul (*caller usage first*), lalu turunkan tipe data, *function signatures*, peta batas modul, dan tubuh `not implemented` atau *pseudocode*.
   - Untuk keputusan dengan *trade-off* besar, uji alternatif bentuk arsitektur secara adversarial melalui `debate` dan tutup pada satu sketsa rekomendasi melalui `recommend` (`>98%`).
3. **Fase C — *Agree* (Gerbang persetujuan pemilik wajib).**
   - Sajikan sketsa kontrak, alasan pemilihan, dan *trade-off* dalam ringkasan *Summary-First* kepada pemilik.
   - Tahan implementasi sampai pemilik menyatakan persetujuan eksplisit. Jika pemilik memberi koreksi bentuk, perlakukan sebagai bukti baru Fase A dan perbarui sketsa sebelum menulis kode.
4. **Fase D — *Implement* (Isi kode mengikuti kontrak).**
   - Ganti tubuh `not implemented` dan *pseudocode* dengan implementasi nyata yang patuh kontrak sketsa, lalu verifikasi secara deterministik (*typecheck*, tes otomatis, *build*).
   - Jangan menyembunyikan deviasi dari kontrak; setiap kebutuhan parameter atau batas baru yang tidak terduga wajib diangkat dan dinilai apakah sketsa perlu direvisi.
5. **Fase E — *Scrap* (Buang dan rancang ulang bila berpola friksi).**
   - Buang sketsa dan kembali ke Fase A–B jika muncul **pola** friksi berulang: *workaround* sejenis di beberapa tempat, *escape hatch* tipe (`any`, *cast* berulang) agar kompilasi lolos, pemanggil harus memahami aturan internal abstraksi, atau $\ge 2$ deviasi Fase D berbentuk sama.
   - Pangkas kompleksitas lebih dulu sebelum merancang ulang dari prinsip dasar.

## Rules & Boundaries

- Fase C (*Agree*) selalu wajib (*Human-Sovereign*); dilarang langsung mengeksekusi implementasi besar tanpa persetujuan pemilik.
- Dilarang mengikat proses ke plugin atau nama model *hardcoded* maupun direktori global; seluruh langkah berjalan lewat berkas teks dan skill lokal vault (`browsing`, `debate`, `recommend`, `anti-sycophancy`).
- Dilarang meniru kode atau arsitektur referensi secara buta (*cargo-cult*) tanpa memverifikasi kesesuaian konteks dan lisensi.
- Fakta eksekusi kode tetap tunduk pada verifikasi deterministik nyata, bukan keyakinan nalar semata.

## Output & Verification

1. Sketsa kontrak (*caller usage*, tipe data, *signatures*, peta modul) beserta alasan pilihan tercatat jelas sebelum implementasi dimulai dan disetujui pemilik.
2. Setiap sumber preseden eksternal tercatat pada `raw-kb/SOURCES.md` bila riset dilakukan.
3. Setelah Fase D, seluruh pemeriksaan deterministik (*typecheck*, tes, *build*) lulus dan deviasi kontrak yang muncul sudah ditangani atau dipicu ulang lewat Fase E.
