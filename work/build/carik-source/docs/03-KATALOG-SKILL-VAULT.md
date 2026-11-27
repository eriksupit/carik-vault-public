---
title: Katalog Lengkap 30 Skill Carik Vault dan Cara Pakainya
date: 2026-11-26
updated: 2026-11-26
type: guide
status: active
tags:
  - panduan-user
  - katalog-skill
  - carik-vault
---

# Katalog Lengkap 30 Skill Carik Vault dan Cara Pakainya

Seluruh 30 skill di dalam `.agents/skills/` adalah panduan kerja terstruktur yang dibaca agen AI hanya saat relevan dengan permintaan Anda. Sebanyak 28 skill teks dan ingatan berjalan penuh tanpa Python maupun terminal, sedangkan 2 skill olah PDF lokal (`pdf-read` dan `pdf-ocr`) membutuhkan `python3` dan alat lokal. Anda tidak perlu menghafal nama teknis skill. Cukup tulis kebutuhan Anda dalam Bahasa Indonesia sehari-hari, lalu agen memilih dan menjalankan prosedur skill yang sesuai.

Setiap skill di bawah diberi satu dari tiga label tingkat pakai:

- **`[Harian]`:** skill yang paling sering Anda picu langsung dalam pekerjaan sehari-hari.
- **`[Berkala]`:** skill yang Anda picu saat menghadapi kebutuhan khusus seperti mengolah PDF, membuat diagram, mencadangkan vault, atau memperbarui Carik.
- **`[Otomatis / Koreksi Agen]`:** skill disiplin penalaran dan pencatatan yang umumnya dijalankan agen di latar belakang, atau Anda picu saat ingin mengoreksi ketelitian agen.

## Kelompok 1: Kerja Harian (9 Skill)

### 1. `carik-guided-goal` `[Harian]`
- **Fungsi:** Mewawancarai Anda satu pertanyaan per giliran untuk mengubah ide yang masih kabur menjadi tujuan kerja yang terukur tanpa langsung menulis berkas.
- **Kapan dipakai:** Saat Anda baru mulai dan belum yakin harus mengerjakan apa lebih dulu.
- **Contoh kalimat pemicu:** `"Saya belum tahu mulai dari mana, bantu saya merumuskan tugas ini."`

### 2. `browsing` `[Harian]`
- **Fungsi:** Mencari informasi di web lewat 3 jalur bertahap sesuai kemampuan harness: (1) alat browser bawaan harness bila aktif, (2) jalur kolaboratif bersama user yang membuka URL di browsernya lalu menyalin teks relevan atau menyimpan berkas ke `raw-kb/user-provided/`, atau (3) skrip bantu CLI opsional saat `python3` tersedia. Hasil riset diringkas ke `notes/` dan sumber dicatat ke `raw-kb/SOURCES.md`.
- **Kapan dipakai:** Saat Anda butuh data terbaru dari situs web resmi, artikel, atau dokumen daring.
- **Contoh kalimat pemicu:** `"Cari data terbaru soal regulasi ini di browser, lalu simpan ringkasan dan sumbernya."`

### 3. `split-task` `[Harian]`
- **Fungsi:** Memecah permintaan besar atau rumit menjadi daftar langkah kecil yang berurutan dan mudah dicentang.
- **Kapan dipakai:** Saat sebuah pekerjaan terasa menumpuk dan perlu dipecah menjadi urutan kerja yang jelas.
- **Contoh kalimat pemicu:** `"Pecah jadi langkah semua pekerjaan ini, lalu urutkan dari yang paling penting."`

### 4. `notulen` `[Harian]`
- **Fungsi:** Menyusun catatan rapat terstruktur di `notes/meeting-minutes/YYYY-MM-DD--<topik>.md` yang memisahkan tegas keputusan final dari usulan tertunda.
- **Kapan dipakai:** Setelah rapat, diskusi tim, atau wawancara selesai.
- **Contoh kalimat pemicu:** `"Buat notulen dari catatan diskusi ini, pisahkan keputusan final dan usulan yang masih pending."`

