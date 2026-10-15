"""Tes validasi input (tanpa model, tanpa jaringan)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.security import (ValidationError, validate_language, validate_text,
                          validate_youtube_url)


def test_youtube_ok():
    assert validate_youtube_url(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    ).startswith("https://")


def test_youtube_singkat_ok():
    assert validate_youtube_url("https://youtu.be/dQw4w9WgXcQ") == \
        "https://youtu.be/dQw4w9WgXcQ"


def test_playlist_ditolak():
    with pytest.raises(ValidationError):
        validate_youtube_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL123")


def test_shorts_ditolak():
    with pytest.raises(ValidationError):
        validate_youtube_url("https://www.youtube.com/shorts/abc123")


def test_bukan_youtube_ditolak():
    with pytest.raises(ValidationError):
        validate_youtube_url("https://example.com/video")


def test_command_injection_aman():
    # validasi menolak; perintah tak pernah disusun dari string user
    with pytest.raises(ValidationError):
        validate_youtube_url("https://www.youtube.com/watch?v=x; rm -rf /")


def test_teks():
    assert validate_text(" halo ", 10) == "halo"
    with pytest.raises(ValidationError):
        validate_text("   ", 10)
    with pytest.raises(ValidationError):
        validate_text("x" * 11, 10)


def test_bahasa():
    assert validate_language("id", ["id", "en"]) == "id"
    with pytest.raises(ValidationError):
        validate_language("jp", ["id", "en"])
