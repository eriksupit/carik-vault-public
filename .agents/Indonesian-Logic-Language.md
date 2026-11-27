---
title: Indonesian Logic and Language Governance Record
date: 2026-08-16
updated: 2026-09-15
type: governance
status: active
tags:
  - file-over-app-harness
  - language
  - governance
---

# Indonesian Logic and Language Governance Record

This file is the living record of Indonesian reasoning, meaning, syntax, reference, and translationese findings for this vault. `indonesian-logic-growth` appends new findings here; `anti-translationese` and `konversi-bahasa-logis` consult it before writing Indonesian prose.

Entries are dated, appended, and never overwritten. The harness ships this file empty of project findings; a generated vault accumulates its own.

## Findings

## [2026-08-17] Larangan Metafora Fisik pada Hal Bukan Benda

**Kesalahan.** Menulis "larangannya sekarang **berdiri** di empat lapis". Dalam pesan yang sama: "AGENTS.md **menguburnya**", "vault turunan **berutang** konsistensi", "pekerjaan desain **bersandar** pada tafsiranku".

**Mengapa salah.** Larangan tidak punya kaki dan tidak menempati ruang; teks tidak dikubur; abstraksi tidak berutang; pekerjaan tidak bersandar. Semuanya satu kelas — kata kerja fisik ditimpakan ke hal yang bukan benda. Sumbernya bukan bahasa Indonesia melainkan frasa Inggris yang diterjemahkan kata per kata: *the rule now stands*, *buried in*, *owes consistency*, *rests on*. Uji balik-terjemah langsung membuktikannya: tiap frasa memetakan mulus ke frasa Inggris itu, artinya memang frasa Inggris yang diterjemahkan, bukan kalimat yang lahir dari bahasa Indonesia. Penutur Indonesia yang menulis dari nol akan menyebut perbuatannya: tertulis, ditaruh di bagian awal, tidak wajib menyamai, memakai sebagai dasar.

Cacat ini tidak terasa salah dari dalam karena terasa seperti menulis dengan cermat. Perasaan sedang berbahasa rapi itulah tandanya, bukan pembelaannya.

**Pemeriksaan.** Pada tiap kalimat yang subjeknya bukan benda fisik — aturan, keputusan, dokumen, pekerjaan, biaya, kontrak — periksa kata kerjanya. Bila kata kerja itu menuntut tubuh, ruang, atau berat (berdiri, jatuh, terkubur, memikul, menopang, bersandar, berutang, berakar), ganti dengan perbuatan yang bisa ditunjuk: tertulis di mana, dilakukan siapa, memakai apa sebagai dasar. Uji balik-terjemah bila ragu: kalau frasanya memetakan mulus ke satu frasa Inggris baku, frasa itu terjemahan dan harus ditulis ulang.

**Ranah.** `umum`

## [2026-08-25] Kata Ganti Orang Ketiga dalam Prosa Naratif: Pakai `dia`, Bukan `ia`

**Kesalahan.** Sinopsis film sepanjang 60 paragraf ditulis dengan `ia` sebagai kata ganti tunggal untuk tokoh manusia, 27 kali. Pemilik menolaknya dan meminta `dia`.

**Mengapa salah.** `ia` memang baku dan memang boleh dipakai untuk manusia, jadi cacatnya bukan tata bahasa melainkan ragam. `ia` hidup di ragam tulis sastra dan terjemahan; orang yang bercerita dengan suara sendiri mengucapkan `dia`. Uji baca nyaring memisahkan keduanya dalam sekali dengar. Menukar kata gantinya saja tidak cukup: begitu `ia` menjadi `dia`, paragraf yang tadinya menumpuk `Ia ... Ia ... Ia` berubah menjadi `Dia ... Dia ... Dia`, dan `check_sentences.py` menandainya sebagai `repeat-opener`. Perbaikannya menuntut pembukaan kalimat yang berganti-ganti — inversi P-S, topik-komen, atau subjek berupa nama — bukan penggantian kata per kata.

