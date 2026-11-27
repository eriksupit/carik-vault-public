---
name: debate
description: >-
  Convene an adversarial multi-perspective forum with a mandatory red-team seat after two repeated mistakes, an owner complaint, or a high-trade-off decision, closing on one verdict via recommend. Use when the owner says "forum debat", "audit multi-perspektif", "red-team ini", or "cari jalan keluar strategis".
---

# debate

## Purpose

Menggelar forum dialektis multi-perspektif untuk menguji keputusan arsitektur, strategi, rancangan, atau klaim penting sebelum diterima. Forum ini wajib dijalankan setelah **dua kesalahan berulang pada masalah yang sama**, saat **pemilik mengeluhkan pendekatan berjalan**, atau ketika keputusan memiliki trade-off nyata lintas disiplin, agar keputusan lahir dari benturan bukti dan bukan intuisi pertama agen.

## Procedure

1. **Rumuskan masalah dan batas keras (Moderator).** Nyatakan persoalan, keputusan yang harus diambil, dan batasan wajib dalam satu kalimat. Jika masih ambigu, selesaikan dulu lewat `clarify` sebelum memulai forum.
2. **Susun daftar panel dan kursi Red Team wajib.** Pilih 3–5 disiplin konkret yang relevan dengan masalah (misalnya insinyur keamanan, arsitek data, perancang UX) dengan minimal satu sudut pandang yang cenderung menentang jawaban yang tampak paling mudah. Tambahkan **satu kursi wajib Devil's Advocate / Red Team** yang tidak memihak opsi mana pun dan bertugas khusus membongkar kelemahan temuan panelis lain.
3. **Putaran 1 — Posisi awal independen.** Minta setiap panelis disiplin (via subagen paralel bila tersedia, atau analisis terpisah yang ketat bila mode agen tunggal) menyusun: (a) satu posisi pilihan, (b) alasan berbasis bukti konkret (`file:line`, data, preseden), dan (c) keberatan terkuat terhadap posisinya sendiri beserta jawabannya. Kursi Red Team belum berbicara di Putaran 1.
4. **Putaran 2 — Sanggahan silang dan serangan Red Team.** Berikan seluruh posisi Putaran 1 kepada tiap panelis disiplin untuk saling menyanggah. Bersamaan dengan itu, jalankan kursi Red Team untuk menguji setiap temuan dengan empat poin: serangan fakta, serangan asumsi tersembunyi, titik buta, dan vonis (`DEMOLISHED`, `WOUNDED` beserta syarat perbaikan, atau `SURVIVES`). Maksimal dua putaran sanggahan.
5. **Resolusi kebuntuan (bila posisi tetap terkunci).** Dilarang mengakhiri forum dengan "para ahli tidak sepakat". Jika seri, ekstrak satu syarat non-negosiabel dari tiap kubu, rancang jalur ketiga yang memenuhi syarat-syarat itu sekaligus (atau sebutkan syarat paling lemah yang dikorbankan beserta alasannya), lalu uji risiko dampaknya sebelum diadopsi.
6. **Sintesis dan putusan tunggal lewat `recommend`.** Jawab daftar serangan Red Team lebih dulu (setiap butir diakui atau dibantah dengan bukti primer). Timbang argumen berdasarkan kekuatan bukti, bukan jumlah suara. Serahkan hasil sintesis ke `recommend` (ambang `confidence` >98% + penyampaian `brave` dan `anti-sycophancy`) untuk menghasilkan **satu rekomendasi terbaik** dengan penutup deklaratif.

## Rules & Boundaries

- Lewati forum ini untuk pertanyaan fakta tunggal yang langsung terjawab dengan membaca satu berkas.
- Moderator tidak boleh ikut berargumen sebagai panelis; tugasnya membingkai, menimbang bukti, dan menyintesis.
- Kursi Red Team bersifat wajib tanpa pengecualian di semua harness; forum tanpa serangan Red Team dan jawaban atas daftar serangannya tidak sah.
- Jika semua panelis langsung sepakat di Putaran 1, susunan panel terlalu sempit — ganti satu kursi dengan perspektif penantang sebelum lanjut.
- Dilarang menampilkan transkrip mentah panelis ke pemilik; sampaikan sintesis, konflik utama, argumen penentu, dan satu keputusan akhir.

## Output & Verification

1. Daftar disiplin panelis dan kursi Red Team tercakup, dan seluruh butir serangan Red Team telah dijawab (diakui atau dibantah dengan bukti).
2. Tidak ada jalan buntu yang dilempar balik ke pemilik dan tidak ada menu opsi tanpa pilihan.
3. Keputusan akhir disalurkan melalui `recommend`, mencantumkan kelebihan/risiko serta alasan pemilihan, dan ditutup secara deklaratif.
