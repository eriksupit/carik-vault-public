---
name: carik-guided-goal
description: >-
  Guide non-technical owners through a short one-question-per-turn interview to turn a vague request into a checkable ## Goal Contract without writing any files. Use when the owner says "mulai dari mana", "rumuskan tugas", or "bantu saya merumuskan".
---

# carik-guided-goal

## Purpose

Membantu pemilik yang membawa permintaan kabur — belum tahu harus mulai dari mana atau belum tahu cara merumuskan langkah kerjanya — untuk menyusun tepat satu blok `## Goal Contract` yang jelas dan dapat diperiksa. Skill ini menjembatani permintaan awal yang masih mentah sebelum masuk ke `goal`, tanpa menulis berkas apa pun selama wawancara berlangsung.

Gunakan skill ini saat pemilik belum memiliki sasaran terukur atau batas lingkup yang jelas. Jika permintaan sudah terarah tetapi kurang satu fakta kunci atau mengandung ambiguitas sempit, gunakan `clarify`. Jika permintaan sudah jelas dan siap dikunci tanpa wawancara, gunakan `define-goal`.

## Procedure

1. **Tangkap pesan awal sebagai data.** Catat fakta yang sudah disampaikan pemilik pada pesan awal sebagai jawaban untuk dimensi terkait, dan jangan tanyakan ulang fakta yang sudah jelas. Periksa maksud eksplisit pemilik lebih dulu: jika pemilik secara eksplisit meminta memecah banyak tugas atau membuat skill baru, akhiri wawancara segera tanpa menulis berkas apa pun lalu beralih ke `split-task` atau `create-carik-skill`.
2. **Gali lima dimensi umum satu pertanyaan atomik per giliran.** Ajukan tepat satu pertanyaan pendek, konkret, dan atomik atas satu aspek tunggal pada setiap giliran — dilarang menggabungkan dua hal dalam satu kalimat tanya (misalnya jangan menanyakan jenis tulisan sekaligus pembaca, atau pokok wajib sekaligus pengecualian dalam satu giliran; jika keduanya belum jelas, bagi ke giliran terpisah), tanpa memanggil tool apa pun dan tanpa basa-basi pembuka atau pujian. Batasi wawancara pada 5 sampai 6 giliran lintas masalah harian (perencanaan, perapian catatan, analisis dokumen, pengambilan keputusan, atau penulisan), lalu berhenti lebih awal begitu seluruh dimensi jelas:
   - **Dimensi 1 — Tujuan inti:** hasil nyata yang ingin dicapai pemilik.
   - **Dimensi 2 — Konteks dan pembaca (bila relevan):** untuk siapa hasil dipakai dan bahan apa yang sudah ada. Untuk tugas tulisan, wajib gali dua fakta (**jenis tulisan spesifik** — istilah umum seperti "artikel" atau "tulisan" belum cukup; pastikan bentuknya seperti panduan praktis, opini, laporan kegiatan, atau pengumuman — dan **pembaca sasaran**), sedangkan **nada bahasa** bersifat opsional jika belum muncul secara alami.
   - **Dimensi 3 — Cakupan dan batasan:** fokus pada satu hal yang belum jelas — pokok yang wajib masuk atau hal yang sengaja dikecualikan — jangan gabungkan keduanya dalam satu pertanyaan.
   - **Dimensi 4 — Ukuran selesai yang teramati:** fakta konkret yang menandai pekerjaan beres tanpa tafsir subjektif.
   - **Dimensi 5 — Cara memeriksa:** cara pemilik atau agen memastikan ukuran selesai tersebut terpenuhi.
3. **Terapkan aturan berhenti pada giliran ke-6.** Jika giliran ke-6 selesai tetapi `Completion condition` atau fakta kunci belum dapat diuji benar-salahnya, hentikan wawancara segera. Sebutkan fakta spesifik yang masih kurang, dan jangan menerbitkan blok `## Goal Contract` ataupun mulai bekerja.
4. **Terbitkan tepat satu blok `## Goal Contract` dan tahan eksekusi.** Begitu kelima dimensi terisi lengkap dan dapat diuji, tampilkan tepat satu blok `## Goal Contract` dengan lima label literal Inggris yang identik dengan `define-goal` (tanpa label ke-6 `Stop conditions`):
   ```markdown
   ## Goal Contract

   - **Objective:** <tujuan utama dalam satu kalimat>
   - **Completion condition:** <syarat selesai benar/salah yang dapat diperiksa langsung>
   - **Evaluator:** <cara pemeriksaan atau bukti yang menentukan selesai>
   - **Out of scope:** <hal yang sengaja tidak dikerjakan>
   - **Ultimate goal:** <tujuan lebih besar dari pemilik, atau "not yet defined by user">
   ```
   Tutup blok kontrak tepat dengan kalimat deklaratif baku berikut:
   > Eksekusi saya tahan sampai Anda menyetujui kontrak ini.
