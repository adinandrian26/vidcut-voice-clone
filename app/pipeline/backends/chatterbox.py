"""Backend Chatterbox Multilingual V3 (MIT, Resemble AI).

Kualitas clone kelas ElevenLabs, zero-shot dari sampel 5-10 detik.
Catatan jujur: daftar bahasa resmi belum ada 'id' (Indonesia),
yang tersedia 'ms' (Melayu) — kerabat terdekat. Teks Indonesia
umumnya dihasilkan baik dengan tag 'ms'; kombinasi cfg_weight rendah
membantu aksen mengikuti referensi.
Lisensi MIT: boleh komersial. Watermark PerTh tertanam di output.
"""
from __future__ import annotations

import gc
import os
from pathlib import Path


class ChatterboxBackend:
    name = "chatterbox"

    # Bahasa didukung Chatterbox Multilingual (V3).
    LANGS = {
        "ar": "Arabic", "da": "Danish", "de": "German", "el": "Greek",
        "en": "English", "es": "Spanish", "fi": "Finnish", "fr": "French",
        "he": "Hebrew", "hi": "Hindi", "it": "Italian", "ja": "Japanese",
        "ko": "Korean", "ms": "Malay", "nl": "Dutch", "no": "Norwegian",
        "pl": "Polish", "pt": "Portuguese", "ru": "Russian",
        "sv": "Swedish", "sw": "Swahili", "tr": "Turkish", "zh": "Chinese",
    }

    def __init__(self, device: str = "auto", exaggeration: float = 0.5,
                 cfg_weight: float = 0.5, t3_model: str = "v3",
                 **kwargs) -> None:
        self._device = device
        self.exaggeration = exaggeration
        self.cfg_weight = cfg_weight
        self.t3_model = t3_model
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
            # Prevent OpenMP/BLAS from reserving excessive memory on small
            # Windows CPU hosts before torch and librosa are imported.
            os.environ.setdefault("OMP_NUM_THREADS", "1")
            os.environ.setdefault("MKL_NUM_THREADS", "1")
            os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
            try:
                import torch
                from chatterbox import mtl_tts as cb
                from huggingface_hub import snapshot_download
            except ImportError as e:
                raise RuntimeError(
                    "chatterbox multilingual belum terpasang. "
                    "Install: pip install --force-reinstall --no-deps "
                    "git+https://github.com/resemble-ai/chatterbox.git") from e
            device = self._device_resolved()
            torch.set_num_threads(1)
            self._model = self._load_low_memory(cb, snapshot_download,
                                                torch, device)
        return self._model

    def _load_low_memory(self, cb, snapshot_download, torch, device: str):
        """Load V3 without retaining multi-GB state dictionaries.

        Chatterbox's stock loader keeps the T3 state dictionary alive while
        loading S3Gen.  On an 8 GB Windows machine this doubles peak memory
        and can terminate Python with 0xC0000005.  Load each component in
        sequence and explicitly release its temporary state before the next.
        """
        t3_file = cb._resolve_multilingual_t3_model(self.t3_model)
        ckpt_dir = Path(snapshot_download(
            repo_id=cb.REPO_ID,
            repo_type="model",
            revision="main",
            allow_patterns=[
                "ve.pt", t3_file, "s3gen.pt",
                "grapheme_mtl_merged_expanded_v1.json",
                "conds.pt", "Cangjie5_TC.json",
            ],
        ))
        map_location = torch.device("cpu") if device in ("cpu", "mps") else None

        ve = cb.VoiceEncoder()
        state = torch.load(ckpt_dir / "ve.pt", map_location=map_location,
                           weights_only=True)
        ve.load_state_dict(state)
        del state
        gc.collect()
        ve.to(device).eval()

        t3 = cb.T3(cb.T3Config.multilingual())
        state = cb.load_safetensors(ckpt_dir / t3_file)
        if "model" in state:
            state = state["model"][0]
        t3.load_state_dict(state)
        del state
        gc.collect()
        t3.to(device).eval()

        s3gen = cb.S3Gen()
        state = torch.load(ckpt_dir / "s3gen.pt",
                           map_location=map_location, weights_only=True)
        s3gen.load_state_dict(state)
        del state
        gc.collect()
        s3gen.to(device).eval()

        tokenizer = cb.MTLTokenizer(
            str(ckpt_dir / "grapheme_mtl_merged_expanded_v1.json"))
        conds = None
        builtin_voice = ckpt_dir / "conds.pt"
        if builtin_voice.exists():
            conds = cb.Conditionals.load(
                builtin_voice, map_location=map_location).to(device)
        return cb.ChatterboxMultilingualTTS(
            t3, s3gen, ve, tokenizer, device, conds=conds)

    def synthesize(self, text: str, ref_wav: Path, language: str,
                   out_wav: Path) -> Path:
        # Indonesia tidak ada di daftar resmi; Melayu adalah padanan
        # terdekat untuk teks bahasa Indonesia.
        lang_id = "ms" if language == "id" else language
        if lang_id not in self.LANGS:
            raise RuntimeError(
                f"Bahasa tidak didukung Chatterbox: {language}. "
                f"Didukung: {', '.join(sorted(self.LANGS))}")
        model = self._get_model()
        wav = model.generate(
            text,
            language_id=lang_id,
            audio_prompt_path=str(ref_wav),
            exaggeration=self.exaggeration,
            cfg_weight=self.cfg_weight,
        )
        import soundfile as sf
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(wav, "detach"):
            wav = wav.detach().cpu().squeeze().numpy()
        sf.write(str(out_wav), wav, int(model.sr),
                 format="WAV", subtype="PCM_16")
        return out_wav
