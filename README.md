# VidCut Voice Clone

Clone suara open-source, self-hosted, tanpa API key. Bahasa Indonesia
didukung penuh via **Piper id_ID + OpenVoice v2 (keduanya MIT)**.

Alur: link YouTube / upload → potong sampel → pisah vokal (Demucs) →
cek kualitas → clone per kalimat → label AI → unduh WAV/MP3.

## 1. Syarat

- Python 3.10+, ffmpeg + ffprobe di PATH, git
- CPU bisa (lambat). GPU NVIDIA otomatis dipakai bila ada (`torch.cuda`).
- Koneksi internet untuk unduh model sekali saja (~700 MB total).

## 2. Instalasi (Windows, lokal)

```powershell
cd D:\Automation\ VidCut\voice-clone   # sesuaikan path
python -m pip install -r requirements.txt
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install torchaudio --index-url https://download.pytorch.org/whl/cpu
python -m pip install demucs piper-tts av librosa pydub eng_to_ipa transformers `
  whisper-timestamped inflect unidecode pypinyin jieba gruut langcodes cn2an wavmark
python -m pip install --no-deps "git+https://github.com/myshell-ai/OpenVoice.git"
# Opsional, clone berkualitas lebih tinggi (butuh RAM/GPU lebih besar):
python -m pip install --no-deps "git+https://github.com/resemble-ai/chatterbox.git"
python -m pip install transformers==5.2.0 safetensors==0.5.3 librosa==0.11.0
```

Catatan Windows: paket `av` versi lama gagal build, jadi pasang `av`
biner dulu baru OpenVoice `--no-deps` (urutan di atas sudah benar).

## 3. Unduh model (sekali saja)

```powershell
# Piper id_ID (56 KB + 63 MB) -> models/
#   id_ID-news_tts-medium.onnx (+ .onnx.json)
#   dari https://huggingface.co/rhasspy/piper-voices (id/id_ID/news_tts/medium/)
# OpenVoice v2 -> models/openvoice_v2/
#   converter/config.json, converter/checkpoint.pth (131 MB),
#   base_speakers/ses/en-default.pth
#   dari https://huggingface.co/myshell-ai/OpenVoiceV2
```

Struktur `models/` yang benar:

```
models/
  id_ID-news_tts-medium.onnx
  id_ID-news_tts-medium.onnx.json
  openvoice_v2/converter/config.json
  openvoice_v2/converter/checkpoint.pth
  openvoice_v2/base_speakers/ses/en-default.pth
```

## 4. Menjalankan

```powershell
copy .env.example .env   # sesuaikan bila perlu
python -m uvicorn app.main:app --host 127.0.0.1 --port 8520
```

Cek: `GET http://localhost:8520/api/health`

Contoh end-to-end:

```powershell
python scripts/contoh_request.py --url "https://www.youtube.com/watch?v=..." --text "Halo dunia" --out hasil.wav
```

Halaman web: buka `static/voice-clone.html` (ganti `API` di `app.js`
bila beda host), atau halaman **Voice Clone** di VidCut Web.

## 5. Konfigurasi (.env)

Lihat `.env.example`. Poin penting:

- `VC_BACKEND=openvoice_piper` — ganti model lewat variabel ini.
- `VC_BACKEND=chatterbox` — Chatterbox Multilingual V3; teks Indonesia
  diproses dengan fonem Melayu (`ms`) karena kode `id` belum didukung resmi.
- `VC_EXAGGERATION=0.5`, `VC_CFG_WEIGHT=0.5`, `VC_T3_MODEL=v3`
- Bobot Chatterbox disimpan di `models/hf_cache` pada drive proyek.
- `VC_PIPER_VOICE=id_ID-news_tts-medium`
- `VC_DEVICE=auto` (cpu/cuda bila mau paksa)
- `VC_RETENTION_HOURS=24`, `VC_RATE_PER_MINUTE=10`
- `VC_CORS_ORIGINS=https://domain-anda.com` (produksi)

