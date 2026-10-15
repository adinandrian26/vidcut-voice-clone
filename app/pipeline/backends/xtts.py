"""Backend XTTS-v2: TERSEDIA tapi NONAKTIF secara default.

Alasan jujur:
- XTTS-v2 belum resmi mendukung bahasa Indonesia (hasil id sering kacau).
- Lisensi Coqui CPML non-komersial: tidak boleh dipakai komersial.
Aktifkan hanya untuk eksperimen non-komersial bahasa yang didukung
(en, es, fr, de, it, pt, pl, tr, ru, nl, cs, ar, zh, ja, hu, ko).
"""
from __future__ import annotations

from pathlib import Path


class XTTSBackend:
    name = "xtts"

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def synthesize(self, text: str, ref_wav: Path, language: str,
                   out_wav: Path) -> Path:
        if language == "id":
            raise RuntimeError(
                "XTTS-v2 tidak resmi mendukung bahasa Indonesia. "
                "Pakai backend openvoice_piper untuk bahasa Indonesia.")
        try:
            from TTS.api import TTS
        except ImportError as e:
            raise RuntimeError("Paket coqui-TTS belum terpasang.") from e
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        tts.tts_to_file(text=text, speaker_wav=str(ref_wav),
                        language=language, file_path=str(out_wav))
        return out_wav
