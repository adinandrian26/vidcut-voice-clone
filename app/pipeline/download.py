"""Unduh audio YouTube via yt-dlp. Selalu argumen list (anti-injection)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


class DownloadError(RuntimeError):
    pass


def probe_duration(url: str, timeout: int = 60) -> float:
    """Durasi video (detik) tanpa mengunduh. Raise DownloadError bila gagal."""
    cmd = ["yt-dlp", "--no-playlist", "--print", "%(duration)s",
           "--skip-download", url]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        raise DownloadError("yt-dlp belum terpasang.") from e
    except subprocess.TimeoutExpired as e:
        raise DownloadError("Pemeriksaan video timeout.") from e
    if p.returncode != 0:
        raise DownloadError("Video tidak bisa diakses atau dibatasi.")
    try:
        return float((p.stdout or "").strip().splitlines()[0])
    except (ValueError, IndexError) as e:
        raise DownloadError("Durasi video tidak terbaca.") from e


def download_audio(url: str, dest: Path, start: float, duration: float,
                   timeout: int = 600) -> Path:
    """Unduh + potong segmen [start, start+duration]. Return path file."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    end = start + duration
    cmd = [
        "yt-dlp", "--no-playlist",
        "--download-sections", f"*{start:.3f}-{end:.3f}",
        "--force-keyframes-at-cuts",
        "-x", "--audio-format", "wav",
        "-o", str(dest), url,
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        raise DownloadError("yt-dlp belum terpasang.") from e
    except subprocess.TimeoutExpired as e:
        raise DownloadError("Unduhan timeout. Coba durasi lebih pendek.") from e
    if p.returncode != 0 or not dest.exists():
        raise DownloadError("Gagal mengunduh audio YouTube.")
    return dest


def download_info(url: str, timeout: int = 60) -> dict:
    cmd = ["yt-dlp", "--no-playlist", "--skip-download", "--print",
           "%(title)s", url]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    title = (p.stdout or "").strip().splitlines()
    return {"title": title[0] if title else ""}
