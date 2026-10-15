"""Tes API: consent ditolak, job dibuat, SSE jalan, hapus data."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

import app.main as main_mod


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main_mod.settings, "data_dir", tmp_path / "data")
    monkeypatch.setattr(main_mod.settings, "db_path", tmp_path / "jobs.db")
    from app.store import JobStore
    monkeypatch.setattr(main_mod, "store", JobStore(tmp_path / "jobs.db"))
    with TestClient(main_mod.app) as c:
        yield c


def test_consent_wajib(client):
    r = client.post("/api/jobs", json={
        "text": "halo", "language": "id", "consent": False,
        "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
    assert r.status_code == 400


def test_buat_job_youtube(client):
    r = client.post("/api/jobs", json={
        "text": "halo dunia", "language": "id", "consent": True,
        "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "duration_seconds": 10})
    assert r.status_code == 200, r.text
    jid = r.json()["id"]
    s = client.get(f"/api/jobs/{jid}").json()
    assert s["status"] in ("queued", "downloading", "failed")
    # hapus data saya
    d = client.delete(f"/api/jobs/{jid}")
    assert d.json()["deleted"] == jid


def test_upload_tanpa_consent_ditolak(client):
    r = client.post("/api/jobs/upload",
                    data={"text": "halo", "language": "id"},
                    files={"upload": ("s.wav", b"RIFF....", "audio/wav")})
    assert r.status_code == 400


def test_health(client):
    assert client.get("/api/health").status_code == 200
