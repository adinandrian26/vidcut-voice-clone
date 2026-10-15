"""Tes pecah kalimat + gabung WAV (tanpa model)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.pipeline.chunk import join_wavs, split_sentences


def test_split():
    s = split_sentences("Halo dunia. Apa kabar? Baik!")
    assert s == ["Halo dunia.", "Apa kabar?", "Baik!"]
    assert split_sentences("   ") == []


def test_split_panjang_dipotong():
    long = "kata " * 100 + "."
    out = split_sentences(long, max_chars=50)
    assert len(out) > 1
    assert all(len(x) <= 60 for x in out)


def test_join(tmp_path):
    import soundfile as sf
    p1 = tmp_path / "a.wav"
    p2 = tmp_path / "b.wav"
    sf.write(str(p1), np.zeros(24000, dtype=np.float32), 24000)
    sf.write(str(p2), np.ones(24000, dtype=np.float32), 24000)
    out = join_wavs([str(p1), str(p2)], str(tmp_path / "o.wav"))
    data, rate = sf.read(out)
    assert rate == 24000
    assert len(data) == 24000 * 2 + int(24000 * 250 / 1000) * 2
