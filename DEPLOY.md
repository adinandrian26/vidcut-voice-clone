# Deploy Publik — Server, Tanpa Kartu, Bisa Diakses Siapa Saja

Panduan ini menjawab tiga hal: **(1)** server mana yang dipakai (bukan
laptop), **(2)** pembayaran tanpa kartu kredit, **(3)** website publik
yang bisa dibuka siapa saja tanpa meng-clone repo.

## Ringkasan pilihan hosting

| Opsi | Biaya | Butuh kartu? | GPU | Website publik 24/7? |
|---|---|---|---|---|
| **A. HF Space ZeroGPU** (Gradio) | Gratis | **Tidak** | Ya (kuota harian) | Ya |
| **B. Biznet Gio NEO GPU** (Indonesia) | Rp74.000/jam (1x H200) | **Tidak** (pembayaran lokal) | Ya, H200 | Ya, selama mesin berjalan |
| **C. RunPod** (internasional) | Mulai ~$0,2–0,7/jam (kelas RTX) | **Tidak** via kripto | Ya | Ya, selama pod berjalan |
| **D. GitHub Codespaces** | Gratis (kuota bulanan) | **Tidak** | Tidak (CPU) | Sementara (mati saat idle) |
| **E. VPS CPU lokal** (Biznet/IDCloudHost) | Puluhan ribu rupiah/bulan | **Tidak** (transfer/QRIS) | Tidak | Ya |

Catatan jujur: layanan gratis yang minta kartu (Render, Railway, Fly.io,
GCP, AWS) tidak masuk daftar karena kartu wajib; Render/Koyeb free tier
juga hanya 512 MB RAM — Chatterbox (0,5B) dan VoxCPM2 (2B) tidak muat.

## Rekomendasi jalur

1. **Sekarang:** pakai Codespaces (lihat bagian D / README) untuk uji coba
   dengan backend `chatterbox` atau `openvoice_piper`.
2. **Setelah akun Hugging Face berumur ≥30 hari + email terverifikasi:**
   dirikan **Space ZeroGPU** (bagian A) — gratis, publik, dan GPU.
   Ini adalah tujuan akhir "website bisa diakses siapa saja".
3. **Kalau butuh produksi serius / banyak pengguna:** GPU lokal
   Biznet (bagian B, tanpa kartu) atau RunPod dengan kripto (bagian C).
4. **Kalau cukup lambat di CPU tapi harus 24/7:** VPS CPU lokal
   (bagian E) menjalankan website; backend `openvoice_piper`.

---

## A. Hugging Face Space + ZeroGPU (Gratis, tanpa kartu)

Ini satu-satunya cara mendapat **GPU gratis** untuk situs publik.

**Syarat (dari kebijakan HF, per 2026):**

- Akun dengan email terverifikasi dan **berumur ≥30 hari**.
- Maksimal **2 Space ZeroGPU** per akun. Gradio SDK saja
  (Docker Space sekarang wajib paket PRO).
- Kuota GPU harian **per pengunjung**: anonim 2 menit, akun HF gratis
  5 menit, PRO 40 menit. Setiap perangkat ZeroGPU adalah NVIDIA
  RTX Pro 6000 Blackwell (kelas H100).

**Langkah:**

