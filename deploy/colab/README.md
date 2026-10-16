# GPU Gratis via Colab/Kaggle (tanpa kartu)

Jalankan VoxCPM2 di GPU gratis dan dapatkan URL publik sementara —
tanpa kartu kredit, tanpa clone manual.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/adinandrian26/vidcut-voice-clone/blob/main/deploy/colab/VidCut_VoiceClone_Publik.ipynb)

1. Klik badge di atas (atau buka file `.ipynb` di folder ini via
   `colab.research.google.com` → File → Open notebook → GitHub →
   `adinandrian26/vidcut-voice-clone`).
2. Runtime → Change runtime type → **T4 GPU**.
3. Runtime → **Run all**. Tunggu install + unduhan model pertama.
4. Salin URL `https://xxx.gradio.live` dari output sel terakhir —
   itu website publiknya (berlaku selama sesi hidup).

Batas (aturan resmi Colab): sesi ≤ ±12 jam, mati bila idle, kuota GPU
harian fluktuatif. Di Kaggle: butuh verifikasi no. HP + nyalakan
Internet & GPU di pengaturan notebook. Detail lengkap: `DEPLOY.md`
bagian F.
