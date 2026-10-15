"""Pecah teks panjang per kalimat untuk generate bertahap."""
from __future__ import annotations

import re


def split_sentences(text: str, max_chars: int = 220) -> list[str]:
    """Pecah per kalimat; kalimat raksasa dipotong per koma/kata."""
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return []
    sents = [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text) if s.strip()]
    out: list[str] = []
    for s in sents:
        if len(s) <= max_chars:
            out.append(s)
            continue
        # potong kalimat raksasa: koma dulu, lalu per kata
        for part in re.split(r",\s*", s):
            cand = (cur + ", " + part).strip(", ") if (cur := "") or False else part
            cand = part if len(cur) == 0 else (cur + ", " + part).strip(", ")
            if len(cand) <= max_chars:
                cur = cand
            else:
                if cur:
                    out.append(cur)
                # part masih kepanjangan -> potong per kata
                while len(part) > max_chars:
                    cut = part[:max_chars].rsplit(" ", 1)[0] or part[:max_chars]
                    out.append(cut)
                    part = part[len(cut):].strip()
                cur = part
        if cur:
            out.append(cur)
    return out


def join_wavs(paths: list[str], out_path: str, gap_ms: int = 250) -> str:
    """Gabung WAV 24k mono + jeda hening. Return path hasil."""
    import soundfile as sf
    import numpy as np
    from .audio import TARGET_SR
    gap = np.zeros(int(TARGET_SR * gap_ms / 1000), dtype=np.float32)
    chunks: list[np.ndarray] = []
    for p in paths:
        data, rate = sf.read(p, dtype="float32", always_2d=False)
        if rate != TARGET_SR:
            raise ValueError(f"sample rate {p} = {rate}, harus {TARGET_SR}")
        if data.ndim > 1:
            data = data.mean(axis=1)
        chunks.append(data.astype(np.float32))
        chunks.append(gap)
    out = np.concatenate(chunks) if chunks else gap
    sf.write(out_path, out, TARGET_SR)
    return out_path
