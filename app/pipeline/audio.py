"""Util audio via ffmpeg (argumen list) + analisis numpy."""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

TARGET_SR = 24000


class AudioError(RuntimeError):
    pass


def _run(cmd: list[str], timeout: int = 300) -> None:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        raise AudioError("ffmpeg/ffprobe belum terpasang.") from e
    except subprocess.TimeoutExpired as e:
        raise AudioError("Proses audio timeout.") from e
    if p.returncode != 0:
        raise AudioError(f"ffmpeg gagal: {(p.stderr or '')[-300:]}")


def to_wav_mono(src: Path, dest: Path, sr: int = TARGET_SR,
                max_seconds: float | None = None) -> Path:
    """Konversi ke WAV mono 24kHz + normalisasi loudness ringan."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-i", str(src)]
    if max_seconds is not None:
        cmd.extend(["-t", str(max_seconds)])
    cmd.extend(["-ac", "1", "-ar", str(sr),
                "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-c:a", "pcm_s16le", str(dest)])
    _run(cmd)
    return dest


def to_mp3(src_wav: Path, dest: Path) -> Path:
    _run(["ffmpeg", "-y", "-i", str(src_wav), "-c:a", "libmp3lame",
          "-q:a", "4", str(dest)])
    return dest


def probe_seconds(path: Path) -> float:
    try:
        p = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, timeout=60)
    except FileNotFoundError as e:
        raise AudioError("ffprobe belum terpasang.") from e
    try:
        return float((p.stdout or "").strip())
    except ValueError as e:
        raise AudioError("Durasi audio tidak terbaca.") from e


def read_mono(path: Path, sr: int = TARGET_SR) -> np.ndarray:
    """Baca WAV mono 24k sebagai float32 [-1, 1]."""
    import soundfile as sf
    data, rate = sf.read(str(path), dtype="float32", always_2d=False)
    if rate != sr:
        raise AudioError(f"Sample rate {rate}, harus {sr}. Konversi dulu.")
    if data.ndim > 1:
        data = data.mean(axis=1)
    return data.astype(np.float32)


def silence_ratio(x: np.ndarray, frame_ms: int = 50,
                  thresh_db: float = -45.0) -> float:
    """Fraksi frame yang (hampir) hening."""
    n = max(1, int(len(x) * frame_ms / 1000))
    frames = x[: len(x) // n * n].reshape(-1, n)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-12)
    return float((db < thresh_db).mean())


def energy_bursts_per_min(x: np.ndarray, sr: int = TARGET_SR) -> float:
    """Estimasi tempo bicara dari letupan energi (kasar, untuk heuristik)."""
    win = np.ones(max(1, sr // 20)) / max(1, sr // 20)
    env = np.convolve(np.abs(x), win, mode="same")
    thr = env.max() * 0.25
    if thr <= 0:
        return 0.0
    above = env > thr
    bursts = int(np.sum(np.diff(above.astype(np.int8)) == 1))
    minutes = len(x) / sr / 60
    return bursts / minutes if minutes > 0 else 0.0
