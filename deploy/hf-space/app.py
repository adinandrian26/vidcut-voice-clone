"""VidCut Voice Clone — demo publik di Hugging Face Space (ZeroGPU).

Backend: VoxCPM2 (openbmb/VoxCPM2, Apache-2.0) — Bahasa Indonesia resmi,
kemiripan suara tertinggi pada benchmark MiniMax-MLS (SIM ID 80.0).

File ini untuk Space SDK "Gradio" dengan perangkat ZeroGPU (gratis).
Dekorator @spaces.GPU otomatis non-aktif bila dijalankan tanpa ZeroGPU.
"""
from __future__ import annotations

import os

import gradio as gr
import librosa
import numpy as np
import soundfile as sf
import spaces
from voxcpm import VoxCPM

MODEL_ID = os.environ.get("VOXCPM_MODEL", "openbmb/VoxCPM2")
MAX_TEXT_CHARS = 600

# Muat model di level modul. Di ZeroGPU, operasi CUDA di luar @spaces.GPU
# memakai mode emulasi resmi Hugging Face.
model = VoxCPM.from_pretrained(MODEL_ID, load_denoiser=False)


def _prepare_reference(path: str | None) -> str:
    """Validasi + normalisasi audio referensi ke 16 kHz mono WAV."""
    if not path:
        raise gr.Error("Unggah audio referensi 5–20 detik dulu.")
    data, sr = sf.read(path, dtype="float32", always_2d=False)
    if data.ndim > 1:
        data = data.mean(axis=1)
    seconds = len(data) / sr
    if seconds < 3:
        raise gr.Error("Audio referensi terlalu pendek (minimal 3 detik).")
    if seconds > 60:
        data = data[: int(60 * sr)]
    if sr != 16000:
        data = librosa.resample(data, orig_sr=sr, target_sr=16000)
    out = os.path.join(os.path.dirname(path), "reference_16k.wav")
    sf.write(out, data, 16000, format="WAV", subtype="PCM_16")
    return out


@spaces.GPU(duration=150)
def _generate(reference_path: str, text: str, prompt_text: str,
              steps: int, cfg: float, seed: int):
    kwargs = dict(
        cfg_value=float(cfg),
        inference_timesteps=int(steps),
        seed=int(seed),
        reference_wav_path=reference_path,
    )
    # Mode "ultimate cloning": sertakan transkrip audio referensi.
    if prompt_text and prompt_text.strip():
        kwargs.update(prompt_wav_path=reference_path,
                      prompt_text=prompt_text.strip())
    wav = model.generate(text=text, **kwargs)
    if hasattr(wav, "detach"):
        wav = wav.detach().cpu().numpy()
    sr = int(getattr(getattr(model, "tts_model", None), "sample_rate", 48000))
    return (sr, np.asarray(wav, dtype="float32").squeeze())


def run(reference, text, prompt_text, steps, cfg, seed):
    text = (text or "").strip()
    if not text:
        raise gr.Error("Isi teks yang ingin diucapkan.")
    if len(text) > MAX_TEXT_CHARS:
        raise gr.Error(
            f"Teks terlalu panjang ({len(text)} karakter). "
            f"Maksimal {MAX_TEXT_CHARS} karakter per proses.")
    ref_path = _prepare_reference(reference)
    return _generate(ref_path, text, prompt_text or "", steps, cfg, seed)


with gr.Blocks(title="VidCut Voice Clone") as demo:
    gr.Markdown(
        "# 🎙️ VidCut Voice Clone\n"
        "Clone suara dari **audio referensi 5–20 detik** dengan "
        "[VoxCPM2](https://huggingface.co/openbmb/VoxCPM2) "
        "(Apache-2.0, Bahasa Indonesia resmi).\n\n"
        "> Gunakan hanya suara milik Anda sendiri atau yang Anda punya "
        "izin tertulis. Hasil berlabel AI-generated.")
    with gr.Row():
        with gr.Column():
            reference = gr.Audio(
                label="Audio referensi (5–20 detik, satu pembicara, "
                      "tanpa musik)",
                type="filepath")
            text = gr.Textbox(
                label="Teks (Bahasa Indonesia/Inggris)",
                lines=4,
                placeholder="Halo, selamat datang di VidCut. "
                            "Hari ini kita belajar membuat suara AI.")
            prompt_text = gr.Textbox(
                label="Transkrip audio referensi (opsional, meningkatkan "
                      "kemiripan — mode ultimate cloning)",
                lines=2,
                placeholder="Tulis kata per kata isi audio referensi...")
            with gr.Accordion("Pengaturan lanjutan", open=False):
                steps = gr.Slider(4, 32, value=10, step=1,
                                  label="Langkah inferensi")
                cfg = gr.Slider(1.0, 3.0, value=2.0, step=0.1,
                                label="CFG (kedekatan ke teks)")
                seed = gr.Slider(0, 99999, value=42, step=1, label="Seed")
            btn = gr.Button("Buat suara", variant="primary")
        with gr.Column():
            output = gr.Audio(label="Hasil (48 kHz)", type="numpy")
            gr.Markdown(
                "**Tips kemiripan terbaik**\n"
                "1. Referensi bersih, satu orang, tanpa musik.\n"
                "2. Sertakan transkrip referensi (mode ultimate cloning).\n"
                "3. Teks pendek (1–3 kalimat) per proses.\n\n"
                "*Tanpa persetujuan pemilik suara, penggunaan dilarang.*")
    btn.click(run, [reference, text, prompt_text, steps, cfg, seed], output)
    gr.Markdown(
        "Kode sumber lengkap + versi mandiri: "
        "[github.com/adinandrian26/vidcut-voice-clone]"
        "(https://github.com/adinandrian26/vidcut-voice-clone)")

demo.launch(share=os.environ.get("GRADIO_SHARE", "0") == "1")
