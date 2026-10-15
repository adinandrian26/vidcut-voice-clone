"""Worker antrean SQLite: ambil job queued satu per satu di thread."""
from __future__ import annotations

import shutil
import threading
import time
import traceback
from pathlib import Path

from .config import settings
from .pipeline.synthesize import run_job
from .store import JobStore


def job_dir(jid: str) -> Path:
    d = settings.data_dir / "jobs" / jid
    d.mkdir(parents=True, exist_ok=True)
    return d


def _work(store: JobStore, stop: threading.Event,
          on_progress=None) -> None:
    from .pipeline.backends.openvoice_piper import get_backend  # noqa
    while not stop.is_set():
        row = store.next_queued()
        if row is None:
            time.sleep(1.0)
            continue
        jid = row["id"]
        import json
        params = json.loads(row["params"]) if isinstance(
            row["params"], str) else row["params"]
        try:
            run_job(
                store, jid, job_dir(jid), params,
                backend_name=settings.voice_backend,
                backend_kwargs={"piper_voice": settings.piper_voice,
                                "device": settings.device,
                                "model_dir": settings.model_dir,
                                "exaggeration": settings.chatterbox_exaggeration,
                                "cfg_weight": settings.chatterbox_cfg_weight,
                                "t3_model": settings.chatterbox_t3_model},
                on_progress=on_progress or (lambda *a: None),
            )
        except Exception as e:  # noqa: BLE001 - simpan pesan ke job
            store.update(jid, status="failed", error=str(e)[:500])
            traceback.print_exc()


def start_worker(store: JobStore) -> threading.Event:
    stop = threading.Event()
    t = threading.Thread(target=_work, args=(store, stop), daemon=True)
    t.start()
    return stop


def cleanup_old(store: JobStore) -> int:
    """Hapus job + file lebih tua dari retention. Return jumlah dihapus."""
    max_age = settings.retention_hours * 3600
    ids = store.old_jobs(max_age)
    n = 0
    for jid in ids:
        shutil.rmtree(job_dir(jid), ignore_errors=True)
        store.delete(jid)
        n += 1
    return n