### 5. `remember` `[Harian]`
- **Fungsi:** Menyimpan satu fakta atau preferensi jangka panjang yang bersumber ke `.agents/memory/` dan memperbarui indeks `.agents/Memory.md`.
- **Kapan dipakai:** Saat ada tanggal tetap, keputusan, nama kontak, atau aturan kerja yang wajib diingat lintas sesi.
- **Contoh kalimat pemicu:** `"Tolong catat bahwa tenggat laporan bulanan jatuh setiap tanggal 25, simpan sebagai fakta."`

### 6. `show-visual` `[Berkala]`
- **Fungsi:** Mengubah catatan, analisis, atau laporan vault menjadi satu berkas `.html` rapi yang siap dibuka di browser secara offline dan siap cetak A4.
- **Kapan dipakai:** Saat hasil kerja teks perlu tampil bersih dan nyaman dibaca oleh atasan, klien, atau tim.
- **Contoh kalimat pemicu:** `"Buat laporan visual dari draf di work/drafts/ agar enak dibaca di browser."`

### 7. `backup-drive` `[Berkala]`
- **Fungsi:** Membuat satu arsip cadangan `.zip` dari vault untuk diunggah ke Google Drive. Penyaringan otomatis berkas sensitif (`.env*`, kredensial, cache) dan penyimpanan otomatis ke `work/archive/` hanya berjalan pada jalur CLI opsional. Pada kompresi manual lewat Finder atau File Explorer tidak ada penyaringan otomatis, sehingga user wajib memastikan tidak menaruh data rahasia di dalam vault.
- **Kapan dipakai:** Setiap selesai tonggak kerja penting atau secara rutin mingguan.
- **Contoh kalimat pemicu:** `"Cadangkan vault ini menjadi arsip ZIP yang siap saya unggah ke Google Drive."`

### 8. `create-carik-skill` `[Berkala]`
- **Fungsi:** Memandu Anda lewat wawancara singkat untuk merancang, menulis, dan menguji skill lokal baru sesuai kebutuhan pribadi Anda.
- **Kapan dipakai:** Saat Anda punya pekerjaan berulang (seperti format laporan rutin atau daftar cek khusus) dan ingin agen selalu mengikuti pola yang sama.
- **Contoh kalimat pemicu:** `"Buat skill baru untuk membantu saya menyusun rekap pengeluaran bulanan."`

### 9. `update-carik` `[Berkala]`
- **Fungsi:** Memperbarui berkas sistem bawaan Carik dari rilis publik resmi (GitHub publik atau subfolder ZIP di `work/inbox/`) lewat pratinjau dan cadangan otomatis tanpa menimpa catatan Anda.
- **Kapan dipakai:** Saat versi baru Carik Vault dirilis.
- **Contoh kalimat pemicu:** `"Cek dan perbarui Carik dari repositori GitHub publik."` atau `"Perbarui Carik dari subfolder rilis baru di work/inbox/."`

## Kelompok 2: Tuas Penalaran Inti (5 Skill)

### 10. `clarify` `[Otomatis / Koreksi Agen]`
- **Fungsi:** Menghentikan penulisan berkas ketika ada kalimat rancu, konteks kurang, atau tafsir ganda, lalu mengajukan pertanyaan penentu sebelum bertindak.
- **Kapan dipakai:** Saat Anda ingin memastikan agen tidak menebak-nebak instruksi yang masih belum lengkap.
- **Contoh kalimat pemicu:** `"Jangan menebak, klarifikasi dulu bagian yang masih rancu sebelum mulai menulis."`

### 11. `brave` `[Otomatis / Koreksi Agen]`
- **Fungsi:** Mendorong agen menuntaskan pekerjaan dari awal sampai selesai tanpa jalan pintas atau tambalan setengah jadi.
- **Kapan dipakai:** Saat tugas bertahap mulai melebar dan Anda ingin agen menyelesaikannya secara tuntas.
- **Contoh kalimat pemicu:** `"Kerjakan sampai tuntas tanpa jalan pintas sampai seluruh bagiannya selesai."`

### 12. `confidence` `[Otomatis / Koreksi Agen]`
- **Fungsi:** Memastikan agen hanya menyampaikan klaim atau rencana substantif setelah mencapai keyakinan di atas 95 persen berdasarkan bukti primer.
- **Kapan dipakai:** Saat Anda ingin menguji apakah angka, fakta, atau kesimpulan agen benar-benar ditopang bukti.
- **Contoh kalimat pemicu:** `"Kamu yakin dengan angka ini? Cek lagi datanya dari berkas sumber."`

