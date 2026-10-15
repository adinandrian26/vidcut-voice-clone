"""Skema request/response API."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    youtube_url: Optional[str] = Field(default=None, max_length=500)
    start_seconds: float = Field(default=0, ge=0)
    duration_seconds: float = Field(default=30, ge=5, le=120)
    text: str = Field(min_length=1, max_length=20000)
    language: Literal["id", "en"] = "id"
    consent: bool = False
    # ID suara tersimpan (dari /api/voices): jika diisi, YouTube/upload diabaikan
    voice_id: Optional[str] = Field(default=None, max_length=100)


class JobStatus(BaseModel):
    id: str
    status: str
    progress: int = 0
    stage_detail: str = ""
    error: str = ""
    has_audio: bool = False
    warning: str = ""


class HealthStatus(BaseModel):
    ok: bool = True
    backend: str = ""
    device: str = ""
    queue: str = ""
