"""API Voice Clone: job antrean + SSE progres + unduh hasil."""
from __future__ import annotations

import asyncio
import json
import re
import shutil
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from .audit import audit
from .config import settings
from .schemas import HealthStatus, JobCreate, JobStatus
from .security import (RateLimiter, ValidationError, client_ip,
                       validate_language, validate_text, validate_youtube_url)
from .store import JobStore
from .worker import cleanup_old, job_dir, start_worker

app = FastAPI(title="VidCut Voice Clone", version="1.0.0")
store = JobStore(settings.db_path)
limiter = RateLimiter(settings.rate_per_minute)
_worker_stop = start_worker(store)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )


def _rate(request: Request) -> str:
    ip = client_ip(dict(request.headers), request.client.host if request.client else "?")
    if not limiter.check(ip):
        audit("rate_limited", ip=ip)
        raise HTTPException(429, "Terlalu banyak request. Tunggu sebentar.")
    return ip


def _status_dict(jid: str) -> dict:
    row = store.get(jid)
    if row is None:
        raise HTTPException(404, "Job tidak ditemukan.")
    jd = job_dir(jid)
    return {
        "id": jid, "status": row["status"], "progress": row["progress"],
        "stage_detail": row["stage_detail"], "error": row["error"],
        "has_audio": (jd / "result.wav").exists(),
        "warning": row["warning"],
    }


@app.get("/api/health", response_model=HealthStatus)
def health() -> HealthStatus:
    try:
        import torch
        dev = "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        dev = "cpu (torch belum dipasang)"
    return HealthStatus(backend=settings.voice_backend, device=dev,
                        queue=settings.queue_backend)


@app.post("/api/jobs")
async def create_job(request: Request, payload: JobCreate) -> dict:
    """Job dari link YouTube (JSON). Untuk upload file pakai /api/jobs/upload."""
    ip = _rate(request)
    if not payload.consent:
        audit("consent_rejected", ip=ip)
        raise HTTPException(
            400, "Centang persetujuan pemilik suara dulu.")
    try:
        text = validate_text(payload.text, settings.max_text_chars)
        language = validate_language(payload.language, settings.languages)
        voice_id = (re.sub(r"[^\w\-]", "", payload.voice_id or "")
                    if payload.voice_id else None)
        if payload.voice_id and not voice_id:
            raise ValidationError("voice_id tidak valid.")
        if voice_id and not (settings.voices_dir / voice_id /
                             "vocals_24k.wav").exists():
            raise ValidationError(f"Suara tersimpan '{voice_id}' tidak ada.")
        youtube_url = (validate_youtube_url(payload.youtube_url)
                       if payload.youtube_url else None)
    except ValidationError as e:
        raise HTTPException(400, str(e)) from e
    if not youtube_url and not voice_id:
        raise HTTPException(
            400, "Sertakan link YouTube atau pakai /api/jobs/upload.")
    params: dict = {
        "text": text, "language": language,
        "youtube_url": youtube_url,
        "start_seconds": payload.start_seconds,
        "duration_seconds": min(payload.duration_seconds,
                                settings.max_sample_seconds),
    }
    if voice_id:
        params["voice_id"] = voice_id
    jid = store.create(params)
    audit("job_created", job_id=jid, ip=ip)
    return {"id": jid}


@app.post("/api/jobs/upload")
async def create_job_upload(
        request: Request,
        text: str = Form(...),
        language: str = Form("id"),
        consent: bool = Form(False),
        upload: UploadFile = File(...)) -> dict:
    """Job dari file audio (multipart)."""
    ip = _rate(request)
    if not consent:
        audit("consent_rejected", ip=ip)
        raise HTTPException(
            400, "Centang persetujuan pemilik suara dulu.")
    try:
        text = validate_text(text, settings.max_text_chars)
        language = validate_language(language, settings.languages)
    except ValidationError as e:
        raise HTTPException(400, str(e)) from e
    data = await upload.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            400, f"File maksimal {settings.max_upload_mb} MB.")
    if not upload.filename or "." not in upload.filename:
        raise HTTPException(400, "Nama file tidak valid.")
    ext = upload.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("wav", "mp3", "m4a", "ogg", "flac"):
        raise HTTPException(400, "Format file: wav/mp3/m4a/ogg/flac.")
    params: dict = {"text": text, "language": language}
    jid = store.create(params)
    up = job_dir(jid) / f"upload.{ext}"
    up.write_bytes(data)
    params["upload_path"] = str(up)
    import json
    with store._lock, store._conn() as c:
        c.execute("UPDATE jobs SET params = ? WHERE id = ?",
                  (json.dumps(params), jid))
    audit("job_created", job_id=jid, ip=ip)
    return {"id": jid}


