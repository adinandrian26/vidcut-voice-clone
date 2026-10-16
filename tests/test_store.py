"""Tes antrean JobStore: klaim atomik, satu job hanya dimenangkan satu worker."""
import threading

from app.store import JobStore


def _make_store(tmp_path, name="jobs.db"):
    return JobStore(tmp_path / name)


def test_claim_menandai_downloading_dan_tidak_dobel(tmp_path):
    store = _make_store(tmp_path)
    jid = store.create({"text": "halo"})
    claimed = store.next_queued()
    assert claimed is not None
    assert claimed["id"] == jid
    assert store.get(jid)["status"] == "downloading"
    # Klaim kedua harus kosong: job sudah diambil.
    assert store.next_queued() is None


def test_banyak_thread_tidak_mengklaim_ganda(tmp_path):
    store = _make_store(tmp_path)
    ids = {store.create({"text": f"kalimat {i}"}) for i in range(5)}
    won: list[str] = []
    lock = threading.Lock()

    def worker():
        while True:
            row = store.next_queued()
            if row is None:
                return
            with lock:
                won.append(row["id"])

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert sorted(won) == sorted(ids)
    assert store.next_queued() is None
