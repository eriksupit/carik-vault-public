---
title: "Creative Law: {{PROJECT_NAME}}"
date: {{DATE}}
updated: {{DATE}}
type: creative-law
status: draft
tags:
  - {{PROJECT_NAME}}
  - creative-law
  - visi-produk
  - kedaulatan-kreatif
  - arsitektur-inti
---

# Creative Law: {{PROJECT_NAME}}

> **Otoritas:** Keputusan Pemilik (*Owner Decision* — Pemegang Kedaulatan Tertinggi).
> **Cakupan:** Prinsip tertinggi produk, visi, filosofi desain, dan perilaku sistem aplikasi/web `{{PROJECT_NAME}}`. Ini adalah Sumber Kebenaran Tunggal (*Single Source of Truth* / SSOT) untuk konsep produk, aturan interaksi, dan batas invarian. Rincian implementasi teknis diatur dalam dokumen desain (`docs/design/`).

---

## 1. Kedaulatan Kreatif & Anti-Pemujaan Dokumen

1. **Dokumen Melayani Produk (*No Document Worship*):**
   Dokumen kerja (`work/research/`, `docs/design/`, `docs/plans/`, `work/implementation-plan/`) adalah hukum lunak (*soft law*)—catatan risalah dari keputusan terakhir, bukan instrumen birokrasi untuk menolak gagasan baru pemilik.
2. **Kaskade Adaptasi Wajib (*Mandatory Adaptation Cascade*):**
   Ketika pemilik membawa arah baru atau merevisi konsep, agen dilarang mempertahankan konsistensi dokumen usang. Agen wajib memetakan konsekuensi perubahan teknis secara proaktif (*"perubahan ini memengaruhi X, Y, Z — berikut langkah kerjanya"*), bukan menjadikannya dalih penolakan (*veto*).
3. **Praduga Benar Keputusan Pemilik (*Presumption of Correctness*):**
   Arah produk dan keputusan estetika/fungsional pemilik memiliki asas praduga benar. Tanggapan agen berfokus pada kelayakan arsitektural, identifikasi risiko nyata, dan eksekusi presisi.
4. **Tantangan Melalui Pintu Nalar Logis:**
   Agen hanya mengajukan keberatan (*challenge*) jika arah baru melanggar batasan fisik keamanan, merusak integritas data pengguna, atau memicu kontradiksi invarian mutlak sistem. Keberatan diajukan satu kali dengan bukti logis; keputusan pemilik setelahnya bersifat final.

---

## 2. Paradigma Produk (Siap Dirumuskan)

*Bagian ini akan diisi dan dimatangkan bersama melalui sesi diskusi di dalam vault:*

### 2.1 Apa itu `{{PROJECT_NAME}}`
[Definisi esensi produk, proposisi nilai utama, dan fungsi inti aplikasi/web]

### 2.2 Apa yang Bukan `{{PROJECT_NAME}}`
[Batasan tegas mengenai apa yang sengaja tidak dibangun agar fokus produk tetap tajam]

### 2.3 Tiga Pilar Pengalaman Pengguna
1. **Pilar 1:** [Prinsip interaksi utama]
2. **Pilar 2:** [Prinsip keandalan arsitektur]
3. **Pilar 3:** [Prinsip transparansi & kontrol pengguna]

### 2.4 Filosofi Arsitektural: Human-Sovereign, File-First, Intelligence-First Agentic Harness Architecture
Proyek `{{PROJECT_NAME}}` beroperasi di bawah 11 prinsip inti berikut:
1. **Dua Sumbu:** Sumbu Otoritas (Pemilik -> `CARIK-CHARTER.md` -> `CREATIVE-LAW.md` -> `AGENTS.md` -> `WORKFLOW.md`) terpisah tegas dari Sumbu *Runtime* (Vault + Memori *Durable* <- *Harness* <- *Agent* <- *Skills* <- *Tools*/*Scripts*/*Hooks* opsional).
2. **Kedaulatan Pemilik & *File-First*:** Vault selalu utuh di disk sebagai berkas teks terbuka tanpa bergantung pada satu aplikasi; *harness* menghubungkan *agent* ke vault di dalam mandat pemilik.
3. **Tata Kelola Berlapis:** `CARIK-CHARTER.md` (FOA & ROM), `CREATIVE-LAW.md` (visi & invarian), `AGENTS.md` (*system prompt* proyek), `WORKFLOW.md` (tahap & gerbang).
4. **Penalaran, *Anti-Sycophancy*, & Larangan Menu Opsi:** Setiap evaluasi dan usulan melewati `anti-sycophancy` dan menghasilkan satu rekomendasi terbaik (`recommend` `>98%`, klaim umum `>95%`) dari penalaran adversarial yang ditopang bukti primer nyata, tanpa menu opsi kosong dan ditutup deklaratif.
5. **Batas *Intelligence-First* pada *Coding*:** Kecerdasan *agent* memimpin substansi rekayasa; fakta eksekusi (*compiler*, *typecheck*, tes, *build*, Class C) dinilai secara deterministik.
6. ***Hooks*, *Scripts*, & *Self-Healing* Terkendali:** Class A regex bahasa alami dihapus; Class B diagnostik (`exit 0`); Class C pengaman fisik (*fail-closed*). Perkakas rusak didiagnosis dan diadaptasi atas persetujuan pemilik tanpa melemahkan Class C.
7. **Lima Lapisan Kontinuitas:** *Scratchpad* obrolan berpicu semantik (`.agents/sessions/`), Memori *Durable* bersumber (`.agents/Memory.md` + `.agents/memory/`), Log Sesi (`Context.md` & `Lessons.md`), Notulen (`notes/meeting-minutes/`), dan Serah-Terima (`handoff/`).
8. **Orkestrasi *Multi-Agent* & *Worker Checkpoint*:** *Single-agent first*, pemisahan peran, batas tulis saling lepas, verifikasi dua arah (*zero blind trust*), satu suara ke pemilik, *self-heal write boundaries* khusus *worker*, isolasi tugas beda *scope*, serta *Worker Checkpoint* ringkas di `.agents/sessions/workers/` untuk tugas multi-langkah (4 pemicu otomatis via `scratchpad`).
9. **Jangkar Ritme Kerja:** *Goal Contract*, *Design-Before-Code*, dan *Summary-First* berbasis nalar.
10. ***Circuit Breaker* Dialektis:** Setelah 2 kesalahan berulang pada masalah sama atau keluhan pemilik, hentikan pengulangan solo dan gelar `debate` dengan kursi *Red Team*.
11. **Skeptisisme Awal (*No Blind Greenfield*):** Untuk *build* baru atau arsitektur non-trivial, tempuh alur wawancara (`grill-with-docs`) -> PRD (`to-prd`) -> riset preseden arsitektur nyata (`browsing`, catat di `raw-kb/SOURCES.md`) -> sketsa kontrak (`architect`) -> persetujuan pemilik.

---

## 3. Invarian Produk (*Product Invariants*)

Aturan-aturan mutlak yang tidak boleh dilanggar oleh implementasi kode apa pun:
1. **Kedaulatan Data Pengguna:** Data dan konten pengguna disimpan dalam format terbuka dan portabel, bebas dari penguncian vendor tertutup.
2. **Determinisme & Uji Perilaku:** Setiap logika bisnis inti wajib memiliki pembuktian verifikasi otomatis yang deterministik.
3. [Invarian spesifik domain yang akan ditetapkan dalam diskusi konsep]
