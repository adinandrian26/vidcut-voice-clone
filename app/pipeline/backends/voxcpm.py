"""Backend VoxCPM2 (Apache-2.0, OpenBMB) — prioritas kemiripan suara.

Alasan memilih VoxCPM2 untuk Bahasa Indonesia:
- Bahasa Indonesia didukung RESMI (30 bahasa, tanpa remap ke 'ms').
- Benchmark MiniMax-MLS (test SIM/%), VoxCPM2 mencatat kemiripan
  Indonesia tertinggi di antara model yang diuji:
  VoxCPM2 80.0 | FishAudio S2 76.3 | Minimax 72.9 | ElevenLabs 66.0.
- Lisensi Apache-2.0: bebas komersial.
- Output 48 kHz (dikonversi ke 24k mono oleh pipeline).
- Ada jalur "ultimate cloning" (audio referensi + transkripnya) yang
  mempertahankan timbre dan gaya bicara paling utuh.

Catatan sumber daya (jujur):
- GPU: ~8 GB VRAM (RTF ~0.3 di RTX 4090; lebih cepat di H200).
- CPU: bisa, tetapi berat (2B parameter). Sediakan RAM >= 16 GB;
  pada 8 GB gunakan backend chatterbox/openvoice_piper.
"""
from __future__ import annotations

import os
from pathlib import Path

# Pindahkan cache HuggingFace ke drive proyek (model besar).
os.environ.setdefault("HF_HUB_CACHE",
                      str(Path(__file__).resolve().parent.parent.parent.parent
                          / "models" / "hf_cache"))

from ..audio import to_wav_mono


class VoxCPMBackend:
    name = "voxcpm2"

    def __init__(self, device: str = "auto",
                 model_id: str = "openbmb/VoxCPM2",
                 cfg_value: float = 2.0, steps: int = 10,
                 seed: int = 42, **kwargs) -> None:
        self._device = device
        self.model_id = model_id
        self.cfg_value = cfg_value
        self.steps = steps
        self.seed = seed
        self._model = None

    def _device_resolved(self) -> str:
        if self._device in ("cpu", "cuda"):
            return self._device
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    def _get_model(self):
        if self._model is None:
            try:
                from voxcpm import VoxCPM
            except ImportError as e:
                raise RuntimeError(
                    "voxcpm belum terpasang. Install: pip install voxcpm "
                    "(butuh RAM >= 16 GB untuk CPU atau GPU ~8 GB VRAM)."
                ) from e
            denoiser = os.environ.get("VC_VOXCPM_DENOISER", "0").strip() in (
                "1", "true", "True")
            self._model = VoxCPM.from_pretrained(
                self.model_id, load_denoiser=denoiser)
        return self._model

    def synthesize(self, text: str, ref_wav: Path, language: str,
                   out_wav: Path) -> Path:
        # VoxCPM2 mendeteksi bahasa otomatis; 'id' didukung resmi.
        model = self._get_model()
        wav = model.generate(
            text=str(text),
            reference_wav_path=str(ref_wav),
            cfg_value=self.cfg_value,
            inference_timesteps=self.steps,
            seed=self.seed,
        )
        import numpy as np
        import soundfile as sf

        if hasattr(wav, "detach"):
            wav = wav.detach().cpu().numpy()
        wav = np.asarray(wav, dtype="float32").squeeze()
        tts = getattr(model, "tts_model", None)
        sr = int(getattr(tts, "sample_rate", 48000))
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_wav), wav, sr, format="WAV", subtype="PCM_16")
        # VoxCPM2 keluar 48 kHz -> samakan ke 24k mono pipeline.
        fixed = out_wav.with_name(out_wav.stem + "_24k.wav")
        to_wav_mono(out_wav, fixed)
        fixed.replace(out_wav)
        return out_wav
