---
name: deepseek-runner
description: >-
  Run vault governance hooks under DeepSeek Harness at turn and tool boundaries by invoking .agents/hooks/deepseek-adapter.py with a fail-open python3 guard. Use when running under DeepSeek Harness or when the owner says "jalankan hook deepseek", "cek deepseek runner", or "aktifkan adapter deepseek".
---

# deepseek-runner

## Purpose

Menjalankan hook tata kelola vault di bawah DeepSeek Harness (DSH) pada setiap batas siklus giliran dan pemanggilan tool, karena DSH tidak memiliki peluncur hook bawaan. Agen DeepSeek memanggil `.agents/hooks/deepseek-adapter.py` secara eksplisit dengan pagar fail-open `python3` agar gerbang `## Goal Contract` dan pengingat tata kelola tetap berjalan konsisten.

## Procedure

1. **Gunakan perintah peluncur baku dengan guard fail-open `python3`:**
   ```bash
   command -v python3 >/dev/null 2>&1 || exit 0; echo '<payload-json>' | python3 .agents/hooks/deepseek-adapter.py <mode>
   ```
   Guard `command -v python3 >/dev/null 2>&1 || exit 0` memastikan host tanpa `python3` melewati hook secara aman (exit 0) alih-alih gagal dengan kode 127, sedangkan bila `python3` ada, kode keluar adapter diteruskan apa adanya.
2. **Jalankan adapter pada lima batas siklus kerja:**
   - **Awal giliran (`pre-prompt`):** kirim `{"session_id","prompt"}`; baca `injectSteps[].ephemeralMessage` dan aktifkan di konteks (termasuk kewajiban memposting `## Goal Contract` lewat `define-goal` sebelum mutasi pertama).
   - **Sebelum tool (`pre-tool`):** kirim `{"session_id","tool_name","tool_input":{...}}` sebelum `read`/`write`/`edit`/`bash`/`glob`/`grep`/`read_image`. Jika keluaran berisi `decision:"deny"`, **batalkan pemanggilan tool** dan patuhi alasannya (misalnya posting `## Goal Contract`, tetap di dalam batas vault, atau hindari staging luas).
   - **Sesudah tulis/sunting (`post-tool`):** kirim `{"session_id","tool_name","tool_input":{...}}` dan terapkan pengingat frontmatter yang muncul.
   - **Sebelum mengakhiri giliran (`stop`):** kirim `{"session_id","last_assistant_message"}`. Jika `decision:"continue"`, selesaikan insiden terbuka lalu periksa ulang sebelum menutup giliran.
   - **Saat memuat skill (`record-skill`):** kirim `{"session_id","skill"}` sebagai telemetri ringan.
3. **Prioritaskan dua gerbang utama:** (a) gerbang `goal-contract-gate.py` pada `pre-tool` `write`/`edit` yang membaca log sesi `$DSH_SESSION_JSONL`, dan (b) `governance-reminder.py` pada `pre-prompt`.

## Rules & Boundaries

- Adapter bersifat **DeepSeek-keyed**: tanpa penanda lingkungan `DSH_SESSION_ID`, `DSH_HOME`, atau `DSH_SESSION_JSONL`, skrip keluar diam-diam sehingga tidak mengganggu Claude Code, Codex, maupun Antigravity.
- Pagar fail-open `command -v python3 >/dev/null 2>&1 || exit 0` wajib dipertahankan agar paritas aktivasi dan lingkungan tanpa Python tetap aman.
- Karena dipanggil oleh agen, lapisan ini bersifat penasihat pada tingkat pemanggilan — jangan mengklaimnya sebagai penegakan runtime keras; jejak audit dasarnya tetap log sesi yang ditulis host.
- Pelanggaran nyata yang terdeteksi adapter (`decision:"deny"` atau `continue`) wajib dipatuhi, bukan diabaikan.

## Output & Verification

1. Pastikan setiap batas giliran dan pemanggilan tool bermutasi di DSH telah melewati `deepseek-adapter.py` dengan keputusan yang diterapkan.
2. Untuk menguji kontrak hook secara lokal bila `python3` tersedia, jalankan:
   ```bash
   python3 -m unittest discover -s .agents/hooks -p "test_*.py"
   ```
3. Laporkan status eksekusi hook atau alasan penolakan (`deny`/`continue`) secara lugas apabila sebuah tindakan ditahan.
