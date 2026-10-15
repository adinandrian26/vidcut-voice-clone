"""Uji A/B: openvoice_piper vs chatterbox pada bahasa Indonesia.

Memakai sampel referensi yang sudah ada (models/ref_segs/seg_06.wav).
Output: tmp_ab/piper.wav dan tmp_ab/chatterbox.wav
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.pipeline.backends.openvoice_piper import get_backend  # noqa: E402

TEXT = ("Halo semuanya, hari ini kita akan membahas sesuatu yang menarik. "
        "Sebenarnya, ini cukup mengejutkan bagi banyak orang.")
REF = ROOT / "models" / "ref_segs" / "seg_06.wav"
OUT = ROOT / "tmp_ab"
OUT.mkdir(exist_ok=True)


def run(name: str, text: str) -> None:
    out = OUT / f"{name}.wav"
    backend = get_backend(name)
    if name == "chatterbox":
        # Uji dua preset ekspresi untuk narasi Indonesia.
        from app.pipeline.backends.chatterbox import ChatterboxBackend
        presets = [("netral", 0.4, 0.3)]
        b = ChatterboxBackend(exaggeration=0.4, cfg_weight=0.3)
        b._device = "cpu"
        for label, ex, cfg in presets:
            out = OUT / f"chatterbox_{label}.wav"
            b.exaggeration = ex
            b.cfg_weight = cfg
            t0 = time.time()
            b.synthesize(text, REF, "id", out)
            print(f"chatterbox[{label}] ex={ex} cfg={cfg}: "
                  f"{time.time()-t0:.1f} dtk -> {out}")
        return
    t0 = time.time()
    backend.synthesize(text, REF, "id", out)
    dt = time.time() - t0
    print(f"{name}: selesai dalam {dt:.1f} dtk -> {out}")


if __name__ == "__main__":
    targets = sys.argv[1:] or ["chatterbox"]
    for n in targets:
        run(n, TEXT)
