# DUA JALAN

Episode 01 **Dompet Rp50 Juta** menggunakan narasi Edge TTS bahasa Indonesia dengan durasi video 15 detik.

## Buat narasi

1. Di GitHub, buka **Actions → DUA JALAN · Narasi Episode 01 → Run workflow** dan pilih branch default.
2. Pilih suara `id-ID-ArdiNeural` (default) atau `id-ID-GadisNeural`. Naskah bisa diedit di formulir.
3. Setelah run berhasil, unduh artifact `dua-jalan-ep01-narasi`. Ekstrak empat MP3 dan `timing.csv` ke `outputs/narasi`.

Untuk menjalankan TTS lokal, siapkan Python 3.10+, FFmpeg, ffprobe, dan akses jaringan ke Edge TTS.

```bash
python -m pip install -r requirements.txt
python scripts/dua_jalan.py tts episodes/ep01.json outputs/narasi
```

## Campur dengan master lokal

Simpan master di `inputs/DUA-JALAN-EP01-Dompet-Rp50-Juta.mp4`. Untuk Episode 01, gunakan master H.264 vertikal 1080 × 1920, 24 fps, 15 detik, dengan track ambience dan efek.

```bash
python scripts/dua_jalan.py mix inputs/DUA-JALAN-EP01-Dompet-Rp50-Juta.mp4 outputs/narasi outputs/DUA-JALAN-EP01-Dompet-Rp50-Juta-Narasi.mp4 --expect-video 1080x1920@24
```

Mixer membaca offset dari CSV, menurunkan ambience saat narasi, dan membatasi puncak audio sebelum encoding AAC. Video H.264 disalin langsung. Codec video lain dikonversi ke H.264 dengan resolusi dan frame rate master. Script memeriksa durasi video dan audio serta mendekode audio hasil sampai akhir. Workflow hanya mengunggah audio narasi dan CSV. Simpan master dan hasil MP4 secara lokal.

## Episode berikutnya

Salin `episodes/ep01.json` dan atur `text`, `start`, dan `end` untuk setiap adegan. Waktu dalam detik, dan `end` adegan terakhir harus sama dengan durasi track video master. `short` opsional dipakai jika narasi asli belum muat dengan percepatan maksimal 1,25×. Jika naskah diubah lewat formulir, versi ringkas perlu disiapkan di konfigurasi agar maknanya tetap sesuai.

Jalankan perintah `tts` dengan konfigurasi dan folder keluaran episode baru, tambahkan `--voice id-ID-GadisNeural` jika diinginkan, lalu jalankan `mix` dengan master dan folder baru. Untuk membuat workflow episode lain, sesuaikan input naskah, path konfigurasi, jumlah klip dan nama artifact di `.github/workflows/dua-jalan-tts.yml`.