### 13. `recommend` `[Otomatis / Koreksi Agen]`
- **Fungsi:** Menyaring pilihan lewat perbandingan kelebihan, risiko, dan kecocokan, lalu menutup pada satu rekomendasi terbaik tanpa melempar menu opsi yang membingungkan.
- **Kapan dipakai:** Saat Anda punya dua atau lebih pilihan dan butuh satu keputusan terbaik beserta alasannya.
- **Contoh kalimat pemicu:** `"Dari dua pendekatan ini, pilihkan yang terbaik dan jelaskan alasannya."`

### 14. `simplify` `[Otomatis / Koreksi Agen]`
- **Fungsi:** Memilih perubahan atau struktur paling sederhana yang tetap lengkap tanpa membuang syarat penting maupun verifikasi.
- **Kapan dipakai:** Saat rancangan, dokumen, atau alur yang disusun agen terasa terlalu rumit.
- **Contoh kalimat pemicu:** `"Jangan bikin ribet, sederhanakan strukturnya supaya lebih ringkas."`

## Kelompok 3: Integritas dan Eksekusi (4 Skill)

### 15. `anti-sycophancy` `[Otomatis / Koreksi Agen]`
- **Fungsi:** Mencegah agen asal mengiyakan pendapat Anda; agen wajib memeriksa bukti primer dan berani menyanggah bila ada premis yang keliru.
- **Kapan dipakai:** Saat Anda ingin masukan jujur atas gagasan, rencana, atau draf Anda.
- **Contoh kalimat pemicu:** `"Jangan asal setuju, cek dulu buktinya dan beri penilaian jujur atas rencana ini."`

### 16. `define-goal` `[Harian]`
- **Fungsi:** Merumuskan blok `## Goal Contract` di awal percakapan berisi tujuan, syarat selesai, cara evaluasi, dan hal di luar cakupan sebelum pekerjaan dimulai.
- **Kapan dipakai:** Sebelum memulai tugas besar atau multi-langkah agar arah kerja tidak melenceng.
- **Contoh kalimat pemicu:** `"Tentukan goal dulu sebelum kita mulai menulis laporan ini."`

### 17. `goal` `[Berkala]`
- **Fungsi:** Menjalankan iterasi berulang sampai syarat selesai dari `define-goal` benar-benar terpenuhi, atau melaporkan hambatan spesifik yang membutuhkan keputusan Anda.
- **Kapan dipakai:** Saat sebuah tugas perlu diulang dan diperbaiki beberapa putaran hingga tuntas.
- **Contoh kalimat pemicu:** `"Kerjakan sampai beres sesuai syarat selesai yang tadi kita sepakati."`

### 18. `debate` `[Berkala]`
- **Fungsi:** Menggelar evaluasi multi-perspektif dengan sudut pandang kritis (red-team) untuk menguji keputusan strategis atau memecah kebuntuan setelah kesalahan berulang.
- **Kapan dipakai:** Saat menghadapi keputusan berisiko tinggi atau ketika dua kali perbaikan tetap gagal.
- **Contoh kalimat pemicu:** `"Gelar forum debat untuk menguji rencana ini dari berbagai sudut pandang."`

## Kelompok 4: Kontinuitas Sesi Bebas-Python (6 Skill)

### 19. `bootstrap` `[Harian]`
- **Fungsi:** Melanjutkan sesi kerja dari pasangan berkas serah-terima terbaru di `handoff/`, `SCOPE.md`, `.agents/Memory.md`, dan catatan log terbaru.
- **Kapan dipakai:** Setiap kali membuka obrolan baru untuk menyambung pekerjaan sebelumnya.
- **Contoh kalimat pemicu:** `"Lanjutkan sesi dari handoff terbaru."`

### 20. `closing` `[Harian]`
- **Fungsi:** Menutup sesi kerja dengan rapi: menulis rekap sesi ke `notes/`, memperbarui fakta di `.agents/Memory.md`, mencatat log sesi, menyegarkan `SCOPE.md` bila berubah, dan membuat `handoff` bila pekerjaan masih berlanjut.
- **Kapan dipakai:** Setiap selesai sesi kerja panjang atau sebelum berpindah hari.
- **Contoh kalimat pemicu:** `"Tutup sesi hari ini dan siapkan catatan untuk dilanjut besok."`

