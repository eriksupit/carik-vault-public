---
name: canvas
description: >-
  Create and edit valid JSON Canvas (.canvas) files with nodes, edges, groups, and clean non-overlapping coordinates using pure Python-free JSON editing. Use when the owner says "buat canvas", "bikin peta konsep", "gambar diagram canvas", or "sunting file .canvas".
---

# canvas

## Purpose

Membuat dan menyunting berkas peta visual berformat terbuka JSON Canvas (`.canvas`, spesifikasi 1.0) yang berisi `nodes`, `edges`, dan `groups` dengan tata letak bersih dan koordinat tidak saling menumpuk. Seluruh proses dilakukan dengan penyuntingan teks JSON murni 100% bebas-Python.

## Procedure

1. **Siapkan struktur dasar atau baca berkas `.canvas` yang ada.** Struktur puncak JSON Canvas terdiri dari dua larik:
   ```json
   {
     "nodes": [],
     "edges": []
   }
   ```
   Contoh lengkap peta konsep, papan proyek, dan diagram alur tersedia di `references/EXAMPLES.md`.
2. **Buat `nodes` dengan ID unik 16 karakter heksadesimal huruf kecil** (misalnya `"6f0ad84f44ce9c17"`). Setiap node wajib memiliki `id`, `type` (`text`, `file`, `link`, atau `group`), `x`, `y`, `width`, `height`, ditambah field khusus tipenya:
   - `text`: wajib `text` (isi Markdown; pakai `\n` untuk baris baru, bukan `\\n`).
   - `file`: wajib `file` (jalur berkas di vault), opsional `subpath` (`#Heading`).
   - `link`: wajib `url`.
   - `group`: opsional `label`, `background`, `backgroundStyle` (`cover`, `ratio`, `repeat`). Letakkan objek `group` lebih awal di larik `nodes` agar berada di lapisan belakang (z-index bawah).
3. **Atur koordinat dan ukuran secara rapi.** Arah `x` ke kanan, `y` ke bawah (titik kiri-atas node). Gunakan kelipatan 10 atau 20 piksel, beri jarak 50–100 px antarnode agar tidak bertumpuk, dan beri ruang dalam (padding) 20–50 px di dalam batas `group`. Warna opsional memakai preset `"1"`–`"6"` atau hex (`"#FF0000"`).
4. **Hubungkan node lewat `edges`.** Setiap edge wajib memuat `id` unik, `fromNode`, dan `toNode` yang merujuk ID node yang benar-benar ada; opsional `fromSide`/`toSide` (`top`, `right`, `bottom`, `left`), `fromEnd`/`toEnd` (`none`, `arrow`), `color`, dan `label`.
5. **Tulis dan validasi berkas `.canvas`.** Periksa seluruh sintaks JSON, keunikan ID, referensi edge, dan koordinat sebelum melaporkan hasil.

## Rules & Boundaries

- Seluruh penyusunan dilakukan secara native bebas-Python; tidak memerlukan aplikasi Obsidian untuk membuat atau memverifikasi berkas.
- Dilarang memakai `\\n` literal di dalam nilai `text`; gunakan `\n` agar baris baru tampil benar.
- Dilarang menyisakan `fromNode` atau `toNode` yang menggantung (merujuk ID yang tidak ada di `nodes`), dan dilarang memakai ID duplikat di antara `nodes` maupun `edges`.
- Pastikan seluruh node anak yang termasuk dalam sebuah `group` berada di dalam kotak koordinat `group` tersebut tanpa saling menimpa.

## Output & Verification

1. Validasi bahwa berkas `.canvas` adalah JSON sah tanpa koma berlebih atau tanda kutip rusak (baca ulang berkas; bila `jq` atau `python3` tersedia, boleh jalankan pemeriksaan JSON baca-saja secara opsional).
2. Pastikan seluruh `id` unik, setiap `fromNode`/`toNode` terhubung ke node valid, seluruh tipe node memiliki field wajibnya, dan tidak ada koordinat bertumpuk.
3. Laporkan kepada pemilik jalur berkas `.canvas`, jumlah node/group/edge, serta ringkasan alur visual yang dibuat.