1. Masuk [huggingface.co](https://huggingface.co) → **New Space**.
2. Isi nama, pilih visibilitas **Public**, SDK **Gradio**.
3. Unggah isi folder `deploy/hf-space/` dari repo ini
   (`app.py`, `requirements.txt`, `README.md`).
   Bisa lewat web (drag & drop) atau:
   ```bash
   huggingface-cli login
   huggingface-cli upload <username>/<nama-space> deploy/hf-space . --repo-type space
   ```
4. **Settings → Space hardware → ZeroGPU**. Space akan build (± beberapa
   menit). Kunjungan pertama mengunduh model (beberapa GB), setelah itu
   normal.
5. URL hasil: `https://huggingface.co/spaces/<username>/<nama-space>` —
   buka oleh siapa saja, tanpa clone apa pun.

Backend di Space adalah **VoxCPM2** (lihat bagian model di bawah).

## B. Biznet Gio NEO GPU (Indonesia, tanpa kartu)

GPU lokal H200 dengan skema *pay-as-you-go* per jam — cocok untuk
"render sekalian cepat lalu matikan".

- **Harga resmi (halaman produk Biznet Gio, 2026):**
  1x H200 = **Rp74.000/jam**, 2x = Rp147.000/jam, bertingkat sampai
  8x H200 (Rp589.000/jam).
- Datacenter di Indonesia, pembayaran portal lokal (transfer bank /
  Virtual Account; konfirmasi metode saat pendaftaran) — tidak butuh
  kartu kredit.
- Di mesin GPU ini jalankan langsung image Docker repo ini:
  ```bash
  git clone https://github.com/adinandrian26/vidcut-voice-clone
  cd vidcut-voice-clone
  cp .env.example .env
  # edit .env: VC_BACKEND=voxcpm2, VC_DEVICE=cuda
  docker compose up --build -d   # atau Dockerfile.gpu + runtime nvidia
  ```
- H200 sangat cepat: VoxCPM2 di RTX 4090 saja RTF ≈0,3 (3x real-time);
  di H200 jauh lebih cepat. Biaya per video pendek: beberapa ribu rupiah.
- Matikan instance jika selesai — hitungan per jam berhenti.

## C. RunPod (internasional, tanpa kartu via kripto)

Untuk GPU kelas menengah yang lebih murah dari H200, RunPod menerima
kartu **dan** deposit kripto (dengan KYC), minimum $10 — jalur tanpa
kartu: beli USDT di exchange lokal (Indodax/Pintu/Tokocrypto, bayar
transfer bank/QRIS) lalu deposit.

- Buat Pod dari template Docker; port aplikasi diekspos lewat proxy
  RunPod (HTTP service), jadi URL-nya publik.
- Container yang dipakai sama: `docker-compose.yml` repo ini;
  set `VC_BACKEND=voxcpm2`, `VC_DEVICE=cuda`.
- Catatan: harga berubah-ubah; cek konsol saat memesan. Untuk hemat,
  pilih GPU kelas RTX 4090/L4 untuk VoxCPM2 (butuh ~8 GB VRAM).

## D. GitHub Codespaces (sekarang, tanpa kartu)

Sudah terdokumentasi di README (bagian "GitHub Codespaces").
Ringkas:

- Mesin **4-core / 16 GB** bila ingin menjalankan VoxCPM2 di CPU
  (2B parameter butuh RAM besar). 2-core / 8 GB hanya untuk
  `chatterbox` (0,5B) atau `openvoice_piper`.
- Port `8520` dijadikan **Public** → URL bisa dibuka siapa saja selama
  Codespace hidup. Ini bukan hosting 24/7 (Codespace berhenti saat idle).

## E. VPS CPU lokal 24/7 (Biznet Gio / IDCloudHost)

Paling murah untuk halaman web yang selalu hidup: VPS CPU kecil
(puluhan ribu rupiah/bulan, bayar transfer bank/QRIS/e-wallet).
Jalankan `docker compose up -d` seperti README bagian 7, taruh nginx +
HTTPS di depannya, isi `VC_CORS_ORIGINS` dengan domain.

- Backend di VPS CPU: `openvoice_piper` (Lambat? Piper + OpenVoice
  masih jauh lebih ringan) atau `chatterbox` bila RAM ≥8 GB.
- VoxCPM2 di CPU hanya layak bila RAM ≥16 GB; tetap lambat.

---

## Perbandingan model (prioritas: kemiripan suara Indonesia)

Hasil verifikasi ulang dari README resmi tiap repo (Oktober 2026).
Angka SIM/SS/WER di bawah adalah benchmark milik vendor masing-masing
(jadi berpotensi bias), tapi daftar bahasa dan lisensi adalah fakta.

| Model | Mirip ElevenLabs? | Indonesia | Lisensi | Ukuran | Vonis |
|---|---|---|---|---|---|
| **VoxCPM2** (OpenBMB) | SIM id **80,0** vs ElevenLabs 66,0 (MiniMax-MLS) | **Resmi** (30 bahasa) | Apache-2.0 | 2B, ~8 GB VRAM | ✅ **pilihan utama** (sudah jadi backend `voxcpm2`) |
| Chatterbox Multilingual V3 | Klaim vendor "kelas ElevenLabs" | via fonem Melayu `ms` | MIT | 0,5B, RAM 8 GB cukup | ✅ cadangan ringan (sudah jadi backend `chatterbox`) |
| Qwen3-TTS 0.6B/1.7B-Base | SIM **di atas ElevenLabs** di 10 bahasanya (mis. en 0,829 vs 0,613) | ❌ **tidak ada** (zh, en, ja, ko, de, fr, ru, pt, es, it) | Apache-2.0 | 0,6B ringan | ❌ bukan untuk Indonesia; opsi bila butuh Inggris |
| Fish S2-Pro / Drama 3 | SIM terbaik di 17/24 bahasa; WER SOTA | ±100 bahasa (id kemungkinan ada) | ❌ lisensi komunitas/riset khusus (non-komersial, pelanggaran ditindak) | S2-Pro 4B / Drama 3 35B-MoE | ❌ lisensi + terlalu berat untuk hosting gratis |
| CosyVoice 3 (0.5B) | SS zh 78,0 / en 71,8 (SOTA open) | ❌ (9 bahasa + dialek Mandarin, tanpa id) | Apache-2.0 | 0,5B ringan | ❌ bukan untuk Indonesia |
| IndexTTS-2.5 | SS kompetitif, RTF 0,2 (cepat) | ❌ (zh, en, ja, es, ar) | ❌ lisensi khusus Bilibili | 0,8B | ❌ bahasa + lisensi |
| Zonos v0.1 (Zyphra) | Klaim vendor "setara/melampaui provider top" | ❌ (en, ja, zh, fr, de) | Apache-2.0 | VRAM 6 GB+ | ❌ bukan untuk Indonesia |
| Seed-VC (Plachtaa) | VC zero-shot 1–30 detik, kualitas level RVC | ✅ **agnostik bahasa** (konversi, bukan TTS) | ⚠️ **GPL-3.0** (copyleft) | 25M–200M ringan | ⚠️ kandidat pengganti converter OpenVoice; boleh jalan server-side, tapi perlu kajian lisensi bobot |
| GPT-SoVITS / RVC | mirip bila training per speaker | ✅ agnostik (training) | MIT | butuh training + GPU | ⚠️ tidak praktis untuk pengunjung acak (zero-shot lemah) |
| OpenVoice v2 + Piper id_ID | di bawah semua di atas (timbre saja) | ✅ ya (Piper id_ID) | MIT | ringan, CPU ok | ✅ cadangan CPU kecil (sudah jadi backend default) |

Kesimpulan (tidak berubah, kini terverifikasi):
**VoxCPM2** satu-satunya yang sekaligus (1) resmi dukung Indonesia,
(2) SIM Indonesia tertinggi yang terdokumentasi, (3) lisensi permisif
komersial, (4) zero-shot untuk pengunjung acak. Jalur upgrade kemiripan
berikutnya tanpa ganti TTS: **Piper id_ID → Seed-VC** (menggantikan
converter OpenVoice), dengan catatan lisensi GPL-3.0.

## Mengaktifkan VoxCPM2 di aplikasi ini

```bash
pip install voxcpm        # dependensi besar; sekali saja
# .env:
VC_BACKEND=voxcpm2
VC_DEVICE=auto
VC_VOXCPM_STEPS=10        # naikkan (mis. 16) = lebih bagus, lebih lambat
VC_VOXCPM_CFG=2.0
```

Tips kemiripan terbaik: sampel 10–20 detik yang bersih satu pembicara,
tanpa musik; hindari Demucs bila audio sudah bersih (lebih cepat, tanpa
artefak); teks pendek per kalimat (sudah otomatis dipotong pipeline).

## Mode publik (tanpa kunci akses)

Bila situs ingin dibuka siapa saja tanpa kunci:

- Kosongkan `VC_API_KEY` di `.env` (header `X-API-Key` jadi opsional).
- Lindungi dari penyalahgunaan: `VC_RATE_PER_MINUTE=10`,
  `VC_RETENTION_HOURS=24`, watermark + label Suara AI, checkbox
  persetujuan (sudah aktif semua secara default).
- Tambahkan halaman Syarat (`/terms`) di deskripsi situs.

Peringatan etika & hukum: tanpa izin pemilik suara, meniru suara orang
lain dilarang. Jangan jadikan situs terbuka tanpa penyaring persetujuan.
