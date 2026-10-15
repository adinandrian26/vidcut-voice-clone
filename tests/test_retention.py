"""Tes retensi: job lama + file dihapus."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import settings
from app.store import JobStore
from app.worker import cleanup_old, job_dir


def test_cleanup(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data")
    monkeypatch.setattr(settings, "retention_hours", -1)  # semua kedaluwarsa
    store = JobStore(tmp_path / "jobs.db")
    jid = store.create({"text": "x"})
    jd = job_dir(jid)
    (jd / "result.wav").write_bytes(b"data")
    time.sleep(0.05)
    n = cleanup_old(store)
    assert n == 1
    assert store.get(jid) is None
    assert not jd.exists()
