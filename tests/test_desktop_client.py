"""Tes klien desktop: validasi + polling, tanpa server."""
import pytest

from desktop import vc_client


def test_normalize_url():
    assert vc_client.normalize_url("http://localhost:8520/") == \
        "http://localhost:8520"
    with pytest.raises(ValueError):
        vc_client.normalize_url("")
    with pytest.raises(ValueError):
        vc_client.normalize_url("localhost:8520")


def test_headers():
    assert vc_client.headers("") == {}
    assert vc_client.headers("abc") == {"X-API-Key": "abc"}


def test_validate_inputs(tmp_path):
    with pytest.raises(ValueError):
        vc_client.validate_inputs("", True, file_path="x.wav")
    with pytest.raises(ValueError):
        vc_client.validate_inputs("halo", False, file_path="x.wav")
    with pytest.raises(ValueError):
        vc_client.validate_inputs("halo", True,
                                  file_path=str(tmp_path / "tak-ada.wav"))
    bad = tmp_path / "a.txt"
    bad.write_text("x")
    with pytest.raises(ValueError):
        vc_client.validate_inputs("halo", True, file_path=str(bad))
    good = tmp_path / "a.wav"
    good.write_bytes(b"0")
    vc_client.validate_inputs("halo", True, file_path=str(good))
    vc_client.validate_inputs("halo", True,
                              youtube_url="https://www.youtube.com/watch?v=x")
    with pytest.raises(ValueError):
        vc_client.validate_inputs("halo", True)


def test_wait_done_success(monkeypatch):
    calls = {"n": 0}

    def fake_status(base_url, api_key, jid, timeout=30):
        calls["n"] += 1
        if calls["n"] < 2:
            return {"status": "cloning", "progress": 50,
                    "stage_detail": "kerja"}
        return {"status": "done", "progress": 100, "stage_detail": ""}

    seen = []
    monkeypatch.setattr(vc_client, "job_status", fake_status)
    out = vc_client.wait_done("http://x", "", "jid",
                              on_progress=lambda *a: seen.append(a),
                              poll_seconds=0, timeout_seconds=5)
    assert out["status"] == "done"
    assert seen and seen[-1][0] == 100


def test_wait_done_failed(monkeypatch):
    monkeypatch.setattr(
        vc_client, "job_status",
        lambda *a, **k: {"status": "failed", "progress": 55,
                         "error": "rusak"})
    with pytest.raises(vc_client.ApiError, match="rusak"):
        vc_client.wait_done("http://x", "", "jid", poll_seconds=0,
                            timeout_seconds=5)


def test_wait_done_timeout(monkeypatch):
    monkeypatch.setattr(
        vc_client, "job_status",
        lambda *a, **k: {"status": "cloning", "progress": 10,
                         "stage_detail": ""})
    with pytest.raises(vc_client.ApiError, match="Timeout"):
        vc_client.wait_done("http://x", "", "jid", poll_seconds=0,
                            timeout_seconds=0)