**Pemeriksaan.** Cari `ia` sebagai kata berdiri sendiri di seluruh prosa naratif dan ekspositori. Ganti menjadi `dia` bila anteseden­nya manusia; bila antesedennya bukan manusia, buang kata gantinya dan ulangi nomina­nya. Sesudah penggantian, jalankan `check_sentences.py` lagi dan periksa `repeat-opener:dia`; setiap paragraf yang tertandai harus diberi variasi pembuka kalimat, bukan sekadar dikembalikan ke `ia`. Catatan: aturan bawaan `anti-translationese` menyuruh mempertahankan `ia` untuk subjek manusia; catatan ini mengesampingkannya untuk vault ini.

**Ranah.** `umum`

## [2026-08-25] Atestasi Boleh Lolos N-gram tapi Tetap Gagal Ranah Pemakaian

**Kesalahan.** Frasa `kadar kemurnian` dipakai untuk endapan nikel di dalam tambang, dengan bukti atestasi dari dua domain Tier-1. Kedua kutipannya berbicara tentang emas batangan Antam dan Freeport pada angka 99,99 persen. Untuk bijih tambang, yang lazim dipakai wartawan ekonomi adalah `kadar nikel`, dan ambangnya 1,7 sampai 1,8 persen.

**Mengapa salah.** Atestasi menjawab pertanyaan "apakah orang menulis frasa ini", bukan "apakah orang menulis frasa ini untuk benda ini". Satu n-gram bisa baku di satu bidang dan salah di sebelahnya. Pemeriksaan yang berhenti pada kecocokan huruf akan meloloskannya sambil terasa sudah terbukti. Cacat semacam ini lebih berbahaya daripada kalke biasa, sebab ia datang membawa surat keterangan.

**Pemeriksaan.** Pada tiap Attestation Record, baca kutipannya sampai ke bendanya, bukan sampai ke frasanya. Tanyakan: benda yang dibicarakan sumber itu sama jenisnya dengan benda yang saya tulis? Emas batangan dan bijih tambang bukan benda yang sama; obligasi dan pinjaman bukan benda yang sama. Bila jenisnya berbeda, cari frasa yang dipakai sumber untuk benda yang benar, lalu atestasi ulang frasa itu.

**Ranah.** `umum`

## [2026-09-22] Kasus regresi prosa eksplanatoris yang diserap dari eriksupit-prosa

**Ranah:** sejarah, umum.

**Asal.** Tujuh kasus berikut hidup di `.agents/skills/eriksupit-prosa/references/semantic-gates.md` sebelum skill itu dibubarkan pada 2026-09-22. Kasusnya spesifik pada satu proyek, jadi tempatnya di catatan hidup ini, bukan di pedoman gaya universal.

| Ditolak | Sebab | Dipakai |
|---|---|---|
| `Hatta berakhir di Bangka` | Bisa terbaca sebagai hidup Hatta yang berakhir di sana. | `Film menutup cerita ketika Hatta menjalani pengasingan di Bangka.` |
| `blokade menahan pasokan` | Menghilangkan barangnya, asalnya, tujuannya, dan mekanismenya. | Sebut barangnya dan nyatakan perpindahan mana yang dihalangi blokade. |
| `bertahan pada dua arah` | Hubungan tindakan dengan arah tidak wajar dalam bahasa Indonesia. | Sebut kedua strateginya, pelakunya, dan tujuannya. |
| `batangannya` | Makna sehari-hari yang bermakna ganda dan objeknya tidak lengkap. | `cadangan emas` atau `emas yang disimpan` |
| `emas terkurung` | Metafora menyembunyikan tempat penyimpanan dan penghalang pemakaiannya. | Nyatakan di mana emas disimpan dan mengapa belum bisa dipakai. |
| `pusat diputus` | Tidak menyebut hubungan apa yang terputus. | Sebut komunikasi, komando, jalan, atau hubungan pemerintahan secara tepat. |
| `tubuh keuangan` | Metafora menyembunyikan lembaga atau jaringannya. | Sebut banknya, kantornya, pegawainya, simpanannya, kreditnya, atau jaringan transaksinya. |

