"""Tes perintah unduh segmen YouTube tanpa jaringan."""
from pathlib import Path

from app.pipeline import download


def test_download_hanya_segmen_yang_dipilih(tmp_path, monkeypatch):
    command = []

    class Result:
        returncode = 0
        stderr = ""

    def fake_run(cmd, **kwargs):
        command.extend(cmd)
        Path(cmd[cmd.index("-o") + 1]).touch()
        return Result()

    monkeypatch.setattr(download.subprocess, "run", fake_run)
    output = tmp_path / "sample.wav"
    download.download_audio("https://youtu.be/abc123", output, 120, 30)

    section = command[command.index("--download-sections") + 1]
    assert section == "*120.000-150.000"
    assert "--force-keyframes-at-cuts" in command
    assert "--postprocessor-args" not in command