@app.get("/api/jobs/{jid}", response_model=JobStatus)
def job_status(jid: str) -> dict:
    return _status_dict(jid)


@app.get("/api/jobs/{jid}/events")
async def job_events(jid: str):
    """SSE: kirim status tiap 1 detik sampai done/failed."""
    async def gen():
        while True:
            try:
                d = _status_dict(jid)
            except HTTPException:
                yield 'event: error\ndata: {"error": "not found"}\n\n'
                return
            import json
            yield f"data: {json.dumps(d)}\n\n"
            if d["status"] in ("done", "failed"):
                return
            await asyncio.sleep(1.0)
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/jobs/{jid}/audio")
def job_audio(jid: str, format: str = "wav"):
    if format not in ("wav", "mp3", "srt"):
        raise HTTPException(400, "Format: wav, mp3, atau srt.")
    f = job_dir(jid) / f"result.{format}"
    if not f.exists():
        raise HTTPException(404, "Hasil belum tersedia.")
    media = {"wav": "audio/wav", "mp3": "audio/mpeg",
             "srt": "application/x-subrip"}[format]
    return FileResponse(str(f), media_type=media,
                        filename=f"voiceclone-{jid}.{format}")


@app.get("/api/jobs/{jid}/sample")
def job_sample(jid: str):
    """Pratinjau sampel vokal yang dipakai."""
    for name in ("sample_clean.wav",):
        f = job_dir(jid) / name
        if f.exists():
            return FileResponse(str(f), media_type="audio/wav",
                                filename=f"sample-{jid}.wav")
    raise HTTPException(404, "Sampel belum tersedia.")


@app.delete("/api/jobs/{jid}")
def job_delete(jid: str, request: Request):
    ip = client_ip(dict(request.headers),
                   request.client.host if request.client else "?")
    row = store.get(jid)
    if row is None:
        raise HTTPException(404, "Job tidak ditemukan.")
    shutil.rmtree(job_dir(jid), ignore_errors=True)
    store.delete(jid)
    audit("job_deleted", job_id=jid, ip=ip)
    return {"deleted": jid}


@app.post("/api/cleanup")
def cleanup() -> dict:
    return {"deleted": cleanup_old(store)}


# ---------- Suara tersimpan (preset hasil clone) ----------

def _slug(nama: str) -> str:
    s = re.sub(r"[^\w\- ]+", "", nama, flags=re.UNICODE).strip()
    s = re.sub(r"[\s\-]+", "_", s)
    return s


@app.get("/api/voices")
def voices_list() -> list[dict]:
    out: list[dict] = []
    if settings.voices_dir.exists():
        for meta_file in sorted(settings.voices_dir.glob("*/meta.json")):
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                out.append({"id": meta_file.parent.name, **meta})
            except Exception:
                continue
    return out


@app.post("/api/jobs/{jid}/save-voice")
def save_voice(jid: str, nama: str = Form(...), request: Request = None):
    """Simpan vokal hasil job sebagai preset suara tersimpan."""
    ip = client_ip(dict(request.headers),
                   request.client.host if request.client else "?")
    row = store.get(jid)
    if row is None:
        raise HTTPException(404, "Job tidak ditemukan.")
    jd = job_dir(jid)
    src = jd / "vocals_24k.wav"
    if not src.exists():
        raise HTTPException(400, "Job ini tidak punya sampel vokal "
                                 "(belum selesai / pakai voice tersimpan).")
    nama_slug = _slug(nama) or f"suara_{int(time.time())}"
    vdir = settings.voices_dir / nama_slug
    if vdir.exists():
        raise HTTPException(400, f"Nama '{nama_slug}' sudah dipakai.")
    vdir.mkdir(parents=True)
    shutil.copy2(src, vdir / "vocals_24k.wav")
    meta = {"nama": nama, "dibuat": time.strftime("%Y-%m-%d %H:%M"),
            "dari_job": jid}
    (vdir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    audit("voice_saved", voice_id=nama_slug, job_id=jid, ip=ip)
    return {"id": nama_slug, "nama": nama}


@app.delete("/api/voices/{vid}")
def voice_delete(vid: str, request: Request):
    ip = client_ip(dict(request.headers),
                   request.client.host if request.client else "?")
    if not re.fullmatch(r"[\w\-]+", vid):
        raise HTTPException(400, "ID tidak valid.")
    vdir = settings.voices_dir / vid
    if not vdir.exists():
        raise HTTPException(404, "Suara tidak ditemukan.")
    shutil.rmtree(vdir, ignore_errors=True)
    audit("voice_deleted", voice_id=vid, ip=ip)
    return {"deleted": vid}