## [2026-09-22] Eksistensial "Dalam X terdapat Y" dan Subjek Melayang "Isinya"

**Kesalahan.** "Dalam alasan tersebut terdapat inkonsistensi logis dan kesalahan hitung. Isinya juga dapat memuat fakta rekaan atau argumen sepihak."

**Mengapa salah.** Dua cacat menumpuk di satu tempat. Pertama, "Dalam X terdapat Y" memetakan mulus ke pola Inggris "In X there is Y" — anteseden dilempar ke keterangan tempat, lalu Y muncul lewat verba eksistensial alih-alih X langsung memegang predikatnya. Kedua, "Isinya" pada kalimat berikut adalah subjek yang tidak jelas menunjuk apa: bukan "alasan", bukan "inkonsistensi", melainkan nomina buatan yang menggantung untuk sekadar menyambung kalimat. Penutur yang bercerita dari nol akan bilang: alasan itu mengandung X, dan alasan itu juga bisa memuat Y — X dan alasan yang sama tetap memegang predikatnya di kedua kalimat.

**Pemeriksaan.** Cari pola "Dalam [nomina] terdapat/ada [nomina]" dan ganti dengan `[nomina pertama] + mengandung/berisi + [nomina kedua]`. Cari kalimat yang dibuka dengan "Isinya", "Hal itu", atau "Ini" tanpa anteseden satu kata yang jelas di kalimat sebelumnya; ganti dengan pengulangan nomina anteseden yang sebenarnya, bukan pronomina umum.

**Ranah.** `umum`

## [2026-09-22] Kerangka Kalimat Ringkasan Akademik Inggris Disangka Bahasa Indonesia

**Kesalahan.** "Feng dkk. (ACL 2026) menguji apakah saran dalam prompt memengaruhi jawaban model." Pemilik menolak seluruh paragraf dengan reaksi keras: "mustahil ini bahasa indonesia... lebih mirip bahasa inggris yang diterjemahkan" — bukan menandai satu frasa, melainkan seluruh kerangka kalimat.

**Mengapa salah.** Cacatnya bukan kalke leksikal per kata (tiap kata memang kata Indonesia baku), melainkan kerangka kalimat: dibuka dengan topik abstrak diikuti anak kalimat "apakah X memengaruhi Y" — pemetaan langsung dari pola abstrak jurnal Inggris "tested whether X affects Y". Setiap pemeriksaan L1–L3 di skill ini memeriksa kalke per-frasa dan bisa lolos semua sementara keseluruhan paragraf tetap terasa terjemahan, karena masalahnya ada di pola susunan kalimat, bukan di kata per kata. Orang Indonesia yang bercerita dari nol membuka dengan pertanyaan konkret atau kejadian nyata, bukan dengan "[Nama] (tahun) meneliti/menguji apakah [abstraksi] mempengaruhi [abstraksi]".

**Pemeriksaan.** Bila kalimat pembuka paragraf berpola "[Aktor] ([tahun/rujukan]) meneliti/menguji/mengkaji apakah [nomina abstrak] mempengaruhi/berdampak pada [nomina abstrak]", baca nyaring dan tanyakan: apakah orang Indonesia akan membuka cerita begini? Bila tidak, ganti dengan bentuk tanya konkret ("[Aktor] meneliti satu hal: kalau [kejadian konkret], apakah [akibat konkret]?") atau bentuk kejadian langsung. Periksa seluruh paragraf, bukan cuma kalimat pembuka — pola topik-abstrak-lalu-anak-kalimat-panjang cenderung menular ke kalimat berikutnya.

**Ranah.** `umum`
