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

## Render master Remotion

Siapkan Node.js 22+, Python 3.10+, FFmpeg, dan ffprobe. Simpan gambar resmi Nara V1 sebagai `public/assets/ep01/nara-v1.png`. Gambar ini dipakai langsung sebagai sumber visual, dengan gerak kamera dan lapisan grafis Remotion. Jika tersedia, simpan empat still vertikal berdasarkan storyboard sebagai `public/assets/ep01/scene-01.png` sampai `scene-04.png`. Still yang tersedia menggantikan gambar referensi pada adegannya dan sebaiknya sudah menampilkan Nara V1 sesuai desain resmi. Simpan gambar empat panel “Nara di antara dua jalan” di `public/assets/ep01/nara-di-antara-dua-jalan.png`. Komposisi memakai panel kiri atas untuk dompet, kanan atas untuk rumah sakit, kiri bawah untuk reaksi Nara, dan kanan bawah untuk ending A/B. PNG adegan tetap dapat menggantikan panel masing-masing. Tambahkan storyboard resmi sebagai `episodes/ep01-storyboard.md` atau kirim di chat untuk penyesuaian shot. Rancangan sementara di `episodes/ep01-visuals.json` mengikuti empat adegan di `episodes/ep01.json`.

```bash
npm ci
npm run render:ep01
```

Master muncul di `outputs/DUA-JALAN-EP01-Dompet-Rp50-Juta.mp4` dengan ambience hujan sintetis. Untuk pengujian tanpa gambar resmi, jalankan `npm run render:fixture`. Fixture memakai nama berawalan `FIXTURE-` dan label visual uji. Pratinjau komposisi di `npm run studio`. Jika diperlukan, arahkan `REMOTION_BROWSER_EXECUTABLE` ke executable Chromium.

Workflow **DUA JALAN · Render Episode 01** menguji fixture pada PR dan bisa dijalankan manual dalam mode fixture atau master. Mode master memerlukan aset di checkout runner. MP4 diverifikasi di runner dan tidak diunggah. Render lokal untuk mendapatkan file MP4.

## Campur dengan master lokal

Gunakan master hasil render di `outputs/DUA-JALAN-EP01-Dompet-Rp50-Juta.mp4`. Untuk Episode 01, gunakan master H.264 vertikal 1080 × 1920, 24 fps, 15 detik, dengan track ambience dan efek.

```bash
python scripts/dua_jalan.py mix outputs/DUA-JALAN-EP01-Dompet-Rp50-Juta.mp4 outputs/narasi outputs/DUA-JALAN-EP01-Dompet-Rp50-Juta-Narasi.mp4 --expect-video 1080x1920@24
```

Mixer membaca offset dari CSV, menurunkan ambience saat narasi, dan membatasi puncak audio sebelum encoding AAC. Video H.264 disalin langsung. Codec video lain dikonversi ke H.264 dengan resolusi dan frame rate master. Script memeriksa durasi video dan audio serta mendekode audio hasil sampai akhir. Workflow hanya mengunggah audio narasi dan CSV. Simpan master dan hasil MP4 secara lokal.

## Episode berikutnya

Salin `episodes/ep01.json` dan atur `text`, `start`, dan `end` untuk setiap adegan. Waktu dalam detik, dan `end` adegan terakhir harus sama dengan durasi track video master. `short` opsional dipakai jika narasi asli belum muat dengan percepatan maksimal 1,25×. Jika naskah diubah lewat formulir, versi ringkas perlu disiapkan di konfigurasi agar maknanya tetap sesuai.

Jalankan perintah `tts` dengan konfigurasi dan folder keluaran episode baru, tambahkan `--voice id-ID-GadisNeural` jika diinginkan, lalu jalankan `mix` dengan master dan folder baru. Untuk membuat workflow episode lain, sesuaikan input naskah, path konfigurasi, jumlah klip dan nama artifact di `.github/workflows/dua-jalan-tts.yml`.
