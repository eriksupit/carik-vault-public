---
name: orient
description: >-
  Run first-contact vault orientation when no Orientation completed marker exists in .agents/Context.md, or on /orient: read canonical files in order, pass a file:line comprehension check, and log the marker (100% Python-free). Use when the owner says "orient", "pahami vault ini", "onboard", or "kenali vault ini".
---

# orient

## Purpose

Membangun pemahaman utuh atas struktur dan tata kelola vault pada **kontak pertama** (ketika belum ada penanda `Orientation completed` di `.agents/Context.md`) atau saat dipanggil lewat `/orient` setelah perubahan tata kelola besar. Skill ini bersifat **router 100% bebas-Python**: ia menunjuk berkas kanonis yang harus dibaca dan menguji pemahaman lewat sitasi `file:line`, tanpa menyimpan salinan aturan agar tidak menciptakan sumber kebenaran kedua.

## Procedure

1. **Deteksi lingkungan vault.** Periksa apakah `work/WORKFLOW.md` ada di akar vault (`generated` jika ada, `harness` jika tidak) dan catat hash pendek Git (`git rev-parse --short HEAD`) bila repositori Git tersedia (isi `no-git` jika tidak).
2. **Baca berkas kanonis secara berurutan.** Jangan melompati urutan dan jangan menebak dari ingatan:
   - Inti tata kelola: `SCOPE.md` → `README.md` → `WORKFLOW.md` → `AGENTS.md`.
   - Kontinuitas sesi: `.agents/Memory.md`, serta indeks heading (`## `) dan entri terbaru `.agents/Context.md` dan `.agents/Lessons.md` (buka berkas fakta di `.agents/memory/` hanya bila relevan).
   - Lapisan domain: `work/WORKFLOW.md` dan `docs/design/README.md` (untuk `generated`) atau berkas `profiles/*/profile.json` (untuk `harness`).
   - Jika melanjutkan sesi sebelumnya, baca juga pasangan terbaru di `handoff/`.
3. **Jawab cek pemahaman bersitasi `file:line` (gerbang wajib).** Buktikan hasil bacaan langsung dari berkas hidup untuk seluruh butir berikut — bila ada satu butir tanpa sitasi `file:line` yang valid, kembali baca berkasnya sebelum lanjut:
   1. Sumber instruksi kanonis lintas-agen dan larangan sumber kebenaran kedua.
   2. Urutan pembacaan bootstrap sebelum kerja substantif.
   3. Berkas identitas `.obsidian` wajib yang harus sah sebagai JSON.
   4. Aturan isolasi Git, aturan staging yang dilarang, dan hook penjaganya.
   5. Properti frontmatter wajib untuk catatan buatan agen.
   6. Gerbang wajib berpersetujuan pemilik antara riset dan rencana implementasi.
   7. Tempat pendaftaran sumber mentah (`raw-kb/SOURCES.md`) dan pemisahan bukti mentah dari sintesis.
   8. Peran masing-masing `.agents/Context.md`, `.agents/Lessons.md`, dan `.agents/Memory.md`.
   9. Jenis lingkungan aktif (`generated` vs `harness`) beserta tahap pipeline atau profilnya.
   10. Kebijakan bahasa percakapan dan lokasi pedoman gaya prosa.
   11. Tujuan toko skill portabel `.agents/skills/` dan urutan hierarki otoritas antarberkas tata kelola.
4. **Catat penanda selesai di `.agents/Context.md`.** Setelah seluruh butir terjawab dengan sitasi sah, tambahkan satu entri ringkas di bagian paling bawah `.agents/Context.md`:
   ```markdown
   ## [YYYY-MM-DD] Orientation completed
   - orient passed for env=<harness|generated>, HEAD <sha>.
   ```
   Jika `.agents/Context.md` tidak ada di vault non-standar, laporkan hal itu daripada membuat berkas liar.

## Rules & Boundaries

- Dilarang menjawab cek pemahaman dari ingatan model atau dari isi skill ini; setiap jawaban wajib merujuk `file:line` berkas aktual di vault.
- Dilarang menyalin ulang aturan tata kelola ke catatan terpisah seolah-olah menjadi kebenaran baru.
- Lewati orientasi penuh untuk re-grounding rutin di tengah sesi bila penanda `Orientation completed` sudah ada; gunakan pembacaan ringan `bootstrap` atau `session-log`.
- Seluruh prosedur 100% bebas-Python dan dapat dijalankan di semua harness maupun editor teks.

## Output & Verification

1. Seluruh 11 butir cek pemahaman terjawab dengan sitasi `file:line` yang sesuai isi berkas terkini.
2. Baris `## [YYYY-MM-DD] Orientation completed` tercatat di bagian bawah `.agents/Context.md` (terverifikasi dengan membaca ekor berkas).
3. Laporkan kepada pemilik bahwa orientasi selesai, sebutkan jenis lingkungan aktif, dan nyatakan kesiapan memulai tugas sesuai `SCOPE.md`.
