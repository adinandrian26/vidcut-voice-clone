"""Validasi input + rate limiting. Tanpa secret apa pun."""
from __future__ import annotations

import re
import time
from collections import defaultdict
from urllib.parse import urlparse

YOUTUBE_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com",
    "youtu.be", "www.youtu.be", "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
PLAYLIST_MARKERS = ("list=", "/playlist", "/ Shorts/".lower())


class ValidationError(ValueError):
    """Error validasi -> HTTP 400 dengan pesan Indonesia."""


def validate_youtube_url(url: str) -> str:
    """Kembalikan URL yang sudah dinormalisasi, atau raise ValidationError."""
    url = (url or "").strip()
    if not url:
        raise ValidationError("Link YouTube tidak boleh kosong.")
    if len(url) > 500:
        raise ValidationError("Link terlalu panjang.")
    try:
        p = urlparse(url if "://" in url else "https://" + url)
    except ValueError:
        raise ValidationError("Format link tidak valid.")
    host = (p.hostname or "").lower()
    if host not in YOUTUBE_HOSTS:
        raise ValidationError("Hanya link YouTube yang diterima.")
    low = url.lower()
    if "list=" in low or "/playlist" in low:
        raise ValidationError("Playlist ditolak. Pakai link satu video saja.")
    if "/shorts/" in low:
        raise ValidationError("Shorts tidak didukung. Pakai video biasa.")
    if host == "youtu.be":
        vid = p.path.strip("/").split("/")[0]
        if not VIDEO_ID_RE.match(vid):
            raise ValidationError("ID video tidak valid.")
        return f"https://youtu.be/{vid}"
    if p.path != "/watch":
        raise ValidationError("Pakai link halaman tonton video (watch).")
    import re as _re
    m = _re.search(r"[?&]v=([A-Za-z0-9_-]{1,64})", url)
    if not m or not VIDEO_ID_RE.match(m.group(1)):
        raise ValidationError("ID video (parameter v=) tidak valid.")
    return url


def validate_text(text: str, max_chars: int) -> str:
    text = (text or "").strip()
    if not text:
        raise ValidationError("Teks tidak boleh kosong.")
    if len(text) > max_chars:
        raise ValidationError(
            f"Teks maksimal {max_chars} karakter (sekarang {len(text)}).")
    return text


def validate_language(lang: str, allowed: list[str]) -> str:
    if lang not in allowed:
        raise ValidationError(f"Bahasa tidak didukung: {lang}.")
    return lang


class RateLimiter:
    """Token-bucket sederhana per IP: N request per 60 detik."""

    def __init__(self, per_minute: int) -> None:
        self.per_minute = max(1, per_minute)
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, ip: str) -> bool:
        now = time.time()
        window = [t for t in self._hits[ip] if now - t < 60]
        self._hits[ip] = window
        if len(window) >= self.per_minute:
            return False
        window.append(now)
        return True


def client_ip(headers: dict, fallback: str) -> str:
    fwd = headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return fallback
