"""Kontrak backend voice clone. Ganti model lewat satu file: config VC_BACKEND."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol


class VoiceBackend(Protocol):
    name: str

    def synthesize(self, text: str, ref_wav: Path, language: str,
                   out_wav: Path) -> Path:
        """Hasilkan WAV 24k mono dari teks dengan suara ref_wav."""
        ...
