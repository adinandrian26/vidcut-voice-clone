"""Backend default: Piper (TTS Indonesia, MIT) + OpenVoice v2 (MIT) tone clone.

Alasan (jujur):
- Piper punya suara id_ID (mis. id_ID-fajri-medium) yang berjalan lokal.
- OpenVoice v2 berlisensi MIT dan meniru timbre dari sampel referensi.
- XTTS-v2 TIDAK dipakai default: bahasa Indonesia belum resmi didukung
  dan lisensinya non-komersial (Coqui CPML).
- edge-tts TIDAK dipakai: layanan cloud, melanggar aturan self-hosted.

Alur: Piper hasilkan base id -> OpenVoice v2 convert timbre -> ref sample.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

# Pindahkan cache HuggingFace ke D: agar C: tidak penuh (checkpoint besar).
os.environ.setdefault("HF_HUB_CACHE",
                      str(Path(__file__).resolve().parent.parent.parent.parent
                          / "models" / "hf_cache"))

from ..audio import TARGET_SR


class BackendError(RuntimeError):
    pass


def _device_wanted(want: str) -> str:
    if want in ("cpu", "cuda"):
        return want
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


class OpenVoicePiperBackend:
    name = "openvoice_piper"

    def __init__(self, piper_voice: str, device: str = "auto",
                 model_dir: Path | None = None) -> None:
        self.piper_voice = piper_voice
        self.device = _device_wanted(device)
        self.model_dir = Path(model_dir or Path("models")).resolve()
        self._piper = None
        self._converter = None
        self._source_se = None
        self._speaker_cache: dict[str, list[str]] = {}
        self._target_cache: dict[str, object] = {}

    # -- langkah 1: base TTS Indonesia via Piper --
    def _piper_tts(self, text: str, out_wav: Path) -> Path:
        voice_file = self.model_dir / f"{self.piper_voice}.onnx"
        if not voice_file.exists():
            raise BackendError(
                f"Model suara Piper tidak ada: {voice_file}. "
                "Unduh dulu (lihat README bagian model).")
        try:
            from piper import PiperVoice
        except ImportError as e:
            raise BackendError("Paket piper-tts belum terpasang.") from e
        # Load Piper once per job instead of once per sentence.
        if self._piper is None:
            self._piper = PiperVoice.load(str(voice_file))
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        import wave
        with wave.open(str(out_wav), "wb") as f:
            self._piper.synthesize_wav(text, f)
        # pastikan 24k mono
        from ..audio import to_wav_mono
        fixed = out_wav.with_name(out_wav.stem + "_24k.wav")
        to_wav_mono(out_wav, fixed)
        return fixed

    # -- langkah 2: clone timbre via OpenVoice v2 --
    def _openvoice_convert(self, base_wav: Path, ref_wav: Path,
                           out_wav: Path) -> Path:
        ckpt = self.model_dir / "openvoice_v2"
        if not (ckpt / "converter").exists():
            raise BackendError(
                f"Checkpoint OpenVoice v2 tidak ada di {ckpt}. "
                "Unduh dulu (lihat README bagian model).")
        try:
            from openvoice import se_extractor
            from openvoice.api import ToneColorConverter
        except ImportError as e:
            raise BackendError("Paket OpenVoice belum terpasang.") from e
        # Loading the converter is expensive; keep it for all cues in a job.
        if self._converter is None:
            self._converter = ToneColorConverter(
                str(ckpt / "converter" / "config.json"),
                device=self.device)
            self._converter.load_ckpt(
                str(ckpt / "converter" / "checkpoint.pth"))
        base_se_path = ckpt / "base_speakers" / "ses" / "en-default.pth"
        if not base_se_path.exists():
            raise BackendError(
                f"Embedding speaker bawaan tidak ada: {base_se_path}.")
        import torch
        if self._source_se is None:
            self._source_se = torch.load(str(base_se_path),
                                         map_location=self.device)
        ref_key = str(ref_wav.resolve())
        segs = self._speaker_cache.get(ref_key)
        if segs is None:
            segs = self._speech_segments(ref_wav)
            self._speaker_cache[ref_key] = segs
        se = self._target_cache.get(ref_key)
        if se is None:
            se = self._converter.extract_se(segs)
            self._target_cache[ref_key] = se
        self._converter.convert(
            audio_src_path=str(base_wav),
            src_se=self._source_se,
            tgt_se=se,
            output_path=str(out_wav))
        # converter keluar 22050 Hz -> samakan ke 24k mono pipeline
        from ..audio import to_wav_mono as _to24
        fixed = out_wav.with_name(out_wav.stem + "_24k.wav")
        _to24(out_wav, fixed)
        fixed.replace(out_wav)
        return out_wav

    @staticmethod
    def _speech_segments(ref_wav: Path, min_s: float = 2.0,
                         max_s: float = 8.0) -> list[str]:
        """Potong referensi jadi segmen bicara (VAD energi numpy).

        Menggantikan whisper/silero bawaan OpenVoice yang butuh unduhan
        besar (faster-whisper medium 1,5 GB + CUDA) dan prompt trust.
        """
        import numpy as np
        import soundfile as sf

        data, sr = sf.read(str(ref_wav), dtype="float32", always_2d=False)
        if data.ndim > 1:
            data = data.mean(axis=1)
        win = max(1, sr // 50)
        env = np.convolve(np.abs(data),
                          np.ones(win) / win, mode="same")
        thr = float(env.max() * 0.15)
        mask = env > thr
        segs: list[str] = []
        i, n = 0, len(data)
        idx = 0
        out_dir = ref_wav.parent / "ref_segs"
        out_dir.mkdir(exist_ok=True)
        existing = sorted(out_dir.glob("seg_*.wav"))
        if existing:
            return [str(p) for p in existing]
        while i < n:
            if not mask[i]:
                i += 1
                continue
            j = i
            while j < n and (mask[j] or (j - i) < int(min_s * sr)):
                # izinkan jeda pendek di dalam segmen
                if not mask[j]:
                    k = j
                    while k < n and not mask[k] and (k - j) < int(0.4 * sr):
                        k += 1
                    if k >= n or (k - j) >= int(0.4 * sr):
                        if (j - i) >= int(min_s * sr):
                            break
                    j = k
                    continue
                j += 1
                if (j - i) >= int(max_s * sr):
                    break
            seg = data[i:j]
            if len(seg) >= int(min_s * sr):
                p = out_dir / f"seg_{idx:02d}.wav"
                sf.write(str(p), seg, sr)
                segs.append(str(p))
                idx += 1
            i = j
        if not segs:
            # fallback: pakai file utuh bila tidak ada segmen terdeteksi
            return [str(ref_wav)]
        return segs

    def synthesize(self, text: str, ref_wav: Path, language: str,
                   out_wav: Path) -> Path:
        if language not in ("id", "en"):
            raise BackendError(f"Bahasa tidak didukung backend: {language}")
        tmp_base = out_wav.parent / "base_tts.wav"
        self._piper_tts(text, tmp_base)
        return self._openvoice_convert(tmp_base, ref_wav, out_wav)


def get_backend(name: str, **kwargs):
    if name == "openvoice_piper":
        return OpenVoicePiperBackend(
            piper_voice=kwargs.get("piper_voice", "id_ID-fajri-medium"),
            device=kwargs.get("device", "auto"),
            model_dir=kwargs.get("model_dir"))
    if name == "xtts":
        from .xtts import XTTSBackend
        return XTTSBackend(**kwargs)
    if name == "chatterbox":
        from .chatterbox import ChatterboxBackend
        return ChatterboxBackend(
            device=kwargs.get("device", "auto"),
            exaggeration=float(kwargs.get("exaggeration", 0.5)),
            cfg_weight=float(kwargs.get("cfg_weight", 0.5)),
            t3_model=kwargs.get("t3_model", "v3"),
        )
    if name in ("voxcpm", "voxcpm2"):
        from .voxcpm import VoxCPMBackend
        return VoxCPMBackend(
            device=kwargs.get("device", "auto"),
            model_id=kwargs.get("voxcpm_model", "openbmb/VoxCPM2"),
            cfg_value=float(kwargs.get("voxcpm_cfg", 2.0)),
            steps=int(kwargs.get("voxcpm_steps", 10)),
            seed=int(kwargs.get("voxcpm_seed", 42)),
        )
    raise BackendError(f"Backend tidak dikenal: {name}. "
                       "Lihat VC_BACKEND di .env "
                       "(openvoice_piper, chatterbox, atau voxcpm2).")
