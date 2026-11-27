# Initial-Prompt Skeleton (Bebas-Python & Ramah Awam)

Templat ini digunakan untuk menulis berkas `handoff/INITIAL-PROMPT-YYYY-MM-DD--<topik>.txt` yang siap ditempel langsung ke awal sesi AI berikutnya (baik di aplikasi GUI awam maupun CLI/ADE), tanpa ketergantungan Python, shell, atau plugin eksternal.

```text
Paired handoff: handoff/HANDOFF-<same-suffix>.md

## Aturan Kerja Awal

1. Baca seluruh prompt ini sampai selesai sebelum bertindak.
2. Baca AGENTS.md dan SCOPE.md untuk memastikan batas kerja dan bahasa komunikasi (Bahasa Indonesia formal-sederhana).
3. Verifikasi fakta langsung dari berkas aktual di vault sebelum menyetujui klaim atau menulis perubahan (ikuti skill anti-sycophancy, confidence, dan brave).

## Konteks Sesi Penerus

<Sebutkan ringkas sesi sebelumnya, apa yang sudah selesai di work/inbox, work/concept, work/drafts, atau work/canon, serta mandat konkret untuk sesi ini.>

## Goal

- **Session Goal:** <Satu kondisi selesai yang terukur dan dapat diperiksa langsung pada akhir sesi ini.>
- **Ultimate Goal:** <Tujuan besar proyek pemilik, atau "not yet defined by user".>
- **Linkage:** <Satu kalimat yang menjelaskan bagaimana Session Goal mendekatkan proyek ke Ultimate Goal.>

## Bacaan Wajib (Berurutan)

1. Baca penuh berkas pasangan: `handoff/HANDOFF-<same-suffix>.md`.
2. Baca `SCOPE.md` dan `.agents/Memory.md`.
3. Baca daftar heading (`## `) dan entri terbaru pada `.agents/Context.md` dan `.agents/Lessons.md`.
4. Baca berkas kerja aktif yang relevan: `<daftar jalur berkas spesifik di work/ atau raw-kb/>`.

## Pemeriksaan Keadaan Awal (Baca-Saja)

- Pastikan berkas kerja terbaru yang disebut di handoff benar-benar ada di lokasi yang dicatat.
- Bandingkan posisi terakhir di `.agents/Context.md` dengan catatan handoff; bila ada perbedaan, berkas aktual di vault dan `.agents/Context.md` menjadi acuan fakta terbaru.

## Arahan Setelah Membaca Konteks

<Pilih satu: "MULAI LANGSUNG pada langkah pertama yang sudah disetujui pemilik" atau "SIAGA — sampaikan ringkasan posisi terbaru dan tunggu konfirmasi pemilik sebelum menyunting berkas".>

## Hal Penting & Larangan

- <Catat 2–4 hal yang rawan salah atau jangan diubah tanpa izin pemilik.>
- Jangan mengarang isi berkas, tanggal, angka, atau status penyelesaian tanpa memeriksa berkasnya langsung.

## Kewajiban Penutupan Sesi Berikutnya

Sebelum sesi berikutnya ditutup, wajib membuat pasangan berkas serah-terima baru di `handoff/`:
1. `handoff/HANDOFF-YYYY-MM-DD--<topik-baru>.md` (memuat blok `## Goal` yang identik).
2. `handoff/INITIAL-PROMPT-YYYY-MM-DD--<topik-baru>.txt` (memuat blok `## Goal` yang identik dan baris `Paired handoff:` yang menunjuk pasangan barunya).
3. Catat posisi akhir sesi di `.agents/Context.md` lewat skill `session-log`.
```

## Aturan Penulisan Ringkas

- Baris `Paired handoff: handoff/HANDOFF-<same-suffix>.md` wajib muncul tepat satu kali di bagian paling atas berkas `.txt`.
- Blok `## Goal` (`Session Goal`, `Ultimate Goal`, `Linkage`) wajib identik kata demi kata dengan blok `## Goal` di berkas `handoff/HANDOFF-<same-suffix>.md`.
- Berkas `.txt` ditulis sebagai teks biasa tanpa frontmatter YAML agar dapat langsung ditempel ke jendela chat aplikasi AI mana pun.