5. **Kunci izin versi terakhir sebelum meneruskan ke `goal`.** Jika pemilik menyampaikan koreksi atas isi kontrak, jangan anggap koreksi tersebut sebagai persetujuan; terbitkan blok `## Goal Contract` revisi dan tunggu persetujuan baru. Setelah pemilik menyetujui **versi terakhir** blok `## Goal Contract` secara eksplisit, teruskan baris `Completion condition` secara verbatim (tanpa pelonggaran) ke skill `goal` untuk memulai eksekusi.

## Rules & Boundaries

- **Nol penulisan berkas:** Dilarang membuat, menyunting, atau menghapus berkas apa pun (termasuk `work/drafts/` atau `work/TODO.txt`) serta dilarang memanggil tool mutasi selama wawancara berlangsung hingga versi terakhir kontrak disetujui.
- **Disiplin satu pertanyaan atomik dan penutup deklaratif:** Dilarang mengajukan lebih dari satu pertanyaan atau pertanyaan majemuk (menggabungkan dua aspek dalam satu giliran), melampaui 6 giliran wawancara, menulis basa-basi atau pujian, atau menutup blok kontrak dengan pertanyaan validasi maupun menu opsi (tunduk pada `anti-sycophancy`).
- **Kontrak ketat 5 label:** Dilarang menambah label ke-6 `Stop conditions` karena kondisi berhenti saat terhambat data atau izin pemilik sudah ditangani eskalasi Kelas 3 pada skill `goal`. Dilarang menerbitkan `## Goal Contract` jika batas 6 giliran habis dengan fakta kunci belum teruji.
- **Maksud eksplisit dan perpindahan bersih:** Maksud eksplisit pemilik selalu mengalahkan frasa generik. Saat beralih ke `split-task` atau `create-carik-skill`, akhiri wawancara `carik-guided-goal` tanpa menulis berkas apa pun; seluruh izin tulis sesudahnya tunduk penuh pada aturan skill tujuan.
- **Kunci izin `goal` sebagai kontrak percakapan:** Tahan setiap panggilan `goal` sebelum persetujuan eksplisit atas versi terakhir blok `## Goal Contract`. Aturan 5 label dan penahanan eksekusi ini berlaku sebagai kontrak percakapan lintas harness tanpa bergantung pada hook.
- **Kemandirian lintas harness:** Jalur kerja berjalan 100% melalui percakapan teks native bebas-Python, tanpa ketergantungan pada direktori global, aplikasi desktop Obsidian sebagai runtime, maupun tool runtime milik harness tertentu.

## Output & Verification

1. Keluaran utama adalah tepat satu blok `## Goal Contract` berisi 5 label literal Inggris (`Objective`, `Completion condition`, `Evaluator`, `Out of scope`, `Ultimate goal`) ditutup kalimat `"Eksekusi saya tahan sampai Anda menyetujui kontrak ini."`, atau pesan berhenti pada giliran ke-6 yang menyebut fakta spesifik yang masih kurang tanpa menerbitkan kontrak.
2. Sebelum menampilkan blok kontrak, periksa seluruh syarat berikut: jumlah giliran tidak melebihi 6, nol berkas dibuat atau diubah, 5 label literal Inggris lengkap tanpa `Stop conditions`, `Completion condition` dapat diuji benar-salahnya secara langsung, penutup bersifat deklaratif tanpa pertanyaan, dan untuk tugas tulisan telah mencakup jenis tulisan spesifik (bukan sekadar kata umum seperti artikel/tulisan) serta pembaca sasaran.
3. Setelah pemilik menyetujui versi terakhir blok kontrak secara eksplisit, pastikan baris `Completion condition` diteruskan secara verbatim ke skill `goal`.
