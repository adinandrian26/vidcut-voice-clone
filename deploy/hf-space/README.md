---
title: VidCut Voice Clone
emoji: 🎙️
colorFrom: indigo
colorTo: gray
sdk: gradio
app_file: app.py
pinned: false
license: apache-2.0
---

# VidCut Voice Clone (VoxCPM2 + ZeroGPU)

Demo publik clone suara Bahasa Indonesia. Backend
[VoxCPM2](https://huggingface.co/openbmb/VoxCPM2) (Apache-2.0) — pada
benchmark MiniMax-MLS mencatat kemiripan suara Indonesia tertinggi
(SIM 80.0, di atas ElevenLabs 66.0 dan FishAudio S2 76.3).

## Mengaktifkan ZeroGPU (gratis, tanpa kartu)

1. Buat Space baru dengan SDK **Gradio** (nama bebas).
2. Unggah isi folder `deploy/hf-space/` dari repositori
   [vidcut-voice-clone](https://github.com/adinandrian26/vidcut-voice-clone):
   `app.py`, `requirements.txt`, dan README ini (Space membaca
   metadata di baris paling atas).
   Cara cepat (satu perintah, dari folder repo):
   ```powershell
   .\deploy\hf-space\deploy-space.ps1 -SpaceId "username/nama-space"
   ```
   Atau manual lewat web (drag & drop).
3. Buka **Settings → Space hardware** dan pilih **ZeroGPU**.
4. Space akan build (beberapa menit). Kunjungan pertama mengunduh model
   (± beberapa GB) sehingga lambat sekali; setelah itu responsif.

Syarat akun gratis: email terverifikasi dan akun berumur lebih dari
30 hari (maksimal 2 Space ZeroGPU per akun). Tanpa ZeroGPU, Space akan
mencoba berjalan di CPU dan sangat lambat.

## Pemakaian

- Unggah audio referensi 5–20 detik (satu pembicara, tanpa musik).
- Isi teks — Bahasa Indonesia didukung resmi.
- Opsional: tulis transkrip audio referensi untuk mode *ultimate
  cloning* (kemiripan gaya bicara paling utuh).
- Tekan **Buat suara**.

Kuota GPU harian per pengguna: anonim 2 menit, akun gratis 5 menit,
PRO 40 menit. Teks pendek (1–3 kalimat) per proses.

## Etika

Gunakan hanya suara milik sendiri atau dengan izin tertulis. Dilarang
untuk penipuan, hoaks, atau meniru orang lain tanpa izin. Hasil perlu
ditandai sebagai suara AI saat dibagikan.
