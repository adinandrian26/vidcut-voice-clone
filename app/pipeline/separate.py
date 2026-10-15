"""Pemisah vokal dengan Demucs (lazy-load, CPU/GPU otomatis)."""
from __future__ import annotations

from pathlib import Path


class SeparateError(RuntimeError):
    pass


def separate_vocals(src_wav: Path, out_dir: Path, device: str = "auto",
                    model: str = "htdemucs") -> Path:
    """Return path vocals.wav. Raise SeparateError bila gagal."""
    import torch
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        from demucs.separate import main as demucs_main
    except ImportError as e:
        raise SeparateError(
            "Paket demucs belum terpasang (pip install demucs).") from e
    args = ["--two-stems", "vocals", "-n", model, "-d", device,
            "--out", str(out_dir), str(src_wav)]
    try:
        demucs_main(args)
    except SystemExit as e:
        if e.code not in (None, 0):
            raise SeparateError("Demucs gagal memisahkan vokal.") from e
    except Exception as e:
        raise SeparateError(f"Demucs gagal: {e}") from e
    cands = sorted(out_dir.rglob("vocals.wav"))
    if not cands:
        raise SeparateError("File vocals.wav tidak dihasilkan.")
    return cands[0]