## 6. Tes

```powershell
python -m pytest -q
```

## 7. Deploy VPS (Docker)

```bash
cp .env.example .env
docker compose up --build -d        # CPU
# GPU: ganti build ke Dockerfile.gpu + runtime nvidia (lihat README docker)
docker compose logs -f api
```

Reverse proxy (nginx) + HTTPS disarankan di depan port 8520.
Isi `VC_CORS_ORIGINS` dengan domain website.

## 8. Batasan jujur

- Kualitas clone tergantung sampel: satu suara, bersih, 10–30 detik.
  Sampel berisik / banyak pembicara → ditolak dengan pesan jelas.
- OpenVoice v2 + Piper menghasilkan intonasi Piper dengan timbre
  sampel (bukan meniru gaya bicara/emosi 100%).
- XTTS-v2 tidak dipakai default: tidak resmi dukung Indonesia +
  lisensi non-komersial. Backend `xtts` tersedia untuk eksperimen
  non-komersial bahasa yang didukung.
- CPU: Demucs + OpenVoice per kalimat bisa menit-menit. GPU disarankan.
- yt-dlp bisa diblokir jaringan tertentu — pakai opsi upload file.
- Watermark: metadata + modul wavmark OpenVoice (inaudible). Ini
  penanda, bukan bukti forensik yang tak terpatahkan.

## 9. Keamanan & etika

Checkbox persetujuan wajib (ditolak server bila tidak dicentang),
halaman Syarat (`static/terms.html`), badge Suara AI, rate limit,
validasi ketat (tanpa shell-string), log audit tanpa isi audio,
retensi 24 jam + tombol hapus data.
# VidCut Voice Clone API

FastAPI backend untuk Voice Clone dan preset suara VidCut.

## Deploy

Repository ini menyertakan `render.yaml` untuk deployment Docker di Render.
Aktifkan persistent disk pada service agar `data/` dan `voices/` tidak hilang.
Setelah backend online, masukkan URL service ke Streamlit Secrets:

```toml
VC_API_URL = "https://vidcut-voice-clone.onrender.com"
```

Jangan gunakan `localhost` untuk URL yang dipakai Streamlit Cloud.

## 7. GitHub Codespaces (tanpa kartu, tanpa PC sebagai server)

Repository ini menyertakan konfigurasi `.devcontainer`. Buat Codespace dari
branch `main`; dependensi Chatterbox akan dipasang dan API otomatis dijalankan
pada port `8520`. Pilih mesin minimal **2-core / 8 GB RAM**. Mesin 4-core lebih
cepat, tetapi menghabiskan kuota core-hours dua kali lebih cepat.

Sebelum membuat Codespace, tambahkan Codespaces secret `VC_API_KEY` pada
repository ini. Gunakan nilai acak yang panjang. Setelah Codespace siap:

1. Buka tab **Ports** dan pastikan port `8520` berstatus **Public**.
2. Salin URL HTTPS port tersebut.
3. Buka URL tersebut langsung di Chrome/Edge. Website Voice Clone tersedia di
   halaman utama dan tidak membutuhkan Streamlit.
4. Masukkan nilai `VC_API_KEY` ke kolom **Kunci akses**, lalu gunakan upload
   audio/YouTube, generate, dengarkan, dan unduh hasil langsung dari browser.

Jika tetap ingin memakai frontend Streamlit terpisah, isi Streamlit Cloud
Secrets berikut:

   ```toml
   VC_API_URL = "https://...app.github.dev"
   VC_API_KEY = "nilai-yang-sama-dengan-codespaces-secret"
   ```

Model diunduh saat penggunaan pertama. Codespace berhenti saat idle; buka lagi
melalui GitHub untuk mengaktifkannya. Data dan cache tetap ada selama Codespace
tidak dihapus. Ini cocok untuk pemakaian pribadi/sesekali, bukan layanan 24/7.
