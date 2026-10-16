"""Konfigurasi layanan Voice Clone dari environment / .env.

Tanpa API key. Hanya port, batas, folder, dan pilihan model.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _get(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


@dataclass
class Settings:
    host: str = _get("VC_HOST", "127.0.0.1")
    port: int = _get_int("VC_PORT", 8520)
    data_dir: Path = Path(_get("VC_DATA_DIR", str(ROOT / "data")))
    db_path: Path = Path(_get("VC_DB_PATH", str(ROOT / "data" / "jobs.db")))
    # Batas
    max_text_chars: int = _get_int("VC_MAX_TEXT_CHARS", 20000)
    max_upload_mb: int = _get_int("VC_MAX_UPLOAD_MB", 50)
    max_sample_seconds: int = _get_int("VC_MAX_SAMPLE_SECONDS", 120)
    # Durasi total video tidak dibatasi; yang dibatasi hanya segmen sampelnya.
    sample_seconds: int = _get_int("VC_SAMPLE_SECONDS", 30)
    retention_hours: int = _get_int("VC_RETENTION_HOURS", 24)
    # Rate limit: request per menit per IP
    rate_per_minute: int = _get_int("VC_RATE_PER_MINUTE", 10)
    # Antrean: "sqlite" (default lokal) atau "redis"
    queue_backend: str = _get("VC_QUEUE", "sqlite")
    redis_url: str = _get("VC_REDIS_URL", "redis://localhost:6379/0")
    # Model: "openvoice_piper" (default, MIT, Indonesia) — ganti di sini
    voice_backend: str = _get("VC_BACKEND", "openvoice_piper")
    piper_voice: str = _get("VC_PIPER_VOICE", "id_ID-news_tts-medium")
    device: str = _get("VC_DEVICE", "auto")  # auto | cpu | cuda
    chatterbox_exaggeration: float = _get_float("VC_EXAGGERATION", 0.5)
    chatterbox_cfg_weight: float = _get_float("VC_CFG_WEIGHT", 0.5)
    chatterbox_t3_model: str = _get("VC_T3_MODEL", "v3")
    # Wajibkan header X-API-Key bila nilai ini diisi (disarankan untuk cloud).
    api_key: str = _get("VC_API_KEY", "").strip()
    # CORS: domain website, koma-dipisah. Kosong = tolak semua kecuali same-origin.
    cors_origins: list[str] = field(default_factory=lambda: [
        o.strip() for o in _get("VC_CORS_ORIGINS", "").split(",") if o.strip()
    ])
    # Bahasa yang didukung
    languages: list[str] = field(default_factory=lambda: ["id", "en"])
    # Model AI di folder proyek (bukan data) agar tidak ikut terhapus retensi
    model_dir: Path = Path(_get("VC_MODEL_DIR", str(ROOT / "models")))
    # Suara tersimpan (hasil clone yang di-save sebagai preset)
    voices_dir: Path = Path(_get("VC_VOICES_DIR", str(ROOT / "voices")))


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
