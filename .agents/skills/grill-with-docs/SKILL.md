---
name: grill-with-docs
description: >-
  Conduct a structured tree-based interview to stress-test a plan or design while recording settled decisions to docs/design/ and ADRs. Use when the owner says "grill me", "uji desain", "wawancara desain", or "bedah rencana".
---

# grill-with-docs

## Purpose

Menjalankan wawancara terstruktur berbasis pohon keputusan (*design tree*) untuk menguji gagasan, membongkar asumsi tersembunyi, dan menutup ambiguitas teknis sebelum implementasi dimulai, sambil mencatat keputusan yang sudah matang ke dokumen desain di `docs/design/` atau ADR secara rapi dan bebas-Python.

## Procedure

1. **Petakan pohon keputusan dan tentukan *frontier*.** Pecah rancangan menjadi keputusan tingkat atas beserta cabang turunannya. Identifikasi *frontier*—yaitu himpunan pertanyaan terbuka yang prasyaratnya sudah jelas dan bisa diputuskan pada putaran ini.
2. **Ajukan satu putaran pertanyaan terstruktur.** Untuk setiap pertanyaan pada *frontier*, sajikan secara ringkas:
   - Nomor dan judul singkat pertanyaan (`Q1`, `Q2`, dst.).
   - Konteks, konflik inti, serta kelebihan dan risiko tiap alternatif yang relevan.
   - **Satu rekomendasi tegas** berbasis bukti primer dan penalaran adversarial (`recommend` `>98%`, tanpa melempar menu opsi kosong).
3. **Selesaikan per putaran sebelum turun ke cabang berikutnya.** Catat jawaban dan koreksi pemilik (simpan ke `scratchpad` bila diskusi meluas $\ge 3$ putaran), lalu buka *frontier* lapisan berikutnya berdasarkan keputusan yang sudah terkunci.
4. **Rekam keputusan matang ke dokumen vault lewat *Summary-First*.** Setelah keputusan stabil, minta persetujuan ringkasan *Summary-First* lalu catat ke berkas yang sesuai:
   - Glosarium domain, invarian, dan batas *out-of-scope* ke dokumen desain di `docs/design/`.
   - Keputusan arsitektural yang sulit dibatalkan sebagai ADR di `docs/design/` atau `docs/plans/`.
5. **Tutup wawancara saat *frontier* habis.** Pastikan tidak ada ambiguitas arsitektural kritis yang tersisa sebelum masuk ke penyusunan PRD (`to-prd`) atau rencana implementasi.

## Rules & Boundaries

- Patuhi `anti-sycophancy` dan `recommend`: setiap pertanyaan wajib disertai satu rekomendasi terbaik dan alasannya, bukan menu opsi tanpa arah.
- Dilarang menulis atau menyunting berkas di `docs/design/` atau `docs/plans/` sebelum mendapat persetujuan *Summary-First* dari pemilik.
- Dilarang mengarang jawaban atas fakta yang bisa diverifikasi langsung dari berkas kode atau dokumen vault; periksa berkas primer lebih dulu sebelum bertanya kepada pemilik.
- Berjalan 100% bebas-Python tanpa ketergantungan pada direktori global maupun aplikasi Obsidian sebagai *runtime*.

## Output & Verification

1. Setiap putaran wawancara menampilkan nomor pertanyaan, konteks/*trade-off*, dan satu rekomendasi tegas.
2. Keputusan final, glosarium, ADR, dan batas *out-of-scope* tercatat di `docs/design/` atau `docs/plans/` setelah persetujuan pemilik, lalu dibaca ulang untuk memverifikasi akurasi isinya.
3. Laporkan ringkas jumlah keputusan yang terkunci, berkas yang diperbarui, dan kesiapan tahap berikutnya secara deklaratif.