### 21. `handoff` `[Berkala]`
- **Fungsi:** Membuat pasangan berkas serah-terima (`HANDOFF-*.md` dan `INITIAL-PROMPT-*.txt`) di folder `handoff/` tanpa bergantung pada Python.
- **Kapan dipakai:** Saat Anda ingin khusus membuat paket serah-terima untuk obrolan baru atau berpindah aplikasi AI.
- **Contoh kalimat pemicu:** `"Buat handoff agar pekerjaan ini bisa saya sambung di sesi berikutnya."`

### 22. `session-log` `[Otomatis / Koreksi Agen]`
- **Fungsi:** Mencatat peristiwa penting dan posisi kerja di `.agents/Context.md` serta koreksi dan pelajaran di `.agents/Lessons.md`.
- **Kapan dipakai:** Saat agen mulai melenceng dari jalur atau ketika Anda ingin menyegarkan konteks sesi.
- **Contoh kalimat pemicu:** `"Refresh konteks dari log sesi terbaru agar kita kembali ke jalur."`

### 23. `orient` `[Otomatis / Koreksi Agen]`
- **Fungsi:** Menjalankan orientasi awal vault pada kontak pertama (sebelum ada tanda `Orientation completed` di `.agents/Context.md`) agar agen memahami seluruh aturan inti.
- **Kapan dipakai:** Otomatis pada obrolan perdana di vault baru, atau saat Anda ingin agen membaca ulang tata kelola dari awal.
- **Contoh kalimat pemicu:** `"Pahami vault ini dulu lewat orientasi awal."`

### 24. `scratchpad` `[Harian]`
- **Fungsi:** Menjaga catatan diskusi hidup di `.agents/sessions/YYYY-MM-DD--<topik>-scratchpad.md` ketika obrolan eksploratif meluas.
- **Kapan dipakai:** Saat diskusi sudah berjalan beberapa putaran dan memunculkan beberapa keputusan yang saling berkaitan.
- **Contoh kalimat pemicu:** `"Catat poin obrolan dan keputusan kita sejauh ini ke scratchpad."`

## Kelompok 5: Bahasa Indonesia dan Format Terbuka (3 Skill)

### 25. `id-prose` `[Harian]`
- **Fungsi:** Mengaudit dan merombak teks Bahasa Indonesia yang kaku, terasa seperti terjemahan Inggris, atau melanggar struktur S-P-O-K berdasarkan `writing-style/prose-writing-style.md`.
- **Kapan dipakai:** Saat draf laporan, artikel, atau surat masih terasa kaku dan butuh bahasa Indonesia yang mengalir alami.
- **Contoh kalimat pemicu:** `"Cek kalimat kaku dan bersihkan kalke pada draf ini agar bahasanya mengalir alami."`

### 26. `markdown` `[Berkala]`
- **Fungsi:** Membuat dan merapikan catatan Markdown bergaya Obsidian lengkap dengan frontmatter YAML, tautan antarcatatan (`[[...]]`), kotak sorotan (*callout*), dan tag.
- **Kapan dipakai:** Saat Anda ingin merapikan struktur dokumen panjang atau menyambungkan beberapa catatan terkait.
- **Contoh kalimat pemicu:** `"Rapikan catatan ini dengan format Markdown yang bersih dan tambahkan tautan antarcatatan."`

### 27. `canvas` `[Berkala]`
- **Fungsi:** Membuat dan menyunting peta konsep atau diagram visual berformat terbuka `.canvas` (JSON Canvas) dengan tata letak node yang rapi dan tidak tumpang tindih.
- **Kapan dipakai:** Saat Anda ingin memetakan alur kerja, struktur gagasan, atau hubungan antartopik secara visual.
- **Contoh kalimat pemicu:** `"Buat peta konsep format canvas dari kerangka proyek di work/concept/."`

## Kelompok 6: Media dan Dokumen (3 Skill)

