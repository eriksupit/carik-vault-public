---
title: Alur Kerja Rekayasa Perangkat Lunak — {{PROJECT_NAME}}
date: {{DATE}}
updated: {{DATE}}
type: workflow
status: active
tags:
  - workflow
  - app-build
  - software-engineering
  - tata-kelola
---

# Alur Kerja Rekayasa Perangkat Lunak — {{PROJECT_NAME}}

Ini adalah prosedur kanonis untuk profil `app-build` pada proyek **{{PROJECT_NAME}}**, beroperasi di bawah filosofi **Human-Sovereign, File-First, Intelligence-First Agentic Harness Architecture** pada [[CREATIVE-LAW]] (`CREATIVE-LAW.md` di akar vault, Bagian 2.4): kecerdasan *agent* memimpin substansi rekayasa (didahului wawancara `grill-with-docs`, PRD `to-prd`, riset preseden arsitektur nyata, dan sketsa kontrak `architect`), sedangkan fakta eksekusi perangkat lunak dinilai secara deterministik oleh *compiler*, *typecheck*, tes otomatis, *build*, dan pagar Class C. Blok `CORE_GOVERNANCE` di bawah mengatur kontrak *frontmatter*, provenans `raw-kb/`, otoritas keputusan, dan isolasi Git; bagian ini mengatur alur kerja deterministik pengembangan perangkat lunak.

## Urutan Kerja Wajib (8 Tahap)

Setiap pembangunan fitur atau aplikasi wajib menempuh urutan berikut. Melompati tahap adalah pelanggaran proses. Alur ini berbentuk *loop*: kegagalan pada verifikasi atau ulasan mengembalikan kerja ke tahap paling awal yang artefaknya harus diperbaiki.

```text
1. research / brainstorming       -> work/research/
2. design doc                     -> docs/design/              (gerbang persetujuan pemilik)
3. implementation plan            -> work/implementation-plan/ & docs/plans/ (goal per tugas + 1 ultimate goal)
4. execution                      -> work/build/
5. verification / audit / resolve -> work/verification/
6. self / agent review            -> work/review/
7. report to user                 -> work/review/              (gerbang persetujuan pemilik)
8. test / review by a reviewer    -> work/review/
```

### 1. Research / Brainstorming (`work/research/`)
- Rumuskan masalah, target pengguna, kriteria sukses, batasan teknis, dan *non-goals*.
- Mulai dari `work/research/intake.md` (`status: research-pending`). Daftarkan seluruh bahan acuan ke `raw-kb/SOURCES.md` sebelum dipakai sebagai bukti.

### 2. Design Doc (`docs/design/`) — Gerbang Pemilik
- Susun dokumen desain sesuai `docs/design/README.md`: konteks, *goals & non-goals*, desain yang diusulkan, alternatif yang dipertimbangkan (dengan tepat satu rekomendasi), *trade-offs & risks*, dampak, dan pertanyaan terbuka.
- Dokumen ini berstatus draf kerja hingga disetujui eksplisit oleh pemilik. Tidak ada rencana implementasi yang boleh ditulis sebelum dokumen desain disetujui.

### 3. Implementation Plan (`work/implementation-plan/` & `docs/plans/`)
- Pecah desain yang disetujui menjadi tugas-tugas terisolasi yang dapat di-*revert* mandiri.
- Setiap tugas wajib menyatakan satu *goal* dan satu metode verifikasi deterministik; seluruh rencana wajib menyatakan satu *ultimate goal*.
- Terapkan prinsip *deep modules*, *seams*, dan *locality*.

### 4. Execution (`work/build/`)
- Kode sumber nyata dibangun tugas demi tugas sesuai rencana.
- **Pemisahan Files-over-App:** FOA berlaku penuh untuk tata kelola, desain, rencana, dan kontinuitas (`.agents/`, `docs/`, `work/research/`, `work/verification/`, `work/review/`). Untuk `work/build/`, direktori ini boleh memuat proyek kode penuh beserta *package manager*, *build toolchain*, dan *test runner*.
- **Otorisasi Eksekusi Kode (`lean-plan`):** Sesuai prinsip kelas *hook* di [[CREATIVE-LAW]] Bagian 2.4 butir 6 (Class A regex bahasa alami dihapus, Class B diagnostik, Class C pengaman fisik), hook regex `summary-first-gate.py` tidak dipakai. Setelah rencana implementasi disetujui dan tercatat di `docs/plans/`, disiplin *Summary-First* dan alur `lean-plan` untuk penulisan kode di `work/build/` ditegakkan melalui penalaran agen atas kontrak teks tanpa token regex per-berkas.
- Jaga setiap commit terisolasi per tugas sesuai aturan Git di `CORE_GOVERNANCE`.

### 5. Verification / Audit / Resolve (`work/verification/`)
- Jalankan verifikasi deterministik yang ditetapkan pada setiap tugas (unit test, integration test, typecheck, linter, build check).
- Setiap kegagalan adalah celah yang harus dilacak akar penyebabnya, diperbaiki, dan diuji ulang—bukan ditambal gejalanya. Audit kesesuaian hasil terhadap kontrak tugas.

### 6. Self / Agent Review (`work/review/`)
- Agen meninjau ulang hasil kerjanya terhadap dokumen desain, *goal* rencana, kesehatan arsitektur, serta kontrak harness (*frontmatter*, provenans, isolasi Git).

### 7. Report to User (`work/review/`) — Gerbang Pemilik
- Laporkan apa yang dibangun, bukti langsung hasil verifikasi/tes, risiko tersisa, dan satu rekomendasi langkah berikutnya.

### 8. Test / Review by Reviewer (`work/review/`)
- Peninjau independen (manusia atau agen peninjau terpisah) menguji dan meninjau perubahan. Temuan yang belum tuntas mengembalikan alur ke tahap terdampak paling awal.

## Gerbang Bukti (*Evidence Gates*)

Promosi status hanya sah bila seluruh syarat terpenuhi dan disetujui eksplisit oleh pemilik:
- **Gate 1 (Research → Design):** Masalah, pengguna, kriteria sukses, batasan, dan *non-goals* jelas; bahan acuan terdaftar; satu rekomendasi agen; disetujui pemilik.
- **Gate 2 (Design → Implementation Plan):** Dokumen desain ada di `docs/design/` dengan satu desain rekomendasi, alternatif, *trade-offs*, dan tanpa pertanyaan terbuka yang menggantung; **persetujuan eksplisit pemilik**.
- **Gate 3 (Plan → Execution):** Setiap tugas memiliki *goal* dan verifikasi terukur; rencana memiliki *ultimate goal*; disetujui pemilik.
- **Gate 4 (Execution → Report):** Implementasi sesuai desain; seluruh verifikasi lulus dengan bukti nyata; temuan *self-review* tuntas tanpa celah tertunda.
- **Gate 5 (Report → Ship):** Persetujuan pemilik setelah laporan; ulasan peninjau independen lulus.

## Tata Kelola Inti (Dikelola Harness)

Blok di bawah ini disinkronkan dari `carik-vault` / `file-over-app-harness` saat inisialisasi. Jangan sunting isinya secara manual di sini.

<!-- BEGIN HARNESS MANAGED: CORE_GOVERNANCE -->
<!-- END HARNESS MANAGED: CORE_GOVERNANCE -->
