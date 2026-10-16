"""Tes backend openvoice_piper: opsi naturalness diteruskan ke Piper."""
import math
import shutil
import struct
from pathlib import Path

import pytest

from app.pipeline.backends.openvoice_piper import (
    OpenVoicePiperBackend,
    get_backend,
)


class FakePiperVoice:
    seen: dict = {}

    @classmethod
    def load(cls, path):
        return cls()

    def synthesize_wav(self, text, wav_file, syn_config=None):
        FakePiperVoice.seen = {"text": text, "syn_config": syn_config}
        import wave
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        frames = b"".join(
            struct.pack("<h", int(9000 * math.sin(
                2 * math.pi * 440 * i / 24000)))
            for i in range(12000))
        wav_file.writeframes(frames)


def test_factory_forwards_piper_naturalness_options():
    backend = get_backend(
        "openvoice_piper", piper_voice="id_ID-news_tts-medium",
        piper_length_scale=1.0, piper_noise_scale=0.8,
        piper_noise_w_scale=0.9)
    assert backend.length_scale == 1.0
    assert backend.noise_scale == 0.8
    assert backend.noise_w_scale == 0.9


@pytest.mark.skipif(shutil.which("ffmpeg") is None,
                    reason="butuh ffmpeg untuk normalisasi 24k")
def test_piper_tts_meneruskan_synthesis_config(monkeypatch, tmp_path: Path):
    (tmp_path / "x.onnx").write_bytes(b"0")
    monkeypatch.setattr("piper.PiperVoice", FakePiperVoice)
    backend = OpenVoicePiperBackend(
        piper_voice="x", device="cpu", model_dir=tmp_path,
        length_scale=1.0, noise_scale=0.8, noise_w_scale=0.9)
    out = backend._piper_tts("halo dunia", tmp_path / "base.wav")

    cfg = FakePiperVoice.seen["syn_config"]
    assert FakePiperVoice.seen["text"] == "halo dunia"
    assert cfg.length_scale == 1.0
    assert cfg.noise_scale == 0.8
    assert cfg.noise_w_scale == 0.9
    assert cfg.normalize_audio is True
    assert Path(out).exists()