### 28. `pdf-read` `[Berkala]`
- **Fungsi:** Mendaftarkan berkas PDF di `raw-kb/` ke `raw-kb/SOURCES.md` dan mengonversinya menjadi turunan teks Markdown sebelum isinya dibaca atau dikutip. Skill ini wajib memakai `python3` dan alat ekstraksi PDF lokal (tidak memiliki jalur bebas-Python).
- **Kapan dipakai:** Setiap kali Anda menaruh berkas PDF berbasis teks baru di `raw-kb/user-provided/` pada lingkungan yang memiliki `python3` dan alat PDF lokal.
- **Contoh kalimat pemicu:** `"Baca PDF yang baru saya taruh di raw-kb/user-provided/ lalu ubah ke Markdown."`

### 29. `pdf-ocr` `[Berkala]`
- **Fungsi:** Mengekstrak teks dari berkas PDF hasil pindai (gambar) yang mengembalikan status `ocr_required` atau `partial_extraction` dari `pdf-read` menjadi turunan Markdown bersumber. Skill ini wajib memakai `python3` serta alat OCR lokal (Tesseract dan Poppler atas izin eksplisit Anda) dan tidak memiliki jalur bebas-Python.
- **Kapan dipakai:** Ketika berkas PDF di `raw-kb/` ternyata hasil scan gambar sehingga ditolak `pdf-read` dengan status `ocr_required` atau `partial_extraction`.
- **Contoh kalimat pemicu:** `"PDF ini hasil scan, tolong proses dengan OCR agar teksnya bisa dibaca."`

### 30. `make-pdf` `[Berkala]`
- **Fungsi:** Mengubah catatan atau laporan vault menjadi PDF siap cetak A4 dengan membuat halaman visual HTML lewat `show-visual` terlebih dahulu, lalu mengekspornya ke PDF setelah Anda setujui.
- **Kapan dipakai:** Saat hasil final di `work/drafts/` atau `work/canon/` siap dikirimkan atau dicetak sebagai dokumen PDF A4.
- **Contoh kalimat pemicu:** `"Jadikan laporan di work/canon/ ini sebagai PDF siap cetak A4."`

## 3 Alur Kerja Gabungan (Playbook Harian)

Ketiga rangkaian berikut memadukan beberapa skill sekaligus untuk pekerjaan nyata yang paling sering ditemui.

### Playbook 1: Olah PDF -> Draf -> Laporan PDF A4
1. Taruh berkas PDF rujukan di `raw-kb/user-provided/`, lalu kirim `"Baca PDF di raw-kb/user-provided/ dan rangkum poin pentingnya"` (`pdf-read`, atau `pdf-ocr` bila muncul status `ocr_required` atau `partial_extraction`). Langkah olah PDF lokal ini membutuhkan `python3` dan alat PDF lokal; di aplikasi GUI tanpa Python, salin teks relevan atau ekstrak PDF lebih dulu sebelum dimasukkan ke vault.
2. Minta agen menyusun draf di `work/drafts/` berdasarkan rangkuman tersebut, lalu haluskan bahasanya dengan `"Cek kalimat kaku dan rapikan draf ini"` (`id-prose`).
3. Setelah isi Anda setujui dan dipindah ke `work/canon/`, tutup dengan `"Buat laporan visual lalu jadikan PDF siap cetak A4"` (`show-visual` -> `make-pdf`).

### Playbook 2: Rapat -> Notulen -> Pecah Tugas
1. Tempel catatan kasar atau transkrip rapat di percakapan, lalu kirim `"Buat notulen rapat dan pisahkan keputusan final dari usulan pending"` (`notulen`).
2. Simpan tenggat atau kesepakatan penting yang muncul dengan `"Simpan tenggat dan keputusan ini sebagai fakta"` (`remember`).
3. Ubah keputusan final menjadi rencana eksekusi dengan `"Pecah keputusan rapat tadi jadi langkah kerja berurutan"` (`split-task`).

### Playbook 3: Tutup Sesi -> Sambung Besok
1. Menjelang selesai bekerja, kirim `"Tutup sesi hari ini dan siapkan handoff"` (`closing` yang mencakup `remember`, `session-log`, dan `handoff`).
2. Jika ada perubahan besar hari itu, tambahkan `"Cadangkan vault ini menjadi arsip ZIP"` (`backup-drive`).
3. Keesokan harinya di obrolan baru (atau di aplikasi AI lain), cukup kirim `"Lanjutkan sesi dari handoff terbaru"` (`bootstrap`) agar pekerjaan langsung tersambung dari titik terakhir.
