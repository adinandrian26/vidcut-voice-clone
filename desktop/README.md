# VidCut Desktop (software, bukan web)

Jendela Windows untuk voice clone. Ringan (Tkinter + `requests` saja,
tanpa torch) sehingga bisa dibundel jadi satu file .exe kecil.

## Cara pakai (lokal)

Klik 2x **`Jalankan_VidCut.bat`** — backend menyala otomatis, lalu
jendela software terbuka. Isi URL (`http://localhost:8520`),
kunci akses (kosongkan bila lokal tanpa kunci), teks, dan sampel
suara → Generate → Putar / Simpan MP3.

URL + kunci diingat otomatis (`~/.vidcut_desktop.json`).

## Arahkan ke GPU cloud (kualitas maksimal)

Ganti **URL layanan** ke server GPU (VPS/RunPod/Colab backend) dan isi
**Kunci akses**-nya. Software-nya sama — yang berubah hanya mesinnya:

| Mesin | Kartu? | Kualitas |
|---|---|---|
| Laptop ini (CPU) | — | Standar (Piper/OpenVoice) |
| Colab T4 per sesi | Tidak | Tinggi (Chatterbox/VoxCPM2) |
| VPS/RunPod GPU sewaan | Transfer/kripto | Tertinggi, 24/7 |

## Build .exe (opsional)

```powershell
pip install pyinstaller
pyinstaller --noconsole --onefile --name VidCutDesktop desktop\vidcut_desktop.py
```

Hasil: `dist\VidCutDesktop.exe` (±15 MB). Jangan commit .exe ke git.
