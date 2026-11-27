---
description: Hasilkan (generate) vault turunan Carik baru yang bersih, berstandar File-Over-App (FOA), dan mandiri untuk rekayasa perangkat lunak deterministik (profil app-build).
---

# /buat-vault

Gunakan skrip `scripts/spawn_vault.py` untuk menghasilkan vault turunan baru yang steril dari draf atau data pribadi vault saat ini. Profil bawaan adalah `app-build` (untuk tugas deterministik *coding / software engineering*); profil lain dipilih dengan `--profile <nama>` sesuai `profiles/<nama>/profile.json`.

## Penggunaan

```bash
# Profil bawaan: app-build (setara --profile app-build). Target selalu di luar vault,
# jadi tulis langsung ke target butuh izin eksplisit pemilik.
VAULT_ALLOW_EXTERNAL=<path-tujuan> python3 scripts/spawn_vault.py --target <path-tujuan> --project-name "<Nama Proyek>"
# atau: python3 scripts/spawn_vault.py --target <path-tujuan> --project-name "<Nama Proyek>" --allow-external
```

Tanpa `VAULT_ALLOW_EXTERNAL` atau `--allow-external`, skrip menolak target maupun ZIP yang berada di luar vault, termasuk jalur di luar folder home seperti `/tmp`.

### Opsi Ekspor Arsip (Tanpa Menulis ke Target)
Dengan `--archive-zip`, vault dirakit di direktori sementara sistem yang langsung dibersihkan, dan hanya berkas ZIP yang ditulis. Simpan ZIP di dalam vault (misal: `work/archive/<nama-proyek>.zip`) agar tidak perlu izin tambahan:

```bash
python3 scripts/spawn_vault.py --target /tmp/<nama-proyek> --project-name "<Nama Proyek>" --profile app-build --archive-zip work/archive/<nama-proyek>.zip
```

Pengguna kemudian dapat memindahkan atau mengekstrak berkas `.zip` tersebut ke folder mana pun yang diinginkan.

$ARGUMENTS
